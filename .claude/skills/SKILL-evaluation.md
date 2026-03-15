# Skill: Evaluation Framework

## Purpose

Define how the matching system is measured, both before post-event data
exists (proxy metrics) and after (feedback-driven reweighting). This skill
is what separates a working algorithm from a trustworthy one — and it is
the most directly portfolio-relevant module in the project.

Load this skill before any APPLY that touches `src/evaluation/`.

---

## Two evaluation phases

### Phase A — Proxy metrics (available immediately)

Before any events have run, evaluate the algorithm using signals that
do not require ground-truth outcomes. These measure the structural
quality of assignments.

### Phase B — Feedback metrics (available after first real event)

After attendees submit post-event ratings, use their responses as a weak
supervision signal to validate and reweight the feature dimensions.

---

## Phase A: Proxy metrics

All proxy metrics are computed from `AssignmentResult` and
`AffinityMatrix` — no external data needed.

### Metric 1: Within-group cohesion distribution

For each event, compute the cohesion score of every group and report:

- Mean cohesion across all groups
- Standard deviation (low SD = consistent quality)
- Minimum cohesion (identifies the worst group)
- Percentage of groups in each fit tier (great / okay / poor)

```python
CohesionReport = {
    "event_id":     str,
    "mean":         float,
    "std":          float,
    "min":          float,
    "max":          float,
    "pct_great":    float,   # cohesion >= 0.68
    "pct_okay":     float,   # 0.42 <= cohesion < 0.68
    "pct_poor":     float,   # cohesion < 0.42
}
```

### Metric 2: Between-group separation

A good assignment not only maximises within-group similarity but also
produces groups that are meaningfully different from each other. Compute:

```
separation = mean pairwise cohesion between groups
           (i.e. mean similarity between members of different groups)
```

A high separation score relative to within-group cohesion means the
algorithm is doing real work — it is finding genuine clusters, not just
making arbitrary cuts.

Report the **contrast ratio**:

```
contrast_ratio = mean_within_cohesion / mean_between_cohesion
```

A contrast ratio > 1.2 is healthy. Below 1.05 suggests the feature space
has insufficient signal for meaningful grouping.

### Metric 3: Flag rate

The proportion of groups that received at least one soft constraint flag.
High flag rates indicate systematic issues:

| Flag rate | Interpretation                                                   |
| --------- | ---------------------------------------------------------------- |
| < 10%     | Healthy                                                          |
| 10–25%    | Monitor — check which flags are most common                      |
| > 25%     | Investigate — feature weights or constraints may need adjustment |

Report flag rates broken down by flag type.

### Metric 4: Override rate

The proportion of algorithm-proposed assignments that the operator
manually overrode. This is the most direct signal that the algorithm
is (or is not) producing trustworthy results.

```
override_rate = overrides_applied / total_attendees
```

Track this per event and over time. A decreasing override rate as events
accumulate is evidence that the algorithm is improving.

### Metric 5: Remainder quality

For events where N does not divide evenly by group size, the remainder
users are the hardest to place well. Report the mean cohesion of groups
that received a remainder attendee vs those that did not. If remainder
groups consistently score lower, the remainder placement heuristic may
need improvement.

---

## Phase B: Feedback metrics

### Feedback data model

Post-event ratings are collected by Blom's existing app. For the
matching system, the relevant fields are:

```python
PostEventRating = {
    "user_id":              str,    # pipeline_user_id
    "event_id":             str,
    "group_id":             str,
    "overall_experience":   int,    # 1–5
    "enjoyed_group":        int,    # 1–5  (did you enjoy your group?)
    "would_rebook":         bool,
    "clicked_with":         list[str],  # pipeline_user_ids they connected with
    "submitted_at":         str,
}
```

The `clicked_with` field is the richest signal — it is explicit pairwise
relevance feedback. Two attendees who both name each other in `clicked_with`
are a confirmed positive pair. Two attendees in the same group who neither
names the other are a soft negative signal.

### Metric 6: Group satisfaction score

```
group_satisfaction = mean(enjoyed_group) for all members who submitted ratings
```

Compute per group and per event. Correlate with cohesion score to validate
that the proxy metric predicts actual satisfaction.

**Target validation:** If `pearson_correlation(cohesion, group_satisfaction) > 0.4`
across 5+ events, the cohesion metric is a valid proxy. If not, the feature
weights need revisiting.

### Metric 7: Confirmed pair precision

```
confirmed_pair_precision =
    confirmed_positive_pairs_that_were_in_same_group /
    total_confirmed_positive_pairs
```

A confirmed positive pair is two attendees who both listed each other in
`clicked_with`. If the algorithm placed them in the same group, that is a
true positive.

This is the most direct measure of whether the similarity metric is
capturing what makes people click.

### Feature reweighting from feedback

When 3+ events have post-event ratings, run a feature importance analysis:

1. For each confirmed positive pair (A, B), compute the per-dimension
   contribution to their similarity score
2. For each unconfirmed pair in the same group (A, C where neither named
   the other in `clicked_with`), compute the same
3. The features that most distinguish positive pairs from unconfirmed pairs
   are the most predictive — increase their weight in `config/matching.yaml`
4. Features that show no difference between positive and unconfirmed pairs
   are noise — reduce their weight

This is not a gradient update — it is a manual analysis that produces
an updated weight config. Automate the analysis but keep the weight update
as a human decision. Emit a `WeightUpdateRecommendation` report rather than
automatically changing weights.

```python
WeightUpdateRecommendation = {
    "based_on_events":    list[str],    # event_ids used in analysis
    "n_positive_pairs":   int,
    "n_unconfirmed_pairs": int,
    "recommended_weights": dict,        # feature_name → new weight
    "confidence":         str,          # "high" / "medium" / "low"
    "notes":              str,          # plain English explanation
}
```

---

## Module: `src/evaluation/metrics.py`

### Functions to implement

```python
def cohesion_report(result: AssignmentResult, affinity: AffinityMatrix) -> CohesionReport

def contrast_ratio(result: AssignmentResult, affinity: AffinityMatrix) -> float

def flag_rate_report(result: AssignmentResult) -> dict[str, float]

def override_rate(result: AssignmentResult) -> float

def group_satisfaction_scores(ratings: list[PostEventRating]) -> dict[str, float]

def confirmed_pair_precision(
    result: AssignmentResult,
    ratings: list[PostEventRating]
) -> float

def weight_update_recommendation(
    events: list[tuple[AssignmentResult, AffinityMatrix, list[PostEventRating]]],
    current_weights: dict,
) -> WeightUpdateRecommendation
```

---

## Module: `src/evaluation/feedback.py`

Handles ingestion of post-event ratings from Blom's backend.

```python
def ingest_ratings(raw_ratings: list[dict], reverse_mapping: dict) -> list[PostEventRating]:
    """
    Converts Blom's raw rating format to PostEventRating objects.
    Resolves blom_user_ids back to pipeline_user_ids via reverse_mapping.
    Validates that all user_ids and group_ids exist in the corresponding
    AssignmentResult before ingesting.
    """

def resolve_confirmed_pairs(ratings: list[PostEventRating]) -> list[tuple[str, str]]:
    """
    Returns all (user_id_a, user_id_b) pairs where both users listed
    each other in clicked_with.
    """
```

---

## Evaluation dashboard (operator tool integration)

The operator tool should display a lightweight evaluation summary after
each event closes. This is a read-only panel showing:

- Cohesion report (bar chart: great / okay / poor)
- Override rate for the event vs running average
- Group satisfaction scores (once ratings are in)
- A call-to-action to run `weight_update_recommendation` when 3+ events
  have ratings

This panel is part of the Phase 05 (frontend) build — define the API
endpoint here and implement the UI there.

API endpoint: `GET /api/evaluation/{event_id}` — returns a combined
`EvaluationSummary` object.

---

## Portfolio narrative

When writing about this project on your website, the evaluation framework
is the story. The narrative is:

> "I didn't just build a matching algorithm — I built a system that
> measures its own quality, detects when it's underperforming, and
> generates recommendations for improvement from real-world feedback.
> The proxy metrics work before any events run. The feedback loop kicks
> in after the first real event. The weight recommendations are human-
> approved, not automatically applied — because the operator's judgment
> is the ground truth."

That is a senior IC story. It is what distinguishes this from a tutorial
project.

---

## Implementation notes for Claude Code

- All metric functions are pure — they take data objects and return
  numbers or reports, with no side effects
- No ML frameworks needed for Phase A metrics — pure Python + NumPy
- The reweighting analysis uses `scipy.stats.pearsonr` for correlation
  and a simple per-feature mean difference for importance — no sklearn
- Keep `metrics.py` and `feedback.py` strictly separated — metrics
  compute, feedback ingests
- All reports are serialisable dicts — no custom classes that can't be
  JSON-serialised

---

## Acceptance criteria

### AC-1: Cohesion report accuracy

```
Given an AssignmentResult with 4 groups with known cohesion scores
  [0.75, 0.60, 0.45, 0.30]
When cohesion_report() is called
Then mean ≈ 0.525
And pct_great ≈ 0.25
And pct_okay ≈ 0.50
And pct_poor ≈ 0.25
```

### AC-2: Contrast ratio > 1.0 for well-separated assignments

```
Given an AssignmentResult where within-group pairs are more similar
  than between-group pairs
When contrast_ratio() is called
Then the result is > 1.0
```

### AC-3: Override rate computation

```
Given an AssignmentResult for 20 attendees across 4 groups
And 3 operator overrides were applied
When override_rate() is called
Then the result equals 3/20 = 0.15
```

### AC-4: Confirmed pair precision

```
Given 10 confirmed positive pairs across an event
And 8 of those pairs were placed in the same group by the algorithm
When confirmed_pair_precision() is called
Then the result equals 0.80
```

### AC-5: Weight recommendation generated correctly

```
Given 3 events with post-event ratings
And feature dimension X consistently distinguishes positive pairs
  from unconfirmed pairs
When weight_update_recommendation() is called
Then dimension X has a higher recommended weight than its current weight
And the report includes n_positive_pairs, n_unconfirmed_pairs,
  and a confidence level
```
