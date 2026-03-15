"""Synthetic attendee data generation for Blom matching system.

Generates realistic fake attendee profiles using a Gaussian copula to
produce correlated Likert responses that reflect real survey distributions.
No real user data is ever touched here.

Entry points
------------
generate_event_fixture(event_type, n_attendees, ...)  -> EventFixture
generate_user(rng)                                    -> RawQuizResponse

CLI
---
python -m src.data.synthetic --event-type social --n 30 --seed 7
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.stats import norm
from pydantic import BaseModel, ConfigDict

from src.data.name_pools import FIRST_NAMES, LAST_NAMES

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RawQuizResponse(BaseModel):
    """Raw attendee record as received from Blom's backend.

    id and name are PII — stripped by anonymiser.strip_pii() at the pipeline
    boundary before any further processing.
    """

    model_config = ConfigDict(frozen=True)

    # --- Metadata (PII — stripped at pipeline boundary) ---
    id: str
    name: str
    friend_pair_id: Optional[str] = None

    # --- Categorical quiz fields ---
    gender: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    religious_identity: Optional[str] = None
    conversation_style: Optional[str] = None
    weekend_energy_level: Optional[str] = None
    preferred_activity_time: Optional[str] = None
    humour_style: Optional[str] = None

    # --- Likert quiz fields (1-5, or None if field was skipped) ---
    energised_meeting_people: Optional[int] = None
    keeps_atmosphere_harmonious: Optional[int] = None
    enjoys_unfamiliar_experiences: Optional[int] = None
    shows_up_on_time: Optional[int] = None
    anxious_in_social_situations: Optional[int] = None
    interested_in_current_events: Optional[int] = None
    spirituality_importance: Optional[int] = None
    eco_friendly_choices: Optional[int] = None
    physical_activity_routine: Optional[int] = None
    messages_regularly_after_clicking: Optional[int] = None
    comfortable_knowing_nobody: Optional[int] = None
    shares_personal_stories: Optional[int] = None


class EventFixture(BaseModel):
    """A synthetic event bundled with its generated attendee list."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    event_name: str
    event_type: str  # "singles" | "social"
    target_group_size: int
    max_groups: int
    attendees: tuple[RawQuizResponse, ...]


# ---------------------------------------------------------------------------
# Distribution tables
# ---------------------------------------------------------------------------

# Order matters -- must match the correlation matrix indices below.
LIKERT_FIELDS: list[str] = [
    "energised_meeting_people",           # 0
    "keeps_atmosphere_harmonious",        # 1
    "enjoys_unfamiliar_experiences",      # 2
    "shows_up_on_time",                   # 3
    "anxious_in_social_situations",       # 4
    "interested_in_current_events",       # 5
    "spirituality_importance",            # 6
    "eco_friendly_choices",               # 7
    "physical_activity_routine",          # 8
    "messages_regularly_after_clicking",  # 9
    "comfortable_knowing_nobody",         # 10
    "shares_personal_stories",            # 11
]

_N_LIKERT = len(LIKERT_FIELDS)
_FIELD_IDX = {f: i for i, f in enumerate(LIKERT_FIELDS)}

# Probability weights for Likert values 1-5 (acquiescence-biased defaults)
_DEFAULT_W = [0.08, 0.14, 0.28, 0.32, 0.18]

LIKERT_WEIGHTS: dict[str, list[float]] = {f: _DEFAULT_W for f in LIKERT_FIELDS}
LIKERT_WEIGHTS.update({
    "anxious_in_social_situations": [0.22, 0.30, 0.26, 0.14, 0.08],
    "comfortable_knowing_nobody":   [0.06, 0.10, 0.22, 0.36, 0.26],
    "shows_up_on_time":             [0.04, 0.08, 0.20, 0.38, 0.30],
})

# Target inter-field correlations (i, j, r) using LIKERT_FIELDS indices.
_TARGET_CORRELATIONS: list[tuple[int, int, float]] = [
    (_FIELD_IDX["energised_meeting_people"],      _FIELD_IDX["comfortable_knowing_nobody"],         0.55),
    (_FIELD_IDX["energised_meeting_people"],      _FIELD_IDX["anxious_in_social_situations"],      -0.50),
    (_FIELD_IDX["enjoys_unfamiliar_experiences"], _FIELD_IDX["interested_in_current_events"],      0.40),
    (_FIELD_IDX["keeps_atmosphere_harmonious"],   _FIELD_IDX["messages_regularly_after_clicking"], 0.35),
    (_FIELD_IDX["eco_friendly_choices"],          _FIELD_IDX["spirituality_importance"],           0.25),
]

# Categorical field options and sampling weights
_GENDER_OPTS = ["man", "woman"]
_GENDER_W    = [0.48, 0.52]

_INDUSTRY_OPTS = [
    "Technology", "Finance", "Healthcare", "Education", "Creative/Media",
    "Retail", "Legal", "Hospitality", "Construction", "Transport",
    "Public Sector", "Charity/NGO", "Science/Research", "Sports/Fitness", "Other",
]
_INDUSTRY_W = [0.18, 0.12, 0.10, 0.09, 0.08] + [0.43 / 10] * 10

_COUNTRY_OPTS = [
    "GB", "IE", "IN", "AU", "US", "ZA", "FR", "DE",
    "CA", "NZ", "NL", "IT", "ES", "NG", "KE", "PK", "BD", "OTHER",
]
_COUNTRY_W = [
    0.45, 0.08, 0.07, 0.06, 0.05, 0.04, 0.04, 0.03,
    0.02, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.06,
]

_RELIGIOUS_OPTS = [
    "No religion", "Christian", "Muslim", "Hindu", "Jewish", "Buddhist",
    "Sikh", "Spiritual but not religious", "Agnostic", "Atheist", "Other",
]
_RELIGIOUS_W = [0.40, 0.25, 0.12, 0.08, 0.03, 0.03, 0.02, 0.02, 0.02, 0.01, 0.02]

_HUMOUR_OPTS = ["playful", "situational_observational", "witty_sarcastic", "bold_edgy"]
_HUMOUR_W    = [0.35, 0.30, 0.25, 0.10]

_CONV_OPTS = ["deep_diver", "light_banter", "storyteller", "listener", "debater"]
_CONV_W    = [0.20, 0.20, 0.20, 0.20, 0.20]

_WEEKEND_OPTS = ["High", "Medium", "Low"]
_WEEKEND_W    = [0.30, 0.45, 0.25]

_ACTIVITY_OPTS = ["Morning", "Afternoon", "Evening"]
_ACTIVITY_W    = [0.20, 0.35, 0.45]

# ---------------------------------------------------------------------------
# Gaussian copula helpers
# ---------------------------------------------------------------------------


def _build_correlation_matrix() -> np.ndarray:
    """Build the 12x12 Likert field correlation matrix from the spec."""
    C = np.eye(_N_LIKERT)
    for i, j, r in _TARGET_CORRELATIONS:
        C[i, j] = r
        C[j, i] = r
    return C


def _nearest_psd(C: np.ndarray) -> np.ndarray:
    """Project a symmetric matrix to the nearest positive semi-definite matrix."""
    eigenvalues, eigenvectors = np.linalg.eigh(C)
    eigenvalues = np.maximum(eigenvalues, 1e-8)
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T


def _uniform_to_likert(u: np.ndarray, weights: list[float]) -> np.ndarray:
    """Map uniform [0,1] values to Likert integers 1-5 using a weight table."""
    cumw = np.cumsum(weights)[:-1]  # 4 boundary thresholds for 5 values
    return np.searchsorted(cumw, u, side="right") + 1


def _generate_correlated_likert(n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Generate n rows of correlated Likert values via Gaussian copula."""
    C = _build_correlation_matrix()
    try:
        L = np.linalg.cholesky(C)
    except np.linalg.LinAlgError:
        C = _nearest_psd(C)
        L = np.linalg.cholesky(C)

    Z = rng.standard_normal((n, _N_LIKERT))
    X = Z @ L.T        # shape (n, 12) -- correlated normals
    U = norm.cdf(X)    # shape (n, 12) -- uniform [0, 1]

    result: dict[str, np.ndarray] = {}
    for j, field in enumerate(LIKERT_FIELDS):
        result[field] = _uniform_to_likert(U[:, j], LIKERT_WEIGHTS[field])
    return result


# ---------------------------------------------------------------------------
# Name generation
# ---------------------------------------------------------------------------


def _generate_names(n: int, rng: np.random.Generator) -> list[tuple[str, str]]:
    """Return n (first_name, last_name) pairs drawn from diverse name pools."""
    first_idx = rng.integers(0, len(FIRST_NAMES), size=n)
    last_idx  = rng.integers(0, len(LAST_NAMES),  size=n)
    return [(FIRST_NAMES[i], LAST_NAMES[j]) for i, j in zip(first_idx, last_idx)]


# ---------------------------------------------------------------------------
# Categorical generation
# ---------------------------------------------------------------------------


def _weighted_choice(rng: np.random.Generator, options: list, weights: list[float]) -> str:
    w = np.array(weights, dtype=float)
    w /= w.sum()
    idx = rng.choice(len(options), p=w)
    return options[idx]


def _generate_categoricals(
    n: int,
    rng: np.random.Generator,
    physical_activity: np.ndarray,
) -> dict[str, list]:
    """Generate categorical field values for n attendees.

    physical_activity is passed in so weekend_energy_level can be
    softly correlated (higher activity -> higher probability of High energy).
    """
    gender   = [_weighted_choice(rng, _GENDER_OPTS,    _GENDER_W)    for _ in range(n)]
    industry = [_weighted_choice(rng, _INDUSTRY_OPTS,  _INDUSTRY_W)  for _ in range(n)]
    country  = [_weighted_choice(rng, _COUNTRY_OPTS,   _COUNTRY_W)   for _ in range(n)]
    religion = [_weighted_choice(rng, _RELIGIOUS_OPTS, _RELIGIOUS_W) for _ in range(n)]
    humour   = [_weighted_choice(rng, _HUMOUR_OPTS,    _HUMOUR_W)    for _ in range(n)]
    conv     = [_weighted_choice(rng, _CONV_OPTS,      _CONV_W)      for _ in range(n)]
    act_time = [_weighted_choice(rng, _ACTIVITY_OPTS,  _ACTIVITY_W)  for _ in range(n)]

    # weekend_energy_level softly correlated with physical_activity_routine
    weekend = []
    for pa in physical_activity:
        if pa >= 4:
            w = [0.50, 0.35, 0.15]
        elif pa <= 2:
            w = [0.15, 0.40, 0.45]
        else:
            w = _WEEKEND_W
        weekend.append(_weighted_choice(rng, _WEEKEND_OPTS, w))

    return {
        "gender":                gender,
        "industry":              industry,
        "country":               country,
        "religious_identity":    religion,
        "humour_style":          humour,
        "conversation_style":    conv,
        "preferred_activity_time": act_time,
        "weekend_energy_level":  weekend,
    }


# ---------------------------------------------------------------------------
# Edge case injection
# ---------------------------------------------------------------------------


def _inject_edge_cases(records: list[dict], rng: np.random.Generator) -> list[dict]:
    """Mutate record dicts in-place to ensure required edge cases are present.

    Counts are proportional to n, with a minimum of 1 per category.
    """
    n = len(records)
    all_indices = list(range(n))
    rng.shuffle(all_indices)
    used: set[int] = set()

    # --- Friend pairs: 2 per 50 users ---
    n_pairs = max(2, (n // 50) * 2)
    pair_indices = all_indices[: n_pairs * 2]
    used.update(pair_indices)
    for k in range(n_pairs):
        shared_id = str(uuid.UUID(int=int(rng.integers(0, 2**63))))
        a, b = pair_indices[k * 2], pair_indices[k * 2 + 1]
        records[a]["friend_pair_id"] = shared_id
        records[b]["friend_pair_id"] = shared_id

    # --- High anxiety outliers: 1 per 30 users ---
    n_anxiety = max(1, n // 30)
    pool = [i for i in all_indices if i not in used]
    anxiety_indices = pool[:n_anxiety]
    used.update(anxiety_indices)
    for i in anxiety_indices:
        records[i]["anxious_in_social_situations"] = 5

    # --- Low profile confidence: 1 per 25 users, 3+ null fields ---
    n_low = max(1, n // 25)
    pool = [i for i in all_indices if i not in used]
    low_indices = pool[:n_low]
    used.update(low_indices)
    nullable_fields = ["industry", "conversation_style", "weekend_energy_level"]
    for i in low_indices:
        for field in nullable_fields:
            records[i][field] = None

    # --- Near-identical twins: 1 pair per 50 users ---
    n_twin_pairs = max(1, n // 50)
    pool = [i for i in all_indices if i not in used]
    for k in range(n_twin_pairs):
        if len(pool) < 2:
            break
        a, b = pool.pop(0), pool.pop(0)
        used |= {a, b}
        for field in LIKERT_FIELDS:
            base = records[a].get(field) or 3
            delta = int(rng.integers(-1, 2))  # -1, 0, or +1
            records[b][field] = int(np.clip(base + delta, 1, 5))

    # --- Polar opposites: 1 pair per 50 users ---
    n_opp_pairs = max(1, n // 50)
    for k in range(n_opp_pairs):
        if len(pool) < 2:
            break
        a, b = pool.pop(0), pool.pop(0)
        used |= {a, b}
        for field in LIKERT_FIELDS:
            base = records[a].get(field) or 3
            records[b][field] = int(np.clip(base - 3 if base >= 3 else base + 3, 1, 5))

    # --- Ungroupable singleton: 1 per 100 users ---
    if n >= 100:
        pool = [i for i in all_indices if i not in used]
        if pool:
            idx = pool[0]
            outlier_fields = LIKERT_FIELDS.copy()
            rng.shuffle(outlier_fields)
            for field in outlier_fields[:4]:
                records[idx][field] = 5 if rng.random() > 0.5 else 1

    return records


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------


def generate_user(rng: np.random.Generator | None = None) -> RawQuizResponse:
    """Generate a single synthetic attendee.

    Uses a fresh unseeded RNG if none provided (non-deterministic).
    """
    if rng is None:
        rng = np.random.default_rng()
    likert = _generate_correlated_likert(1, rng)
    cats = _generate_categoricals(
        1, rng, physical_activity=np.array([likert["physical_activity_routine"][0]])
    )
    first, last = _generate_names(1, rng)[0]
    return RawQuizResponse(
        id=str(uuid.UUID(int=int(rng.integers(0, 2**63)))),
        name=f"{first} {last}",
        **{f: int(likert[f][0]) for f in LIKERT_FIELDS},
        **{k: v[0] for k, v in cats.items()},
    )


def generate_event_fixture(
    event_type: str,
    n_attendees: int,
    target_group_size: int = 5,
    seed: int | None = None,
    edge_cases: bool = True,
) -> EventFixture:
    """Generate a complete synthetic event fixture.

    Parameters
    ----------
    event_type:        "singles" or "social"
    n_attendees:       Number of attendees to generate
    target_group_size: Target group size (used to compute max_groups)
    seed:              RNG seed for reproducibility. None = random.
    edge_cases:        If True, inject required edge-case attendees.

    Returns
    -------
    EventFixture with a deterministic attendee list when seed is set.
    """
    if event_type not in ("singles", "social"):
        raise ValueError(f"event_type must be 'singles' or 'social', got {event_type!r}")

    rng = np.random.default_rng(seed)

    # Generate correlated Likert fields
    likert_arrays = _generate_correlated_likert(n_attendees, rng)

    # Generate categoricals (weekend_energy softly correlated with physical_activity)
    cat_arrays = _generate_categoricals(
        n_attendees, rng, physical_activity=likert_arrays["physical_activity_routine"]
    )

    # Generate names and IDs
    names = _generate_names(n_attendees, rng)
    ids = [str(uuid.UUID(int=int(rng.integers(0, 2**63)))) for _ in range(n_attendees)]

    # Assemble mutable dicts for edge-case injection
    records: list[dict] = []
    for k in range(n_attendees):
        rec: dict = {
            "id":             ids[k],
            "name":           f"{names[k][0]} {names[k][1]}",
            "friend_pair_id": None,
        }
        for field in LIKERT_FIELDS:
            rec[field] = int(likert_arrays[field][k])
        for field, values in cat_arrays.items():
            rec[field] = values[k]
        records.append(rec)

    if edge_cases:
        records = _inject_edge_cases(records, rng)

    attendees = tuple(RawQuizResponse(**r) for r in records)
    max_groups = n_attendees // target_group_size

    event_name_map = {"singles": "Singles mixer", "social": "Social evening"}

    return EventFixture(
        event_id=str(uuid.UUID(int=int(rng.integers(0, 2**63)))),
        event_name=event_name_map[event_type],
        event_type=event_type,
        target_group_size=target_group_size,
        max_groups=max_groups,
        attendees=attendees,
    )


# ---------------------------------------------------------------------------
# Canned fixtures
# ---------------------------------------------------------------------------


def generate_canned_fixtures(output_dir: Path, seed: int = 42) -> None:
    """Write the three standard canned fixtures to output_dir as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ("small_social",   "social",  18, 6),
        ("medium_singles", "singles", 23, 5),
        ("large_social",   "social",  47, 6),
    ]
    for name, event_type, n, group_size in fixtures:
        fixture = generate_event_fixture(
            event_type, n, target_group_size=group_size, seed=seed
        )
        out_path = output_dir / f"{name}_seed{seed}.json"
        with out_path.open("w") as f:
            json.dump(fixture.model_dump(), f, indent=2)
        print(f"Written: {out_path} ({n} attendees)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic Blom event fixtures."
    )
    parser.add_argument("--event-type", required=True, choices=["singles", "social"])
    parser.add_argument("--n", type=int, required=True, help="Number of attendees")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--group-size", type=int, default=5)
    parser.add_argument("--no-edge-cases", action="store_true")
    args = parser.parse_args()

    fixture = generate_event_fixture(
        event_type=args.event_type,
        n_attendees=args.n,
        target_group_size=args.group_size,
        seed=args.seed,
        edge_cases=not args.no_edge_cases,
    )

    out_path = args.output or Path("data/synthetic") / f"custom_{args.event_type}_n{args.n}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(fixture.model_dump(), f, indent=2)
    print(f"Written {len(fixture.attendees)} attendees -> {out_path}")


if __name__ == "__main__":
    _cli()
