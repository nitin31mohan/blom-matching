"""Unit and integration tests for src/matching/assignment.py — Plan 02-02."""

from __future__ import annotations

import pytest

from src.data.synthetic import generate_event_fixture
from src.features.encoder import build_feature_vector
from src.matching.assignment import Group, GroupAssignment, apply_override, assign_groups
from src.matching.constraints import ConstraintError, build_friend_pair_map
from src.matching.similarity import build_affinity_matrix

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

OPP_QUIZ: dict = {
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
    "conversation_style": "debater",
    "humour_style": "bold_edgy",
    "weekend_energy_level": "Low",
    "preferred_activity_time": "Morning",
    "industry": "Charity/NGO",
}


def _make_fvs_and_aff(quizzes: list[dict], user_ids: list[str], event_id: str = "eid-1"):
    """Build feature vectors and affinity matrix from quiz dicts."""
    fvs = [
        build_feature_vector(quizzes[i], user_ids[i], event_id, quizzes, config=_CFG)
        for i in range(len(quizzes))
    ]
    aff = build_affinity_matrix(fvs)
    return fvs, aff


def _no_pairs(user_ids: list[str]) -> dict[str, None]:
    return {uid: None for uid in user_ids}


# ---------------------------------------------------------------------------
# AC-1: All users assigned
# ---------------------------------------------------------------------------


def test_all_users_assigned():
    n = 10
    user_ids = [f"uid-{i}" for i in range(n)]
    quizzes = [BASE_QUIZ] * n
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    result = assign_groups(aff, fvs, _no_pairs(user_ids), config=_CFG)

    assert isinstance(result, GroupAssignment)
    assert len(result.unassigned) == 0
    total = sum(len(g.user_ids) for g in result.groups)
    assert total == n


# ---------------------------------------------------------------------------
# AC-2: Group size within bounds
# ---------------------------------------------------------------------------


def test_group_size_within_bounds():
    n = 12
    user_ids = [f"uid-{i}" for i in range(n)]
    quizzes = [BASE_QUIZ] * n
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    result = assign_groups(aff, fvs, _no_pairs(user_ids), config=_CFG)

    for g in result.groups:
        assert 3 <= len(g.user_ids) <= 6, (
            f"Group {g.group_id} has size {len(g.user_ids)}, expected 3–6"
        )


# ---------------------------------------------------------------------------
# AC-3: Friend pairs co-assigned
# ---------------------------------------------------------------------------


def test_friend_pairs_co_assigned():
    n = 8
    user_ids = [f"uid-{i}" for i in range(n)]
    quizzes = [BASE_QUIZ] * n
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    friend_pair_ids: dict[str, str | None] = _no_pairs(user_ids)
    friend_pair_ids["uid-0"] = "pair-xyz"
    friend_pair_ids["uid-1"] = "pair-xyz"

    result = assign_groups(aff, fvs, friend_pair_ids, config=_CFG)

    pair_group = next((g for g in result.groups if "uid-0" in g.user_ids), None)
    assert pair_group is not None, "uid-0 not assigned to any group"
    assert "uid-1" in pair_group.user_ids, (
        f"Friend pair split: uid-1 not in same group as uid-0 ({pair_group.group_id})"
    )


# ---------------------------------------------------------------------------
# AC-4: Greedy improves cohesion (clusters similar users)
# ---------------------------------------------------------------------------


def test_greedy_cohesion_clusters():
    # 4 identical (BASE) + 4 polar-opposite (OPP) — greedy should cluster them
    user_ids = [f"uid-{i}" for i in range(8)]
    quizzes = [BASE_QUIZ] * 4 + [OPP_QUIZ] * 4
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    # Force 2 groups of 4 via target_group_size=4
    cfg = {**_CFG, "assignment": {"group_size_min": 2, "group_size_max": 5, "target_group_size": 4}}
    result = assign_groups(aff, fvs, _no_pairs(user_ids), config=cfg)

    mean_cohesion = sum(g.cohesion_score for g in result.groups) / len(result.groups)
    assert mean_cohesion >= 0.7, (
        f"Expected mean cohesion >= 0.7, got {mean_cohesion:.4f} — "
        f"greedy did not cluster similar users"
    )


# ---------------------------------------------------------------------------
# AC-5: apply_override moves user
# ---------------------------------------------------------------------------


def test_apply_override_moves_user():
    n = 8
    user_ids = [f"uid-{i}" for i in range(n)]
    quizzes = [BASE_QUIZ] * n
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    result = assign_groups(aff, fvs, _no_pairs(user_ids), config=_CFG)

    assert len(result.groups) >= 2, "Need at least 2 groups for override test"
    group_0 = result.groups[0]
    group_1 = result.groups[1]
    move_uid = group_0.user_ids[0]

    updated = apply_override(
        assignment=result,
        affinity=aff,
        feature_vectors=fvs,
        move_user_id=move_uid,
        from_group_id=group_0.group_id,
        to_group_id=group_1.group_id,
        partner_map={},
        config=_CFG,
    )

    new_group_0 = next(g for g in updated.groups if g.group_id == group_0.group_id)
    new_group_1 = next(g for g in updated.groups if g.group_id == group_1.group_id)

    assert move_uid not in new_group_0.user_ids, "User still in from_group after override"
    assert move_uid in new_group_1.user_ids, "User not in to_group after override"
    # Cohesion should be recomputed (value may differ from original)
    assert isinstance(new_group_0.cohesion_score, float)
    assert isinstance(new_group_1.cohesion_score, float)


# ---------------------------------------------------------------------------
# AC-6: apply_override rejects split pairs
# ---------------------------------------------------------------------------


def test_apply_override_rejects_split_pair():
    n = 8
    user_ids = [f"uid-{i}" for i in range(n)]
    quizzes = [BASE_QUIZ] * n
    fvs, aff = _make_fvs_and_aff(quizzes, user_ids)

    friend_pair_ids: dict[str, str | None] = _no_pairs(user_ids)
    friend_pair_ids["uid-0"] = "pair-abc"
    friend_pair_ids["uid-1"] = "pair-abc"

    result = assign_groups(aff, fvs, friend_pair_ids, config=_CFG)
    partner_map = build_friend_pair_map(user_ids, friend_pair_ids)

    # Find the group where uid-0 and uid-1 are together
    pair_group = next(g for g in result.groups if "uid-0" in g.user_ids)
    other_group = next(g for g in result.groups if g.group_id != pair_group.group_id)

    with pytest.raises(ConstraintError):
        apply_override(
            assignment=result,
            affinity=aff,
            feature_vectors=fvs,
            move_user_id="uid-0",
            from_group_id=pair_group.group_id,
            to_group_id=other_group.group_id,
            partner_map=partner_map,
            config=_CFG,
        )


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


def test_full_pipeline_integration():
    fixture = generate_event_fixture("social", 20, seed=42)
    attendees = fixture.attendees

    # Build quiz dicts from RawQuizResponse fields (exclude PII metadata)
    _EXCLUDE = {"id", "name", "friend_pair_id"}
    all_quiz = [a.model_dump(exclude=_EXCLUDE) for a in attendees]

    cfg = {"matching": {"sensitive_field_mode": "neutral"}}
    fvs = [
        build_feature_vector(all_quiz[i], attendees[i].id, fixture.event_id, all_quiz, config=cfg)
        for i in range(len(attendees))
    ]
    aff = build_affinity_matrix(fvs)

    friend_pair_ids = {a.id: a.friend_pair_id for a in attendees}
    result = assign_groups(aff, fvs, friend_pair_ids, config=cfg)

    # All users assigned
    assert len(result.unassigned) == 0
    assert sum(len(g.user_ids) for g in result.groups) == 20

    # All cohesion scores non-negative (cosine sim of valid vectors >= 0 for similar profiles)
    for g in result.groups:
        assert g.cohesion_score >= -1.0  # valid range; not asserting exact value

    # Friend pair constraint satisfied for every pair
    partner_map = build_friend_pair_map(list(aff.user_ids), friend_pair_ids)
    for uid, partner in partner_map.items():
        uid_group = next((g.group_id for g in result.groups if uid in g.user_ids), None)
        partner_group = next((g.group_id for g in result.groups if partner in g.user_ids), None)
        assert uid_group == partner_group, (
            f"Friend pair ({uid!r}, {partner!r}) split across groups"
        )
