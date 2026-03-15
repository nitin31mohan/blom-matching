# Skill: API and Deployment

## Purpose

Wrap the matching pipeline as a FastAPI service, expose the endpoints
consumed by the operator tool and portfolio demo, and deploy both the
backend and frontend to production.

Load this skill before any APPLY that touches `src/api/` or any
deployment configuration files.

---

## API design principles

- **Thin routes** — route handlers do nothing but validate input, call
  the appropriate service function, and serialise the response. All
  business logic lives in `src/matching/`, `src/agent/`, or
  `src/evaluation/`
- **Async throughout** — all I/O-bound operations (LLM calls, DB writes)
  are `async def`
- **Explicit error responses** — never return a 500 with a raw exception
  message. Every error case has a defined response schema
- **No auth on demo endpoints** — the demo prong is public; the operator
  endpoints require a static API key (Bearer token) in v1

---

## Route inventory

### Events

| Method | Path                          | Auth     | Description                                                                                               |
| ------ | ----------------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/events`                 | Operator | List all events                                                                                           |
| `GET`  | `/api/events/{event_id}`      | Operator | Get event details + attendee count                                                                        |
| `POST` | `/api/events/{event_id}/load` | Operator | Fetch attendees from Blom backend, strip PII, build feature vectors and affinity matrix, cache in session |

### Matching

| Method | Path                                 | Auth     | Description                                                          |
| ------ | ------------------------------------ | -------- | -------------------------------------------------------------------- |
| `POST` | `/api/matching/{event_id}/run`       | Operator | Run assignment + LangGraph review workflow. Returns `ReviewedResult` |
| `POST` | `/api/matching/{event_id}/override`  | Operator | Apply a single `OperatorOverride`. Returns updated groups + scores   |
| `POST` | `/api/matching/{event_id}/writeback` | Operator | Write final group assignments back to Blom backend                   |
| `POST` | `/api/matching/{event_id}/resume`    | Operator | Resume a paused LangGraph human checkpoint with operator input       |

### Users

| Method  | Path                            | Auth     | Description                                                                     |
| ------- | ------------------------------- | -------- | ------------------------------------------------------------------------------- |
| `PATCH` | `/api/users/{pipeline_user_id}` | Operator | Update a user's quiz responses; triggers feature vector and score recomputation |

### Evaluation

| Method | Path                                        | Auth     | Description                                      |
| ------ | ------------------------------------------- | -------- | ------------------------------------------------ |
| `GET`  | `/api/evaluation/{event_id}`                | Operator | Return `EvaluationSummary` for a completed event |
| `POST` | `/api/evaluation/{event_id}/ingest-ratings` | Operator | Ingest post-event ratings from Blom backend      |

### Demo

| Method | Path                 | Auth | Description                                                                    |
| ------ | -------------------- | ---- | ------------------------------------------------------------------------------ |
| `GET`  | `/api/demo/seed`     | None | Return a pre-generated synthetic `ReviewedResult` for the demo canvas          |
| `POST` | `/api/demo/override` | None | Apply an override to the demo state (in-memory only, resets on server restart) |

---

## Session state

The operator tool requires a server-side session to hold:

- The cached `AffinityMatrix` for the loaded event
- The reverse mapping (`pipeline_user_id → blom_user_id`)
- The paused LangGraph workflow state (if at a human checkpoint)

In v1, use a simple in-memory dict keyed by a session token (UUID issued
on `/api/events/{event_id}/load`). The session token is returned in the
response and sent as a header `X-Session-Token` on subsequent requests.

**Do not use a persistent session store in v1.** If the server restarts,
the operator must reload the event. This is acceptable at Blom's current
scale.

```python
SESSION_STORE: dict[str, OperatorSession] = {}

OperatorSession = {
    "event_id":       str,
    "affinity":       AffinityMatrix,
    "reverse_map":    dict[str, str],
    "workflow_state": AgentState | None,
    "created_at":     str,
    "last_active":    str,
}
```

Add a background task that clears sessions older than 4 hours.

---

## Rate limiting and spend controls

All endpoints — including demo endpoints — are rate limited. Use
`slowapi` (FastAPI-compatible rate limiting) with `upstash-redis` as the
backing store (free tier sufficient).

| Endpoint group                      | Limit                                      |
| ----------------------------------- | ------------------------------------------ |
| Operator endpoints                  | 60 requests / minute per API key           |
| `POST /api/matching/{event_id}/run` | 5 requests / minute per API key (LLM cost) |
| Demo endpoints                      | 20 requests / minute per IP                |
| `POST /api/demo/override`           | 30 requests / minute per IP                |

Additionally, set a hard monthly spend cap on the LLM API key at the
provider level (Anthropic console) — £10/month maximum. This is a safety
net, not a primary control.

---

## Request / response schemas

Define all schemas in `src/api/schemas.py` using Pydantic v2.

Key schemas:

```python
class RunMatchingRequest(BaseModel):
    target_group_size:     int = 5
    sensitive_field_mode:  Literal["neutral", "affinity", "diversity"] = "neutral"

class OverrideRequest(BaseModel):
    pipeline_user_id: str
    from_group_id:    str
    to_group_id:      str
    reason:           str = ""

class ResumeRequest(BaseModel):
    session_token:    str
    approved:         bool
    operator_notes:   str = ""
    overrides:        list[OverrideRequest] = []

class UserUpdateRequest(BaseModel):
    quiz_updates: dict[str, int | str]  # field_name → new value
```

---

## Error handling

Define a global exception handler in `src/api/main.py`:

```python
@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": "invalid_input", "detail": str(exc)})

@app.exception_handler(SessionNotFoundError)
async def session_not_found(request, exc):
    return JSONResponse(status_code=404, content={"error": "session_not_found",
        "detail": "Session expired or not found. Please reload the event."})

@app.exception_handler(LLMError)
async def llm_error(request, exc):
    return JSONResponse(status_code=503, content={"error": "llm_unavailable",
        "detail": "LLM service temporarily unavailable. The algorithm result is available without explanations."})
```

The `LLMError` handler is important — if the LangGraph workflow fails, the
operator should still receive the raw `AssignmentResult` without explanations.
Never block the operator tool entirely on an LLM failure.

---

## CORS

The operator tool frontend is served from a different origin than the API.
Configure CORS in `src/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nitinmohan.dev",            # portfolio demo
        "https://operator.blom.social",      # operator tool (TBD with friend)
        "http://localhost:5173",              # local dev
    ],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "X-Session-Token", "Content-Type"],
)
```

---

## Deployment

### Backend — Railway

Railway is the recommended host for the FastAPI backend. It supports
always-on containers, environment variable management, and automatic
deploys from GitHub.

```
# Procfile
web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Use a single worker in v1 — the in-memory session store is not shared
across workers. If scaling becomes necessary, migrate the session store
to Redis first.

Environment variables to set in Railway:

```
ANTHROPIC_API_KEY=...
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
OPERATOR_API_KEY=...          # Static key for operator tool auth
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
BLOM_BACKEND_URL=...          # Blom's existing backend (TBD)
BLOM_BACKEND_API_KEY=...
```

### Frontend — Vercel

Both frontends deploy to Vercel from the same repo, using separate
project configurations.

```
# vercel.json for operator tool
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{"source": "/(.*)", "destination": "/index.html"}]
}
```

Environment variables to set in Vercel:

```
VITE_API_BASE_URL=https://your-railway-app.railway.app
VITE_OPERATOR_API_KEY=...     # Operator tool only
```

The demo frontend has no secret environment variables — all its data
comes from the static synthetic seed file bundled at build time.

### Health check

Add a health endpoint at `GET /health` that returns:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_available": true
}
```

Railway uses this for deployment health checks. The `llm_available` field
pings the Anthropic API with a minimal request to confirm the key is valid.

---

## Implementation notes for Claude Code

- Use `httpx.AsyncClient` for all outbound HTTP calls (to Blom's backend
  and to LLM APIs) — not `requests`, which is synchronous
- The `POST /api/events/{event_id}/load` endpoint is the most complex —
  it chains: fetch from Blom → strip PII → build feature vectors →
  build affinity matrix → store in session. Each step must be awaited
  and any failure must clean up the partial session
- The demo seed is pre-generated and committed to the repo at
  `data/synthetic/demo_seed.json`. The `GET /api/demo/seed` endpoint
  simply reads and returns this file — no computation at request time
- Add `startup` and `shutdown` event handlers to `main.py` to initialise
  and teardown the session cleanup task

---

## Acceptance criteria

### AC-1: Load endpoint chains correctly

```
Given a valid event_id and operator API key
When POST /api/events/{event_id}/load is called
Then a session_token is returned
And the session contains a valid AffinityMatrix
And the session contains a reverse_map with entries for all attendees
And no PII fields are present in the cached feature vectors
```

### AC-2: LLM failure degrades gracefully

```
Given the LLM API is unavailable
When POST /api/matching/{event_id}/run is called
Then the response has status 503
And the response body contains error "llm_unavailable"
And the AssignmentResult (without explanations) is included in the response
```

### AC-3: Demo endpoint rate limit

```
Given 21 requests to POST /api/demo/override from the same IP
  within one minute
When the 21st request is made
Then the response has status 429
```

### AC-4: Session expiry

```
Given a session created more than 4 hours ago
When any operator endpoint is called with that session token
Then the response has status 404 with error "session_not_found"
```

### AC-5: Override persists in session

```
Given an active session with a ReviewedResult
When POST /api/matching/{event_id}/override is called
Then the returned groups reflect the override
And a subsequent GET /api/evaluation/{event_id} reflects the updated
  group membership
```

### AC-6: Health check passes on deploy

```
Given the backend is deployed to Railway
When GET /health is called
Then status is 200
And the response body contains status "ok" and llm_available true
```
