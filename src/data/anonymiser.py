"""PII anonymisation module for the Blom matching pipeline.

The pipeline boundary rule
--------------------------
Real PII must be stripped at the point of entry. strip_pii() must be called
immediately when the operator tool receives attendee data from Blom's backend —
before feature engineering, before logging, before any LangGraph call.

GDPR notes
----------
religious_identity and gender are special category data (GDPR Art. 9).
Never log these fields in plain text. See SKILL-pii.md for full logging rules.

Zero external dependencies at module level (stdlib + uuid + pydantic only).
numpy is imported lazily inside export_for_demo() to keep import footprint minimal.
"""

from __future__ import annotations

import re
import secrets
import uuid
from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 21 quiz/demographic fields that travel through the matching pipeline.
# Derived from SKILL-feature-engineering.md input schema + age demographic.
QUIZ_FIELDS: list[str] = [
    "gender",
    "industry",
    "country",
    "energised_meeting_people",
    "keeps_atmosphere_harmonious",
    "enjoys_unfamiliar_experiences",
    "shows_up_on_time",
    "anxious_in_social_situations",
    "interested_in_current_events",
    "religious_identity",
    "spirituality_importance",
    "eco_friendly_choices",
    "physical_activity_routine",
    "conversation_style",
    "messages_regularly_after_clicking",
    "comfortable_knowing_nobody",
    "shares_personal_stories",
    "weekend_energy_level",
    "preferred_activity_time",
    "humour_style",
    "age",  # demographic — not PII, flows through pipeline for age-homogeneity matching
]

# Likert fields that may be perturbed during demo export.
_LIKERT_FIELDS: list[str] = [
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

# Regional country buckets for demo export — preserves plausibility without
# carrying the original country value.
COUNTRY_REGIONS: dict[str, list[str]] = {
    "GB": ["GB", "IE", "FR", "DE", "NL"],
    "IE": ["GB", "IE", "FR", "DE", "NL"],
    "IN": ["IN", "PK", "BD", "LK"],
    "AU": ["AU", "NZ"],
    "US": ["US", "CA"],
    "ZA": ["ZA", "NG", "KE"],
    "FR": ["FR", "BE", "DE", "NL"],
    "DE": ["DE", "AT", "CH", "NL"],
    "CA": ["US", "CA"],
    "NZ": ["AU", "NZ"],
    "NL": ["DE", "BE", "FR", "NL"],
    "IT": ["IT", "ES", "FR"],
    "ES": ["ES", "IT", "FR"],
    "NG": ["NG", "GH", "KE"],
    "KE": ["KE", "NG", "ZA"],
    "PK": ["PK", "IN", "BD"],
    "BD": ["BD", "IN", "PK"],
    "OTHER": ["OTHER"],
}

RELIGIOUS_TAXONOMY: list[str] = [
    "No religion", "Christian", "Muslim", "Hindu", "Jewish", "Buddhist",
    "Sikh", "Spiritual but not religious", "Agnostic", "Atheist", "Other",
]

# Patterns used to detect residual PII in demo exports.
_EMAIL_PATTERN = re.compile(r"@")
_UK_MOBILE_PATTERN = re.compile(r"07\d{9}")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AnonymisedAttendee(BaseModel):
    """Attendee record with PII removed, ready for pipeline processing.

    pipeline_user_id is the only identifier used beyond this point.
    It must never be stored alongside any real Blom user identifier.
    """

    model_config = ConfigDict(frozen=True)

    pipeline_user_id: str   # Fresh UUID4 — never derived from any real identifier
    display_name: str       # First name only — safe for UI display
    quiz_responses: dict    # Exactly 20 quiz fields, values unchanged from raw


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def strip_pii(raw_attendee: dict) -> AnonymisedAttendee:
    """Strip PII from a raw Blom attendee record at the pipeline boundary.

    Must be called before any feature engineering, logging, or LangGraph call.

    Parameters
    ----------
    raw_attendee:
        Dict as received from Blom's backend. May contain name, email, phone,
        and any other fields — all non-quiz fields are silently dropped.

    Returns
    -------
    AnonymisedAttendee with a fresh UUID, first-name-only display_name,
    and exactly 20 quiz response fields.
    """
    # Fresh UUID — never derived from any input identifier.
    pipeline_user_id = str(uuid.uuid4())

    # Extract display name: first token of name field only.
    raw_name = raw_attendee.get("name", "")
    if isinstance(raw_name, str):
        raw_name = raw_name.strip()
    else:
        raw_name = ""

    if raw_name:
        display_name = raw_name.split()[0]
    else:
        # Fallback: "Attendee" + cryptographically random 4-digit suffix.
        suffix = secrets.randbelow(9000) + 1000
        display_name = f"Attendee{suffix}"

    # Extract only the 20 quiz fields — all other keys silently dropped.
    quiz_responses = {field: raw_attendee.get(field, None) for field in QUIZ_FIELDS}

    return AnonymisedAttendee(
        pipeline_user_id=pipeline_user_id,
        display_name=display_name,
        quiz_responses=quiz_responses,
    )


def build_reverse_mapping(
    stripped_list: list[AnonymisedAttendee],
    original_list: list[dict],
) -> dict[str, str]:
    """Build an in-memory mapping from pipeline UUIDs back to Blom user IDs.

    **In-memory only. Never persist or log this dict.**

    Used at session end to write group assignment results back to Blom's DB.
    Discarded when the operator session ends.

    Parameters
    ----------
    stripped_list:  Anonymised attendees produced by strip_pii().
    original_list:  The original raw attendee dicts in the same order.

    Returns
    -------
    {pipeline_user_id: blom_user_id}
    """
    return {
        anonymised.pipeline_user_id: original["id"]
        for anonymised, original in zip(stripped_list, original_list)
    }


def export_for_demo(
    stripped_list: list[AnonymisedAttendee],
    seed: int | None = None,
) -> list[dict]:
    """Produce fully anonymised records for the portfolio demo or public sharing.

    Additional steps beyond strip_pii():
    - display_name replaced with a synthetic name (no connection to real person)
    - Each Likert value perturbed by ±1 with 40% probability (breaks re-identification)
    - country replaced with a randomly sampled country from the same region
    - religious_identity replaced with a randomly sampled value (severs identity link)
    - New UUID assigned (different from pipeline_user_id)

    The output must never be traceable back to any real Blom user.

    Parameters
    ----------
    stripped_list:  Anonymised attendees from strip_pii().
    seed:           RNG seed for reproducibility in tests. None = random.

    Returns
    -------
    list[dict] — each dict has pipeline_user_id, display_name, quiz_responses.
    Caller is responsible for writing to disk.
    """
    import numpy as np  # lazy import — keep module-level footprint clean
    from src.data.name_pools import FIRST_NAMES

    rng = np.random.default_rng(seed)
    results = []

    for attendee in stripped_list:
        # New UUID — must differ from pipeline_user_id.
        demo_uuid = str(uuid.uuid4())

        # Synthetic display name — drawn from diverse name pool.
        name_idx = int(rng.integers(0, len(FIRST_NAMES)))
        demo_name = FIRST_NAMES[name_idx]

        # Copy quiz responses and apply perturbations.
        quiz = dict(attendee.quiz_responses)

        # Likert perturbation: ±1 with 40% probability, clamped to [1, 5].
        for field in _LIKERT_FIELDS:
            value = quiz.get(field)
            if value is not None:
                if rng.random() < 0.40:
                    delta = int(rng.choice([-1, 1]))
                    quiz[field] = int(max(1, min(5, value + delta)))

        # Country substitution: replace with a value from the same region.
        original_country = quiz.get("country")
        if original_country and original_country in COUNTRY_REGIONS:
            region = COUNTRY_REGIONS[original_country]
            idx = int(rng.integers(0, len(region)))
            quiz["country"] = region[idx]

        # Religious identity: always replace — severs identity link.
        rel_idx = int(rng.integers(0, len(RELIGIOUS_TAXONOMY)))
        quiz["religious_identity"] = RELIGIOUS_TAXONOMY[rel_idx]

        results.append({
            "pipeline_user_id": demo_uuid,
            "display_name": demo_name,
            "quiz_responses": quiz,
        })

    return results


def scan_for_pii_patterns(records: list[dict]) -> list[str]:
    """Scan demo export records for residual email or phone patterns.

    Returns a list of violation descriptions. Empty list means clean.
    Used in CI and pre-commit hooks.
    """
    violations = []
    for i, record in enumerate(records):
        text = str(record)
        if _EMAIL_PATTERN.search(text):
            violations.append(f"Record {i}: email pattern (@) found")
        if _UK_MOBILE_PATTERN.search(text):
            violations.append(f"Record {i}: UK mobile pattern (07xxxxxxxxx) found")
    return violations
