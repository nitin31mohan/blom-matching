# Skill: Feature Engineering for Psychographic Matching

## Purpose

Transform raw Blom quiz responses into a weighted feature vector suitable
for cosine similarity computation and constrained group assignment.

Load this skill before any APPLY that touches `src/features/`.

---

## Input schema

The raw input per user is a JSON object with 20 keyed fields.

| Key | Type | Notes |
|-----|------|-------|
| `gender` | binary string | `"man"` or `"woman"` |
| `industry` | categorical string | One of ~15 fixed options |
| `country` | categorical string | ISO 3166-1 alpha-2 code |
| `energised_meeting_people` | int 1–5 | Likert |
| `keeps_atmosphere_harmonious` | int 1–5 | Likert |
| `enjoys_unfamiliar_experiences` | int 1–5 | Likert |
| `shows_up_on_time` | int 1–5 | Likert |
| `anxious_in_social_situations` | int 1–5 | Likert |
| `interested_in_current_events` | int 1–5 | Likert |
| `religious_identity` | categorical string | Free taxonomy, ~20 options |
| `spirituality_importance` | int 1–5 | Likert |
| `eco_friendly_choices` | int 1–5 | Likert |
| `physical_activity_routine` | int 1–5 | Likert |
| `conversation_style` | categorical string | Options TBC from operator |
| `messages_regularly_after_clicking` | int 1–5 | Likert |
| `comfortable_knowing_nobody` | int 1–5 | Likert |
| `shares_personal_stories` | int 1–5 | Likert |
| `weekend_energy_level` | categorical string | Options TBC |
| `preferred_activity_time` | categorical string | e.g. morning / afternoon / evening |
| `humour_style` | categorical string | `"playful"` / `"witty_sarcastic"` / `"bold_edgy"` / `"situational_observational"` |

---

## Encoding rules

### Likert items (13 fields)

Min-max scale to [0, 1] over the fixed range [1, 5]:

```
scaled = (raw - 1) / 4
```

Do NOT z-score. Absolute position is meaningful — a group of all 5s is
genuinely different from a group of all 3s.

> **Special case — `anxious_in_social_situations`:** Scale normally, but
> also emit a flag `"high_anxiety"` on any user whose raw value >= 4. Groups
> where mean anxiety exceeds 3.5 trigger an LLM flag regardless of overall
> fit score.

### Binary field (`gender`)

Encode as `0` (man) / `1` (woman). Never used as a similarity signal
directly. Applied only as a soft constraint — see Event-type modifiers.

### Ordinal categoricals with natural order

Applies to: `weekend_energy_level`, `preferred_activity_time`.

Assign integer ranks preserving the natural order, then scale to [0, 1].
Treat as continuous for similarity. Example:

```
preferred_activity_time: morning=0, afternoon=0.5, evening=1.0
```

### Nominal categoricals — no natural order

Applies to: `industry`, `conversation_style`, `humour_style`.

One-hot encode. Similarity between two users on these dimensions is binary:
same option = 1, different option = 0. Do NOT use ordinal encoding.

### Sensitive categoricals (`country`, `religious_identity`)

Controlled by a runtime config flag `sensitive_field_mode`. Three modes:

| Mode | Behaviour |
|------|-----------|
| `"affinity"` | One-hot encode and include in similarity vector — like with like |
| `"diversity"` | Invert the similarity contribution — different is rewarded |
| `"neutral"` | Exclude from vector entirely (default) |

**Default: `"neutral"`** until post-event feedback validates which mode
predicts good outcomes for Blom's specific context.

Implement as a config dict switch, not separate code paths.

---

## Big Five proxy dimensions

Derive these from quiz items and store alongside the raw vector. Used
exclusively by the LLM explanation layer — not fed into cosine similarity.

| Proxy | Source questions | Derivation |
|-------|-----------------|------------|
| Extraversion | `energised_meeting_people`, `comfortable_knowing_nobody` | Mean of scaled values |
| Neuroticism | `anxious_in_social_situations` | Scaled value (display as reversed polarity: "Emotional stability") |
| Openness | `enjoys_unfamiliar_experiences`, `interested_in_current_events`, `eco_friendly_choices` | Mean of scaled values |
| Conscientiousness | `shows_up_on_time` | Scaled value |
| Agreeableness | `keeps_atmosphere_harmonious`, `messages_regularly_after_clicking` | Mean of scaled values |

---

## Feature weighting

Applied as a scalar multiplier on each dimension group before the vector
is normalised. Store as a config dict — the operator UI will expose sliders
for these in a later phase.

| Dimension group | Fields | Default weight |
|----------------|--------|---------------|
| Social energy | `energised_meeting_people`, `anxious_in_social_situations`, `comfortable_knowing_nobody`, `shares_personal_stories` | `1.5` |
| Values alignment | `interested_in_current_events`, `spirituality_importance`, `eco_friendly_choices` | `1.2` |
| Activity compatibility | `physical_activity_routine`, `weekend_energy_level`, `preferred_activity_time` | `1.2` |
| Relational style | `keeps_atmosphere_harmonious`, `shows_up_on_time`, `messages_regularly_after_clicking` | `1.0` |
| Humour style | `humour_style` | `1.0` |
| Conversation style | `conversation_style` | `1.0` |
| Industry | `industry` | `1.0` |
| Sensitive fields | `country`, `religious_identity` | `0.0` (neutral mode default) |

---

## Event-type modifiers

Applied as post-encoding vector transforms based on `event.event_type`.
Store `event_type` on the event object — never infer it from the event name.

**Singles events (`event_type: "singles"`):**
- Multiply social energy dimension weights by an additional `1.3×`
- Emit a soft flag `"gender_imbalance"` on any proposed group that is
  more than 75% one gender

**Social events (`event_type: "social"`):**
- Multiply values alignment dimension weights by an additional `1.2×`
- No gender constraint applied

---

## Missing data handling

Users who skipped optional fields receive the **event-level population
median** for that field, computed across all users registered for the
same event. Do not use the global population median.

Log all imputed fields in the user's feature object. Emit flag
`"low_profile_confidence"` for users with 3 or more imputed fields.

---

## Output schema

```python
UserFeatureVector = {
    "user_id":        str,         # UUID — never a real identifier
    "event_id":       str,
    "raw_encoded":    dict,        # All 20 fields, encoded pre-weighting
    "vector":         list[float], # Weighted, L2-normalised — used for cosine sim
    "big_five":       dict,        # 5 proxy scores for LLM explanation layer
    "imputed_fields": list[str],   # Fields filled by event-level median
    "flags":          list[str],   # e.g. "high_anxiety", "low_profile_confidence"
}
```

The `vector` field must be **L2-normalised** before storage so that cosine
similarity reduces to a dot product at query time.

---

## Implementation notes for Claude Code

- All encoding logic lives in `src/features/encoder.py`
- Weight config lives in `src/features/weights.py` as a plain dict — no
  magic, no ORM
- Event-type modifiers are applied in `src/features/modifiers.py`,
  called after encoding, before normalisation
- Sensitive field mode is read from `config/matching.yaml` at runtime
- Unit tests live in `tests/features/` — one test file per module above
- No external ML libraries required for this module — pure Python + NumPy

---

## Acceptance criteria

### AC-1: Encoding correctness

```
Given a raw quiz response with all 20 fields present
When build_feature_vector() is called
Then all Likert values in the output vector are in [0.0, 1.0]
And all nominal categoricals are one-hot encoded
And the output vector length equals the expected dimension count for the current config
```

### AC-2: Weight application

```
Given two users with identical profiles
  except user_a has energised_meeting_people=5
  and   user_b has energised_meeting_people=1
When their vectors are compared with a third user
Then the social energy dimension contributes proportionally more to
  their distance than an equivalent difference on a 1.0x weight field
```

### AC-3: Missing data imputation

```
Given a user with 3 skipped fields
And an event with at least 5 other registrants
When build_feature_vector() is called
Then imputed_fields lists the 3 skipped keys
And each imputed value equals the event-level median for that field
And the flag "low_profile_confidence" is present in flags
```

### AC-4: Sensitive field config

```
Given sensitive_field_mode = "affinity"
When feature vectors are built
Then country and religious_identity are included in the similarity vector

Given sensitive_field_mode = "neutral"
When feature vectors are built
Then country and religious_identity are absent from the similarity vector
And their weights are 0.0
```

### AC-5: Event-type modifier — singles

```
Given an event with event_type = "singles"
And a proposed group that is 80% one gender
When group flags are evaluated
Then the flag "gender_imbalance" is present on that group
```
