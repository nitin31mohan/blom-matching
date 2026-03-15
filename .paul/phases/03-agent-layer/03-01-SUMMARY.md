---
phase: 03-agent-layer
plan: 01
subsystem: agent
tags: [langgraph, langchain-anthropic, langsmith, pydantic, asyncio]

# Dependency graph
requires:
  - phase: 02-core-algorithm
    provides: GroupAssignment, Group, AffinityMatrix, UserFeatureVector, apply_override, ConstraintError

provides:
  - LangGraph StateGraph with 4 nodes (explain_groups → flag_review → human_checkpoint → compile_output)
  - GroupExplanationSchema, GroupExplanation, OperatorOverride, ReviewedResult Pydantic models
  - SYSTEM_PROMPT + USER_PROMPT_TEMPLATE + format_member_profiles()
  - run_review_workflow() public async API
  - 5 tests covering AC-1, AC-2, AC-3, AC-6

affects: [03-02-override-parsing, 05-frontend, 06-api-deployment]

# Tech tracking
tech-stack:
  added: [langgraph>=0.2, langchain-anthropic>=0.3, langsmith>=0.1, pytest-asyncio>=0.23]
  patterns:
    - AgentState TypedDict pattern for LangGraph state
    - AsyncMock + patch("src.agent.workflow.ChatAnthropic") for LLM test isolation
    - asyncio.gather for parallel LLM calls across groups
    - interrupt() primitive for human-in-the-loop pause

key-files:
  created:
    - src/agent/schemas.py
    - src/agent/prompts.py
    - src/agent/workflow.py
    - src/agent/__init__.py
    - tests/agent/test_workflow.py
  modified:
    - pyproject.toml

key-decisions:
  - "build_affinity_matrix() takes only feature_vectors (no event_id arg) — event_id sourced from fv[0].event_id"
  - "Mock target is src.agent.workflow.ChatAnthropic, not langchain_anthropic directly"
  - "mock_chain.ainvoke = AsyncMock(...) — not AsyncMock(return_value=...) on the chain itself"
  - "hatchling requires [tool.hatch.build.targets.wheel] packages = ['src'] for editable installs"

patterns-established:
  - "All LangGraph nodes are pure functions (sync or async) returning dict state updates"
  - "compile_output imports build_affinity_matrix locally to avoid circular imports"
  - "Tests build real GroupAssignment via full pipeline (synthetic → feature vectors → affinity → assign)"

# Metrics
duration: ~30min
started: 2026-03-15T00:00:00Z
completed: 2026-03-15T00:30:00Z
---

# Phase 03 Plan 01: LangGraph Workflow + Prompt Templates — Summary

**Four-node LangGraph StateGraph (explain_groups → flag_review → human_checkpoint → compile_output) with parallel async LLM calls, structured Pydantic output, and interrupt()-based human checkpoint — 5 tests passing, 85 total.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 6 of 6 completed |
| Files modified | 6 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Structured output always parseable | **Pass** | `test_explain_groups_returns_valid_schema` — 2 groups, mocked LLM, all GroupExplanation fields non-empty |
| AC-2: Checkpoint triggers on low-cohesion/confidence | **Pass** | `test_flag_review_triggers_on_low_cohesion` + `test_flag_review_triggers_on_low_confidence` both pass |
| AC-3: Clean path returns ReviewedResult directly | **Pass** | `test_workflow_clean_path_no_interrupt` — 12 attendees, high-confidence mock, no interrupt raised |
| AC-6: Parallel LLM calls via asyncio.gather | **Pass** | `test_explain_groups_calls_llm_in_parallel` — 20 attendees (4 groups), gather called once with N coroutines |

## Accomplishments

- Full LangGraph StateGraph compiles at module import time with `MemorySaver` checkpointer and `interrupt_before=["human_checkpoint"]`
- Parallel async LLM calls via `asyncio.gather` in `explain_groups` — all N groups explained concurrently
- `flag_review` covers three trigger conditions: `fit_color == "#ef4444"`, `confidence == "low"`, >25% medium
- `compile_output` safely applies OperatorOverrides via `apply_override()`, logging `ConstraintError` warnings without raising
- 85 total tests pass (5 new + 80 prior), zero regressions

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/agent/schemas.py` | Created | GroupExplanationSchema, GroupExplanation, OperatorOverride, ReviewedResult |
| `src/agent/prompts.py` | Created | SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_member_profiles() |
| `src/agent/workflow.py` | Created | AgentState, 4 graph nodes, compiled StateGraph, run_review_workflow() |
| `src/agent/__init__.py` | Created | Public exports |
| `tests/agent/test_workflow.py` | Created | AC-1, AC-2×2, AC-3, AC-6 tests (5 total) |
| `pyproject.toml` | Modified | Added langgraph, langchain-anthropic, langsmith, pytest-asyncio; hatchling wheel config; asyncio_mode="auto" |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `build_affinity_matrix(feature_vectors)` — no event_id arg | Actual signature takes only one arg; event_id sourced internally from fv[0].event_id | Fixed during Task 4; compile_output works correctly |
| Patch `src.agent.workflow.ChatAnthropic` not `langchain_anthropic.ChatAnthropic` | Module-level import means patching the name at the call site | Required for all 3 LLM-mocked tests |
| `mock_chain.ainvoke = AsyncMock(return_value=resp)` | Workflow calls `.ainvoke()` on the chain object — AsyncMock on chain itself intercepts `__call__`, not `.ainvoke` | Fixed failing AC-1, AC-3, AC-6 tests |
| Added `[tool.hatch.build.targets.wheel] packages = ["src"]` | hatchling refused to build metadata without explicit package target | Unblocked `pip install -e ".[dev]"` for new deps |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 3 | Essential corrections, no scope change |
| Scope additions | 1 | Extra AC-2 variant (low_confidence test) |
| Deferred | 0 | — |

**Total impact:** All auto-fixes were essential API corrections discovered during verification. One extra test added for better AC-2 coverage.

### Auto-fixed Issues

**1. build_affinity_matrix() signature mismatch**
- **Found during:** Task 4 (workflow.py) verification
- **Issue:** Plan showed `build_affinity_matrix(feature_vectors, event_id)` — actual API takes only `feature_vectors`
- **Fix:** Removed second argument; event_id flows from `fv[0].event_id` inside the function
- **Files:** `src/agent/workflow.py`

**2. LLM mock structure (AsyncMock on chain vs .ainvoke)**
- **Found during:** Task 6 test run
- **Issue:** `AsyncMock(return_value=resp)` intercepts `mock_chain(...)` not `mock_chain.ainvoke(...)`, causing ValidationError
- **Fix:** Changed to `mock_chain = MagicMock(); mock_chain.ainvoke = AsyncMock(return_value=resp)`
- **Files:** `tests/agent/test_workflow.py`

**3. hatchling build metadata error**
- **Found during:** Task 1 pip install
- **Issue:** hatchling required explicit `packages` config to locate source
- **Fix:** Added `[tool.hatch.build.targets.wheel] packages = ["src"]` to pyproject.toml
- **Files:** `pyproject.toml`

### Deferred Items

None — plan executed completely.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Python 3.14 warning: `Core Pydantic V1 functionality isn't compatible` | Non-blocking warning from langchain-core internals; does not affect functionality |
| AC-6 needed 20 attendees (not 12) to produce ≥3 groups | Increased fixture size for AC-6 test only |

## Next Phase Readiness

**Ready:**
- `run_review_workflow(assignment, feature_vectors, event_type)` — public async API callable from any context
- `graph` module-level object — can be resumed after interrupt via `graph.ainvoke(None, config={"configurable": {"thread_id": tid}})`
- All schemas importable from `src.agent` — ready for Plan 03-02 override parsing and LangSmith integration

**Concerns:**
- Python 3.14 Pydantic v1 warning (from langchain-core) is cosmetic but should be monitored if langchain-core updates
- `workflow_trace_id = "local"` placeholder — will be replaced with LangSmith run ID in Plan 03-02

**Blockers:**
- None

---
*Phase: 03-agent-layer, Plan: 01*
*Completed: 2026-03-15*
