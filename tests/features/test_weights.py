"""Unit tests for src/features/weights.py"""

from src.data.anonymiser import QUIZ_FIELDS
from src.features.weights import DIMENSION_GROUPS, field_weight, group_for_field


def test_all_quiz_fields_have_a_group():
    """Every quiz field (except the binary gender field) must belong to exactly one group."""
    all_grouped: set[str] = set()
    for group_info in DIMENSION_GROUPS.values():
        all_grouped.update(group_info["fields"])

    # gender is binary — excluded from the vector and from DIMENSION_GROUPS by design
    expected = set(QUIZ_FIELDS) - {"gender"}
    missing = expected - all_grouped
    assert missing == set(), f"Fields not in any dimension group: {missing}"

    # Also check no field appears in more than one group
    seen: set[str] = set()
    duplicates: set[str] = set()
    for group_info in DIMENSION_GROUPS.values():
        for field in group_info["fields"]:
            if field in seen:
                duplicates.add(field)
            seen.add(field)
    assert duplicates == set(), f"Fields in multiple groups: {duplicates}"


def test_field_weight_returns_correct_value():
    assert field_weight("energised_meeting_people") == 1.5
    assert field_weight("humour_style") == 1.0
    assert field_weight("country") == 0.0


def test_group_for_field_returns_correct_group():
    assert group_for_field("country") == "sensitive_fields"
    assert group_for_field("energised_meeting_people") == "social_energy"
    assert group_for_field("gender") is None   # binary, not in any group
    assert group_for_field("__nonexistent__") is None


def test_sensitive_fields_default_weight_zero():
    """Sensitive fields default to weight 0.0 (neutral mode)."""
    assert DIMENSION_GROUPS["sensitive_fields"]["weight"] == 0.0
    for field in DIMENSION_GROUPS["sensitive_fields"]["fields"]:
        assert field_weight(field) == 0.0, f"{field} should have weight 0.0"
