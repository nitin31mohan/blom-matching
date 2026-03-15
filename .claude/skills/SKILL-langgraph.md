# Skill: LangGraph Agentic Workflow

## Purpose

Implement the human-in-the-loop review layer that sits between the
assignment algorithm and the operator. Takes a proposed `AssignmentResult`,
runs it through a LangGraph workflow that generates plain-English
explanations and flags for each group, and returns a reviewed result
ready for the operator to inspect and override.

Load this skill before any APPLY that touches `src/agent/`.

---

## Workflow overview

```
AssignmentResult
      │
      ▼
 [explain_groups]  ── calls LLM once per group
      │
      ▼
 [flag_review]     ── evaluates flags, decides if human pause needed
      │
      ├─ flags present ──▶ [human_checkpoint]  ── pauses for operator input
      │                          │
      │                    operator provides
      │                    override or approval
      │                          │
      └─ no flags ───────────────┤
                                 ▼
                          [compile_output]  ── assembles final ReviewedResult
```

The workflow is implemented as a LangGraph `StateGraph`. Each node is a
pure function that transforms the state dict. No side effects inside nodes —
all I/O (API calls, DB writes) happens at the edges of the graph.

---

## State schema

```python
AgentState = {
    # Inputs (set before graph entry)
    "assignment":       AssignmentResult,
    "feature_vectors":  list[UserFeatureVector],
    "event":            dict,

    # Set by explain_groups
    "group_explanations": list[GroupExplanation],

    # Set by flag_review
    "requires_human":   bool,
    "flagged_groups":   list[str],   # group_ids that need attention

    # Set by human_checkpoint (if reached)
    "operator_notes":   str,         # free text from operator
    "overrides":        list[OperatorOverride],

    # Set by compile_output
    "reviewed_result":  ReviewedResult,
}
```

---

## Data models

### `GroupExplanation`

```python
GroupExplanation = {
    "group_id":          str,
    "summary":           str,         # 2–3 sentence plain English summary
    "compatibility":     str,         # One sentence on why they fit (or don't)
    "flags_explained":   list[str],   # Human-readable explanation of each flag
    "confidence":        str,         # "high" / "medium" / "low"
    "suggested_action":  str | None,  # Suggestion if confidence is medium/low
}
```

### `ReviewedResult`

```python
ReviewedResult = {
    "event_id":           str,
    "groups":             list[GroupAssignment],    # from assignment module
    "explanations":       list[GroupExplanation],   # from explain_groups node
    "operator_notes":     str,
    "overrides_applied":  list[OperatorOverride],
    "workflow_trace_id":  str,    # LangSmith trace ID for this run
    "reviewed_at":        str,    # ISO 8601
}
```

---

## Node: `explain_groups`

Calls the LLM once per group. Constructs a prompt that includes:

- The group's Big Five proxy scores (from `feature_vectors`)
- The group's cohesion score and fit colour
- Any flags on the group
- The event type (singles vs social)

Returns a `GroupExplanation` for each group.

### Prompt template (`src/agent/prompts.py`)

```
SYSTEM:
You are an assistant helping an event organiser review algorithmically
proposed social groups. Your job is to explain each group in plain English
so the organiser can decide whether to approve or adjust it.

Be concise and specific. Do not use jargon. Refer to attendees by their
group position (e.g. "the most extroverted member") — never by name or ID.

USER:
Event type: {event_type}
Group label: {group_label}
Group size: {group_size}
Cohesion score: {cohesion_score:.2f} ({fit_label})
Flags: {flags_list}

Member profiles (Big Five proxies, scored 0.0–1.0):
{member_profiles_table}

Write:
1. A 2–3 sentence summary of who this group is.
2. One sentence on why they are (or are not) a good fit for each other.
3. For each flag, one sentence explaining what it means in plain English.
4. A confidence level: high / medium / low.
5. If confidence is medium or low, one concrete suggestion for improvement.

Respond in JSON matching this schema:
{schema}
```

### Structured output schema (`src/agent/schemas.py`)

Use Pydantic to define `GroupExplanationSchema` and pass it to the LLM
via `model.with_structured_output(GroupExplanationSchema)`. This ensures
the explanation is always parseable — never rely on free-text parsing.

```python
class GroupExplanationSchema(BaseModel):
    summary:           str
    compatibility:     str
    flags_explained:   list[str]
    confidence:        Literal["high", "medium", "low"]
    suggested_action:  str | None
```

---

## Node: `flag_review`

Examines all `GroupExplanation` objects. Sets `requires_human = True` if
any of the following conditions are met:

| Condition                                                | Rationale                             |
| -------------------------------------------------------- | ------------------------------------- |
| Any group has `confidence = "low"`                       | LLM is uncertain — human should check |
| Any group has flag `"low_cohesion"`                      | Algorithm produced a poor group       |
| Any group has flag `"gender_imbalance"` (singles events) | Sensitive constraint violated         |
| More than 25% of groups have `confidence = "medium"`     | Too many uncertain placements         |

If `requires_human = False`, the workflow skips `human_checkpoint` and
proceeds directly to `compile_output`.

---

## Node: `human_checkpoint`

This is a LangGraph interrupt node — it pauses the workflow and returns
control to the operator via the API. The operator sees:

- All group explanations
- The flagged groups highlighted
- A text field for notes
- Buttons to approve, override individual groups, or re-run the algorithm

When the operator submits their response, the workflow resumes with
`operator_notes` and `overrides` set in the state.

Implementation: use LangGraph's `interrupt()` primitive. The API route
`POST /api/matching/resume` resumes the graph with the operator's input.

The workflow state is serialised to the operator session between interrupt
and resume — it is NOT persisted to any external store in v1.

---

## Node: `compile_output`

Assembles the final `ReviewedResult` from the state. Applies any
`overrides` from the operator (by calling `apply_override` from the
assignment module). Attaches the LangSmith trace ID. Returns the result.

---

## LangSmith tracing

Every workflow run must be traced. Configure in `src/agent/workflow.py`:

```python
from langsmith import traceable

@traceable(name="blom-group-review")
def run_review_workflow(assignment, feature_vectors, event):
    ...
```

Trace metadata to attach:

- `event_id`
- `event_type`
- `n_groups`
- `n_attendees`
- `algorithm_version`

Never attach attendee names, emails, or real IDs to traces. Only
`pipeline_user_id` values if user-level detail is needed.

---

## Model selection

Use `claude-haiku-4-5` for `explain_groups` — it is fast, cheap, and
sufficient for structured explanation tasks. The prompt is constrained
enough that a smaller model handles it reliably.

Do not use a larger model unless `confidence = "low"` explanations
consistently contain errors — revisit this decision after 10+ real events.

---

## Override parsing

When the operator types a natural language override (e.g. "move Attendee 3
from Group A to Group C"), parse it in `compile_output` using a lightweight
LLM call with a structured output schema:

```python
class OverrideParseSchema(BaseModel):
    pipeline_user_id:  str | None   # None if ambiguous
    from_group_label:  str | None
    to_group_label:    str | None
    is_ambiguous:      bool
    clarification_needed: str | None
```

If `is_ambiguous = True`, return the `clarification_needed` message to
the operator before applying anything.

---

## Cost controls

- Hard cap `max_tokens = 400` on all `explain_groups` calls — explanations
  must be concise
- Batch all group explanation calls as parallel async requests — do not
  call the LLM sequentially per group
- Log token usage per run in the LangSmith trace metadata

---

## Implementation notes for Claude Code

- The LangGraph graph is defined in `src/agent/workflow.py`
- Prompts live in `src/agent/prompts.py` as plain string constants —
  no templating library, use Python f-strings
- Pydantic schemas live in `src/agent/schemas.py`
- The graph must be compiled once at module load and reused across
  requests — do not recompile on every API call
- Use `asyncio.gather` for parallel LLM calls in `explain_groups`
- LangSmith requires `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true`
  in `.env` — add both to `.env.example`

---

## Acceptance criteria

### AC-1: Structured output always parseable

```
Given any valid AssignmentResult passed to explain_groups
When the LLM responds
Then the response is parsed into GroupExplanationSchema without error
And no group has a missing summary, compatibility, or confidence field
```

### AC-2: Human checkpoint triggers correctly

```
Given an AssignmentResult with one group flagged "low_cohesion"
When the workflow runs
Then requires_human is True
And the workflow pauses at human_checkpoint
And the API returns the flagged group's explanation to the operator
```

### AC-3: Workflow skips checkpoint when clean

```
Given an AssignmentResult with no flags
And all groups have cohesion > 0.68
When the workflow runs
Then requires_human is False
And the workflow proceeds directly to compile_output
And a ReviewedResult is returned without operator input
```

### AC-4: Override applied correctly

```
Given an operator override moving pipeline_user_id X from Group A to Group B
When compile_output runs
Then X appears in Group B's member_ids
And X no longer appears in Group A's member_ids
And Group A and Group B's cohesion scores are updated
And the override appears in the reviewed_result.overrides_applied list
```

### AC-5: No PII in LangSmith traces

```
Given a workflow run with real (stripped) attendee data
When the LangSmith trace is inspected
Then no entry in the trace payload contains a string matching
  any attendee's display_name
And no Blom user IDs appear in the trace
```

### AC-6: Parallel LLM calls

```
Given an event with 5 groups
When explain_groups runs
Then all 5 LLM calls are made concurrently
And total wall-clock time is less than 1.5× the time of a single call
```
