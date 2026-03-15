"""Unit tests for src/data/synthetic.py.

Covers:
- Determinism (same seed → identical output)
- Count correctness
- Field range validity
- No self-references in friend_pair_id
- Symmetric friend pairs
- Schema validation against quiz_response.json
- Large corpus (500 attendees)
- Distribution plausibility for key fields
- Edge case presence (anxiety outlier, low-profile, friend pairs)
- CLI entry point
- Remainder user (n not divisible by group size)
"""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from src.data.synthetic import (
    LIKERT_FIELDS,
    EventFixture,
    RawQuizResponse,
    generate_event_fixture,
    generate_user,
)

SCHEMA_PATH = Path("data/schemas/quiz_response.json")

@pytest.fixture(scope="module")
def quiz_schema():
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture(scope="module")
def fixture_50():
    return generate_event_fixture("social", 50, seed=42)


@pytest.fixture(scope="module")
def fixture_500():
    return generate_event_fixture("social", 500, seed=1)


# ---------------------------------------------------------------------------
# AC-2: Determinism
# ---------------------------------------------------------------------------

def test_deterministic_small():
    """Same seed produces identical fixtures."""
    a = generate_event_fixture("social", 50, seed=42)
    b = generate_event_fixture("social", 50, seed=42)
    assert a == b, "generate_event_fixture is not deterministic with the same seed"


def test_deterministic_singles():
    """Determinism holds for singles event type."""
    a = generate_event_fixture("singles", 23, seed=99)
    b = generate_event_fixture("singles", 23, seed=99)
    assert a == b


def test_different_seeds_differ():
    """Different seeds produce different outputs."""
    a = generate_event_fixture("social", 20, seed=1)
    b = generate_event_fixture("social", 20, seed=2)
    assert a != b, "Different seeds produced identical results (extremely unlikely)"


# ---------------------------------------------------------------------------
# AC-5: Count correctness and scale
# ---------------------------------------------------------------------------

def test_count_exact(fixture_50):
    assert len(fixture_50.attendees) == 50


def test_count_large(fixture_500):
    assert len(fixture_500.attendees) == 500


def test_large_corpus_no_error():
    """generate_event_fixture(500) completes without error."""
    f = generate_event_fixture("singles", 500, seed=1)
    assert isinstance(f, EventFixture)
    assert len(f.attendees) == 500


# ---------------------------------------------------------------------------
# AC-3: Field range validity
# ---------------------------------------------------------------------------

def test_likert_range(fixture_500):
    """All Likert values are in [1, 5] (or None for skipped fields)."""
    for attendee in fixture_500.attendees:
        for field in LIKERT_FIELDS:
            value = getattr(attendee, field)
            if value is not None:
                assert 1 <= value <= 5, (
                    f"Attendee {attendee.id}: {field}={value} out of range [1,5]"
                )


def test_gender_values(fixture_500):
    genders = {a.gender for a in fixture_500.attendees if a.gender}
    assert genders.issubset({"man", "woman"})


def test_humour_style_values(fixture_500):
    valid = {"playful", "situational_observational", "witty_sarcastic", "bold_edgy", None}
    for a in fixture_500.attendees:
        assert a.humour_style in valid


def test_weekend_energy_values(fixture_500):
    valid = {"High", "Medium", "Low", None}
    for a in fixture_500.attendees:
        assert a.weekend_energy_level in valid


def test_preferred_activity_time_values(fixture_500):
    valid = {"Morning", "Afternoon", "Evening", None}
    for a in fixture_500.attendees:
        assert a.preferred_activity_time in valid


# ---------------------------------------------------------------------------
# AC-4: No self-references
# ---------------------------------------------------------------------------

def test_no_self_reference(fixture_500):
    """No attendee has their own ID as a friend_pair_id."""
    for attendee in fixture_500.attendees:
        if attendee.friend_pair_id:
            # friend_pair_id is a shared UUID, not a user ID — just check
            # that it's not literally their own ID
            assert attendee.friend_pair_id != attendee.id, (
                f"Attendee {attendee.id} has self-referential friend_pair_id"
            )


# ---------------------------------------------------------------------------
# AC-4: Symmetric friend pairs
# ---------------------------------------------------------------------------

def test_symmetric_friend_pairs(fixture_500):
    """Every friend_pair_id is shared by exactly 2 attendees."""
    pairs: dict[str, list[str]] = defaultdict(list)
    for a in fixture_500.attendees:
        if a.friend_pair_id:
            pairs[a.friend_pair_id].append(a.id)

    assert len(pairs) >= 1, "No friend pairs found in 500-attendee fixture"
    for pair_id, members in pairs.items():
        assert len(members) == 2, (
            f"friend_pair_id {pair_id} has {len(members)} members, expected 2"
        )


# ---------------------------------------------------------------------------
# AC-1: JSON Schema validation
# ---------------------------------------------------------------------------

def test_schema_validation(quiz_schema, fixture_50):
    """First 5 attendees validate against quiz_response.json."""
    for attendee in fixture_50.attendees[:5]:
        doc = attendee.model_dump()
        jsonschema.validate(instance=doc, schema=quiz_schema)


# ---------------------------------------------------------------------------
# Edge case presence
# ---------------------------------------------------------------------------

def test_high_anxiety_outlier_present(fixture_50):
    """At least 1 attendee per 30 has anxious_in_social_situations == 5."""
    n = len(fixture_50.attendees)
    expected_min = max(1, n // 30)
    count = sum(
        1 for a in fixture_50.attendees
        if a.anxious_in_social_situations == 5
    )
    assert count >= expected_min, (
        f"Expected >= {expected_min} high-anxiety outliers, found {count}"
    )


def test_friend_pairs_present(fixture_50):
    """At least 2 friend pairs present in a 50-attendee fixture."""
    pairs = {
        a.friend_pair_id for a in fixture_50.attendees if a.friend_pair_id
    }
    assert len(pairs) >= 2, (
        f"Expected >= 2 friend pairs in 50-attendee fixture, found {len(pairs)}"
    )


def test_low_profile_confidence_present(fixture_50):
    """At least 1 attendee has 3+ null quiz fields (low profile confidence)."""
    def null_field_count(a: RawQuizResponse) -> int:
        quiz_fields = [
            "gender", "industry", "country", "religious_identity",
            "conversation_style", "weekend_energy_level", "preferred_activity_time",
            "humour_style", *LIKERT_FIELDS,
        ]
        return sum(1 for f in quiz_fields if getattr(a, f) is None)

    low_confidence = [a for a in fixture_50.attendees if null_field_count(a) >= 3]
    assert len(low_confidence) >= 1, "No low-profile-confidence attendees found"


# ---------------------------------------------------------------------------
# Distribution plausibility
# ---------------------------------------------------------------------------

def test_anxious_distribution_plausibility(fixture_500):
    """Values 1+2 account for >40% of anxious_in_social_situations responses."""
    values = [
        a.anxious_in_social_situations for a in fixture_500.attendees
        if a.anxious_in_social_situations is not None
    ]
    low_anxiety = sum(1 for v in values if v <= 2)
    fraction = low_anxiety / len(values)
    assert fraction > 0.40, (
        f"Expected >40% low-anxiety responses, got {fraction:.1%}"
    )


def test_shows_up_on_time_skews_high(fixture_500):
    """shows_up_on_time should have >50% of responses at 4 or 5."""
    values = [
        a.shows_up_on_time for a in fixture_500.attendees
        if a.shows_up_on_time is not None
    ]
    high = sum(1 for v in values if v >= 4)
    fraction = high / len(values)
    assert fraction > 0.50, (
        f"Expected >50% of shows_up_on_time >= 4, got {fraction:.1%}"
    )


def test_comfortable_knowing_nobody_skews_high(fixture_500):
    """comfortable_knowing_nobody should have >50% at 4 or 5."""
    values = [
        a.comfortable_knowing_nobody for a in fixture_500.attendees
        if a.comfortable_knowing_nobody is not None
    ]
    high = sum(1 for v in values if v >= 4)
    fraction = high / len(values)
    assert fraction > 0.50, (
        f"Expected >50% comfortable_knowing_nobody >= 4, got {fraction:.1%}"
    )


def test_likert_correlation_energised_vs_anxious(fixture_500):
    """energised_meeting_people and anxious_in_social_situations are negatively correlated."""
    energised = np.array([
        a.energised_meeting_people for a in fixture_500.attendees
        if a.energised_meeting_people is not None and a.anxious_in_social_situations is not None
    ], dtype=float)
    anxious = np.array([
        a.anxious_in_social_situations for a in fixture_500.attendees
        if a.energised_meeting_people is not None and a.anxious_in_social_situations is not None
    ], dtype=float)
    r = float(np.corrcoef(energised, anxious)[0, 1])
    assert -0.70 <= r <= -0.25, (
        f"Expected energised/anxious correlation in [-0.70, -0.25], got {r:.3f}"
    )


# ---------------------------------------------------------------------------
# AC-5: Remainder user (n not divisible by group size)
# ---------------------------------------------------------------------------

def test_remainder_user():
    """medium_singles fixture (23 attendees) does not divide evenly by group size 5."""
    f = generate_event_fixture("singles", 23, target_group_size=5, seed=42)
    assert len(f.attendees) == 23
    assert 23 % 5 != 0, "Test premise wrong: 23 is divisible by 5"


# ---------------------------------------------------------------------------
# generate_user smoke test
# ---------------------------------------------------------------------------

def test_generate_user_returns_valid_record():
    user = generate_user(rng=np.random.default_rng(7))
    assert isinstance(user, RawQuizResponse)
    assert user.id
    assert user.name


# ---------------------------------------------------------------------------
# AC-6: CLI entry point
# ---------------------------------------------------------------------------

def test_cli_entry_point(tmp_path):
    """CLI writes a valid JSON file with the correct number of attendees."""
    out = tmp_path / "cli_test.json"
    result = subprocess.run(
        [
            sys.executable, "-m", "src.data.synthetic",
            "--event-type", "singles",
            "--n", "15",
            "--seed", "1",
            "--output", str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert out.exists(), "CLI did not create output file"
    data = json.loads(out.read_text())
    assert len(data["attendees"]) == 15
