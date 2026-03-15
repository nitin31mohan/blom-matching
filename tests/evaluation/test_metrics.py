"""Tests for proxy metrics layer — AC-1, AC-2, AC-3."""
from __future__ import annotations

import pytest

from src.data.synthetic import generate_event_fixture
from src.evaluation.metrics import compute_event_metrics, compute_group_similarity_stats
from src.features.encoder import build_feature_vector
from src.matching.assignment import Group, GroupAssignment, assign_groups
from src.matching.similarity import AffinityMatrix, build_affinity_matrix, group_cohesion_score


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _build_assignment_and_fvs(n_attendees: int = 8, seed: int = 42):
    """Build a real GroupAssignment + affinity + feature vectors from synthetic data."""
    fix = generate_event_fixture("social", n_attendees, seed=seed)
    quiz_dicts = [a.__dict__ for a in fix.attendees]
    fvs = [
        build_feature_vector(quiz_dicts[i], a.id, fix.event_id, quiz_dicts)
        for i, a in enumerate(fix.attendees)
    ]
    affinity = build_affinity_matrix(fvs)
    fp_ids = {a.id: a.friend_pair_id for a in fix.attendees}
    assignment = assign_groups(affinity, fvs, fp_ids)
    return assignment, affinity, fvs


# ---------------------------------------------------------------------------
# AC-1: Per-group similarity stats computed correctly
# ---------------------------------------------------------------------------


def test_group_similarity_stats_correctness():
    """AC-1: GroupSimilarityStats values are correct and consistent with group_cohesion_score."""
    assignment, affinity, _ = _build_assignment_and_fvs(n_attendees=8, seed=42)

    # Pick first group with >= 3 members
    group = next(g for g in assignment.groups if len(g.user_ids) >= 3)

    stats = compute_group_similarity_stats(group, affinity)

    expected_mean = group_cohesion_score(affinity, list(group.user_ids))

    assert stats.n_members == len(group.user_ids)
    assert stats.mean_pairwise_sim == pytest.approx(expected_mean, rel=1e-4)
    assert stats.std_pairwise_sim >= 0
    assert stats.min_pairwise_sim <= stats.mean_pairwise_sim <= stats.max_pairwise_sim
    assert -1.0 <= stats.min_pairwise_sim
    assert stats.max_pairwise_sim <= 1.0


# ---------------------------------------------------------------------------
# AC-2: Event-level metrics aggregate correctly
# ---------------------------------------------------------------------------


def test_event_metrics_aggregation():
    """AC-2: EventMetrics correctly aggregates cohesion, flag_rate, and group stats."""
    assignment, affinity, _ = _build_assignment_and_fvs(n_attendees=12, seed=99)

    metrics = compute_event_metrics(assignment, affinity)

    expected_mean_cohesion = sum(g.cohesion_score for g in assignment.groups) / len(assignment.groups)
    n_flagged = sum(1 for g in assignment.groups if g.flags)
    expected_flag_rate = n_flagged / len(assignment.groups)

    assert metrics.event_id == assignment.event_id
    assert metrics.n_groups == len(assignment.groups)
    assert metrics.mean_cohesion == pytest.approx(expected_mean_cohesion, rel=1e-4)
    assert metrics.flag_rate == pytest.approx(expected_flag_rate, rel=1e-4)
    assert len(metrics.groups) == metrics.n_groups
    assert metrics.computed_at  # non-empty ISO timestamp


# ---------------------------------------------------------------------------
# AC-3: Single-member group returns zero stats without raising
# ---------------------------------------------------------------------------


def test_single_member_group_returns_zeros():
    """AC-3: A solo group produces all-zero float stats with no exception."""
    assignment, affinity, _ = _build_assignment_and_fvs(n_attendees=8, seed=42)

    solo_group = Group(
        group_id="group-solo",
        user_ids=(affinity.user_ids[0],),
        cohesion_score=0.0,
        fit_color="#22c55e",
        flags=(),
    )

    stats = compute_group_similarity_stats(solo_group, affinity)

    assert stats.n_members == 1
    assert stats.mean_pairwise_sim == 0.0
    assert stats.std_pairwise_sim == 0.0
    assert stats.min_pairwise_sim == 0.0
    assert stats.max_pairwise_sim == 0.0
