# Skill: PII Handling and Data Anonymisation

## Purpose

Define the rules and utilities for handling personally identifiable
information (PII) across the Blom matching system. Ensures that real
user data never appears in the demo prong, logs, traces, or test
fixtures — and that the operator prong handles it with appropriate care.

Load this skill before any APPLY that touches real user data, the
anonymiser module, or the API routes that receive data from Blom's
existing backend.

---

## PII classification for Blom data

| Field                          | Classification                   | Notes                                               |
| ------------------------------ | -------------------------------- | --------------------------------------------------- |
| Full name                      | PII — high sensitivity           | Never stored in matching pipeline                   |
| Email address                  | PII — high sensitivity           | Never stored in matching pipeline                   |
| Phone number                   | PII — high sensitivity           | Never stored in matching pipeline                   |
| Profile photo                  | PII — high sensitivity           | Never stored in matching pipeline                   |
| Date of birth                  | PII — medium sensitivity         | Age band only, if needed                            |
| Device ID / IP                 | PII — medium sensitivity         | Never logged                                        |
| `user_id` (Blom's internal ID) | PII — low sensitivity            | Replaced with UUID at pipeline boundary             |
| Quiz responses                 | Pseudonymous                     | Low sensitivity individually; linkable in aggregate |
| `country`                      | Pseudonymous                     | Keep — needed for matching logic                    |
| `religious_identity`           | Sensitive category (GDPR Art. 9) | Keep for matching but never log in plain text       |
| `gender`                       | Sensitive category (GDPR Art. 9) | Keep for matching but never log in plain text       |

---

## The pipeline boundary rule

This is the single most important rule in this skill:

> **Real PII must be stripped at the point of entry into the matching
> pipeline. It must never travel further than the boundary function.**

Concretely: when the operator tool receives an attendee list from Blom's
backend, `anonymiser.strip_pii()` is called immediately — before any
feature engineering, before any logging, before any LangGraph call.

The anonymised record that travels through the pipeline contains:

- A fresh UUID (`pipeline_user_id`) — not Blom's internal user ID
- A mapping entry stored only in the operator tool's session (never
  persisted to disk or sent to any external service): `pipeline_user_id
→ blom_user_id`
- All 20 quiz response fields
- A display name for the UI: **first name only** — no surname, no email

The reverse mapping (UUID → Blom user ID) is held in memory for the
duration of the operator session so that group assignment results can be
written back to Blom's DB at the end.

---

## Module: `src/data/anonymiser.py`

### `strip_pii(raw_attendee: dict) -> AnonymisedAttendee`

Accepts a raw attendee record as received from Blom's backend.
Returns an `AnonymisedAttendee` with PII removed and a fresh UUID assigned.

```python
AnonymisedAttendee = {
    "pipeline_user_id": str,   # Fresh UUID — used throughout the pipeline
    "display_name":     str,   # First name only — for UI display
    "quiz_responses":   dict,  # All 20 quiz fields, unchanged
}
```

Rules:

- `pipeline_user_id` is generated with `uuid.uuid4()` — never derived
  from any real identifier
- `display_name` is extracted as the first token of the full name field,
  split on whitespace — if the name field is absent or blank, use
  `"Attendee"` + a 4-digit random suffix
- All other fields not in `quiz_responses` are dropped silently — no
  logging of dropped fields

### `build_reverse_mapping(stripped_list: list[AnonymisedAttendee], original_list: list[dict]) -> dict`

Returns `{pipeline_user_id: blom_user_id}` for write-back at session end.
This dict lives only in memory — never written to disk or sent over the
network.

### `export_for_demo(stripped_list: list[AnonymisedAttendee]) -> list[dict]`

Produces a fully anonymised export suitable for the portfolio demo or for
sharing publicly. Additional steps beyond `strip_pii`:

- Replace `display_name` with a synthetic name drawn from the name pools
  in `src/data/name_pools.py` — no connection to any real person
- Perturb each Likert value by ±1 with 40% probability (preserving the
  1–5 range) — breaks any possible re-identification via quiz fingerprint
- Replace `country` with a randomly sampled country from the same region
  (e.g. GB → one of: GB, IE, FR, DE, NL) — preserves regional plausibility
- Replace `religious_identity` with a randomly sampled value from the
  full taxonomy — severs any link to the real person's identity
- Assign a new UUID — different from the pipeline UUID

The output of `export_for_demo` is what populates `data/synthetic/` for
the portfolio demo. It must never be traceable back to a real Blom user.

---

## Logging rules

These rules apply everywhere in the codebase — in API routes, LangGraph
nodes, FastAPI middleware, and LangSmith traces.

**Never log:**

- Any field classified as PII — high or medium sensitivity (see table above)
- The reverse mapping dict
- Raw attendee records before `strip_pii` has been called
- Full quiz response objects tagged with any real identifier
- `religious_identity` or `gender` as plain-text strings in any log line

**Safe to log:**

- `pipeline_user_id` (the UUID assigned by the pipeline)
- `event_id`
- Aggregate statistics (group count, mean fit score, flag count)
- LangGraph node names and execution times
- Error types and stack traces — but scrub any dict that might contain PII
  before logging an exception

**LangSmith traces specifically:**
LangSmith traces are sent to an external service. Before any LangGraph
workflow is called with attendee data, confirm that the input payload
contains only `pipeline_user_id` values and quiz responses — never display
names, never Blom user IDs. The LLM prompt templates in `src/agent/prompts.py`
must reference users by `pipeline_user_id` and group label only.

---

## GDPR considerations

This system processes data about UK and EU residents. The following
minimum requirements apply:

- `religious_identity` and `gender` are special category data under GDPR
  Article 9. Your friend (as data controller) is responsible for ensuring
  that the Blom sign-up flow obtains explicit consent for using these
  fields in automated matching decisions.
- The matching pipeline constitutes automated processing that produces
  effects on individuals (which group they are placed in). Document this
  in the system's README so your friend can assess whether a DPIA
  (Data Protection Impact Assessment) is required.
- Do not add any analytics, telemetry, or third-party tracking to the
  operator tool without explicit instruction.

> **Note:** You are not a lawyer and this skill does not constitute legal
> advice. Flag these points to your friend and suggest he consults a
> GDPR-aware solicitor if unsure — especially before launching the singles
> event product commercially.

---

## Demo prong data contract

The portfolio demo (`frontend/demo/`) must satisfy all of the following:

- Loads data only from `data/synthetic/` or from `export_for_demo()` output
- Never makes API calls that return real attendee data
- Never accepts a real Blom user ID as input (no query params, no URL paths)
- The synthetic seed file is committed to the repo and reviewed before
  commit to confirm it contains no real names, emails, or identifiers

---

## Implementation notes for Claude Code

- `anonymiser.py` has zero external dependencies beyond the Python
  standard library and `uuid`
- The reverse mapping dict is initialised in the operator tool's API
  session state (`src/api/routes/matching.py`) and discarded when the
  session ends — it is never persisted
- Add a pre-commit hook or CI check that scans `data/synthetic/` for
  strings matching common email patterns (`@`) and common UK mobile
  formats (`07\d{9}`) — fail the check if any are found
- `export_for_demo` must be callable independently of the operator tool
  so that synthetic exports can be regenerated without running a full
  operator session

---

## Acceptance criteria

### AC-1: PII stripped at boundary

```
Given a raw attendee record containing name, email, phone, and quiz fields
When strip_pii() is called
Then the returned AnonymisedAttendee contains no name, email, or phone
And it contains a valid UUID as pipeline_user_id
And it contains a display_name with no surname
And all 20 quiz fields are present and unchanged
```

### AC-2: Reverse mapping correctness

```
Given a list of 10 raw attendees passed through strip_pii()
When build_reverse_mapping() is called with the stripped list
  and the original list
Then the returned dict has exactly 10 entries
And each pipeline_user_id maps to the correct original blom_user_id
```

### AC-3: Demo export untraceability

```
Given the same raw attendee passed through export_for_demo() twice
  with different random seeds
When the two outputs are compared
Then display_name, religious_identity, country, and pipeline_user_id
  differ between the two outputs
And no Likert value in the output matches the original value
  more than 90% of the time across a batch of 100 users
```

### AC-4: No PII in demo seed files

```
Given all JSON files in data/synthetic/
When each file is scanned for email patterns and phone patterns
Then no matches are found
```

### AC-5: LangSmith trace safety

```
Given a LangGraph workflow run with a stripped attendee list
When the LangSmith trace payload is inspected
Then no entry in the payload contains a string matching
  any of the original attendees' full names or email addresses
```
