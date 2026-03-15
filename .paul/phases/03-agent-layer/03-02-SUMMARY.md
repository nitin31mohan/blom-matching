---
phase: 03-agent-layer
plan: 02
subsystem: agent
tags: [langchain-anthropic, langsmith, pydantic, asyncio, structured-output, traceable]

# Dependency graph
requires:
  - phase: 03-agent-layer/03-01
    provides: run_review_workflow, compile_output, AgentState, OperatorOverride, GroupAssignment

provides:
  - parse_operator_overrides() async function with LLM-backed NL parsing + ID validation
  - OverrideParseResult Pydantic schema (internal to override_parser.py)
  - compile_output wired to NL parser (async, calls parser when operator_notes non-empty)
  - run_review_workflow decorated with @traceable(name="blom_review_workflow")
  - workflow_trace_id populated from get_current_run_tree() or "local" fallback
  - 5 new tests: AC-4, AC-4b, AC-4c, AC-5, AC-5b

affects: [05-frontend, 06-api-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - parse_operator_overrides imported inside compile_output to avoid circular import
    - Patch target for override_parser LLM: src.agent.override_parser.ChatAnthropic
    - @traceable wraps async function — inspect.iscoroutinefunction still returns True
    - get_current_run_tree() returns None when LangSmith not active — no exception

key-files:
  created:
    - src/agent/override_parser.py
    - tests/agent/test_override_parser.py
  modified:
    - src/agent/workflow.py
    - src/agent/__init__.py
    - tests/agent/test_workflow.py

key-decisions:
  - "parse_operator_overrides imported inside compile_output (not module-level) to avoid circular import"
  - "OverrideParseResult lives in override_parser.py, NOT schemas.py — internal to parser"
  - "workflow_trace_id uses model_copy(update=...) to produce new ReviewedResult (immutable pattern)"
  - "Filter silently on invalid IDs — log warning only, never raise"

patterns-established:
  - "NL parser short-circuits on empty notes (no LLM call)"
  - "run_review_workflow is @traceable — LangSmith traces entire workflow including LLM calls"

# Metrics
duration: ~20min
started: 2026-03-15T00:30:00Z
completed: 2026-03-15T00:50:00Z
---

# Phase 03 Plan 02: Override Parsing + LangSmith Integration — Summary

**NL override parser with ID validation wired into compile_output; run_review_workflow decorated with @traceable and LangSmith run ID captured into ReviewedResult — 5 new tests pass, 90 total.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~20 min |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 3 of 3 completed |
| Files modified | 5 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-4: NL parser returns valid OperatorOverride | **Pass** | `test_parse_returns_valid_override` — real assignment, mocked LLM, correct IDs |
| AC-4b: Invalid user_id filtered silently | **Pass** | `test_parse_filters_invalid_user_id` — fake-user-id dropped, empty list returned |
| AC-4c: Empty notes returns [] without LLM call | **Pass** | `test_parse_empty_notes_returns_empty` — ainvoke.assert_not_called() |
| AC-5: LangSmith run ID captured | **Pass** | `test_workflow_captures_langsmith_run_id` — trace_id == "test-run-abc" |
| AC-5b: Falls back to "local" when no run tree | **Pass** | `test_workflow_falls_back_to_local_when_no_run_tree` — trace_id == "local" |

## Accomplishments

- Full NL-to-override pipeline: operator types plain English → LLM extracts structured moves → invalid IDs silently filtered → applied via existing `apply_override()`
- LangSmith tracing wired end-to-end: `@traceable` wraps `run_review_workflow`; run ID flows into `ReviewedResult.workflow_trace_id`
- 90 total tests pass, zero regressions

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/agent/override_parser.py` | Created | `OverrideParseResult` schema + `parse_operator_overrides()` with LLM + ID filtering |
| `src/agent/workflow.py` | Modified | `compile_output` → async + parser wired; `run_review_workflow` → `@traceable` + run ID |
| `src/agent/__init__.py` | Modified | Added `parse_operator_overrides` to exports and `__all__` |
| `tests/agent/test_override_parser.py` | Created | AC-4, AC-4b, AC-4c tests (3 total) |
| `tests/agent/test_workflow.py` | Modified | AC-5, AC-5b tests added (2 new, 7 total in file) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Import `parse_operator_overrides` inside `compile_output` | Avoids circular: override_parser imports from schemas + matching; workflow imports from schemas | Required pattern — module-level import would fail |
| `OverrideParseResult` in `override_parser.py` not `schemas.py` | Internal LLM schema; consumers only need `list[OperatorOverride]` | Keeps schemas.py stable |
| `result.model_copy(update={"workflow_trace_id": ...})` | `ReviewedResult` is a frozen-style Pydantic model; model_copy is the correct mutation pattern | Consistent with Phase 01/02 immutable conventions |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- `parse_operator_overrides` exported from `src.agent` — callable from API layer (Phase 06)
- `run_review_workflow` fully traceable — LangSmith audit trail available for every review session
- Full agent layer complete: explain → flag → checkpoint → parse overrides → compile result

**Concerns:**
- Python 3.14 Pydantic v1 warning from langchain-core persists (cosmetic, non-blocking)

**Blockers:**
- None

---
*Phase: 03-agent-layer, Plan: 02*
*Completed: 2026-03-15*
