# Skill: Constrained Group Assignment

## Purpose

Assign attendees to groups for a given event, maximising within-group
cohesion while respecting hard and soft constraints. Produces the initial
group allocation that the operator reviews and optionally overrides via
the canvas UI.

Load this skill before any APPLY that touches `src/matching/assignment.py`
or `src/matching/constraints.py`.

---

## Problem definition

Given:

- N attendees with pairwise similarity scores from the affinity matrix
- A target group size G (typically 4–6)
- A set of hard constraints (must-be-together, must-not-be-together)
- A set of soft constraints (gender balance, anxiety flags)

Produce:

- K groups of approximately G members each
- Maximising mean within-group cohesion across all groups
- With all hard constraints satisfied
- With soft constraint violations minimised and flagged

---

## Algorithm: greedy graph partitioning

For Blom's corpus sizes (10–500 per event), a greedy approach is
sufficient and fast. Do not implement ILP or Hungarian algorithm for v1 —
the greedy approach is easier to explain, debug, and override manually.

### Step 1 — Hard constraint pre-processing

Before any assignment, resolve hard constraints:

1. Collect all friend pairs (`friend_pair_id` groups) — these users must
   be assigned to the same group
2. Collect any must-not-be-together constraints if present (v1: none by
   default, but the data model should support them)
3. Merge friend pairs into "super-nodes" for the purpose of assignment —
   treat each pair as a single unit that occupies 2 seats in a group
4. Validate that no friend pair exceeds `target_group_size - 1` members
   (a pair of 6 cannot fit in a group of 5) — emit an error, not a
   silent failure

### Step 2 — Seed selection

For each group to be formed, select a seed attendee:

- Sort all unassigned attendees by their mean similarity to all other
  unassigned attendees (descending) — most "central" attendee first
- The first seed is the most central unassigned attendee
- Subsequent seeds are chosen by maximum distance from all already-chosen
  seeds — this spreads groups across the personality space and avoids
  all seeds clustering in the same region

### Step 3 — Greedy fill

For each group in turn (round-robin across groups until all attendees
are assigned):

- Find the unassigned attendee (or super-node) with the highest
  marginal cohesion to the current group
- Assign them to that group
- Continue until the group reaches `target_group_size` or no unassigned
  attendees remain

### Step 4 — Remainder handling

When N does not divide evenly by G:

- Compute the remainder R = N mod G
- The R remainder attendees are assigned to the groups where their
  marginal cohesion is highest — even if those groups already have G members
- Groups may have G or G+1 members — never G-1 (prefer slightly large
  groups over undersized ones)
- Emit a soft flag `"oversized_group"` on any group that exceeds G members

### Step 5 — Soft constraint evaluation

After initial assignment, evaluate soft constraints and emit flags:

| Constraint                                              | Flag emitted                                         |
| ------------------------------------------------------- | ---------------------------------------------------- |
| Group mean anxiety score > 3.5                          | `"high_anxiety_group"`                               |
| Gender imbalance > 75% one gender (singles events only) | `"gender_imbalance"`                                 |
| Any user with `"low_profile_confidence"` flag           | `"uncertain_placement"`                              |
| Group cohesion < 0.42                                   | `"low_cohesion"` — triggers LLM review automatically |

Flags are attached to the group object, not to individual users (except
`uncertain_placement` which is also attached to the user).

### Step 6 — Optional local search improvement

After greedy assignment, run a single pass of swap improvement:

- For every pair of attendees in different groups, compute the change in
  total cohesion if they were swapped
- Execute the swap if it strictly improves total cohesion without
  violating any hard constraint
- A single pass is sufficient — do not iterate to convergence for v1

---

## Data model

### `GroupAssignment`

```python
GroupAssignment = {
    "group_id":        str,           # UUID
    "event_id":        str,
    "label":           str,           # "Group A", "Group B", etc.
    "member_ids":      list[str],     # pipeline_user_ids
    "cohesion_score":  float,         # from group_cohesion_score()
    "fit_color":       str,           # "#22c55e" / "#f59e0b" / "#ef4444"
    "flags":           list[str],     # soft constraint violations
    "override_log":    list[dict],    # operator manual overrides, append-only
}
```

### `AssignmentResult`

```python
AssignmentResult = {
    "event_id":        str,
    "groups":          list[GroupAssignment],
    "unassigned":      list[str],     # pipeline_user_ids — should be empty
    "total_cohesion":  float,         # mean cohesion across all groups
    "flags":           list[str],     # event-level flags
    "algorithm":       str,           # "greedy_v1" — for traceability
    "computed_at":     str,           # ISO 8601
}
```

---

## Module: `src/matching/assignment.py`

### `assign_groups(affinity: AffinityMatrix, feature_vectors: list[UserFeatureVector], event: dict, config: dict) -> AssignmentResult`

Main entry point. Accepts the affinity matrix, feature vectors (for
constraint evaluation), the event object (for `event_type` and
`target_group_size`), and the runtime config dict.

Returns a complete `AssignmentResult`.

### `apply_override(result: AssignmentResult, move: OperatorOverride) -> AssignmentResult`

Applies a single operator override (drag-and-drop or panel reassignment)
to an existing result. Returns a new `AssignmentResult` with updated
cohesion scores, flags, and an entry appended to the group's
`override_log`.

Does NOT re-run the full assignment algorithm — only updates the affected
groups' cohesion scores and flags.

```python
OperatorOverride = {
    "user_id":      str,    # pipeline_user_id being moved
    "from_group":   str,    # group_id
    "to_group":     str,    # group_id
    "reason":       str,    # optional free text from operator
    "timestamp":    str,    # ISO 8601
}
```

### Module: `src/matching/constraints.py`

Defines and validates hard and soft constraints. Separating this from
`assignment.py` keeps the constraint logic independently testable.

```python
def validate_hard_constraints(feature_vectors, config) -> list[str]:
    """Returns a list of constraint violation messages. Empty = all clear."""

def extract_friend_pairs(feature_vectors) -> list[list[str]]:
    """Returns list of groups of pipeline_user_ids that must be co-assigned."""

def evaluate_soft_constraints(group, feature_vectors, event_type) -> list[str]:
    """Returns list of flag strings for a single group."""
```

---

## Override log

The `override_log` on each group is append-only and persisted for the
full lifecycle of the event. It is used by:

- The LLM explanation layer — to note when a group was manually adjusted
- The evaluation module — to distinguish algorithm-assigned pairs from
  human-overridden pairs when computing post-event feedback signal
- The portfolio demo — to show recruiters that the system supports
  human-in-the-loop correction

---

## Write-back to Blom's backend

After the operator is satisfied with the groups, the operator tool calls
a write-back endpoint that:

1. Resolves all `pipeline_user_id` values back to `blom_user_id` using
   the in-memory reverse mapping
2. Posts the final group assignments to Blom's backend in whatever format
   the existing system expects (TBD with the Blom founder)
3. Clears the reverse mapping from session memory

Write-back is a one-shot operation, not a streaming sync. The operator
confirms before triggering it. This is a button in the UI, not an
automatic action.

---

## Configuration keys (`config/matching.yaml`)

```yaml
assignment:
  target_group_size: 5
  max_group_overage: 1 # Groups may be at most target_group_size + 1
  seed_strategy: "max_distance" # or "random" for testing
  run_swap_improvement: true
  fit_thresholds:
    great: 0.68
    okay: 0.42
  soft_constraint_thresholds:
    max_anxiety_mean: 3.5
    max_gender_imbalance: 0.75
```

---

## Implementation notes for Claude Code

- All assignment logic lives in `src/matching/assignment.py`
- Constraint logic lives in `src/matching/constraints.py`
- Dependencies: `numpy`, `uuid`, `datetime` — no external packages
- The swap improvement step must check hard constraints before executing
  any swap — a swap that breaks a friend pair must be rejected silently
- Group labels ("Group A", "Group B", ...) are assigned alphabetically
  in order of seed selection — deterministic given the same affinity matrix
  and seed
- The `algorithm` field in `AssignmentResult` must be set to a versioned
  string (e.g. `"greedy_v1"`) so that future algorithm changes can be
  tracked in the evaluation module

---

## Acceptance criteria

### AC-1: Hard constraints satisfied

```
Given two users with matching friend_pair_id
When assign_groups() is called
Then both users appear in the same group in the result
And this holds regardless of their similarity scores
```

### AC-2: Group size bounds

```
Given N=23 attendees and target_group_size=5
When assign_groups() is called
Then no group has fewer than 5 members
And no group has more than 6 members
And result.unassigned is empty
```

### AC-3: Remainder handled without undersized groups

```
Given N=22 attendees and target_group_size=5
When assign_groups() is called
Then groups have sizes summing to 22
And no group has fewer than 5 members
And the flag "oversized_group" appears on any group with 6 members
```

### AC-4: Swap improvement does not violate hard constraints

```
Given a result where two users are in the same group due to friend_pair_id
When swap improvement runs
Then the two users remain in the same group after improvement
```

### AC-5: Override log append

```
Given an AssignmentResult with one group
When apply_override() is called moving a user to a different group
Then the source group's override_log has one new entry
And the entry contains user_id, from_group, to_group, and timestamp
And the cohesion scores of both affected groups are updated
```

### AC-6: Total cohesion improves or holds after swap pass

```
Given an AssignmentResult produced by greedy assignment
When the swap improvement pass runs
Then result.total_cohesion after swap >= result.total_cohesion before swap
```

### AC-7: Gender imbalance flag (singles events)

```
Given a singles event
And a proposed group where 4 of 5 members share the same gender
When evaluate_soft_constraints() is called
Then the flag "gender_imbalance" is present in the returned list
```

### AC-8: Determinism

```
Given the same affinity matrix and config
When assign_groups() is called twice
Then both results have identical group membership
```
