"""Weight configuration for the Blom feature engineering pipeline.

DIMENSION_GROUPS defines the dimension groups and their default weight multipliers.
Weights are applied as scalar multipliers on each dimension group before the
similarity vector is L2-normalised.

This module has zero external dependencies — plain Python dicts only.
The encoder (encoder.py) is responsible for loading matching.yaml and applying
runtime overrides (e.g. sensitive field mode).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Dimension groups
# ---------------------------------------------------------------------------

#: Each group has:
#:   "fields": list[str]  — quiz field names belonging to this group
#:   "weight": float      — default multiplier applied before L2-normalisation
DIMENSION_GROUPS: dict[str, dict] = {
    "social_energy": {
        "fields": [
            "energised_meeting_people",
            "anxious_in_social_situations",
            "comfortable_knowing_nobody",
            "shares_personal_stories",
        ],
        "weight": 1.5,
    },
    "values_alignment": {
        "fields": [
            "interested_in_current_events",
            "spirituality_importance",
            "eco_friendly_choices",
            "enjoys_unfamiliar_experiences",
        ],
        "weight": 1.2,
    },
    "activity_compatibility": {
        "fields": [
            "physical_activity_routine",
            "weekend_energy_level",
            "preferred_activity_time",
        ],
        "weight": 1.2,
    },
    "relational_style": {
        "fields": [
            "keeps_atmosphere_harmonious",
            "shows_up_on_time",
            "messages_regularly_after_clicking",
        ],
        "weight": 1.0,
    },
    "humour_style": {
        "fields": ["humour_style"],
        "weight": 1.0,
    },
    "conversation_style": {
        "fields": ["conversation_style"],
        "weight": 1.0,
    },
    "industry": {
        "fields": ["industry"],
        "weight": 1.0,
    },
    "sensitive_fields": {
        # Default weight is 0.0 (neutral mode). Encoder overrides to 1.0
        # when sensitive_field_mode is "affinity" or "diversity".
        "fields": ["country", "religious_identity"],
        "weight": 0.0,
    },
}

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

# Build a reverse map {field: group_name} at module load time.
_FIELD_TO_GROUP: dict[str, str] = {
    field: group_name
    for group_name, group_info in DIMENSION_GROUPS.items()
    for field in group_info["fields"]
}


def field_weight(field: str) -> float:
    """Return the default weight multiplier for a given quiz field name.

    Returns 1.0 for any field not found in DIMENSION_GROUPS (safe fallback).
    """
    group_name = _FIELD_TO_GROUP.get(field)
    if group_name is None:
        return 1.0
    return DIMENSION_GROUPS[group_name]["weight"]


def group_for_field(field: str) -> str | None:
    """Return the group name for a given quiz field, or None if not assigned."""
    return _FIELD_TO_GROUP.get(field)
