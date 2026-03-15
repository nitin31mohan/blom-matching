"""Pairwise affinity matrix and similarity query functions for the Blom matching pipeline.

All vectors are assumed to be L2-normalised (as produced by encoder.py),
so cosine similarity reduces to a plain dot product.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from src.features.encoder import UserFeatureVector

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load fit_thresholds from config/matching.yaml. Returns defaults if absent."""
    yaml_path = Path(__file__).parent.parent.parent / "config" / "matching.yaml"
    try:
        import yaml

        with open(yaml_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


_CONFIG: dict = _load_config()

_DEFAULT_THRESHOLDS = {"great": 0.68, "okay": 0.42}

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class AffinityMatrix(BaseModel):
    """Pairwise cosine similarity matrix for all attendees in one event."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    event_id: str
    user_ids: tuple[str, ...]   # pipeline_user_ids; index maps to matrix row/col
    matrix: np.ndarray          # shape (N, N), dtype float32
    computed_at: str            # ISO 8601


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_affinity_matrix(feature_vectors: list[UserFeatureVector]) -> AffinityMatrix:
    """Build a pairwise affinity matrix from a list of UserFeatureVectors.

    Vectors must all belong to the same event. They are already L2-normalised
    by the encoder, so cosine similarity = dot product.
    """
    if not feature_vectors:
        raise ValueError("feature_vectors must not be empty")

    user_ids = tuple(fv.user_id for fv in feature_vectors)
    event_id = feature_vectors[0].event_id

    # Stack into (N, dim) float32 array
    vecs = np.array([fv.vector for fv in feature_vectors], dtype=np.float32)

    # Cosine sim = dot product (vectors already L2-normalised)
    matrix = (vecs @ vecs.T).astype(np.float32)

    # Guard against float32 drift outside [-1, 1]
    matrix = np.clip(matrix, -1.0, 1.0)

    computed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return AffinityMatrix(
        event_id=event_id,
        user_ids=user_ids,
        matrix=matrix,
        computed_at=computed_at,
    )


def top_k_similar(
    affinity: AffinityMatrix, user_id: str, k: int = 5
) -> list[tuple[str, float]]:
    """Return the top-k most similar users to user_id (excluding self).

    Returns a list of (user_id, score) pairs sorted by score descending.
    Raises ValueError if user_id is not in the affinity matrix.
    """
    if user_id not in affinity.user_ids:
        raise ValueError(f"user_id {user_id!r} not found in affinity matrix")

    idx = affinity.user_ids.index(user_id)
    row = affinity.matrix[idx].copy()
    row[idx] = -2.0  # zero out self-similarity (below any valid score)

    top_indices = np.argsort(row)[::-1][:k]
    return [(affinity.user_ids[i], float(row[i])) for i in top_indices]


def group_cohesion_score(
    affinity: AffinityMatrix, group_user_ids: list[str]
) -> float:
    """Mean pairwise similarity for all off-diagonal pairs in the group.

    Returns 0.0 if the group has fewer than 2 members.
    """
    if len(group_user_ids) < 2:
        return 0.0

    indices = [affinity.user_ids.index(uid) for uid in group_user_ids]
    sub = affinity.matrix[np.ix_(indices, indices)]

    n = len(indices)
    # Sum off-diagonal entries and divide by number of off-diagonal pairs
    total = float(sub.sum()) - float(np.trace(sub))
    num_pairs = n * (n - 1)
    return total / num_pairs


def group_fit_color(cohesion: float, config: dict | None = None) -> str:
    """Map a cohesion score to a hex colour string.

    Thresholds (from config/matching.yaml or defaults):
      great >= 0.68  →  "#22c55e"
      okay  >= 0.42  →  "#f59e0b"
      poor  <  0.42  →  "#ef4444"
    """
    cfg = config if config is not None else _CONFIG
    thresholds = cfg.get("fit_thresholds", _DEFAULT_THRESHOLDS)
    great = thresholds.get("great", _DEFAULT_THRESHOLDS["great"])
    okay = thresholds.get("okay", _DEFAULT_THRESHOLDS["okay"])

    if cohesion >= great:
        return "#22c55e"
    if cohesion >= okay:
        return "#f59e0b"
    return "#ef4444"


def marginal_cohesion(
    affinity: AffinityMatrix, candidate_id: str, group_user_ids: list[str]
) -> float:
    """Mean similarity between candidate_id and each member of group_user_ids.

    Returns 0.0 if group_user_ids is empty.
    Raises ValueError if candidate_id is not in the affinity matrix.
    """
    if candidate_id not in affinity.user_ids:
        raise ValueError(f"candidate_id {candidate_id!r} not found in affinity matrix")

    if not group_user_ids:
        return 0.0

    candidate_row = affinity.user_ids.index(candidate_id)
    group_cols = [affinity.user_ids.index(uid) for uid in group_user_ids]
    scores = affinity.matrix[candidate_row, group_cols]
    return float(np.mean(scores))
