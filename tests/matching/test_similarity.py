"""Unit tests for src/matching/similarity.py — Plan 02-01."""

from __future__ import annotations

import numpy as np
import pytest

from src.features.encoder import build_feature_vector
from src.matching.similarity import (
    AffinityMatrix,
    build_affinity_matrix,
    group_cohesion_score,
    group_fit_color,
    marginal_cohesion,
    top_k_similar,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_CFG = {"matching": {"sensitive_field_mode": "neutral"}}

BASE_QUIZ: dict = {
    "gender": "woman",
    "industry": "Technology",
    "country": "GB",
    "energised_meeting_people": 4,
    "keeps_atmosphere_harmonious": 3,
    "enjoys_unfamiliar_experiences": 5,
    "shows_up_on_time": 4,
    "anxious_in_social_situations": 2,
    "interested_in_current_events": 3,
    "religious_identity": "No religion",
    "spirituality_importance": 2,
    "eco_friendly_choices": 4,
    "physical_activity_routine": 3,
    "conversation_style": "deep_diver",
    "messages_regularly_after_clicking": 3,
    "comfortable_knowing_nobody": 4,
    "shares_personal_stories": 3,
    "weekend_energy_level": "High",
    "preferred_activity_time": "Evening",
    "humour_style": "playful",
}

# Polar-opposite profile: Likert fields all at the other end.
_OPPOSING_QUIZ: dict = {
    **BASE_QUIZ,
    "energised_meeting_people": 1,
    "keeps_atmosphere_harmonious": 5,
    "enjoys_unfamiliar_experiences": 1,
    "shows_up_on_time": 5,
    "anxious_in_social_situations": 4,
    "interested_in_current_events": 5,
    "spirituality_importance": 4,
    "eco_friendly_choices": 1,
    "physical_activity_routine": 5,
    "messages_regularly_after_clicking": 5,
    "comfortable_knowing_nobody": 1,
    "shares_personal_stories": 5,
    # Different nominal fields
    "conversation_style": "debater",
    "humour_style": "bold_edgy",
    "weekend_energy_level": "Low",
    "preferred_activity_time": "Morning",
    "industry": "Charity/NGO",
}


def _make_identical_aff(n: int = 5) -> AffinityMatrix:
    """N users with identical quiz → cohesion ≈ 1.0."""
    all_quiz = [BASE_QUIZ] * n
    fvs = [
        build_feature_vector(BASE_QUIZ, f"uid-{i}", "eid-1", all_quiz, config=_CFG)
        for i in range(n)
    ]
    return build_affinity_matrix(fvs)


def _make_opposing_aff() -> AffinityMatrix:
    """2 users with polar-opposite profiles → low cohesion."""
    quizzes = [BASE_QUIZ, _OPPOSING_QUIZ]
    fvs = [
        build_feature_vector(quizzes[i], f"opp-{i}", "eid-2", quizzes, config=_CFG)
        for i in range(2)
    ]
    return build_affinity_matrix(fvs)


def _make_mixed_aff() -> AffinityMatrix:
    """4 users: 2 identical (base), 2 opposing → medium cohesion."""
    quizzes = [BASE_QUIZ, BASE_QUIZ, _OPPOSING_QUIZ, _OPPOSING_QUIZ]
    fvs = [
        build_feature_vector(quizzes[i], f"mix-{i}", "eid-3", quizzes, config=_CFG)
        for i in range(4)
    ]
    return build_affinity_matrix(fvs)


# ---------------------------------------------------------------------------
# AC-1: Matrix symmetry
# ---------------------------------------------------------------------------


def test_matrix_is_symmetric():
    aff = _make_identical_aff(5)
    n = len(aff.user_ids)
    for i in range(n):
        for j in range(n):
            assert aff.matrix[i, j] == pytest.approx(aff.matrix[j, i], abs=1e-6), (
                f"matrix[{i},{j}] != matrix[{j},{i}]"
            )


# ---------------------------------------------------------------------------
# AC-2: Diagonal is 1.0
# ---------------------------------------------------------------------------


def test_matrix_diagonal_is_one():
    aff = _make_identical_aff(5)
    diag = np.diag(aff.matrix)
    assert all(abs(d - 1.0) < 1e-6 for d in diag), f"Diagonal not all 1.0: {diag}"


# ---------------------------------------------------------------------------
# AC-3: Score range [-1, 1]
# ---------------------------------------------------------------------------


def test_matrix_values_in_range():
    aff = _make_mixed_aff()
    assert float(aff.matrix.min()) >= -1.0 - 1e-6
    assert float(aff.matrix.max()) <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# AC-4: Cohesion ordering
# ---------------------------------------------------------------------------


def test_cohesion_ordering():
    aff_identical = _make_identical_aff(4)
    aff_opposing = _make_opposing_aff()
    aff_mixed = _make_mixed_aff()

    c_identical = group_cohesion_score(aff_identical, list(aff_identical.user_ids))
    c_opposing = group_cohesion_score(aff_opposing, list(aff_opposing.user_ids))
    c_mixed = group_cohesion_score(aff_mixed, list(aff_mixed.user_ids))

    assert c_identical > c_mixed, f"Expected identical({c_identical:.4f}) > mixed({c_mixed:.4f})"
    assert c_mixed > c_opposing, f"Expected mixed({c_mixed:.4f}) > opposing({c_opposing:.4f})"


# ---------------------------------------------------------------------------
# AC-5: Marginal cohesion equals mean of individual scores
# ---------------------------------------------------------------------------


def test_marginal_cohesion_equals_mean():
    aff = _make_identical_aff(5)
    candidate_id = "uid-0"
    group_ids = ["uid-1", "uid-2", "uid-3"]

    mc = marginal_cohesion(aff, candidate_id, group_ids)

    # Compute expected: mean of direct matrix lookups
    c_row = aff.user_ids.index(candidate_id)
    expected = np.mean([
        aff.matrix[c_row, aff.user_ids.index(gid)] for gid in group_ids
    ])

    assert mc == pytest.approx(float(expected), rel=1e-4)


# ---------------------------------------------------------------------------
# AC-6: Fit colour thresholds
# ---------------------------------------------------------------------------


def test_group_fit_color_great():
    assert group_fit_color(0.75) == "#22c55e"


def test_group_fit_color_okay():
    assert group_fit_color(0.55) == "#f59e0b"


def test_group_fit_color_poor():
    assert group_fit_color(0.30) == "#ef4444"
