"""Event-type modifiers for the Blom feature engineering pipeline.

Applies post-encoding vector transforms based on event_type.
Must be called after build_feature_vector(), before Phase 02 similarity computation.

Produces new (frozen) UserFeatureVector instances — never mutates inputs.
"""

from __future__ import annotations

import numpy as np

from src.features.encoder import UserFeatureVector, _load_config, get_dimension_index_map
from src.features.weights import DIMENSION_GROUPS


def apply_event_modifiers(
    vectors: list[UserFeatureVector],
    event_type: str,
    user_genders: dict[str, str],
    config: dict | None = None,
) -> list[UserFeatureVector]:
    """Apply event-type weight modifiers and re-normalise vectors.

    For each UserFeatureVector, produces a new frozen instance with:

    **singles events:**
    - Social energy dimensions multiplied by an additional 1.3× (then re-normalised).
    - "gender_imbalance" flag added to all users if the whole event corpus
      is >75% one gender (corpus-level signal for the operator).

    **social events:**
    - Values alignment dimensions multiplied by an additional 1.2× (then re-normalised).

    Parameters
    ----------
    vectors:
        Feature vectors produced by build_feature_vector() for all event users.
    event_type:
        "singles" or "social".
    user_genders:
        {user_id: "man" | "woman" | "unknown"} — needed for gender imbalance check.
    config:
        Explicit config dict for testing. None = load from matching.yaml.
    """
    cfg = config if config is not None else _load_config()
    event_cfg = cfg.get("event_type_modifiers", {}).get(event_type, {})
    dim_map = get_dimension_index_map(cfg)

    # Determine corpus-level gender imbalance (singles events only).
    gender_imbalance = False
    if event_type == "singles" and user_genders:
        total = len(user_genders)
        man_count = sum(1 for g in user_genders.values() if g == "man")
        woman_count = sum(1 for g in user_genders.values() if g == "woman")
        threshold = event_cfg.get("gender_imbalance_threshold", 0.75)
        if total > 0 and max(man_count, woman_count) / total > threshold:
            gender_imbalance = True

    result: list[UserFeatureVector] = []

    for fv in vectors:
        vec = list(fv.vector)
        new_flags = set(fv.flags)

        if event_type == "singles":
            multiplier = event_cfg.get("social_energy_multiplier", 1.3)
            for field in DIMENSION_GROUPS["social_energy"]["fields"]:
                if field in dim_map:
                    for i in dim_map[field]:
                        vec[i] *= multiplier
            if gender_imbalance:
                new_flags.add("gender_imbalance")

        elif event_type == "social":
            multiplier = event_cfg.get("values_alignment_multiplier", 1.2)
            for field in DIMENSION_GROUPS["values_alignment"]["fields"]:
                if field in dim_map:
                    for i in dim_map[field]:
                        vec[i] *= multiplier

        # Re-normalise after reweighting.
        arr = np.array(vec, dtype=float)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm

        result.append(UserFeatureVector(
            user_id=fv.user_id,
            event_id=fv.event_id,
            raw_encoded=fv.raw_encoded,
            vector=tuple(float(x) for x in arr),
            big_five=fv.big_five,
            imputed_fields=fv.imputed_fields,
            flags=tuple(sorted(new_flags)),
        ))

    return result
