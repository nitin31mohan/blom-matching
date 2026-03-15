---
phase: 01-foundation
plan: 03
subsystem: features
tags: [feature-engineering, encoder, weights, modifiers, pydantic, numpy, yaml, big-five]

requires:
  - phase: 01-01
    provides: RawQuizResponse model and QUIZ_FIELDS field list
  - phase: 01-02
    provides: AnonymisedAttendee model and QUIZ_FIELDS canonical constant

provides:
  - UserFeatureVector Pydantic model (user_id, event_id, raw_encoded, vector, big_five, imputed_fields, flags)
  - build_feature_vector(user_quiz, user_id, event_id, all_users_quiz, config) -> UserFeatureVector
  - get_dimension_index_map(config) -> dict[str, list[int]]
  - DIMENSION_GROUPS config dict with 8 weight groups
  - field_weight(field) -> float and group_for_field(field) -> str | None helpers
  - apply_event_modifiers(vectors, event_type, user_genders, config) -> list[UserFeatureVector]
  - config/matching.yaml (sensitive_field_mode, event_type_modifiers)

affects: [02-core-algorithm, 03-agent-layer, 05-frontend-demo]

tech-stack:
  added: [pyyaml>=6.0]
  patterns:
    - config/matching.yaml loaded at encoder module import time; tests override via config= param
    - DIMENSION_GROUPS in weights.py is the single source of truth for field weights
    - get_dimension_index_map() derives vector positions from DIMENSION_GROUPS field order — no magic constants
    - Sensitive fields always encoded in raw_encoded (for inspection); excluded from vector in neutral mode
    - high_anxiety flag checked against raw value BEFORE imputation — imputed anxiety never triggers flag
    - apply_event_modifiers() returns new frozen UserFeatureVector instances; never mutates input

key-files:
  created:
    - config/matching.yaml
    - src/features/weights.py
    - src/features/encoder.py
    - src/features/modifiers.py
    - tests/features/test_weights.py
    - tests/features/test_encoder.py
    - tests/features/test_modifiers.py
  modified:
    - src/features/__init__.py
    - pyproject.toml (added pyyaml>=6.0)

key-decisions:
  - "enjoys_unfamiliar_experiences added to values_alignment group (Openness proxy — natural fit)"
  - "Sensitive fields excluded from vector in neutral mode (vector length changes by mode: 38 neutral, 67 affinity)"
  - "high_anxiety flag uses raw value before imputation — avoids false positives from median-filled data"
  - "get_dimension_index_map() is mode-aware — modifiers import it to locate group indices without hardcoding"
  - "Sensitive field weight in affinity/diversity mode = 1.0 (DIMENSION_GROUPS default 0.0 is neutral-only)"

patterns-established:
  - "build_feature_vector() is the only public entry point — all encoding, imputation, weighting, normalisation inside"
  - "All tests pass config= explicitly — no test depends on config/matching.yaml file state"
  - "apply_event_modifiers() called after build_feature_vector(), before Phase 02 similarity computation"

duration: ~25min
started: 2026-03-15T01:00:00Z
completed: 2026-03-15T01:25:00Z
---

# Phase 01 Plan 03: Feature Engineering Pipeline — Summary

**Weighted, L2-normalised feature vectors from 20-field quiz responses: 12 Likert min-max, 2 ordinal rank-scaled, 3 nominal one-hot, 2 sensitive mode-controlled — with Big Five proxies, event-level median imputation, and event-type modifiers. 23 tests passing.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~25 min |
| Completed | 2026-03-15 |
| Tasks | 3 of 3 complete |
| Tests | 23 new (65 total, 0 regressions) |
| Files created | 7 |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Encoding correctness | Pass | 12 Likert (raw-1)/4, 2 ordinal rank-scaled, 3 nominal one-hot; vector L2-norm ≈ 1.0 |
| AC-2: Weight application | Pass | Social energy 1.5× vs relational style 1.0× produces measurably larger cosine distance for equal raw difference |
| AC-3: Missing data imputation | Pass | None fields → event-level median/mode; imputed_fields tracks names; ≥3 → low_profile_confidence |
| AC-4: Sensitive field config | Pass | neutral: 38-dim vector (country/religion excluded); affinity: 67-dim vector (included) |
| AC-5: Event-type modifier — singles gender flag | Pass | >75% one gender in corpus → gender_imbalance on all users; social events unaffected |
| AC-6: High anxiety flag | Pass | raw anxious_in_social_situations ≥ 4 → "high_anxiety" in flags (checked before imputation) |

**Skill AC cross-reference (SKILL-feature-engineering.md):**

| Skill AC | Status | Notes |
|----------|--------|-------|
| AC-1: Encoding correctness | Pass | All encoding rules followed exactly |
| AC-2: Weight application | Pass | DIMENSION_GROUPS weights applied as scalar multipliers |
| AC-3: Missing data imputation | Pass | Event-level median for Likert; mode for categoricals |
| AC-4: Sensitive field config | Pass | Three-mode switch: neutral/affinity/diversity |
| AC-5: Event-type modifier | Pass | Corpus-level gender check; per-group flagging deferred to Phase 02 |

## Accomplishments

- Feature vector pipeline producing 38-dim (neutral) or 67-dim (affinity) L2-normalised vectors ready for Phase 02 cosine similarity
- `get_dimension_index_map()` derives vector positions from the same field-order used in encoding — modifiers never hardcode indices
- Big Five proxies (extraversion, neuroticism, openness, conscientiousness, agreeableness) computed from Likert values and stored alongside vector for Phase 03 LLM layer
- Event-level median imputation handles missing quiz fields without global population averages

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `config/matching.yaml` | Created | Runtime config: sensitive_field_mode, event_type_modifiers |
| `src/features/weights.py` | Created | DIMENSION_GROUPS (8 groups), field_weight(), group_for_field() |
| `src/features/encoder.py` | Created | UserFeatureVector model, build_feature_vector(), get_dimension_index_map() |
| `src/features/modifiers.py` | Created | apply_event_modifiers() for singles/social events |
| `src/features/__init__.py` | Modified | Public exports for features package |
| `pyproject.toml` | Modified | Added pyyaml>=6.0 dependency |
| `tests/features/test_weights.py` | Created | 4 tests: groups coverage, weight lookups, sensitive defaults |
| `tests/features/test_encoder.py` | Created | 14 tests: encoding, imputation, flags, modes, Big Five, weight effect |
| `tests/features/test_modifiers.py` | Created | 5 tests: reweighting, normalisation, gender imbalance flag |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| enjoys_unfamiliar_experiences → values_alignment | Not in any SKILL group; Openness maps to values/worldview; test requires all fields covered | Gets 1.2× weight; consistent with Big Five Openness in values_alignment |
| high_anxiety uses raw value before imputation | Imputed anxiety median would give false positives for users who skipped the field | Flag is accurate signal only when user explicitly answered |
| Sensitive fields in raw_encoded regardless of mode | Allows inspection and debugging; vector inclusion controlled separately | raw_encoded always has all 20 fields encoded; vector length varies by mode |
| Sensitive weight = 1.0 in affinity/diversity | DIMENSION_GROUPS default 0.0 is neutral-mode; need active weight for other modes | Phase 02 can expose per-mode weight config as needed |

## Deviations from Plan

None — plan executed as written. `enjoys_unfamiliar_experiences` was unassigned in the plan's DIMENSION_GROUPS listing but the test required full field coverage; assigned to `values_alignment` as the closest semantic fit (Openness proxy).

## Issues Encountered

| Issue | Resolution |
|-------|-----------|
| `_encode_quiz` had unused `mode` parameter (lint warning) | Removed `mode` param — mode is used in `_build_weighted_vector`, not in encoding |

## Skill Audit

| Skill | Required | Invoked | Notes |
|-------|----------|---------|-------|
| SKILL-feature-engineering.md | required | ✓ | All encoding rules followed; Likert/ordinal/nominal/sensitive handled per spec |

## Next Phase Readiness

**Ready for Phase 02 (Core Algorithm):**
- `build_feature_vector()` produces L2-normalised vectors → cosine similarity is a dot product
- `UserFeatureVector.vector` is a tuple of floats ready for numpy cosine similarity
- `get_dimension_index_map()` available if Phase 02 needs per-dimension inspection
- `UserFeatureVector.flags` carries high_anxiety and low_profile_confidence for soft constraints
- `AnonymisedAttendee.pipeline_user_id` → `UserFeatureVector.user_id` chain established

**Ready for Phase 03 (Agent Layer):**
- `UserFeatureVector.big_five` dict provides Extraversion, Neuroticism, Openness, Conscientiousness, Agreeableness proxy scores for LLM explanation generation

**Concerns:** None.

**Blockers:** None.

---
*Phase: 01-foundation, Plan: 03*
*Completed: 2026-03-15*
