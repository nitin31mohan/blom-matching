---
phase: 05-frontend
plan: 04
subsystem: ui
tags: [react, typescript, d3, algorithm, fit-scoring, activity-profiles]

requires:
  - phase: 05-03
    provides: Force canvas with group hulls, fit score coloring, drag-to-reassign, reset, live attendee state

provides:
  - Two-axis fit scoring engine (values cohesion + dominance balance) with singles/social branching
  - Per-activity profiles (pub_quiz, hiit_mocktails, life_drawing) with configurable weights and catalyst targets
  - Pair compatibility scaffolding (PairScoreMap typed, empty for now)
  - Operator view-mode toggle (simple → single composite; detailed → split sub-scores)
  - MockEvent type replacing plain event strings

affects: [05-05, phase-06]

tech-stack:
  added: []
  patterns:
    - Two-axis fit model (values cohesion × dominance balance) with per-profile weights
    - Singles/social branching inside fitScoreDetailed via profile.socialIntent
    - Derived assertiveness from existing traits (social_energy × 0.6 + (6 - agreeableness) × 0.4)
    - PairScoreMap scaffold pattern (typed but empty; populated by Phase 06 API)
    - fitScoreDetailed returns FitBreakdown struct; fitScore is a thin wrapper returning composite

key-files:
  created:
    - frontend/operator/src/lib/activity-profiles.ts
  modified:
    - frontend/operator/src/lib/fit.ts
    - frontend/operator/src/types.ts
    - frontend/operator/src/canvas/mock-data.ts
    - frontend/operator/src/canvas/ForceCanvas.tsx
    - frontend/operator/src/canvas/GroupHull.tsx
    - frontend/operator/src/panels/AttendeeDetail.tsx
    - frontend/operator/src/App.tsx

key-decisions:
  - "fitScoreDetailed returns FitBreakdown; fitScore is a wrapper — avoids duplicate computation for detailed view"
  - "Two separate <text> elements for V:XX D:XX in GroupHull (not tspan) — SVG tspan fill inheritance is unreliable"
  - "Compatibility sub-score shows 0.5 + 'No history yet' for cold-start — accepted as feature, not masked"
  - "Catalyst ratio target for singles events (life_drawing) is defined but unused — assertivenessMatch replaces catalystBalance"

patterns-established:
  - "ActivityProfile is the single config object per event type — weights, target, window, socialIntent all in one place"
  - "fitScoreDetailed signature: (node, groupId, allNodes, profile, pairScores?) — node carries id + traits"
  - "dynamicLabel: 'Assertiveness match' for singles, 'Group dynamic' for social — label switches on profile.socialIntent"

duration: ~90min
started: 2026-03-15T00:00:00Z
completed: 2026-03-15T00:00:00Z
---

# Phase 05 Plan 04: Two-Axis Algorithm Upgrade Summary

**Two-axis fit engine with per-activity profiles, singles/social branching, pair compatibility scaffolding, and operator simple/detailed view toggle — shipped in one session, 0 TypeScript errors.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~90 min |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 3 auto + 1 human-verify checkpoint |
| Files created | 1 |
| Files modified | 7 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Two-axis fit scoring — social events | Pass | valuesCohesion (indices 1,3,4) + catalystBalance + pairCompatibility weighted by profile |
| AC-2: Singles-mode scoring differs from social | Pass | assertivenessMatch replaces catalystBalance when profile.socialIntent === 'singles' |
| AC-3: Activity profiles are per-event | Pass | 3 profiles (pub_quiz, hiit_mocktails, life_drawing); switching event triggers full recolor |
| AC-4: View mode toggle — simple | Pass | Single composite badge in panel; "XX% fit" on hulls; default behavior preserved |
| AC-5: View mode toggle — detailed | Pass | Three sub-score bars in AttendeeDetail; V:XX D:XX on hulls; each colored independently |
| AC-6: TypeScript compiles clean | Pass | npm run type-check → exit 0, 0 errors on first run |

## Accomplishments

- Rewrote fit.ts from flat similarity to two-axis scoring: Axis A = values cohesion (mean pairwise agreement on openness/agreeableness/eco_values), Axis B = dominance balance (catalystBalance for social; assertivenessMatch for singles)
- Created activity-profiles.ts with 3 named profiles carrying independent weight distributions and catalyst targets — switching events now meaningfully changes color distributions
- Wired `viewMode` toggle through App → ForceCanvas → GroupHull and App → AttendeeDetail; detailed mode adds three labeled sub-score bars and V:XX D:XX hull labels with per-axis coloring
- Scaffolded PairScoreMap (typed, empty state in App) — foundation for Phase 06 pair feedback API

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/lib/fit.ts` | Rewritten | Two-axis scoring engine — fitScoreDetailed, fitScore, helpers |
| `src/lib/activity-profiles.ts` | Created | ACTIVITY_PROFILES record + getActivityProfile() lookup |
| `src/types.ts` | Modified | Added SocialIntent, ActivityProfile, MockEvent, FitBreakdown, PairScoreMap |
| `src/canvas/mock-data.ts` | Modified | MOCK_EVENTS: string[] → MockEvent[] with activityType and socialIntent |
| `src/canvas/ForceCanvas.tsx` | Modified | Accepts activeProfile + pairScores + viewMode; computes per-group FitBreakdown averages |
| `src/canvas/GroupHull.tsx` | Rewritten | fitPct → fitBreakdown + viewMode; FitLabel component handles both modes |
| `src/panels/AttendeeDetail.tsx` | Rewritten | Uses fitScoreDetailed; shows split sub-score bars in detailed mode |
| `src/App.tsx` | Modified | selectedEvent typed as MockEvent; activeProfile derived; viewMode state + toggle button |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Two separate `<text>` elements for V:XX D:XX in GroupHull | SVG tspan fill inheritance is browser-inconsistent; plan noted this as a fallback | Cleaner, more predictable rendering than tspan |
| fitScore is a thin wrapper over fitScoreDetailed | Avoids computing the breakdown twice for callers that need both | All callers (ForceCanvas node color + group average) share one implementation path |
| Compatibility displays 0.5 + "No history yet" (not hidden) | Cold-start transparency is a feature — operator sees exactly what the algorithm has to work with | Sets expectation for Phase 06 pair feedback wiring |
| catalystTarget defined on life_drawing profile even though unused for singles | Keeps ActivityProfile shape consistent; avoids conditional field access | No special-casing needed in consumers |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Rendering improvement |
| Scope additions | 0 | None |
| Deferred | 0 | None |

**Total impact:** One minor rendering fix, no scope creep.

### Auto-fixed Issues

**1. GroupHull: two `<text>` elements instead of tspan**
- **Found during:** Task 3 (GroupHull rewrite)
- **Issue:** Plan suggested tspan for V:XX D:XX but noted fill inheritance may be awkward
- **Fix:** Used two sibling `<text>` elements (cx-18 and cx+18) each with their own `fill` — extracted into a `FitLabel` sub-component
- **Files:** `src/canvas/GroupHull.tsx`
- **Verification:** Both labels render correctly with independent fit colors

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| None | — |

## Next Phase Readiness

**Ready:**
- Two-axis fit engine in place — 05-05 (portfolio demo) can use it directly with synthetic data
- ActivityProfile pattern established — adding new event types is one record in ACTIVITY_PROFILES
- PairScoreMap scaffold ready — Phase 06 populates it from API without any structural change

**Concerns:**
- pairCompatibility is always 0.5 until Phase 06 wires the feedback API — composite scores are currently two-axis in practice (three-axis in code)
- Python 3.14 Pydantic v1 warning from langchain-core remains (cosmetic, non-blocking, pre-existing)

**Blockers:**
- None

---
*Phase: 05-frontend, Plan: 04*
*Completed: 2026-03-15*
