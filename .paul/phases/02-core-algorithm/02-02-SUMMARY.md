---
phase: 02-core-algorithm
plan: 02
type: summary
status: complete
completed: 2026-03-15
---

# Summary: Plan 02-02 — Constrained Group Assignment

## What Was Built

- **`config/matching.yaml`** — added `assignment` section (`group_size_min: 3`, `group_size_max: 6`, `target_group_size: 5`)
- **`src/matching/constraints.py`** — `ConstraintError`, `build_friend_pair_map()`, `check_group_sizes()`, `validate_friend_pairs()`
- **`src/matching/assignment.py`** — `Group`, `GroupAssignment`, `assign_groups()`, `apply_override()`
- **`src/matching/__init__.py`** — updated with all new public exports
- **`tests/matching/test_assignment.py`** — 7 tests covering all 6 ACs + full pipeline integration

## Acceptance Criteria Results

| AC | Description | Result |
|----|-------------|--------|
| AC-1 | All users assigned (unassigned = empty) | ✅ Pass |
| AC-2 | Group sizes within [3, 6] bounds | ✅ Pass |
| AC-3 | Friend pairs co-assigned | ✅ Pass |
| AC-4 | Greedy cohesion ≥ 0.7 with clear clusters | ✅ Pass |
| AC-5 | apply_override moves user + recomputes cohesion | ✅ Pass |
| AC-6 | apply_override raises ConstraintError on split pair | ✅ Pass |

## Test Results

- `tests/matching/test_assignment.py` — **7/7 passed**
- `tests/matching/test_similarity.py + tests/data/ + tests/features/` — **73/73 passed** (zero regressions)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `assign_groups` accepts `friend_pair_ids: dict[str, str | None]` separately from `AffinityMatrix` | `friend_pair_id` is not PII but isn't part of the anonymised quiz schema — caller maintains the mapping alongside the pipeline |
| Greedy sorts unassigned users by max-affinity score descending | Places most "matchable" users first — they have the strongest preference signal and should anchor group formation |
| Overflow to least-full group when all groups at max_size | Hard constraint: no user left unassigned; soft constraint (size bound) yields in edge cases |
| `apply_override` only blocks split pairs, not reuniting them | If partner already in `to_group_id`, moving user there is valid (and beneficial) |
| `_build_group_object` is a shared helper used by both `assign_groups` and `apply_override` | DRY: cohesion + fit_color + flags recomputation logic in one place |

## Files Modified

- `config/matching.yaml` — added `assignment` section
- `src/matching/constraints.py` — created (was empty stub)
- `src/matching/assignment.py` — created (was empty stub)
- `src/matching/__init__.py` — updated with new exports
- `tests/matching/test_assignment.py` — created (was empty stub)

## Deferred Issues

None.

---
*Plan 02-02 complete. Phase 02 (Core Algorithm) is now fully complete.*
*Next: Phase 03 — Agent Layer*
