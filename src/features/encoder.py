"""Feature engineering encoder for the Blom matching pipeline.

Transforms AnonymisedAttendee quiz responses into a weighted, L2-normalised
feature vector suitable for cosine similarity computation.

Also computes Big Five proxy scores for the LLM explanation layer (Phase 03).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from src.data.anonymiser import QUIZ_FIELDS
from src.features.weights import DIMENSION_GROUPS, field_weight

# ---------------------------------------------------------------------------
# Encoding constants
# ---------------------------------------------------------------------------

#: The 12 integer Likert fields (raw value 1–5, scaled to [0, 1] via (raw-1)/4).
LIKERT_FIELDS: list[str] = [
    "energised_meeting_people",
    "keeps_atmosphere_harmonious",
    "enjoys_unfamiliar_experiences",
    "shows_up_on_time",
    "anxious_in_social_situations",
    "interested_in_current_events",
    "spirituality_importance",
    "eco_friendly_choices",
    "physical_activity_routine",
    "messages_regularly_after_clicking",
    "comfortable_knowing_nobody",
    "shares_personal_stories",
]

#: Ordinal categoricals with a natural rank order — scaled to [0, 1].
ORDINAL_ENCODINGS: dict[str, dict[str, float]] = {
    "weekend_energy_level": {"Low": 0.0, "Medium": 0.5, "High": 1.0},
    "preferred_activity_time": {"Morning": 0.0, "Afternoon": 0.5, "Evening": 1.0},
}

#: Nominal categoricals — one-hot encoded. Order defines vector dimension order.
NOMINAL_OPTIONS: dict[str, list[str]] = {
    "industry": [
        "Technology", "Finance", "Healthcare", "Education", "Creative/Media",
        "Retail", "Legal", "Hospitality", "Construction", "Transport",
        "Public Sector", "Charity/NGO", "Science/Research", "Sports/Fitness", "Other",
    ],
    "conversation_style": ["deep_diver", "light_banter", "storyteller", "listener", "debater"],
    "humour_style": ["playful", "situational_observational", "witty_sarcastic", "bold_edgy"],
}

#: Sensitive categoricals — included only when sensitive_field_mode != "neutral".
SENSITIVE_OPTIONS: dict[str, list[str]] = {
    "country": [
        "GB", "IE", "IN", "AU", "US", "ZA", "FR", "DE", "CA", "NZ",
        "NL", "IT", "ES", "NG", "KE", "PK", "BD", "OTHER",
    ],
    "religious_identity": [
        "No religion", "Christian", "Muslim", "Hindu", "Jewish",
        "Buddhist", "Sikh", "Spiritual but not religious",
        "Agnostic", "Atheist", "Other",
    ],
}

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load config/matching.yaml. Returns neutral defaults if file absent."""
    yaml_path = Path(__file__).parent.parent.parent / "config" / "matching.yaml"
    try:
        import yaml
        with open(yaml_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {"matching": {"sensitive_field_mode": "neutral"}}


# Loaded once at module import; tests pass config= explicitly to override.
_CONFIG: dict = _load_config()

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class UserFeatureVector(BaseModel):
    """Weighted, L2-normalised feature vector for one user in one event."""

    model_config = ConfigDict(frozen=True)

    user_id: str                     # pipeline_user_id from AnonymisedAttendee
    event_id: str
    raw_encoded: dict                # All fields encoded pre-weighting (for inspection)
    vector: tuple[float, ...]        # Weighted, L2-normalised — used for cosine sim
    big_five: dict                   # 5 proxy scores for LLM explanation layer
    imputed_fields: tuple[str, ...]  # Fields filled by event-level median/mode
    flags: tuple[str, ...]           # e.g. "high_anxiety", "low_profile_confidence"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _event_median(field: str, all_users_quiz: list[dict]) -> Any:
    """Compute event-level median (Likert) or mode (categorical) for a field."""
    values = [u.get(field) for u in all_users_quiz if u.get(field) is not None]
    if not values:
        return None

    if field in LIKERT_FIELDS:
        int_vals = sorted(int(v) for v in values)
        n = len(int_vals)
        if n % 2 == 1:
            return float(int_vals[n // 2])
        return (int_vals[n // 2 - 1] + int_vals[n // 2]) / 2.0

    # Categorical: most common non-None value
    return Counter(values).most_common(1)[0][0]


def _safe_encode_likert(val: Any) -> float:
    """Scale a Likert int [1, 5] to [0, 1]. Clamps if out of range."""
    v = float(val) if val is not None else 3.0
    return max(0.0, min(1.0, (v - 1) / 4))


def _encode_quiz(
    user_quiz: dict,
    all_users_quiz: list[dict],
) -> tuple[dict, list[str], list[str]]:
    """Impute missing values, encode all fields. Returns (raw_encoded, imputed_fields, flags)."""
    quiz = dict(user_quiz)
    imputed_fields: list[str] = []
    flags: list[str] = []

    # Check raw anxiety value BEFORE imputation — an imputed value should not trigger the flag.
    raw_anxious = quiz.get("anxious_in_social_situations")
    if raw_anxious is not None and int(raw_anxious) >= 4:
        flags.append("high_anxiety")

    # Impute missing fields using event-level median/mode.
    for field in QUIZ_FIELDS:
        if quiz.get(field) is None:
            median_val = _event_median(field, all_users_quiz)
            if median_val is not None:
                quiz[field] = median_val
                imputed_fields.append(field)

    if len(imputed_fields) >= 3:
        flags.append("low_profile_confidence")

    # --- Encode ---
    raw_encoded: dict[str, Any] = {}

    # Likert (12 fields) → float in [0, 1]
    for field in LIKERT_FIELDS:
        raw_encoded[field] = _safe_encode_likert(quiz.get(field))

    # Ordinal (2 fields) → float in {0.0, 0.5, 1.0}
    for field, mapping in ORDINAL_ENCODINGS.items():
        val = quiz.get(field)
        raw_encoded[field] = mapping.get(val, 0.5)

    # Binary (gender) → stored for reference; NOT used in similarity vector
    raw_encoded["gender"] = 1.0 if quiz.get("gender") == "woman" else 0.0

    # Nominal one-hot (industry, conversation_style, humour_style)
    for field, options in NOMINAL_OPTIONS.items():
        val = quiz.get(field)
        raw_encoded[field] = [1.0 if opt == val else 0.0 for opt in options]

    # Sensitive one-hot — always encoded for inspection; vector inclusion is mode-controlled
    for field, options in SENSITIVE_OPTIONS.items():
        val = quiz.get(field)
        raw_encoded[field] = [1.0 if opt == val else 0.0 for opt in options]

    return raw_encoded, imputed_fields, flags


def _build_weighted_vector(raw_encoded: dict, mode: str) -> list[float]:
    """Assemble weighted vector dimensions from raw_encoded in stable field order."""
    dims: list[float] = []

    # Likert fields (12 scalar dims)
    for field in LIKERT_FIELDS:
        w = field_weight(field)
        dims.append(raw_encoded[field] * w)

    # Ordinal fields (2 scalar dims)
    for field in ORDINAL_ENCODINGS:
        w = field_weight(field)
        dims.append(raw_encoded[field] * w)

    # Nominal one-hot (15 + 5 + 4 = 24 dims)
    for field in NOMINAL_OPTIONS:
        w = field_weight(field)
        dims.extend(v * w for v in raw_encoded[field])

    # Sensitive one-hot — included only when mode != "neutral"
    if mode != "neutral":
        # Weight is 1.0 in affinity/diversity mode (DIMENSION_GROUPS default 0.0 is neutral-only)
        for field in SENSITIVE_OPTIONS:
            dims.extend(v * 1.0 for v in raw_encoded[field])

    return dims


def _compute_big_five(raw_encoded: dict) -> dict[str, float]:
    """Derive Big Five proxy scores from encoded Likert values.

    Stored alongside the vector for the LLM explanation layer (Phase 03).
    NOT included in the similarity vector.
    """
    e = raw_encoded
    return {
        "extraversion": round(
            (e["energised_meeting_people"] + e["comfortable_knowing_nobody"]) / 2, 4
        ),
        # Display as "Emotional stability" in UI = 1 - neuroticism
        "neuroticism": round(e["anxious_in_social_situations"], 4),
        "openness": round(
            (
                e["enjoys_unfamiliar_experiences"]
                + e["interested_in_current_events"]
                + e["eco_friendly_choices"]
            ) / 3,
            4,
        ),
        "conscientiousness": round(e["shows_up_on_time"], 4),
        "agreeableness": round(
            (e["keeps_atmosphere_harmonious"] + e["messages_regularly_after_clicking"]) / 2, 4
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_dimension_index_map(config: dict | None = None) -> dict[str, list[int]]:
    """Return {field_name: [vector_indices]} for each field in the vector.

    Used by modifiers.py to locate group dimensions without guessing positions.
    The index map is mode-aware: sensitive fields are absent in neutral mode.
    """
    cfg = config if config is not None else _CONFIG
    mode = cfg.get("matching", {}).get("sensitive_field_mode", "neutral")

    idx = 0
    result: dict[str, list[int]] = {}

    # Likert fields (1 dim each)
    for field in LIKERT_FIELDS:
        result[field] = [idx]
        idx += 1

    # Ordinal fields (1 dim each)
    for field in ORDINAL_ENCODINGS:
        result[field] = [idx]
        idx += 1

    # Nominal one-hot
    for field, options in NOMINAL_OPTIONS.items():
        result[field] = list(range(idx, idx + len(options)))
        idx += len(options)

    # Sensitive one-hot (only if mode != "neutral")
    if mode != "neutral":
        for field, options in SENSITIVE_OPTIONS.items():
            result[field] = list(range(idx, idx + len(options)))
            idx += len(options)

    return result


def build_feature_vector(
    user_quiz: dict,
    user_id: str,
    event_id: str,
    all_users_quiz: list[dict],
    config: dict | None = None,
) -> UserFeatureVector:
    """Build a weighted, L2-normalised feature vector for one user.

    Parameters
    ----------
    user_quiz:
        The user's quiz_responses dict (20 fields from AnonymisedAttendee).
    user_id:
        The pipeline_user_id from AnonymisedAttendee.
    event_id:
        Identifier for the event (used for grouping).
    all_users_quiz:
        All users' quiz_responses dicts for the same event — used for
        event-level median imputation of missing fields.
    config:
        Pass an explicit config dict for testing. None = use module-level _CONFIG.
    """
    cfg = config if config is not None else _CONFIG
    mode = cfg.get("matching", {}).get("sensitive_field_mode", "neutral")

    raw_encoded, imputed_fields, flags = _encode_quiz(user_quiz, all_users_quiz)

    dims = _build_weighted_vector(raw_encoded, mode)
    arr = np.array(dims, dtype=float)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm

    big_five = _compute_big_five(raw_encoded)

    return UserFeatureVector(
        user_id=user_id,
        event_id=event_id,
        raw_encoded=raw_encoded,
        vector=tuple(float(x) for x in arr),
        big_five=big_five,
        imputed_fields=tuple(imputed_fields),
        flags=tuple(sorted(set(flags))),
    )
