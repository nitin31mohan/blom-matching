"""Unit tests for src/features/encoder.py"""

import pytest
import numpy as np

from src.features.encoder import (
    UserFeatureVector,
    build_feature_vector,
    LIKERT_FIELDS,
    ORDINAL_ENCODINGS,
    NOMINAL_OPTIONS,
    SENSITIVE_OPTIONS,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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

NEUTRAL_CONFIG = {"matching": {"sensitive_field_mode": "neutral"}}
AFFINITY_CONFIG = {"matching": {"sensitive_field_mode": "affinity"}}


def make_fv(quiz: dict | None = None, config: dict | None = None) -> UserFeatureVector:
    q = quiz or BASE_QUIZ
    cfg = config or NEUTRAL_CONFIG
    return build_feature_vector(q, "uid-1", "eid-1", [q] * 5, config=cfg)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_vector_is_l2_normalised():
    fv = make_fv()
    norm = np.linalg.norm(list(fv.vector))
    assert abs(norm - 1.0) < 1e-6, f"Expected norm≈1.0, got {norm}"


def test_likert_scaling():
    for raw, expected in [(1, 0.0), (5, 1.0), (3, 0.5)]:
        quiz = {**BASE_QUIZ, "energised_meeting_people": raw}
        fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
        assert fv.raw_encoded["energised_meeting_people"] == pytest.approx(expected), (
            f"raw={raw} → expected {expected}, got {fv.raw_encoded['energised_meeting_people']}"
        )


def test_ordinal_scaling():
    for level, expected in [("High", 1.0), ("Low", 0.0), ("Medium", 0.5)]:
        quiz = {**BASE_QUIZ, "weekend_energy_level": level}
        fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
        assert fv.raw_encoded["weekend_energy_level"] == pytest.approx(expected)

    quiz = {**BASE_QUIZ, "preferred_activity_time": "Morning"}
    fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
    assert fv.raw_encoded["preferred_activity_time"] == pytest.approx(0.0)


def test_one_hot_encoding():
    # "Technology" is the first option in NOMINAL_OPTIONS["industry"]
    assert NOMINAL_OPTIONS["industry"][0] == "Technology"
    fv = make_fv()
    one_hot = fv.raw_encoded["industry"]
    assert one_hot[0] == 1.0
    assert all(v == 0.0 for v in one_hot[1:])


def test_high_anxiety_flag():
    quiz = {**BASE_QUIZ, "anxious_in_social_situations": 4}
    fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
    assert "high_anxiety" in fv.flags


def test_high_anxiety_threshold():
    quiz = {**BASE_QUIZ, "anxious_in_social_situations": 3}
    fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
    assert "high_anxiety" not in fv.flags


def test_imputation_fills_missing():
    # 5 event users all have energised_meeting_people=3
    event_users = [{**BASE_QUIZ, "energised_meeting_people": 3}] * 5
    user_quiz = {**BASE_QUIZ, "energised_meeting_people": None}
    fv = build_feature_vector(user_quiz, "u", "e", event_users, config=NEUTRAL_CONFIG)
    # Event median is 3.0, scaled → (3-1)/4 = 0.5
    assert fv.raw_encoded["energised_meeting_people"] == pytest.approx(0.5)


def test_imputation_tracks_field():
    event_users = [{**BASE_QUIZ, "energised_meeting_people": 3}] * 5
    user_quiz = {**BASE_QUIZ, "energised_meeting_people": None}
    fv = build_feature_vector(user_quiz, "u", "e", event_users, config=NEUTRAL_CONFIG)
    assert "energised_meeting_people" in fv.imputed_fields


def test_low_profile_confidence_flag():
    event_users = [BASE_QUIZ] * 5
    user_quiz = {
        **BASE_QUIZ,
        "energised_meeting_people": None,
        "shows_up_on_time": None,
        "eco_friendly_choices": None,
    }
    fv = build_feature_vector(user_quiz, "u", "e", event_users, config=NEUTRAL_CONFIG)
    assert len(fv.imputed_fields) == 3
    assert "low_profile_confidence" in fv.flags


def test_sensitive_neutral_mode():
    fv = make_fv(config=NEUTRAL_CONFIG)
    # 12 Likert + 2 ordinal + 15 industry + 5 conversation + 4 humour = 38 dims
    assert len(fv.vector) == 38


def test_sensitive_affinity_mode():
    fv = make_fv(config=AFFINITY_CONFIG)
    # 38 + 18 country + 11 religious_identity = 67 dims
    assert len(fv.vector) == 67


def test_big_five_extraversion():
    # extraversion = mean(scaled(energised), scaled(comfortable))
    # energised=5 → 1.0, comfortable=1 → 0.0, mean=0.5
    quiz = {**BASE_QUIZ, "energised_meeting_people": 5, "comfortable_knowing_nobody": 1}
    fv = build_feature_vector(quiz, "u", "e", [quiz] * 3, config=NEUTRAL_CONFIG)
    assert fv.big_five["extraversion"] == pytest.approx(0.5)


def test_weight_effect():
    """Higher-weighted field difference → larger cosine distance than equal difference on 1.0× field."""
    # social_energy weight=1.5, relational_style weight=1.0
    ref = {**BASE_QUIZ, "energised_meeting_people": 3, "keeps_atmosphere_harmonious": 3}
    user_a = {**ref, "energised_meeting_people": 5}    # 2-pt diff in 1.5× field
    user_b = {**ref, "keeps_atmosphere_harmonious": 5}  # 2-pt diff in 1.0× field

    event = [ref, user_a, user_b]
    fv_ref = build_feature_vector(ref, "r", "e", event, config=NEUTRAL_CONFIG)
    fv_a = build_feature_vector(user_a, "a", "e", event, config=NEUTRAL_CONFIG)
    fv_b = build_feature_vector(user_b, "b", "e", event, config=NEUTRAL_CONFIG)

    vec_ref = np.array(fv_ref.vector)
    dist_a = 1 - np.dot(vec_ref, np.array(fv_a.vector))
    dist_b = 1 - np.dot(vec_ref, np.array(fv_b.vector))

    assert dist_a > dist_b, (
        f"Social energy field (1.5×) should produce larger cosine distance "
        f"than relational style field (1.0×): dist_a={dist_a:.4f}, dist_b={dist_b:.4f}"
    )


def test_output_is_frozen_model():
    fv = make_fv()
    with pytest.raises(Exception):
        fv.user_id = "new_id"  # type: ignore[misc]
