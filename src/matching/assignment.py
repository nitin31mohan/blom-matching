"""Constrained greedy group assignment for the Blom matching pipeline.

Partitions event attendees into cohesion-maximising groups while honouring
hard constraints: friend pairs co-assigned, group sizes within configured bounds.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from src.features.encoder import UserFeatureVector
from src.matching.constraints import ConstraintError, build_friend_pair_map
from src.matching.similarity import (
    AffinityMatrix,
    group_cohesion_score,
    group_fit_color,
    marginal_cohesion,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load config/matching.yaml. Returns defaults if absent."""
    yaml_path = Path(__file__).parent.parent.parent / "config" / "matching.yaml"
    try:
        import yaml

        with open(yaml_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


_CONFIG: dict = _load_config()

_DEFAULT_ASSIGNMENT = {"group_size_min": 3, "group_size_max": 6, "target_group_size": 5}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Group(BaseModel):
    """A single assigned group with cohesion metrics and flags."""

    model_config = ConfigDict(frozen=True)

    group_id: str                   # e.g. "group-01"
    user_ids: tuple[str, ...]
    cohesion_score: float
    fit_color: str                  # hex colour from group_fit_color()
    flags: tuple[str, ...]          # "high_anxiety_present", "size_warning"


class GroupAssignment(BaseModel):
    """The full group assignment result for one event."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    groups: tuple[Group, ...]
    assigned_at: str                # ISO 8601
    unassigned: tuple[str, ...]     # should be empty in happy path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _assignment_config(config: dict | None) -> dict:
    """Extract assignment sub-config, falling back to defaults."""
    cfg = config if config is not None else _CONFIG
    return {**_DEFAULT_ASSIGNMENT, **cfg.get("assignment", {})}


def _build_group_object(
    group_index: int,
    member_ids: list[str],
    affinity: AffinityMatrix,
    fv_map: dict[str, UserFeatureVector],
    group_size_min: int,
    fit_config: dict | None,
) -> Group:
    """Compute cohesion, colour, and flags for a group of user_ids."""
    cohesion = group_cohesion_score(affinity, member_ids)
    color = group_fit_color(cohesion, config=fit_config)

    flags: list[str] = []
    for uid in member_ids:
        fv = fv_map.get(uid)
        if fv and "high_anxiety" in fv.flags:
            flags.append("high_anxiety_present")
            break  # one flag per group, not per member

    if len(member_ids) < group_size_min:
        flags.append("size_warning")

    return Group(
        group_id=f"group-{group_index + 1:02d}",
        user_ids=tuple(member_ids),
        cohesion_score=cohesion,
        fit_color=color,
        flags=tuple(sorted(set(flags))),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assign_groups(
    affinity: AffinityMatrix,
    feature_vectors: list[UserFeatureVector],
    friend_pair_ids: dict[str, str | None],
    config: dict | None = None,
) -> GroupAssignment:
    """Assign attendees to cohesion-maximising groups with hard constraints.

    Parameters
    ----------
    affinity:
        Pairwise affinity matrix from build_affinity_matrix().
    feature_vectors:
        UserFeatureVector list (same order as affinity.user_ids is not required,
        but every user_id in affinity must have a matching feature vector).
    friend_pair_ids:
        {pipeline_user_id: friend_pair_id_uuid_or_None}. Users sharing the same
        non-None friend_pair_id are guaranteed to be placed in the same group.
    config:
        Pass explicit config dict for testing. None = use module-level _CONFIG.
    """
    acfg = _assignment_config(config)
    group_size_min: int = acfg["group_size_min"]
    group_size_max: int = acfg["group_size_max"]
    target_group_size: int = acfg["target_group_size"]

    user_ids = list(affinity.user_ids)
    N = len(user_ids)

    if len(feature_vectors) != N:
        raise ValueError(
            f"feature_vectors length ({len(feature_vectors)}) != "
            f"affinity user count ({N})"
        )

    fv_map: dict[str, UserFeatureVector] = {fv.user_id: fv for fv in feature_vectors}
    partner_map = build_friend_pair_map(user_ids, friend_pair_ids)

    K = max(1, math.ceil(N / target_group_size))
    groups: list[list[str]] = [[] for _ in range(K)]
    assigned: set[str] = set()

    # ------------------------------------------------------------------
    # Step 1: Pre-assign friend pairs (hard constraint)
    # ------------------------------------------------------------------
    seen_pairs: set[frozenset] = set()
    pair_index = 0

    for uid, partner in partner_map.items():
        pair_key = frozenset({uid, partner})
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        # Round-robin slot, skipping full groups
        target_slot = pair_index % K
        for offset in range(K):
            slot = (target_slot + offset) % K
            if len(groups[slot]) + 2 <= group_size_max:
                groups[slot].extend([uid, partner])
                assigned.update([uid, partner])
                break
        else:
            # All existing groups full — overflow: append new group
            groups.append([uid, partner])
            assigned.update([uid, partner])

        pair_index += 1

    # ------------------------------------------------------------------
    # Step 2: Greedy assignment of remaining users
    # ------------------------------------------------------------------
    unassigned_ids = [uid for uid in user_ids if uid not in assigned]

    # Sort by max affinity score to any other user (most "matchable" first)
    def _max_affinity(uid: str) -> float:
        row = affinity.user_ids.index(uid)
        scores = affinity.matrix[row].copy()
        scores[row] = -2.0  # exclude self
        return float(np.max(scores))

    unassigned_ids.sort(key=_max_affinity, reverse=True)

    # Seed: one user per empty group so all K groups have a positive cohesion
    # baseline before the marginal-cohesion greedy pass. Without this, groups
    # left empty after friend-pair pre-assignment score 0.0 and are never
    # chosen, collapsing K=4 into however many pairs were placed.
    for g in groups:
        if not g and unassigned_ids:
            g.append(unassigned_ids.pop(0))

    for uid in unassigned_ids:
        open_groups = [g for g in groups if len(g) < group_size_max]

        if open_groups:
            # Compute marginal cohesion for each open group
            best_group = max(
                open_groups,
                key=lambda g: (
                    marginal_cohesion(affinity, uid, g) if g else 0.0,
                    -len(g),  # tie-break: least full
                ),
            )
            best_group.append(uid)
        else:
            # Overflow: place in least-full group
            least_full = min(groups, key=len)
            least_full.append(uid)

        assigned.add(uid)

    # ------------------------------------------------------------------
    # Step 3: Build Group objects
    # ------------------------------------------------------------------
    fit_config = config if config is not None else _CONFIG
    built_groups = [
        _build_group_object(i, members, affinity, fv_map, group_size_min, fit_config)
        for i, members in enumerate(groups)
        if members  # skip any empty groups (shouldn't happen, but guard)
    ]

    assigned_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return GroupAssignment(
        event_id=affinity.event_id,
        groups=tuple(built_groups),
        assigned_at=assigned_at,
        unassigned=(),
    )


def apply_override(
    assignment: GroupAssignment,
    affinity: AffinityMatrix,
    feature_vectors: list[UserFeatureVector],
    move_user_id: str,
    from_group_id: str,
    to_group_id: str,
    partner_map: dict[str, str],
    config: dict | None = None,
) -> GroupAssignment:
    """Move one user from one group to another, validating friend-pair constraints.

    Parameters
    ----------
    assignment:
        Current GroupAssignment to modify.
    affinity:
        Affinity matrix (for recomputing cohesion scores).
    feature_vectors:
        All feature vectors (for flag recomputation).
    move_user_id:
        pipeline_user_id of the user to move.
    from_group_id:
        group_id of the group to remove the user from.
    to_group_id:
        group_id of the group to add the user to.
    partner_map:
        {user_id: partner_user_id} — built by build_friend_pair_map().
    config:
        Optional config override.
    """
    # Validate group IDs exist
    group_map = {g.group_id: g for g in assignment.groups}
    if from_group_id not in group_map:
        raise ValueError(f"from_group_id {from_group_id!r} not found in assignment")
    if to_group_id not in group_map:
        raise ValueError(f"to_group_id {to_group_id!r} not found in assignment")

    from_group = group_map[from_group_id]
    if move_user_id not in from_group.user_ids:
        raise ValueError(
            f"move_user_id {move_user_id!r} not in group {from_group_id!r}"
        )

    # Friend-pair constraint check
    if move_user_id in partner_map:
        partner = partner_map[move_user_id]
        if partner in from_group.user_ids:
            raise ConstraintError(
                f"Cannot split friend pair: {move_user_id!r} and partner {partner!r} "
                f"are both in {from_group_id!r}. Move both or neither."
            )

    # Rebuild the two affected groups
    acfg = _assignment_config(config)
    group_size_min: int = acfg["group_size_min"]
    fit_config = config if config is not None else _CONFIG
    fv_map: dict[str, UserFeatureVector] = {fv.user_id: fv for fv in feature_vectors}

    new_from_ids = [uid for uid in from_group.user_ids if uid != move_user_id]
    new_to_ids = list(group_map[to_group_id].user_ids) + [move_user_id]

    new_groups: list[Group] = []

    for g in assignment.groups:
        if g.group_id == from_group_id:
            idx = int(g.group_id.split("-")[1]) - 1
            new_groups.append(
                _build_group_object(idx, new_from_ids, affinity, fv_map, group_size_min, fit_config)
            )
        elif g.group_id == to_group_id:
            idx = int(g.group_id.split("-")[1]) - 1
            new_groups.append(
                _build_group_object(idx, new_to_ids, affinity, fv_map, group_size_min, fit_config)
            )
        else:
            new_groups.append(g)

    return GroupAssignment(
        event_id=assignment.event_id,
        groups=tuple(new_groups),
        assigned_at=assignment.assigned_at,
        unassigned=assignment.unassigned,
    )
