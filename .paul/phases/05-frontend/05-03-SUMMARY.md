---
phase: 05-frontend
plan: 03
subsystem: ui
tags: [react, d3, typescript, force-simulation, zustand]

# Dependency graph
requires:
  - phase: 05-02
    provides: Zustand store (selectedAttendeeId), AttendeeDetail skeleton, App.tsx shell
provides:
  - Group-attractor physics canvas with throw, drag-to-reassign, live fit coloring
  - fit.ts library (traitAgreement metric, fitScore, fitColor, fitLabel)
  - Group-level fit percentages on hulls
  - Reset-on-activity-change pattern (key={resetKey})
affects: [05-04, 06-backend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - D3 sim owns positions, React re-renders SVG on tick via useState counter
    - forceX/Y reads node.group_id every tick — automatic response to reassignment
    - key={resetKey} pattern for clean sim remount
    - Two color systems: identity color (hull/stroke/bars) vs fit quality color (fill/percentage)

key-files:
  created: [frontend/operator/src/lib/fit.ts]
  modified:
    - frontend/operator/src/types.ts
    - frontend/operator/src/canvas/mock-data.ts
    - frontend/operator/src/canvas/ForceCanvas.tsx
    - frontend/operator/src/canvas/AttendeeNode.tsx
    - frontend/operator/src/canvas/GroupHull.tsx
    - frontend/operator/src/panels/AttendeeDetail.tsx
    - frontend/operator/src/App.tsx
  deleted: [frontend/operator/src/panels/GroupSummary.tsx]

key-decisions:
  - "traitAgreement metric (mean absolute agreement) replaces cosine similarity — cosine fails for maximally opposite vectors"
  - "Group-level fitPct computed in ForceCanvas render (not effect) — recomputes every tick at zero cost"
  - "key={resetKey} on ForceCanvas for clean remount — avoids leftover velocities on reset"
  - "forceX/Y instead of forceLink — reads group_id live, no stale links after reassignment"

patterns-established:
  - "Identity color vs fit quality color: always keep these two color systems separate"
  - "handleDragStart closure pattern: hasMoved flag for click/drag disambiguation, velocity tracking for throw"
  - "8-point circle hull padding: better shape for close clusters than centroid-outward approach"

# Metrics
duration: ~2 hours (across multiple sessions including post-approval additions)
started: 2026-03-15T00:00:00Z
completed: 2026-03-15T00:00:00Z
---

# Phase 05 Plan 03: Tony Stark Canvas Summary

**Group-attractor physics canvas shipped with throw, drag-to-reassign, live fit recoloring, group-level fit percentages, trait inspection panel, and activity-based reset.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2 hours |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 3 auto + 1 human-verify + 3 post-approval additions |
| Files modified | 8 modified, 1 created, 1 deleted |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Group attractors form visible clusters | Pass | 4 distinct clusters via forceX/Y group centers |
| AC-2: Throw physics | Pass | velX/velY tracked per mousemove; node.vx = velX * 5 on fast release |
| AC-3: Drag-to-reassign | Pass | Nearest group within 110px triggers group_id mutation + onReassign |
| AC-4: Live fit coloring | Pass | fitColor(fitScore(...)) called inline on every render tick |
| AC-5: Detail panel — traits + fit + move buttons | Pass | 5 trait bars, fit% badge, move buttons per other group |
| AC-6: Header — event selector + stats + legend | Pass | Dropdown, attendee count, per-group counts, fit legend |
| AC-7: TypeScript compiles clean | Pass | npm run type-check exit 0, 0 errors |

## Accomplishments

- Full Tony Stark canvas operational: physics objects cluster by group, can be thrown, snap to nearest group on drop, and immediately recolor to reflect fit quality
- `fit.ts` library with mean absolute agreement metric — correctly penalises maximally opposite trait pairings (e.g. [1,1,1,1,1] vs [5,5,5,5,5] → 0.0)
- Group-level fit percentage displayed on each hull label — updates live on every reassignment
- Activity-based reset: switching events resets attendees, clears selection, remounts simulation cleanly via `key={resetKey}` pattern

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/lib/fit.ts` | Created | traitAgreement, fitScore, fitColor, fitLabel |
| `src/types.ts` | Modified | Added `traits: number[]` to Attendee |
| `src/canvas/mock-data.ts` | Rewritten | 20 attendees × 4 groups, trait vectors, GROUP_LAYOUT |
| `src/canvas/ForceCanvas.tsx` | Rewritten | Full physics refactor: attractors, velocity, throw, reassign, live colors, group fitPct |
| `src/canvas/AttendeeNode.tsx` | Rewritten | Simplified: drag/click logic moved to ForceCanvas; groupColor prop added |
| `src/canvas/GroupHull.tsx` | Rewritten | 8-point circle hull padding; fitPct label rendering |
| `src/panels/AttendeeDetail.tsx` | Rewritten | Trait bars, fit% badge, move-to-group buttons |
| `src/App.tsx` | Rewritten | Header, event selector, reset, stats bar, legend, sidebar |
| `src/panels/GroupSummary.tsx` | Deleted | Superseded by enhanced AttendeeDetail |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Replace cosine similarity with mean absolute agreement | Cosine measures vector angle, not value-level mismatch — two vectors with many high values score ~0.8+ even if profiles are opposite | More semantically correct fit scoring; adversarial groupings now correctly produce low scores |
| Group-level fitPct in render, not effect | Recomputes on every tick for free — no additional state or subscriptions | Live hull fit percentages with zero overhead |
| key={resetKey} on ForceCanvas | Incrementing key causes React to fully unmount/remount — clean slate including node positions and velocities | Clean reset without leftover physics state |
| forceX/Y instead of forceLink | Reads node.group_id every tick — drag-to-reassign automatically pulls node toward new group | No manual link management on reassignment |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Metric replacement — essential correctness fix |
| Scope additions | 3 | All user-requested; no scope creep |
| Deferred | 0 | — |

**Total impact:** Essential metric fix + meaningful feature additions, no unplanned scope creep.

### Auto-fixed Issues

**1. Semantic bug — cosine similarity for trait scoring**
- **Found during:** Human-verify checkpoint (user testing)
- **Issue:** Cosine similarity measures vector angle, not value agreement. Forcing [1,1,1,1,1] and [5,5,5,5,5] together scored ~0.5 instead of 0.0 — adverse groupings didn't visibly hurt fit scores.
- **Fix:** Replaced with `traitAgreement = 1 - mean(|a_i - b_i|) / 4`, where 4 is max per-dimension diff on [1,5] scale.
- **Files:** `src/lib/fit.ts`
- **Verification:** Maximally opposite vectors now score 0.0; identical vectors score 1.0

### Scope Additions (post-approval, user-requested)

1. **Group-level fit percentages on hulls** — average fitScore of all members, displayed as "XX% fit" on each group hull label, colored by fitColor threshold
2. **Cosine → traitAgreement metric** — correctness fix triggered by user observation (documented above as auto-fix)
3. **Reset functionality** — "Reset groupings" button in header + auto-reset on event change. Uses `key={resetKey}` + `MOCK_ATTENDEES` restore + `clearSelection()`

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Edit tool "string not found" on fit.ts cosine replacement | Rewrote entire file with Write tool instead |

## Next Phase Readiness

**Ready:**
- Physics canvas fully operational — foundation for algorithm upgrade (05-04)
- fit.ts is a clean black box — external API unchanged when internals evolve
- GROUP_LAYOUT + activity mock events in place — activity profiles can be attached
- Attendee trait schema established — ready for assertiveness derivation

**Concerns:**
- Derived assertiveness (social_energy × 0.6 + (6 - agreeableness) × 0.4) not yet implemented — 05-04 territory
- Activity profiles (per-event matching weights) not yet defined — 05-04 territory
- Pair-level compatibility matrix not yet in schema — deferred to backend phase

**Blockers:**
- None

---
*Phase: 05-frontend, Plan: 03*
*Completed: 2026-03-15*
