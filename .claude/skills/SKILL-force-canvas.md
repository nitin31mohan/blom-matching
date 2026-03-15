# Skill: Force-Directed Canvas UI

## Purpose

Build the interactive group canvas that is the primary interface for both
the operator tool (Prong 1) and the portfolio demo (Prong 2). The canvas
renders attendees as draggable nodes on a physics-based force layout,
with group membership encoded as convex hull overlays and fit quality
encoded as node colour.

Load this skill before any APPLY that touches `frontend/operator/src/canvas/`
or `frontend/demo/src/`.

---

## Design reference

The target aesthetic is spatial and physical — nodes have mass, they
bounce when thrown, they settle into clusters. The operator should feel
like they are arranging people in a room, not filling in a spreadsheet.

Key interactions:

- **Drag and throw** — nodes follow the cursor; release with velocity and
  they continue moving before settling
- **Group reassignment** — dropping a node near a different group's hull
  reassigns it automatically; cohesion scores update immediately
- **Click to inspect** — clicking a stationary node opens a detail panel
  showing the attendee's Big Five proxies and fit score
- **Edit and save** — fields in the detail panel are editable and write
  back to the API (operator tool only; read-only in demo)
- **Event switcher** — a top bar control switches between events,
  reloading the canvas with the new event's attendees

---

## Tech stack

| Concern          | Library              | Notes                                                             |
| ---------------- | -------------------- | ----------------------------------------------------------------- |
| Force simulation | `d3-force` (v7)      | Collision, charge, group-centering forces                         |
| Rendering        | SVG via D3           | Not Canvas — SVG gives accessible DOM nodes for click handlers    |
| State management | Zustand              | Single store for groups, scores, panel state                      |
| Animations       | CSS transitions + D3 | Panel open/close via CSS; node movement via D3 tick               |
| Framework        | React 18             | Components wrap D3 — D3 owns the SVG DOM, React owns the UI shell |

**Important:** D3 must own the SVG DOM for the force simulation to work
correctly. Do not attempt to manage SVG nodes as React state — React
manages the container `<div>` and the detail panel; D3 manages everything
inside `<svg>`.

---

## Component structure

```
frontend/operator/src/
├── canvas/
│   ├── ForceCanvas.tsx          # Main component — mounts D3 simulation
│   ├── useForceSimulation.ts    # Custom hook — initialises and manages D3
│   ├── AttendeeNode.tsx         # D3-rendered node (not a React component)
│   └── GroupHull.tsx            # D3-rendered convex hull overlay
├── panels/
│   ├── AttendeeDetail.tsx       # Click-to-inspect panel (React)
│   └── GroupSummary.tsx         # Group cohesion + LLM explanation panel
├── store/
│   └── canvas.store.ts          # Zustand store
└── App.tsx
```

---

## `useForceSimulation.ts`

The core hook. Initialises the D3 force simulation and returns refs to
the SVG and simulation objects.

### Forces

```typescript
const simulation = d3
  .forceSimulation(nodes)
  .force("collision", d3.forceCollide(NODE_RADIUS + 6))
  .force("charge", d3.forceManyBody().strength(-60))
  .force("groupX", d3.forceX((d) => groupCenter(d.groupId).x).strength(0.15))
  .force("groupY", d3.forceY((d) => groupCenter(d.groupId).y).strength(0.15))
  .alphaDecay(0.02);
```

Group centers are computed from the canvas dimensions as fixed fractions:

- Group A: (0.25, 0.38)
- Group B: (0.62, 0.32)
- Group C: (0.78, 0.65)
- Group D: (0.35, 0.70)

Recalculate on canvas resize using a `ResizeObserver`.

### Throw physics

On drag end, carry the cursor velocity into the node:

```typescript
.on('end', (event, d) => {
  simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
  // Carry velocity — multiply by throw factor
  d.vx = lastDeltaX * THROW_FACTOR;
  d.vy = lastDeltaY * THROW_FACTOR;
  simulation.alpha(0.5).restart();
  // Check proximity to group centers for reassignment
  checkGroupReassignment(d, event.x, event.y);
})
```

`THROW_FACTOR = 5.0` — tunable in `config/canvas.ts`.

### Group reassignment on drop

After a throw or drag release, check if the node's final position is
within `REASSIGNMENT_RADIUS = 110px` of a different group's center.
If so:

1. Update `d.groupId` in the node data
2. Update the Zustand store
3. Recalculate cohesion scores for the affected groups
4. Restart the simulation with `alpha(0.4)` to let the node settle
5. If operator tool: fire the override API call

---

## Node rendering

Nodes are `<g>` elements appended to the SVG by D3. Each node contains:

```svg
<g class="attendee-node" transform="translate(x, y)">
  <circle r="18" fill="{fitColor}" stroke="{groupColor}" stroke-width="2.5"/>
  <text class="initial" text-anchor="middle" dominant-baseline="central">{initial}</text>
  <text class="name" y="26" text-anchor="middle">{firstName}</text>
</g>
```

### Fit colour mapping

Match the Python backend constants exactly — read from a shared config:

| Cohesion | Fill colour       |
| -------- | ----------------- |
| >= 0.68  | `#22c55e` (green) |
| >= 0.42  | `#f59e0b` (amber) |
| < 0.42   | `#ef4444` (red)   |

Node fill is the attendee's individual fit score within their current
group (computed by `marginal_cohesion` on the backend, returned in the
API response). This updates reactively when the node is moved.

### Group hull rendering

Convex hulls are `<path>` elements rendered behind the nodes. Use
`d3.polygonHull` on the node positions + a 28px padding ring:

```typescript
const padded = nodePositions.flatMap(([x, y]) =>
  Array.from(
    { length: 8 },
    (_, i) =>
      [
        x + 28 * Math.cos((i * Math.PI) / 4),
        y + 28 * Math.sin((i * Math.PI) / 4),
      ] as [number, number],
  ),
);
const hull = d3.polygonHull(padded);
```

Hull fill: group colour at 7% opacity. Hull stroke: group colour at 18%
opacity, dashed (5 3). Group label text sits 38px above the hull centroid.

---

## `AttendeeDetail.tsx`

A React component rendered as an absolutely positioned panel over the
canvas. Opens when the user clicks a stationary node. Closes on the ×
button, on clicking another node, or on clicking the canvas background.

### Panel contents

- Attendee display name (first name only)
- Current group label and group colour indicator
- Big Five proxy bars (5 traits, each a labelled horizontal bar 0–1)
- Individual fit score with traffic-light colour and label
- "Move to group" buttons for all other groups (click to reassign without
  dragging)
- **Operator tool only:** editable Likert sliders for each quiz response
  with a "Save changes" button that calls `PATCH /api/users/{pipeline_user_id}`

### Reactivity

The panel must update in real-time if the open attendee's fit score
changes (e.g. because another attendee in their group was moved). Subscribe
to the Zustand store for this.

---

## Zustand store (`canvas.store.ts`)

```typescript
type CanvasStore = {
  // Data
  event: Event | null;
  groups: GroupAssignment[];
  attendees: AnonymisedAttendee[];
  affinityMatrix: number[][]; // N×N, indexed by attendee order
  userIndex: Map<string, number>; // pipeline_user_id → matrix index

  // UI state
  selectedNodeId: string | null;
  panelOpen: boolean;

  // Actions
  loadEvent: (eventId: string) => Promise<void>;
  moveAttendee: (userId: string, toGroupId: string) => void;
  updateProfile: (
    userId: string,
    updates: Partial<QuizResponse>,
  ) => Promise<void>;
  recomputeScores: () => void;
};
```

`recomputeScores` recomputes all group cohesion scores client-side using
the cached affinity matrix — no API call needed. This is what makes
group reassignment feel instant.

---

## Demo prong differences

The demo (`frontend/demo/`) shares all canvas components but differs in:

| Concern           | Operator tool               | Portfolio demo                    |
| ----------------- | --------------------------- | --------------------------------- |
| Data source       | API with auth               | `synthetic-seed.ts` (static JSON) |
| Profile editing   | Enabled                     | Disabled                          |
| Write-back button | Present                     | Hidden                            |
| Auth              | Required                    | None                              |
| Node names        | Real first names (stripped) | Synthetic names                   |

Implement the data source difference via a React context provider:
`CanvasDataProvider`. The operator tool wraps the canvas in
`<ApiDataProvider>`; the demo wraps it in `<SyntheticDataProvider>`.
The canvas components themselves never know which provider they are under.

---

## Accessibility

- All interactive nodes must have `role="button"` and `aria-label="{name}, {group}, {fit}"`
- The detail panel must be keyboard-navigable (Tab between fields, Escape
  to close)
- Colour alone must not be the only fit signal — add a shape indicator:
  a small checkmark inside great-fit nodes, a dot inside okay nodes,
  an exclamation inside poor-fit nodes

---

## Performance targets

| Scenario                          | Target           |
| --------------------------------- | ---------------- |
| Initial render (20 nodes)         | < 100ms          |
| Group reassignment + score update | < 50ms perceived |
| Canvas resize reflow              | < 200ms          |
| Detail panel open                 | < 30ms           |

No virtual DOM diffing happens inside the SVG — D3 handles all updates
directly. Keep React out of the inner render loop.

---

## Implementation notes for Claude Code

- D3 is imported as `import * as d3 from 'd3'` — use the full bundle,
  not tree-shaken submodules, to avoid module resolution issues
- The simulation is initialised in a `useEffect` with an empty dependency
  array — it runs once on mount
- The `tick` callback must be stable — do not recreate it on every render
- Fit threshold constants must be imported from a shared config file
  (`src/config/thresholds.ts`) that mirrors `config/matching.yaml` — keep
  them in sync manually or via a build step
- The convex hull computation runs on every simulation tick — it is cheap
  for N < 50 but profile it if you notice jank at larger sizes

---

## Acceptance criteria

### AC-1: Throw and settle

```
Given a node dragged and released with high velocity
When the drag end handler fires
Then the node continues moving in the direction of the throw
And decelerates and settles within 2 seconds
And does not leave the canvas bounds
```

### AC-2: Group reassignment on drop

```
Given a node dragged and dropped within 110px of a different group center
When the drag end handler fires
Then the node's groupId is updated to the new group
And the convex hull of both affected groups updates within one tick
And the cohesion scores of both groups update immediately
And the node's fill colour reflects its new fit score
```

### AC-3: Click does not fire after throw

```
Given a node that was thrown (high drag velocity)
When the throw animation is still running
Then clicking the node does not open the detail panel
```

### AC-4: Detail panel reactivity

```
Given the detail panel is open for attendee A in Group X
When another attendee in Group X is moved to a different group
Then the fit score displayed in the panel updates without closing
  and reopening the panel
```

### AC-5: Demo provider isolation

```
Given the canvas mounted under SyntheticDataProvider
When updateProfile() is called
Then no API call is made
And the change is applied only to local Zustand state
```

### AC-6: Operator tool write-back

```
Given a node moved to a new group in the operator tool
When the reassignment completes
Then a POST /api/matching/override request is made with the correct
  pipeline_user_id, from_group, and to_group
And the request is made exactly once per reassignment
```
