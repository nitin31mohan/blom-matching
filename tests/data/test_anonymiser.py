"""Unit tests for src/data/anonymiser.py.

Covers:
- AC-1: PII stripped at boundary (strip_pii)
- AC-2: Reverse mapping correctness
- AC-3: Demo export untraceability
- AC-4: No PII patterns in demo export
- AC-5: Blank/missing name fallback
"""

import re
import uuid

import pytest

from src.data.anonymiser import (
    QUIZ_FIELDS,
    AnonymisedAttendee,
    build_reverse_mapping,
    export_for_demo,
    scan_for_pii_patterns,
    strip_pii,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_attendee():
    """A fully-populated raw attendee dict as received from Blom's backend."""
    return {
        "id":    "blom-user-abc123",
        "name":  "Alice Smith",
        "email": "alice@example.com",
        "phone": "07712345678",
        "friend_pair_id": "pair-uuid-xyz",
        # 20 quiz fields
        "gender":                          "woman",
        "industry":                        "Technology",
        "country":                         "GB",
        "energised_meeting_people":        4,
        "keeps_atmosphere_harmonious":     3,
        "enjoys_unfamiliar_experiences":   5,
        "shows_up_on_time":                4,
        "anxious_in_social_situations":    2,
        "interested_in_current_events":    3,
        "religious_identity":              "Christian",
        "spirituality_importance":         2,
        "eco_friendly_choices":            4,
        "physical_activity_routine":       3,
        "conversation_style":              "deep_diver",
        "messages_regularly_after_clicking": 3,
        "comfortable_knowing_nobody":      4,
        "shares_personal_stories":         3,
        "weekend_energy_level":            "High",
        "preferred_activity_time":         "Evening",
        "humour_style":                    "playful",
    }


@pytest.fixture
def stripped(raw_attendee):
    return strip_pii(raw_attendee)


# ---------------------------------------------------------------------------
# AC-1: PII stripped at boundary
# ---------------------------------------------------------------------------

def test_strip_pii_removes_name(stripped):
    """name, email, phone must not appear in quiz_responses."""
    assert "name"  not in stripped.quiz_responses
    assert "email" not in stripped.quiz_responses
    assert "phone" not in stripped.quiz_responses


def test_strip_pii_fresh_uuid(raw_attendee, stripped):
    """pipeline_user_id must be a valid UUID and differ from the original id."""
    try:
        uuid.UUID(stripped.pipeline_user_id)
    except ValueError:
        pytest.fail(f"pipeline_user_id is not a valid UUID: {stripped.pipeline_user_id}")
    assert stripped.pipeline_user_id != raw_attendee["id"]


def test_strip_pii_display_name_first_only(stripped):
    """'Alice Smith' → display_name == 'Alice' (no surname)."""
    assert stripped.display_name == "Alice"


def test_strip_pii_all_20_quiz_fields(stripped):
    """quiz_responses must contain exactly the 20 QUIZ_FIELDS keys."""
    assert set(stripped.quiz_responses.keys()) == set(QUIZ_FIELDS)
    assert len(stripped.quiz_responses) == 20


def test_strip_pii_values_unchanged(raw_attendee, stripped):
    """All quiz field values must pass through unmodified."""
    for field in QUIZ_FIELDS:
        expected = raw_attendee.get(field)
        assert stripped.quiz_responses[field] == expected, (
            f"{field}: expected {expected!r}, got {stripped.quiz_responses[field]!r}"
        )


def test_strip_pii_drops_extra_fields(stripped):
    """Non-quiz fields (email, phone, friend_pair_id) must not appear in quiz_responses."""
    for extra in ("email", "phone", "friend_pair_id", "id", "name"):
        assert extra not in stripped.quiz_responses


def test_strip_pii_returns_frozen_model(stripped):
    """AnonymisedAttendee must be immutable (frozen Pydantic model)."""
    with pytest.raises(Exception):
        stripped.display_name = "Hacked"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC-5: Blank/missing name fallback
# ---------------------------------------------------------------------------

def test_strip_pii_blank_name_fallback():
    """Blank name → display_name starts with 'Attendee' + 4-digit suffix."""
    raw = {"id": "x", "name": ""}
    result = strip_pii(raw)
    assert result.display_name.startswith("Attendee")
    suffix = result.display_name[len("Attendee"):]
    assert suffix.isdigit() and len(suffix) == 4


def test_strip_pii_missing_name_fallback():
    """Absent name key → display_name starts with 'Attendee' + 4-digit suffix."""
    raw = {"id": "x"}
    result = strip_pii(raw)
    assert result.display_name.startswith("Attendee")
    suffix = result.display_name[len("Attendee"):]
    assert suffix.isdigit() and len(suffix) == 4


# ---------------------------------------------------------------------------
# AC-2: Reverse mapping correctness
# ---------------------------------------------------------------------------

def test_build_reverse_mapping_length(raw_attendee):
    """10 inputs → 10-entry mapping dict."""
    raws = [{**raw_attendee, "id": f"blom-{i}"} for i in range(10)]
    stripped_list = [strip_pii(r) for r in raws]
    mapping = build_reverse_mapping(stripped_list, raws)
    assert len(mapping) == 10


def test_build_reverse_mapping_correctness(raw_attendee):
    """Each pipeline_user_id maps to the correct original Blom user id."""
    raws = [{**raw_attendee, "id": f"blom-{i}"} for i in range(5)]
    stripped_list = [strip_pii(r) for r in raws]
    mapping = build_reverse_mapping(stripped_list, raws)
    for anonymised, original in zip(stripped_list, raws):
        assert mapping[anonymised.pipeline_user_id] == original["id"]


# ---------------------------------------------------------------------------
# AC-3: Demo export untraceability
# ---------------------------------------------------------------------------

def test_export_for_demo_new_uuid(stripped):
    """pipeline_user_id in demo output must differ from input pipeline_user_id."""
    demo = export_for_demo([stripped], seed=1)[0]
    assert demo["pipeline_user_id"] != stripped.pipeline_user_id


def test_export_for_demo_name_changed(stripped):
    """display_name in demo must differ from the anonymised display_name."""
    # Run enough times to be statistically certain it changes
    changed = any(
        export_for_demo([stripped], seed=s)[0]["display_name"] != stripped.display_name
        for s in range(10)
    )
    assert changed, "display_name never changed across 10 seeds"


def test_export_for_demo_religion_always_replaced(stripped):
    """religious_identity must always be replaced, even if it happens to match."""
    original_religion = stripped.quiz_responses.get("religious_identity")
    # Run with many seeds — the replacement is always a fresh draw
    results = [
        export_for_demo([stripped], seed=s)[0]["quiz_responses"]["religious_identity"]
        for s in range(20)
    ]
    # At least some should differ from the original
    different = sum(1 for r in results if r != original_religion)
    assert different >= 10, (
        f"religious_identity rarely changed: {different}/20 differed from original"
    )


def test_export_for_demo_country_regional(stripped):
    """Exported country must be in the same regional bucket as the original."""
    from src.data.anonymiser import COUNTRY_REGIONS
    original_country = stripped.quiz_responses.get("country")
    if original_country not in COUNTRY_REGIONS:
        pytest.skip(f"country {original_country!r} not in COUNTRY_REGIONS")

    valid_countries = set(COUNTRY_REGIONS[original_country])
    for seed in range(10):
        demo = export_for_demo([stripped], seed=seed)[0]
        exported_country = demo["quiz_responses"]["country"]
        assert exported_country in valid_countries, (
            f"seed={seed}: {exported_country!r} not in region for {original_country!r}"
        )


def test_export_for_demo_different_seeds_differ(stripped):
    """Same input, different seeds → different output UUIDs."""
    demo1 = export_for_demo([stripped], seed=1)[0]
    demo2 = export_for_demo([stripped], seed=99)[0]
    assert demo1["pipeline_user_id"] != demo2["pipeline_user_id"]


# ---------------------------------------------------------------------------
# AC-4: No PII patterns in demo export
# ---------------------------------------------------------------------------

def test_export_for_demo_no_pii_patterns(raw_attendee):
    """Demo export must contain no email (@) or UK mobile (07xxxxxxxxx) patterns."""
    raws = [
        {**raw_attendee, "id": f"blom-{i}", "email": f"user{i}@example.com",
         "phone": f"0771234{i:04d}"}
        for i in range(20)
    ]
    stripped_list = [strip_pii(r) for r in raws]
    demo_records = export_for_demo(stripped_list, seed=42)
    violations = scan_for_pii_patterns(demo_records)
    assert violations == [], f"PII patterns found: {violations}"


# ---------------------------------------------------------------------------
# Likert range preservation
# ---------------------------------------------------------------------------

def test_export_for_demo_likert_range(raw_attendee):
    """All Likert values in demo export must remain in [1, 5]."""
    from src.data.anonymiser import _LIKERT_FIELDS
    raws = [{**raw_attendee, "id": f"blom-{i}"} for i in range(30)]
    stripped_list = [strip_pii(r) for r in raws]
    demo_records = export_for_demo(stripped_list, seed=7)
    for record in demo_records:
        for field in _LIKERT_FIELDS:
            value = record["quiz_responses"].get(field)
            if value is not None:
                assert 1 <= value <= 5, (
                    f"{field}={value} out of [1,5] range in demo export"
                )
