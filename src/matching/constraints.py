"""Constraint utilities for the Blom group assignment pipeline.

Provides friend-pair mapping and size/constraint validation helpers
used by assignment.py before and after group formation.
"""

from __future__ import annotations


class ConstraintError(Exception):
    """Raised when a hard assignment constraint would be violated."""


def build_friend_pair_map(
    user_ids: list[str],
    friend_pair_ids: dict[str, str | None],
) -> dict[str, str]:
    """Return {user_id: partner_user_id} for all users with a shared friend_pair_id.

    Groups user_ids by their friend_pair_id value. If a pair_id appears on exactly
    2 users, both get an entry. If it appears on only 1 (lone/broken pair), skip.

    Parameters
    ----------
    user_ids:
        Ordered list of pipeline_user_ids present in the affinity matrix.
    friend_pair_ids:
        {pipeline_user_id: friend_pair_id_uuid_or_None}
    """
    # Group user_ids by shared friend_pair_id value
    pair_id_to_users: dict[str, list[str]] = {}
    for uid in user_ids:
        pair_id = friend_pair_ids.get(uid)
        if pair_id is not None:
            pair_id_to_users.setdefault(pair_id, []).append(uid)

    partner_map: dict[str, str] = {}
    for pair_id, members in pair_id_to_users.items():
        if len(members) == 2:
            uid_a, uid_b = members
            partner_map[uid_a] = uid_b
            partner_map[uid_b] = uid_a
        # If len != 2 (broken pair), skip — no entry added

    return partner_map


def check_group_sizes(
    groups: list[list[str]],
    min_size: int,
    max_size: int,
) -> list[str]:
    """Return list of size violation descriptions. Empty list = all OK.

    Parameters
    ----------
    groups:
        List of groups, each a list of user_id strings.
    min_size:
        Minimum allowed group size (inclusive).
    max_size:
        Maximum allowed group size (inclusive).
    """
    violations: list[str] = []
    for i, group in enumerate(groups):
        n = len(group)
        if n < min_size:
            violations.append(f"Group {i}: size {n} < min {min_size}")
        elif n > max_size:
            violations.append(f"Group {i}: size {n} > max {max_size}")
    return violations


def validate_friend_pairs(
    groups: list[list[str]],
    partner_map: dict[str, str],
) -> list[str]:
    """Return list of friend-pair constraint violations. Empty list = all OK.

    A violation occurs when two users who are partners end up in different groups.

    Parameters
    ----------
    groups:
        List of groups, each a list of user_id strings.
    partner_map:
        {user_id: partner_user_id} — built by build_friend_pair_map().
    """
    if not partner_map:
        return []

    # Build membership map: {user_id: group_index}
    membership: dict[str, int] = {}
    for i, group in enumerate(groups):
        for uid in group:
            membership[uid] = i

    violations: list[str] = []
    seen_pairs: set[frozenset] = set()

    for uid, partner in partner_map.items():
        pair_key = frozenset({uid, partner})
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        uid_group = membership.get(uid)
        partner_group = membership.get(partner)

        if uid_group is None:
            violations.append(f"User {uid!r} (friend pair) not assigned to any group")
        elif partner_group is None:
            violations.append(f"User {partner!r} (friend pair) not assigned to any group")
        elif uid_group != partner_group:
            violations.append(
                f"Friend pair ({uid!r}, {partner!r}) split: "
                f"group {uid_group} vs group {partner_group}"
            )

    return violations
