# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-03-15)

**Core value:** Automated group-matching for Blom Social — algorithm-driven assignment with human-in-the-loop LLM review.
**Current focus:** Phase 06 — API + Deployment (Not started)

## Current Position

Milestone: v0.1 Initial Release
Phase: 6 of 7 (API + Deployment) — Not started
Plan: None active
Status: Ready to plan Phase 06
Last activity: 2026-03-15 — Unified 05-07 (portfolio demo complete); Phase 05 ✅

Progress:
- Milestone: [█████████░] 92%
- Phase 01: [██████████] 100% ✅
- Phase 02: [██████████] 100% ✅
- Phase 03: [██████████] 100% ✅
- Phase 04: [██████████] 100% ✅
- Phase 05: [██████████] 100% ✅ (7/7 plans complete)
- Phase 06: [░░░░░░░░░░] 0% (Not started)

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ○        ○        ○     [Ready to start Phase 06]
```

## Accumulated Context

### Decisions
| Decision | Phase | Impact |
|----------|-------|--------|
| RawQuizResponse model (20 quiz fields + 3 metadata) | 01-01 | All downstream consumers use this schema |
| generate_event_fixture() bundles event + attendees | 01-01 | Phase 02 receives EventFixture directly |
| friend_pair_id = shared UUID between exactly 2 attendees | 01-01 | O(1) constraint lookup in Phase 02 |
| QUIZ_FIELDS constant in anonymiser.py is canonical list of 20 fields | 01-02 | Feature encoder imports from here |
| 12 Likert + 2 ordinal = 14 continuous-scaled fields | 01-03 | Encoder implements 12+2 correctly |
| Vector length varies by mode: 38-dim neutral, 67-dim affinity | 01-03 | Phase 02 cosine sim must handle variable-length vectors |
| high_anxiety flag uses raw value before imputation | 01-03 | Avoids false positives from median-filled data |
| AffinityMatrix as frozen Pydantic model with arbitrary_types_allowed | 02-01 | Consistent with Phase 01 conventions; stores numpy array directly |
| build_affinity_matrix() takes only feature_vectors (no event_id) | 03-01 | event_id sourced internally from fv[0].event_id |
| Patch target for LLM mocks: src.agent.workflow.ChatAnthropic | 03-01 | Module-level import means patching at call site, not library |
| mock_chain.ainvoke = AsyncMock(return_value=resp) pattern | 03-01 | Workflow calls .ainvoke() on chain — not __call__ |
| parse_operator_overrides imported inside compile_output | 03-02 | Avoids circular import — override_parser → schemas + matching |
| OverrideParseResult in override_parser.py (not schemas.py) | 03-02 | Internal LLM schema; public API is list[OperatorOverride] |
| workflow_trace_id via model_copy(update=...) | 03-02 | Immutable Pydantic pattern; "local" fallback when LangSmith inactive |
| suggest_weight_adjustments threshold >= 0.5 | 04-02 | Boundary at 0.5 confirms algorithm working |
| All-equal weight guard in suggest_weight_adjustments | 04-02 | Prevents meaningless max/min assignment on flat weight dicts |
| Two-axis fit: valuesCohesion (indices 1,3,4) + dominanceBalance + pairCompatibility | 05-04 | Social: catalystBalance; singles: assertivenessMatch — branched via profile.socialIntent |
| Derived assertiveness = social_energy×0.6 + (6-agreeableness)×0.4 | 05-04 | Avoids new questionnaire fields; uses existing trait indices 0 and 3 |
| ActivityProfile carries all per-event config (weights, catalystTarget, window, socialIntent) | 05-04 | Single config object; adding new event types = one record in ACTIVITY_PROFILES |
| PairScoreMap typed + empty in App; populated by Phase 06 API | 05-04 | Scaffold pattern — no structural change needed when API wires in |
| GroupHull V:XX D:XX uses two sibling <text> elements, not tspan | 05-04 | SVG tspan fill inheritance is browser-inconsistent |
| Lock icon badge (SVG padlock) replaces green ring on approved+frozen nodes | 05-05 | Ring was not visually noticeable; padlock communicates locked state semantically |
| groupSizeLimit (combobox) replaces frozenGroupSizes (implicit baseline) | 05-05 | Baseline from empty {} caused false +5 over-capacity on first load |
| hasImportedStragglers drives three-state button machine | 05-05 | Freeze/Unfreeze/Import state: Import disappears post-use; Freeze re-appears for re-approval |
| Frozen+approved nodes block drag in handleDragStart; stragglers remain draggable | 05-05 | Approved = notified; only Unfreeze unlocks them |
| Straggler banner as position:absolute overlay (not inside header) | 05-05 | Inside-header banner overflowed 72px fixed height |
| Window listeners over setPointerCapture for node/hull drag | 05-06 | Capture routes click events to SVG, firing onClearSelection post-selection |
| DEFAULT_GROUP_LAYOUT + GROUP_LAYOUT alias in mock-data.ts | 05-06 | App gains reactive groupLayout state; ForceCanvas import unchanged |
| handleDeleteGroup: remainingLayout.length === 0 guard → no-op | 05-06 | Cannot delete last group; straggler redistribution requires ≥1 target group |

### Deferred Issues
None.

### Blockers/Concerns
- Python 3.14 Pydantic v1 warning from langchain-core (cosmetic, non-blocking)
- GROUP_LAYOUT is still hardcoded (4 groups); dynamic group count planned for 05-06

### Git State
Last commit: 5e477a7 docs(paul): update STATE.md with Phase 01 commit hash
Branch: main (no feature branches)

## Session Continuity

Last session: 2026-03-15
Stopped at: 05-07 UNIFY complete — Phase 05 closed
Next action: Run /paul:plan for Phase 06 (API + Deployment)
Resume file: .paul/phases/06-api-deployment/ (to be created)

---
*STATE.md — Updated after every significant action*
