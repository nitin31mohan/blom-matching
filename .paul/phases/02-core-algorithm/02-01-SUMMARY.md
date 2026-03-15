---
phase: 02-core-algorithm
plan: 01
type: summary
status: complete
completed: 2026-03-15
---

# Summary: Plan 02-01 — Similarity Computation + Affinity Matrix

## What Was Built

- **`config/matching.yaml`** — added `fit_thresholds` section (`great: 0.68`, `okay: 0.42`)
- **`src/matching/similarity.py`** — `AffinityMatrix` Pydantic model + 5 similarity functions
- **`src/matching/__init__.py`** — public exports for all 6 symbols
- **`tests/matching/test_similarity.py`** — 8 unit tests covering all 6 acceptance criteria

## Acceptance Criteria Results

| AC | Description | Result |
|----|-------------|--------|
| AC-1 | Matrix symmetry (within 1e-6) | ✅ Pass |
| AC-2 | Diagonal entries = 1.0 | ✅ Pass |
| AC-3 | All values in [-1.0, 1.0] | ✅ Pass |
| AC-4 | Cohesion ordering: identical > mixed > opposing | ✅ Pass |
| AC-5 | marginal_cohesion = mean of individual scores | ✅ Pass |
| AC-6 | group_fit_color correct hex for all three thresholds | ✅ Pass |

## Test Results

- `tests/matching/test_similarity.py` — **8/8 passed**
- `tests/data/ tests/features/` — **65/65 passed** (zero regressions)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| cosine sim = dot product (no re-normalisation) | Vectors already L2-normalised by encoder; re-normalising here would be redundant and could introduce drift |
| `datetime.now(timezone.utc)` instead of `datetime.utcnow()` | `utcnow()` is deprecated in Python 3.12+; timezone-aware form is correct |
| `_CONFIG` loaded once at module import | Same pattern as encoder.py; tests pass `config=` explicitly to override |
| `group_cohesion_score` returns 0.0 for < 2 members | Prevents division by zero; semantically correct (no pairs = no cohesion measure) |

## Files Modified

- `config/matching.yaml` — added `fit_thresholds`
- `src/matching/similarity.py` — created (was empty stub)
- `src/matching/__init__.py` — created (was empty stub)
- `tests/matching/test_similarity.py` — created (was empty stub)

## Deferred Issues

None.

---
*Plan 02-01 complete. Next: Plan 02-02 — Constrained Group Assignment*
