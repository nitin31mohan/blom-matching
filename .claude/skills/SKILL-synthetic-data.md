# Skill: Synthetic Data Generation

## Purpose

Generate realistic, statistically plausible fake Blom attendee profiles
for use during development and testing. No real user data is required or
touched at any point during Phase 01 or 02.

Load this skill before any APPLY that touches `src/data/synthetic.py`.

---

## Core principles

- All generated users are assigned a UUID — never a sequential integer ID
- Names are randomly composed from diverse name pools (do not use a fixed
  list of 20 names — generate from first-name and last-name pools of 200+
  entries each covering multiple cultural backgrounds)
- Quiz response distributions should reflect realistic human behaviour,
  not uniform random noise — see distribution rules below
- Edge cases must be explicitly seeded, not left to chance — see edge case
  catalogue below
- Generated data is written to `data/synthetic/` and gitignored if > 1MB

---

## Distribution rules

Uniform random draws produce unrealistic data. The following rules govern
how each field is distributed across a synthetic population.

### Likert fields

Most Likert responses in real survey data cluster toward the centre and
upper end (acquiescence bias). Use the following sampling weights for all
Likert fields unless a field-specific override is given below:

```python
LIKERT_WEIGHTS = {1: 0.08, 2: 0.14, 3: 0.28, 4: 0.32, 5: 0.18}
```

**Field-specific overrides:**

| Field                          | Rationale                                                             | Override weights                                |
| ------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------- |
| `anxious_in_social_situations` | Blom self-selects for socially motivated people — anxiety skews lower | `{1: 0.22, 2: 0.30, 3: 0.26, 4: 0.14, 5: 0.08}` |
| `comfortable_knowing_nobody`   | Same self-selection — skews higher                                    | `{1: 0.06, 2: 0.10, 3: 0.22, 4: 0.36, 5: 0.26}` |
| `shows_up_on_time`             | Conscientiousness skews high in event sign-up contexts                | `{1: 0.04, 2: 0.08, 3: 0.20, 4: 0.38, 5: 0.30}` |

### Trait correlations

Real personality data has inter-trait correlations. Implement these as
soft nudges, not hard rules — use a correlation matrix to generate
correlated Likert draws via a Gaussian copula or a simpler post-hoc
adjustment:

| Field A                         | Field B                             | Direction | Strength |
| ------------------------------- | ----------------------------------- | --------- | -------- |
| `energised_meeting_people`      | `comfortable_knowing_nobody`        | positive  | 0.55     |
| `energised_meeting_people`      | `anxious_in_social_situations`      | negative  | -0.50    |
| `enjoys_unfamiliar_experiences` | `interested_in_current_events`      | positive  | 0.40     |
| `keeps_atmosphere_harmonious`   | `messages_regularly_after_clicking` | positive  | 0.35     |
| `eco_friendly_choices`          | `spirituality_importance`           | positive  | 0.25     |
| `physical_activity_routine`     | `weekend_energy_level` (high)       | positive  | 0.45     |

A simple implementation: generate all Likert fields independently using
the weight tables, then apply a post-hoc swap algorithm that brings the
correlation matrix within 0.1 of the target values. Exact match is not
required — plausibility is.

### Categorical fields

| Field                     | Distribution                                                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `gender`                  | 52% woman / 48% man (reflects typical dating/social app skew)                                                                          |
| `industry`                | Weight toward: Technology 18%, Finance 12%, Healthcare 10%, Education 9%, Creative/Media 8%, other options share the remainder equally |
| `country`                 | For a London-based service: GB 45%, IE 8%, IN 7%, AU 6%, US 5%, ZA 4%, FR 4%, DE 3%, other 18%                                         |
| `humour_style`            | `playful` 35%, `situational_observational` 30%, `witty_sarcastic` 25%, `bold_edgy` 10%                                                 |
| `conversation_style`      | Equal weight across options once confirmed with operator                                                                               |
| `weekend_energy_level`    | High 30%, Medium 45%, Low 25%                                                                                                          |
| `preferred_activity_time` | Morning 20%, Afternoon 35%, Evening 45%                                                                                                |
| `religious_identity`      | No religion 40%, Christian 25%, Muslim 12%, Hindu 8%, Jewish 3%, Buddhist 3%, other 9%                                                 |

---

## Edge case catalogue

These must be explicitly present in every generated dataset of 50+ users.
Seed them deliberately — do not rely on random chance to produce them.

| Edge case              | Minimum count        | Description                                                                   |
| ---------------------- | -------------------- | ----------------------------------------------------------------------------- |
| Friend pair            | 2 pairs per 50 users | Two users with matching `friend_pair_id` field set to a shared UUID           |
| High anxiety outlier   | 1 per 30 users       | `anxious_in_social_situations` = 5                                            |
| Low profile confidence | 1 per 25 users       | 3+ fields set to `null` (will trigger imputation)                             |
| Remainder user         | Varies               | Total attendees for an event that does not divide evenly by target group size |
| Near-identical twins   | 1 pair per 50 users  | Two users with Likert values differing by at most 1 on every field            |
| Polar opposites        | 1 pair per 50 users  | Two users with Likert values differing by 3–4 on every field                  |
| Ungroupable singleton  | 1 per 100 users      | User whose profile is an outlier on 4+ dimensions simultaneously              |

---

## Event fixture schema

Synthetic datasets are always generated in the context of a fake event.
Each event fixture includes:

```python
EventFixture = {
    "event_id":    str,          # UUID
    "event_name":  str,          # Human-readable, e.g. "Pub quiz — Fri 21 Mar"
    "event_type":  str,          # "singles" or "social"
    "target_group_size": int,    # Typically 4–6
    "max_groups":  int,          # Maximum number of groups for this event
    "attendees":   list[RawQuizResponse],  # Generated users for this event
}
```

Provide at least three canned event fixtures:

| Fixture name     | Event type | Attendee count | Notes                                             |
| ---------------- | ---------- | -------------- | ------------------------------------------------- |
| `small_social`   | social     | 18             | Divides evenly into groups of 6                   |
| `medium_singles` | singles    | 23             | Does NOT divide evenly — tests remainder handling |
| `large_social`   | social     | 47             | Tests performance at realistic scale              |

---

## Generator interface

All synthetic data is produced through a single entry point in
`src/data/synthetic.py`:

```python
def generate_event_fixture(
    event_type: str,            # "singles" or "social"
    n_attendees: int,
    target_group_size: int = 5,
    seed: int | None = None,    # For reproducibility in tests
    edge_cases: bool = True,    # Inject edge case users
) -> EventFixture:
    ...

def generate_user(
    seed: int | None = None,
) -> RawQuizResponse:
    ...
```

The `seed` parameter must produce fully deterministic output when set.
Test fixtures must always pass an explicit seed.

---

## Output

Write generated fixtures to `data/synthetic/` as JSON:

```
data/synthetic/
├── small_social_seed42.json
├── medium_singles_seed42.json
└── large_social_seed42.json
```

Also expose a CLI entry point for ad-hoc generation:

```bash
python -m src.data.synthetic --event-type social --n 30 --seed 7 --output data/synthetic/custom.json
```

---

## Implementation notes for Claude Code

- Use `numpy.random.default_rng(seed)` for all random draws — not
  `random` or `numpy.random` legacy API
- The Gaussian copula for correlated Likert draws can be approximated
  with `numpy.random.multivariate_normal` — generate standard normals
  with the target correlation matrix, then map to Likert values via the
  weight-table quantiles
- Name pools live in `src/data/name_pools.py` as plain Python lists —
  no external dependency needed
- All `null` fields for low-profile-confidence users must be set
  explicitly, not omitted from the dict — the feature engineering module
  expects all 20 keys to be present

---

## Acceptance criteria

### AC-1: Reproducibility

```
Given generate_event_fixture(event_type="social", n_attendees=20, seed=42)
  is called twice
When the outputs are compared
Then both outputs are byte-for-byte identical
```

### AC-2: Distribution plausibility

```
Given a generated dataset of 200 users
When the distribution of anxious_in_social_situations is measured
Then values 1 and 2 together account for more than 40% of responses
And value 5 accounts for less than 15% of responses
```

### AC-3: Trait correlation

```
Given a generated dataset of 500 users
When the Pearson correlation between energised_meeting_people
  and anxious_in_social_situations is computed
Then the correlation is between -0.65 and -0.35
```

### AC-4: Edge cases present

```
Given generate_event_fixture(n_attendees=50, edge_cases=True)
When the attendee list is inspected
Then at least 2 users have a non-null friend_pair_id
And at least 1 user has anxious_in_social_situations = 5
And at least 1 user has 3 or more null fields
And at least 1 pair of users exists whose Likert values differ
  by at most 1 on every field
```

### AC-5: Remainder user present

```
Given generate_event_fixture(n_attendees=23, target_group_size=5)
When groups are later assigned
Then the assignment module receives a corpus that does not
  divide evenly — confirmed by (23 % 5) != 0
```

### AC-6: CLI entry point

```
Given python -m src.data.synthetic --event-type singles --n 15 --seed 1
  is run from the project root
When the command completes
Then a valid JSON file is written to data/synthetic/
And the file contains exactly 15 attendee records
```
