"""Proxy metrics for the Blom evaluation layer.

Computes per-group pairwise similarity distributions and event-level aggregates
(mean cohesion, flag rate) from a GroupAssignment + AffinityMatrix.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from pydantic import BaseModel

from src.matching.assignment import Group, GroupAssignment
from src.matching.similarity import AffinityMatrix


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GroupSimilarityStats(BaseModel):
    group_id: str
    n_members: int
    mean_pairwise_sim: float
    std_pairwise_sim: float
    min_pairwise_sim: float
    max_pairwise_sim: float


class EventMetrics(BaseModel):
    event_id: str
    n_groups: int
    mean_cohesion: float
    flag_rate: float        # fraction of groups with any flags
    groups: list[GroupSimilarityStats]
    computed_at: str        # ISO 8601


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_group_similarity_stats(
    group: Group,
    affinity: AffinityMatrix,
) -> GroupSimilarityStats:
    """Compute pairwise similarity distribution stats for one group.

    Returns zero stats if the group has fewer than 2 members.
    """
    n = len(group.user_ids)

    if n < 2:
        return GroupSimilarityStats(
            group_id=group.group_id,
            n_members=n,
            mean_pairwise_sim=0.0,
            std_pairwise_sim=0.0,
            min_pairwise_sim=0.0,
            max_pairwise_sim=0.0,
        )

    indices = [affinity.user_ids.index(uid) for uid in group.user_ids]
    sub = affinity.matrix[np.ix_(indices, indices)]
    pairs = sub[np.triu_indices(n, k=1)]

    return GroupSimilarityStats(
        group_id=group.group_id,
        n_members=n,
        mean_pairwise_sim=float(np.mean(pairs)),
        std_pairwise_sim=float(np.std(pairs)),
        min_pairwise_sim=float(np.min(pairs)),
        max_pairwise_sim=float(np.max(pairs)),
    )


def compute_event_metrics(
    assignment: GroupAssignment,
    affinity: AffinityMatrix,
) -> EventMetrics:
    """Compute event-level proxy metrics across all groups."""
    group_stats = [compute_group_similarity_stats(g, affinity) for g in assignment.groups]
    mean_cohesion = float(np.mean([g.cohesion_score for g in assignment.groups]))
    n_flagged = sum(1 for g in assignment.groups if g.flags)
    flag_rate = n_flagged / len(assignment.groups)
    computed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return EventMetrics(
        event_id=assignment.event_id,
        n_groups=len(assignment.groups),
        mean_cohesion=mean_cohesion,
        flag_rate=flag_rate,
        groups=group_stats,
        computed_at=computed_at,
    )
