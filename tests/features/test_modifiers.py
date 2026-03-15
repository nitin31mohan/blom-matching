"""Unit tests for src/features/modifiers.py"""

import numpy as np

from src.features.encoder import UserFeatureVector, build_feature_vector
from src.features.modifiers import apply_event_modifiers

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

NEUTRAL_CONFIG = {
    "matching": {"sensitive_field_mode": "neutral"},
    "event_type_modifiers": {
        "singles": {"social_energy_multiplier": 1.3, "gender_imbalance_threshold": 0.75},
        "social": {"values_alignment_multiplier": 1.2},
    },
}


def make_vectors(n: int = 3, quiz: dict | None = None) -> list[UserFeatureVector]:
    q = quiz or BASE_QUIZ
    event = [q] * n
    return [
        build_feature_vector(q, f"uid-{i}", "eid-1", event, config=NEUTRAL_CONFIG)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_singles_modifier_reweights_social_energy():
    """apply_event_modifiers('singles') changes the vector by boosting social energy dims."""
    vectors = make_vectors()
    genders = {fv.user_id: "woman" for fv in vectors}
    modified = apply_event_modifiers(vectors, "singles", genders, config=NEUTRAL_CONFIG)

    # Vectors must change (social energy dims got an extra 1.3× boost)
    for orig, mod in zip(vectors, modified):
        assert orig.vector != mod.vector


def test_social_modifier_reweights_values():
    """apply_event_modifiers('social') changes the vector by boosting values alignment dims."""
    vectors = make_vectors()
    genders = {fv.user_id: "woman" for fv in vectors}
    modified = apply_event_modifiers(vectors, "social", genders, config=NEUTRAL_CONFIG)

    for orig, mod in zip(vectors, modified):
        assert orig.vector != mod.vector


def test_modifiers_preserve_normalisation():
    """Vectors remain L2-normalised after applying either event modifier."""
    vectors = make_vectors()
    genders = {fv.user_id: "woman" for fv in vectors}

    for event_type in ("singles", "social"):
        modified = apply_event_modifiers(vectors, event_type, genders, config=NEUTRAL_CONFIG)
        for fv in modified:
            norm = np.linalg.norm(list(fv.vector))
            assert abs(norm - 1.0) < 1e-6, f"norm={norm:.8f} for {event_type}"


def test_gender_imbalance_flag_singles():
    """Corpus >75% one gender → 'gender_imbalance' flag on all users in a singles event."""
    # 4 women, 1 man = 80% women → exceeds 75% threshold
    vectors = make_vectors(5)
    genders = {
        vectors[0].user_id: "woman",
        vectors[1].user_id: "woman",
        vectors[2].user_id: "woman",
        vectors[3].user_id: "woman",
        vectors[4].user_id: "man",
    }
    modified = apply_event_modifiers(vectors, "singles", genders, config=NEUTRAL_CONFIG)
    for fv in modified:
        assert "gender_imbalance" in fv.flags


def test_no_gender_imbalance_flag_social():
    """Social events never emit 'gender_imbalance' regardless of gender distribution."""
    vectors = make_vectors(5)
    genders = {
        vectors[0].user_id: "woman",
        vectors[1].user_id: "woman",
        vectors[2].user_id: "woman",
        vectors[3].user_id: "woman",
        vectors[4].user_id: "man",
    }
    modified = apply_event_modifiers(vectors, "social", genders, config=NEUTRAL_CONFIG)
    for fv in modified:
        assert "gender_imbalance" not in fv.flags
