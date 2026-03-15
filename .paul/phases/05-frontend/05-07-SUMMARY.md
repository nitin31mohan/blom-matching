---
phase: 05-frontend
plan: 07
subsystem: ui
tags: [react, typescript, vite, d3, portfolio, demo, synthetic-data]

requires:
  - phase: 05-06
    provides: ForceCanvas with pointer events + group deletion, GroupHull drag handle, AttendeeNode with 44px hit area, GroupLayout type

provides:
  - frontend/demo/ — standalone Vite React app for portfolio (Prong 2)
  - Synthetic seed: 16 attendees, 4 groups, 2 events (pub quiz + life drawing)
  - Simplified App.tsx: canvas + algo explainer panel + trait breakdown on node click
  - No auth, no admin controls, no Zustand — public-facing demo

affects: [phase-06]

tech-stack:
  added:
    - blom-demo Vite app (d3, react, react-dom — no zustand)
  patterns:
    - Verbatim file copy for shared components (no shared package for v0.1)
    - useMemo for stable assignment reference (avoids simulation restart on re-render)
    - CSS reset in index.html <style> block (no extra CSS file)
    - AlgoExplainer / SelectedPanel as local functions in App.tsx

key-files:
  created:
    - frontend/demo/package.json
    - frontend/demo/vite.config.ts
    - frontend/demo/tsconfig.json
    - frontend/demo/tsconfig.app.json
    - frontend/demo/index.html
    - frontend/demo/src/main.tsx
    - frontend/demo/src/types.ts
    - frontend/demo/src/lib/fit.ts
    - frontend/demo/src/lib/activity-profiles.ts
    - frontend/demo/src/canvas/ForceCanvas.tsx
    - frontend/demo/src/canvas/AttendeeNode.tsx
    - frontend/demo/src/canvas/GroupHull.tsx
    - frontend/demo/src/data/demo-seed.ts
    - frontend/demo/src/App.tsx
  modified: []

key-decisions:
  - "Verbatim file copy over shared package: simpler for v0.1; Phase 06 can extract shared lib if needed"
  - "useMemo for dummyAssignment: prevents ForceCanvas simulation restart on every App re-render"
  - "CSS reset in index.html <style> block: removes browser default body margin without extra file"
  - "No Zustand in demo: useState sufficient; removes dependency from demo bundle"

patterns-established:
  - "Demo seed uses demo-XX IDs and first-name-only invented names (AC-8 compliance)"
  - "AlgoExplainer and SelectedPanel as named local functions (not components in separate files)"

duration: ~1h
started: 2026-03-15T00:00:00Z
completed: 2026-03-15T00:00:00Z
---

# Phase 05 Plan 07: Portfolio Demo Summary

**Standalone `frontend/demo/` Vite React app — same D3 force canvas as operator tool, synthetic seed, algo explainer panel, no auth — ready for Vercel deployment in Phase 06.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1h (tasks + 1 post-checkpoint fix) |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 2 auto + 1 human-verify + 1 post-checkpoint fix |
| Files created | 14 |
| Files modified | 0 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: App scaffolds and builds clean | Pass | npm install + type-check + build → exit 0 |
| AC-2: Canvas renders with synthetic data | Pass | 16 nodes in 4 coloured groups, fit score colours |
| AC-3: Drag to reassign works | Pass | Inherited from ForceCanvas unchanged |
| AC-4: Event picker switches dataset | Pass | Pub quiz ↔ Life drawing, canvas resets |
| AC-5: View mode toggle works | Pass | Simple/Detailed hull label switch |
| AC-6: Right panel — algo explainer by default | Pass | Values cohesion / Dominance balance / Pair compatibility |
| AC-7: Right panel — trait breakdown on click | Pass | Fit %, three score bars, five trait bars |
| AC-8: No real PII — all names synthetic | Pass | Invented first names, demo-XX IDs |

## Accomplishments

- Scaffolded a fully independent `frontend/demo/` Vite app with no shared runtime coupling to the operator app; both build and type-check independently
- Created curated synthetic seed with 16 attendees across 4 groups: one cohesive group (alpha, mostly green), one divergent group (gamma, amber/red), two moderate groups — good visual range for portfolio showcase
- Built simplified App.tsx: algo explainer panel on load, switches to fit score + trait breakdown on node click, no freeze/admin controls anywhere in the UI

## Files Created

| File | Purpose |
|------|---------|
| `package.json` | blom-demo app (d3, react, react-dom; no zustand) |
| `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json` | Build config |
| `index.html` | Entry point + CSS reset (`* { margin:0; padding:0; box-sizing:border-box }`) |
| `src/main.tsx` | React root mount |
| `src/types.ts` | Verbatim copy from operator |
| `src/lib/fit.ts` | Verbatim copy from operator |
| `src/lib/activity-profiles.ts` | Verbatim copy from operator |
| `src/canvas/ForceCanvas.tsx` | Verbatim copy from operator (already has GroupLayout type, pointer events) |
| `src/canvas/AttendeeNode.tsx` | Verbatim copy from operator |
| `src/canvas/GroupHull.tsx` | Verbatim copy from operator |
| `src/data/demo-seed.ts` | DEMO_EVENTS (2), DEMO_GROUP_LAYOUT (4 groups), DEMO_ATTENDEES (16) |
| `src/App.tsx` | Simplified canvas app + AlgoExplainer + SelectedPanel |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Verbatim file copy (no shared package) | Extracting a shared lib adds build complexity not needed for v0.1 | Both apps independently deployable; sync is manual |
| useMemo for dummyAssignment | Stable object reference prevents ForceCanvas simulation restart on every App re-render | Smooth physics; no unnecessary sim resets |
| CSS reset in index.html `<style>` | Removes browser default body margin (8px) without adding a CSS file | Clean full-viewport layout |
| No Zustand in demo | useState sufficient for single-selection; no cross-component selection state needed | Smaller bundle, simpler code |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed (post-checkpoint) | 1 | Visual fix; essential |
| Scope additions | 0 | None |
| Deferred | 0 | None |

### Auto-fixed Issues

**1. Browser default body margin visible as padding around canvas**
- **Found during:** Human verify checkpoint
- **Issue:** Browser applies 8px margin to `<body>` by default; visible as gap around the full-viewport layout
- **Fix:** Added `<style>` block in `index.html`: `*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; } body { overflow: hidden; }`
- **Files:** `frontend/demo/index.html`

## Next Phase Readiness

**Ready:**
- `frontend/demo/` builds independently → ready for `vercel deploy` in Phase 06
- `frontend/operator/` unaffected — type-checks clean
- Both apps share identical canvas engine; any Phase 06 canvas fix applies to both via manual sync

**Concerns:**
- Shared source files (types, fit, canvas) are duplicated — if Phase 06 changes ForceCanvas in operator, demo must be manually synced
- Demo has no loading state or error boundary — acceptable for v0.1 portfolio

**Blockers:**
- None

---
*Phase: 05-frontend, Plan: 07*
*Completed: 2026-03-15*
