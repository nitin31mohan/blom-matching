# Skill: Similarity and Embedding Computation

## Purpose

Build and query the pairwise affinity matrix across all attendees
registered for a given event. Produces the similarity scores that
the constrained assignment algorithm uses to form groups.

Load this skill before any APPLY that touches `src/matching/similarity.py`.

---

## Core concept

Each attendee is represented by a `UserFeatureVector` produced by the
feature engineering module. Similarity between two attendees is the
**cosine similarity** of their weighted, L2-normalised feature vectors.

Because vectors are L2-normalised at the end of the feature engineering
step, cosine similarity reduces to a dot product:

```
similarity(a, b) = dot(a.vector, b.vector)
```

This is fast, numerically stable, and scales well to the corpus sizes
Blom will encounter (10–500 attendees per event).

---

## Affinity matrix

For an event with N attendees, the affinity matrix is an N × N symmetric
matrix where entry `[i, j]` is the cosine similarity between attendee i
and attendee j. The diagonal is 1.0 (every attendee is perfectly similar
to themselves) and is ignored in all downstream computations.

```python
AffinityMatrix = {
    "event_id":    str,
    "user_ids":    list[str],          # pipeline_user_ids, ordered — index maps to matrix row/col
    "matrix":      np.ndarray,         # shape (N, N), dtype float32
    "computed_at": str,                # ISO 8601 timestamp
}
```

Store `user_ids` alongside the matrix so that row/column indices can
always be resolved back to `pipeline_user_id` without ambiguity.

---

## Module: `src/matching/similarity.py`

### `build_affinity_matrix(feature_vectors: list[UserFeatureVector]) -> AffinityMatrix`

Accepts the full list of feature vectors for an event.
Returns the affinity matrix.

Implementation:

```python
import numpy as np

def build_affinity_matrix(feature_vectors):
    user_ids = [fv["user_id"] for fv in feature_vectors]
    vectors = np.array([fv["vector"] for fv in feature_vectors], dtype=np.float32)
    # Vectors are already L2-normalised by the feature engineering module.
    # Cosine similarity = dot product for normalised vectors.
    matrix = vectors @ vectors.T
    # Clip to [-1, 1] to guard against floating point drift
    matrix = np.clip(matrix, -1.0, 1.0)
    return {
        "event_id":    feature_vectors[0]["event_id"],
        "user_ids":    user_ids,
        "matrix":      matrix,
        "computed_at": datetime.utcnow().isoformat(),
    }
```

### `top_k_similar(affinity: AffinityMatrix, user_id: str, k: int = 5) -> list[tuple[str, float]]`

Returns the k most similar attendees to a given user, excluding the user
themselves. Returns a list of `(pipeline_user_id, score)` tuples sorted
by score descending.

Used by the LLM explanation layer to describe who a user is most
compatible with.

### `group_cohesion_score(affinity: AffinityMatrix, group_user_ids: list[str]) -> float`

Returns the mean pairwise similarity for all pairs within a group.
Used as the primary quality signal for group fitness — this is the number
that drives the green/amber/red colour coding on the canvas UI.

```
cohesion = mean of affinity[i][j] for all i != j within the group
```

### `group_fit_color(cohesion: float) -> str`

Maps cohesion score to a traffic-light classification:

| Cohesion | Label     | Hex       |
| -------- | --------- | --------- |
| >= 0.68  | Great fit | `#22c55e` |
| >= 0.42  | Okay fit  | `#f59e0b` |
| < 0.42   | Poor fit  | `#ef4444` |

These thresholds are configurable in `config/matching.yaml` under
`fit_thresholds`. They will be revised once post-event feedback data
is available.

### `marginal_cohesion(affinity: AffinityMatrix, candidate_id: str, group_user_ids: list[str]) -> float`

Returns the mean similarity between a candidate user and all current
members of a group. Used by the assignment algorithm to evaluate the
cost of adding a user to a group before committing.

---

## Handling sparse profiles

Users with `"low_profile_confidence"` flag (3+ imputed fields) produce
less reliable similarity scores. Handle these as follows:

- Compute their similarity normally — do not exclude or special-case them
  in the matrix
- Pass the flag through to the assignment module so the LLM explanation
  layer can note "low profile confidence" when explaining that user's
  placement
- Do not artificially inflate or deflate their scores

---

## Handling near-duplicate vectors

Two users with near-identical quiz responses will have similarity close
to 1.0. This is valid data — they are genuinely similar. Do not deduplicate
or merge them. The assignment algorithm handles this naturally (they will
likely end up in the same group, which is correct).

---

## Incremental updates

When the operator drags a user to a new group on the canvas, the UI
needs to display updated cohesion scores immediately. The full affinity
matrix does not need to be recomputed — only `group_cohesion_score` and
`marginal_cohesion` need to be called with the new group membership.

The matrix itself is computed once per event load and cached in the
operator session. Expose it as a serialisable dict so the API can return
it to the frontend in a single response.

---

## Performance expectations

| N attendees | Matrix build time | Notes                       |
| ----------- | ----------------- | --------------------------- |
| 20          | < 1ms             | Trivial                     |
| 100         | < 5ms             | NumPy dot product           |
| 500         | < 50ms            | Still NumPy — no GPU needed |

No optimisation beyond NumPy is required for v1. If Blom ever reaches
1000+ attendees per event, switch to batched computation or approximate
nearest neighbours (Faiss or similar) — but that is explicitly out of
scope for now.

---

## Implementation notes for Claude Code

- All similarity logic lives in `src/matching/similarity.py`
- Only dependencies: `numpy`, `datetime` from stdlib
- No ML frameworks required — this is linear algebra, not deep learning
- The `group_fit_color` thresholds must match the constants used in the
  canvas UI (`frontend/operator/src/canvas/ForceCanvas.tsx`) — define
  them once in `config/matching.yaml` and read from there in both the
  Python backend and the TypeScript frontend
- Serialise the affinity matrix as a nested list (not `ndarray`) when
  returning it from the API — JSON does not support NumPy types

---

## Acceptance criteria

### AC-1: Symmetry

```
Given an affinity matrix built from N feature vectors
When any entry matrix[i][j] is compared to matrix[j][i]
Then they are equal to within 1e-6
```

### AC-2: Diagonal

```
Given an affinity matrix built from N feature vectors
When the diagonal is inspected
Then all diagonal entries equal 1.0 to within 1e-6
```

### AC-3: Score range

```
Given an affinity matrix built from any valid feature vectors
When all entries are inspected
Then all values are in the range [-1.0, 1.0]
```

### AC-4: Cohesion ordering

```
Given three groups:
  group_identical — all members have identical feature vectors
  group_random    — members drawn randomly
  group_opposing  — members drawn from polar-opposite edge cases
When group_cohesion_score is computed for each
Then cohesion(group_identical) > cohesion(group_random) > cohesion(group_opposing)
```

### AC-5: Marginal cohesion used correctly

```
Given a group of 4 users and a candidate user
When marginal_cohesion is computed for the candidate against the group
Then the result equals the mean of the 4 individual similarity scores
  between the candidate and each group member
```

### AC-6: Incremental update does not recompute matrix

```
Given an affinity matrix already built for an event
When a user is moved to a new group
Then group_cohesion_score is called with the new membership
And build_affinity_matrix is NOT called again
```
