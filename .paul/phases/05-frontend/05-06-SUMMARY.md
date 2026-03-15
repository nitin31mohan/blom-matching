---
phase: 05-frontend
plan: 06
subsystem: ui
tags: [react, typescript, svg, pointer-events, touch, drag-to-bin, group-deletion]

requires:
  - phase: 05-05
    provides: Freeze/straggler workflow, placeAllStragglers, isFrozen threading, node locking

provides:
  - Dynamic GROUP_LAYOUT reactive state (groupLayout useState replacing hardcoded constant)
  - handleDeleteGroup: dissolves group, redistributes members as stragglers via placeAllStragglers
  - Drag-to-bin group deletion (grip handle on GroupHull → dustbin drop zone in canvas corner)
  - Pointer Events API migration (onPointerDown + window pointermove/pointerup, touch-action: none)
  - Expanded 44px tap targets on AttendeeNode (invisible r=22 hit area circle)
  - GroupLayout interface in types.ts (canonical type for layout entries)

affects: [05-07, phase-06]

tech-stack:
  added: []
  patterns:
    - Hull drag handle: DragHandle SVG component at top-right of each group, onDragHandlePointerDown prop
    - Dustbin zone: fixed bottom-right SVG element, visible only during hull drag, highlights on hover
    - Pointer Events with window listeners: onPointerDown on node → window pointermove/pointerup (no setPointerCapture — avoids click routing side-effect)
    - touch-action: none on SVG root — prevents browser scroll during drag without needing pointer capture
    - DEFAULT_GROUP_LAYOUT + GROUP_LAYOUT alias: backward-compat export pattern for renamed constants

key-files:
  created: []
  modified:
    - frontend/operator/src/types.ts
    - frontend/operator/src/canvas/mock-data.ts
    - frontend/operator/src/App.tsx
    - frontend/operator/src/canvas/GroupHull.tsx
    - frontend/operator/src/canvas/ForceCanvas.tsx
    - frontend/operator/src/canvas/AttendeeNode.tsx

key-decisions:
  - "Window listeners over setPointerCapture: capture caused click events to route to SVG, firing onClearSelection and immediately deselecting nodes"
  - "DEFAULT_GROUP_LAYOUT + GROUP_LAYOUT alias: ForceCanvas import unchanged; App uses reactive state"
  - "DragHandle as standalone SVG component inside GroupHull: grip icon with transparent 20×20 hit area"

patterns-established:
  - "setPointerCapture avoided for node/hull drag — window listeners preserve normal click event routing"
  - "Dustbin zone: threshold check pos.x > width - 76 && pos.y > height - 76 in pointerup handler"
  - "handleDeleteGroup: remainingLayout guard (length === 0 → no-op), placeAllStragglers for redistribution, setStragglerMessage for feedback"

duration: ~2h
started: 2026-03-15T00:00:00Z
completed: 2026-03-15T00:00:00Z
---

# Phase 05 Plan 06: Group Deletion + Touch/Pointer Events Summary

**Dynamic GROUP_LAYOUT state, drag-to-bin group dissolution with straggler redistribution, and full Pointer Events API migration — all with one post-checkpoint fix for click detection via window listeners.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2h (tasks + 1 post-checkpoint fix) |
| Started | 2026-03-15 |
| Completed | 2026-03-15 |
| Tasks | 2 auto + 1 human-verify + 1 post-checkpoint fix |
| Files created | 0 |
| Files modified | 6 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Group deletion dissolves and redistributes | Pass | placeAllStragglers called with remainingGroupIds; members show yellow pulse |
| AC-2: Cannot delete last group | Pass | `remainingLayout.length === 0` guard in handleDeleteGroup → early return |
| AC-3: Dustbin zone highlights on hover | Pass | `isOverDustbin` derived from hullDragPos vs threshold; dark red fill when over |
| AC-4: Node drag works on touch | Pass | Pointer Events + touch-action: none; DevTools simulation verified |
| AC-5: Locked nodes click-select on touch | Pass | Fixed via window listeners (no capture side-effect) |
| AC-6: Expanded 44px tap targets | Pass | Invisible `<circle r={22} fill="transparent">` as first child of AttendeeNode `<g>` |
| AC-7: TypeScript compiles clean | Pass | npm run type-check → exit 0; npm run build → clean |

## Accomplishments

- Built drag-to-bin group deletion: grip handle (3-line SVG icon) on each GroupHull, dustbin drop zone in canvas bottom-right corner; dropping over zone calls `handleDeleteGroup` in App — members redistributed as yellow-pulsing stragglers via existing `placeAllStragglers`
- Made `GROUP_LAYOUT` reactive: `groupLayout` useState in App initialized from `DEFAULT_GROUP_LAYOUT`; resets on handleReset and handleEventChange; removing a group updates layout in real-time
- Migrated all canvas drag from mouse events to Pointer Events API: `onPointerDown` on nodes and hull handles, `window.addEventListener('pointermove'/'pointerup')` for global tracking, `touch-action: none` on SVG root

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/types.ts` | Modified | Added `GroupLayout` interface (group_id, color, cx, cy) |
| `src/canvas/mock-data.ts` | Modified | `DEFAULT_GROUP_LAYOUT` + `GROUP_LAYOUT` alias for backward compat |
| `src/App.tsx` | Modified | `groupLayout` state, `handleDeleteGroup`, `onDeleteGroup` → ForceCanvas, reset in handleReset/handleEventChange |
| `src/canvas/GroupHull.tsx` | Modified | `DragHandle` SVG component, `onDragHandlePointerDown` prop, grip icon in both hull branches |
| `src/canvas/ForceCanvas.tsx` | Modified | `draggingGroupId`/`hullDragPos` state, `makeHullDragHandler`, dustbin SVG, pointer events migration, `GroupLayout[]` type, `onDeleteGroup` prop |
| `src/canvas/AttendeeNode.tsx` | Modified | `onDragStart` as `React.PointerEvent`, `onPointerDown`, expanded r=22 hit area |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Window listeners over setPointerCapture | Capture routes click events to SVG, firing onClearSelection immediately after node selection | Node click-select works correctly on mouse and touch |
| DEFAULT_GROUP_LAYOUT + GROUP_LAYOUT alias | Keeps ForceCanvas import unchanged while App gains reactive state | Zero breaking changes to ForceCanvas consumers |
| DragHandle as standalone SVG component | Reused in both polygon-hull and circle-hull branches of GroupHull | Single implementation, consistent grip icon in both rendering paths |
| Dustbin only visible during hull drag | Reduces visual noise; signals intent (drag started → bin appears) | Cleaner canvas; bin can't be accidentally triggered without intent |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed (post-checkpoint) | 1 | Selection regression; essential fix |
| Scope additions | 0 | None |
| Deferred | 0 | None |

**Total impact:** One post-checkpoint fix for node click regression; no scope creep.

### Auto-fixed Issues

**1. Node click-select broken after pointer events migration**
- **Found during:** Human verify checkpoint (user reported detail panel stopped populating)
- **Issue:** `svgEl.setPointerCapture(e.pointerId)` routed the subsequent `click` event to the SVG root. SVG's `onClick` checked `e.target === e.currentTarget` → true → `onClearSelection()` fired, immediately deselecting the node just clicked
- **Fix:** Removed `setPointerCapture` from node drag and locked-node path; switched to `window.addEventListener('pointermove'/'pointerup')`. `touch-action: none` on SVG root already prevents browser scroll without requiring capture. Same fix applied to `makeHullDragHandler`.
- **Files:** `frontend/operator/src/canvas/ForceCanvas.tsx`

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `setPointerCapture` on SVG re-routes click to capturing element | Switched to window listeners; touch-action: none handles scroll prevention instead |

## Next Phase Readiness

**Ready:**
- `handleDeleteGroup` calls `placeAllStragglers` — same pattern Phase 06 Supabase wiring will use
- `groupLayout` state is Phase 06-ready: real group data from DB replaces `DEFAULT_GROUP_LAYOUT` init
- Pointer Events migration complete — canvas is tablet-friendly
- `onDeleteGroup` prop wired through App → ForceCanvas → GroupHull

**Concerns:**
- Hull grip handle position is computed from label coordinates — if label moves significantly (very large/small groups), handle may drift. Acceptable for now.
- Group creation is not implemented — admins can only delete existing groups, not add new ones. Out of scope for v0.1.

**Blockers:**
- None

---
*Phase: 05-frontend, Plan: 06*
*Completed: 2026-03-15*
