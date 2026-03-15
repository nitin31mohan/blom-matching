# Blom matching system

## What this is
An automated group-matching pipeline for Blom Social (blom.social).
Replaces manual attendee grouping with an algorithm-driven assignment
system backed by a human-in-the-loop LLM review layer.

## Two delivery prongs
1. **Operator tool** — private admin dashboard for the Blom founder.
   Real attendee data, write-back to DB, drag-and-drop group canvas.
2. **Portfolio demo** — public-facing version on nitinmohan.dev.
   Synthetic anonymised data, same UI, no auth required.

## Core tech
- Python backend: FastAPI, LangGraph, NumPy
- Frontend: React + D3 force simulation + Zustand
- DB: TBD with Blom founder (likely Supabase or Firebase)
- Deployment: Railway (backend) + Vercel (frontend)

## Key constraints
- No real PII in the demo prong under any circumstances
- Spend cap on all LLM API calls — hard limit enforced at provider level
- Operator tool must work for corpus sizes 10–500 without re-architecture
- Matching must be explainable in plain English (LLM review layer)

## Out of scope (v1)
- Mobile app integration
- Real-time collaborative editing of groups
- User-facing match explanations (operator-only for now)

## Key Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| RawQuizResponse model (20 quiz fields + 3 metadata) | 01-01 | All downstream consumers use this schema |
| generate_event_fixture() bundles event + attendees | 01-01 | Phase 02 receives EventFixture directly |
| friend_pair_id = shared UUID between exactly 2 attendees | 01-01 | O(1) constraint lookup in Phase 02 |
| scipy in main deps (Gaussian copula via Cholesky) | 01-01 | Realistic correlated Likert data in synthetic generator |
| venv at .venv/ (Python 3.14.2) | 01-01 | All commands: .venv/bin/python3 |
| QUIZ_FIELDS constant in anonymiser.py is canonical list of 20 fields | 01-02 | Feature encoder imports from here |
| strip_pii() is always the first call when operator receives Blom data | 01-02 | Hard pipeline boundary — no exceptions |
| 12 Likert + 2 ordinal = 14 continuous-scaled fields; "13" in SKILL is a typo | 01-03 | Encoder implements 12+2 correctly |
| enjoys_unfamiliar_experiences → values_alignment group (1.2× weight) | 01-03 | Openness proxy; test requires all fields assigned |
| Sensitive fields excluded from vector in neutral mode (vector length changes) | 01-03 | 38-dim neutral, 67-dim affinity; Phase 02 must handle variable length |
| high_anxiety flag uses raw value before imputation | 01-03 | Avoids false positives from median-filled data |
| LangGraph 4-node StateGraph with interrupt_before=["human_checkpoint"] | 03-01 | Enables pause/resume for human review without graph recompilation |
| Mock target: src.agent.workflow.ChatAnthropic (not langchain_anthropic directly) | 03-01 | Module-level import requires patching at call site |
| mock_chain.ainvoke = AsyncMock(return_value=resp) pattern for structured output chains | 03-01 | Workflow calls .ainvoke() on chain — patching __call__ is wrong |
| parse_operator_overrides imported inside compile_output (not module-level) | 03-02 | Avoids circular import: override_parser → schemas + matching → workflow |
| OverrideParseResult lives in override_parser.py, not schemas.py | 03-02 | Internal LLM schema; public API is list[OperatorOverride] only |
| workflow_trace_id via model_copy(update=...) after get_current_run_tree() | 03-02 | Immutable Pydantic pattern; "local" fallback when LangSmith inactive |

## Validated Requirements

- ✓ Attendee schema (RawQuizResponse) — Phase 01-01
- ✓ Synthetic data generator (deterministic, scales to 500) — Phase 01-01
- ✓ PII anonymisation utilities (strip_pii, export_for_demo) — Phase 01-02
- ✓ Feature engineering pipeline (encoder, weights, modifiers) — Phase 01-03
- ✓ Cosine similarity affinity matrix — Phase 02-01
- ✓ Constrained greedy group assignment with friend-pair hard constraints — Phase 02-02
- ✓ LangGraph review workflow (explain → flag → checkpoint → compile) — Phase 03-01
- ✓ NL override parsing with ID validation (parse_operator_overrides) — Phase 03-02
- ✓ LangSmith tracing via @traceable + workflow_trace_id in ReviewedResult — Phase 03-02

---
*Last updated: 2026-03-15 after Phase 03*
