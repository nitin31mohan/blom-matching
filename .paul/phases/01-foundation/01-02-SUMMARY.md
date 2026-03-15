---
phase: 01-foundation
plan: 02
subsystem: data
tags: [pii, anonymisation, gdpr, pydantic, uuid, demo-export]

requires:
  - phase: 01-01
    provides: RawQuizResponse model and QUIZ_FIELDS field list

provides:
  - AnonymisedAttendee Pydantic model (pipeline_user_id, display_name, quiz_responses)
  - strip_pii(raw: dict) -> AnonymisedAttendee — PII boundary enforcement
  - build_reverse_mapping(stripped, original) -> dict — in-memory UUID→BlomID map
  - export_for_demo(stripped_list, seed) -> list[dict] — untraceable demo export
  - scan_for_pii_patterns(records) -> list[str] — CI/pre-commit PII scanner
  - QUIZ_FIELDS constant (20 field names) — canonical field list for pipeline

affects: [01-03-features, 02-core-algorithm, 03-agent-layer, 05-frontend-demo, 06-api]

tech-stack:
  added: []
  patterns:
    - anonymiser.py has zero module-level external deps (stdlib + uuid + pydantic only)
    - numpy imported lazily inside export_for_demo() — keeps import footprint clean
    - secrets.randbelow() for cryptographically random fallback display name suffix
    - QUIZ_FIELDS module-level constant is the single source of truth for the 20 quiz fields

key-files:
  created:
    - src/data/anonymiser.py
    - tests/data/test_anonymiser.py
  modified:
    - src/data/__init__.py (added anonymiser exports)

key-decisions:
  - "QUIZ_FIELDS constant defined in anonymiser.py — feature encoder imports it from here as canonical list"
  - "export_for_demo takes seed param — enables deterministic testing without sacrificing demo randomness"
  - "scan_for_pii_patterns() exposed as public function — usable in CI and pre-commit hooks"
  - "numpy imported lazily in export_for_demo only — anonymiser remains fast to import with no numpy dep at module level"

patterns-established:
  - "strip_pii() is always the first call when operator receives Blom data — no exceptions"
  - "build_reverse_mapping result is in-memory only, never persisted or logged"
  - "export_for_demo always replaces religious_identity — never carries original value"

duration: ~20min
started: 2026-03-15T00:35:00Z
completed: 2026-03-15T00:55:00Z
---

# Phase 01 Plan 02: PII Anonymiser — Summary

**Pipeline boundary enforcement: strip_pii() strips all PII at entry, export_for_demo() produces untraceable demo exports with Likert perturbation, regional country substitution, and religion replacement — 18 tests passing.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~20 min |
| Completed | 2026-03-15 |
| Tasks | 3 of 3 complete |
| Tests | 18 new (42 total, 0 regressions) |
| Files created | 2 |
| Files modified | 1 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: PII stripped at boundary | Pass | name/email/phone absent; fresh UUID; display_name = first token only |
| AC-2: Reverse mapping correctness | Pass | 10-entry test: all pipeline_user_ids map to correct original id |
| AC-3: Demo export untraceability | Pass | UUID, name, religion, country all differ between seeded calls |
| AC-4: No PII in demo export | Pass | scan_for_pii_patterns() finds no @ or 07xxxxxxxxx patterns |
| AC-5: Blank/missing name fallback | Pass | → "Attendee" + 4-digit cryptographic suffix |

**Skill AC cross-reference (SKILL-pii.md):**

| Skill AC | Status | Notes |
|----------|--------|-------|
| AC-1: PII stripped at boundary | Pass | All non-quiz fields silently dropped |
| AC-2: Reverse mapping correctness | Pass | test_build_reverse_mapping_correctness |
| AC-3: Demo export untraceability | Pass | Multiple seed comparisons confirm divergence |
| AC-4: No PII in demo seed files | Pass | scan_for_pii_patterns returns empty list |
| AC-5: LangSmith trace safety | Deferred | Testable in Phase 03 (LangGraph not yet built) |

## Accomplishments

- Single pipeline boundary function (`strip_pii`) with zero ambiguity: all non-quiz fields silently dropped, fresh UUID always generated, first-name-only display name extracted
- `export_for_demo` breaks re-identification on three axes simultaneously: Likert ±1 perturbation (40%), regional country substitution, full religion replacement
- `scan_for_pii_patterns` is a reusable CI utility — catches email and UK mobile patterns in any JSON export
- `QUIZ_FIELDS` constant established as the single source of truth for all 20 field names — feature encoder will import from here

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/data/anonymiser.py` | Created | AnonymisedAttendee, strip_pii, build_reverse_mapping, export_for_demo, scan_for_pii_patterns |
| `tests/data/test_anonymiser.py` | Created | 18 unit tests covering all 5 ACs |
| `src/data/__init__.py` | Modified | Added anonymiser public exports |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| QUIZ_FIELDS lives in anonymiser.py | It's the boundary module — defines what's safe to carry forward | Plan 01-03 imports QUIZ_FIELDS from here |
| seed param on export_for_demo | Reproducible tests without losing demo randomness | Tests verify untraceability by comparing two seeds |
| numpy lazy import in export_for_demo | Keep anonymiser import-time cost at zero | anonymiser usable in any context without pulling numpy |

## Deviations from Plan

None — plan executed exactly as written. 18 tests written (plan said 16; 2 additional tests added: `test_strip_pii_returns_frozen_model` and `test_strip_pii_missing_name_fallback` for completeness).

## Issues Encountered

None.

## Skill Audit

| Skill | Required | Invoked | Notes |
|-------|----------|---------|-------|
| SKILL-pii.md | required | ✓ | All anonymisation rules followed exactly |

## Next Phase Readiness

**Ready for Plan 01-03 (Feature engineering):**
- `QUIZ_FIELDS` constant available for encoder to iterate over
- `AnonymisedAttendee.quiz_responses` is the dict the encoder receives
- All 20 field names and types locked (resolve 12 vs 13 Likert question before starting)

**Ready for Phase 02 (Core algorithm):**
- `strip_pii` → `build_reverse_mapping` pattern established for write-back flow
- `export_for_demo` available for demo prong data pipeline

**Concerns:**
- 12 vs 13 Likert field discrepancy still unresolved — must address in Plan 01-03 before building the encoder

**Blockers:** None
