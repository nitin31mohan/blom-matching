"""Tests for post-event feedback — AC-4, AC-5, AC-5b, AC-6, AC-6b."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.data.synthetic import generate_event_fixture
from src.evaluation.feedback import (
    AttendeeRating,
    EventFeedback,
    cohesion_satisfaction_correlation,
    group_satisfaction_scores,
    suggest_weight_adjustments,
)
from src.features.encoder import build_feature_vector
from src.matching.assignment import assign_groups
from src.matching.similarity import build_affinity_matrix


# ---------------------------------------------------------------------------
# Shared fixture helper (local copy — no cross-test imports)
# ---------------------------------------------------------------------------


def _build_assignment_and_fvs(n_attendees: int = 8, seed: int = 42):
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
# AC-4: Group satisfaction scores computed correctly
# ---------------------------------------------------------------------------


def test_group_satisfaction_scores():
    feedback = EventFeedback(
        event_id="test-event",
        ratings=[
            AttendeeRating(pipeline_user_id="u1", group_id="group-01", satisfaction=5),
            AttendeeRating(pipeline_user_id="u2", group_id="group-01", satisfaction=4),
            AttendeeRating(pipeline_user_id="u3", group_id="group-02", satisfaction=2),
            AttendeeRating(pipeline_user_id="u4", group_id="group-02", satisfaction=3),
        ],
        collected_at=datetime.now(timezone.utc).isoformat(),
    )

    scores = group_satisfaction_scores(feedback)

    assert scores["group-01"] == pytest.approx(4.5)
    assert scores["group-02"] == pytest.approx(2.5)
    assert len(scores) == 2


# ---------------------------------------------------------------------------
# AC-5: Cohesion-satisfaction correlation — perfect match
# ---------------------------------------------------------------------------


def test_cohesion_satisfaction_correlation_perfect():
    assignment, _, _ = _build_assignment_and_fvs(n_attendees=12, seed=99)

    # Sort groups by cohesion descending; highest cohesion → satisfaction 5, etc.
    sorted_groups = sorted(assignment.groups, key=lambda g: g.cohesion_score, reverse=True)
    n = len(sorted_groups)
    sat_values = list(range(n, 0, -1))  # [n, n-1, ..., 1]

    ratings = [
        AttendeeRating(
            pipeline_user_id=f"u{i}",
            group_id=g.group_id,
            satisfaction=min(max(sat_values[i], 1), 5),
        )
        for i, g in enumerate(sorted_groups)
    ]
    feedback = EventFeedback(
        event_id="test-event",
        ratings=ratings,
        collected_at=datetime.now(timezone.utc).isoformat(),
    )

    result = cohesion_satisfaction_correlation(assignment, feedback)
    assert result == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# AC-5b: Cohesion-satisfaction correlation — inverted
# ---------------------------------------------------------------------------


def test_cohesion_satisfaction_correlation_inverted():
    assignment, _, _ = _build_assignment_and_fvs(n_attendees=12, seed=99)

    # Sort groups by cohesion descending; highest cohesion → satisfaction 1 (inverted)
    sorted_groups = sorted(assignment.groups, key=lambda g: g.cohesion_score, reverse=True)
    n = len(sorted_groups)
    sat_values = list(range(1, n + 1))  # [1, 2, ..., n]

    ratings = [
        AttendeeRating(
            pipeline_user_id=f"u{i}",
            group_id=g.group_id,
            satisfaction=min(max(sat_values[i], 1), 5),
        )
        for i, g in enumerate(sorted_groups)
    ]
    feedback = EventFeedback(
        event_id="test-event",
        ratings=ratings,
        collected_at=datetime.now(timezone.utc).isoformat(),
    )

    result = cohesion_satisfaction_correlation(assignment, feedback)
    assert result == pytest.approx(-1.0, abs=0.01)


# ---------------------------------------------------------------------------
# AC-6: Weight adjustments — low correlation
# ---------------------------------------------------------------------------


def test_suggest_weight_adjustments_low_corr():
    current_weights = {
        "social_energy": 1.5,
        "values_alignment": 1.2,
        "relational_style": 1.0,
    }
    result = suggest_weight_adjustments(current_weights, rank_corr=0.1, delta=0.1)

    assert result["social_energy"] == pytest.approx(1.4)
    assert result["relational_style"] == pytest.approx(1.1)
    assert result["values_alignment"] == pytest.approx(1.2)
    assert all(0.5 <= v <= 2.0 for v in result.values())


# ---------------------------------------------------------------------------
# AC-6b: Weight adjustments — high correlation (no change)
# ---------------------------------------------------------------------------


def test_suggest_weight_adjustments_high_corr():
    current_weights = {
        "social_energy": 1.5,
        "values_alignment": 1.2,
        "relational_style": 1.0,
    }
    result = suggest_weight_adjustments(current_weights, rank_corr=0.7)

    assert result == current_weights
