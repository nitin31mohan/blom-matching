# Blom matching system — project structure

## How to initialise

```bash
# 1. Create the project root (alongside or inside your existing blom repo)
mkdir blom-matching && cd blom-matching

# 2. Install PAUL
npx paul-framework --local

# 3. Create the directory tree below
# (copy-paste the mkdir block, then populate files from this guide)
```

---

## Full directory tree

```
blom-matching/
│
├── .paul/                          # PAUL state — managed by PAUL commands
│   ├── PROJECT.md                  # Project context (fill in once)
│   ├── ROADMAP.md                  # Phase breakdown (fill in once)
│   ├── STATE.md                    # Auto-managed by PAUL
│   ├── config.md                   # Optional integrations
│   ├── SPECIAL-FLOWS.md            # ← Skill declarations live here
│   └── phases/                     # Auto-populated by /paul:plan
│
├── config/
│   └── matching.yaml               # Runtime config: weights, sensitive_field_mode, etc.
│
├── src/
│   ├── features/
│   │   ├── __init__.py
│   │   ├── encoder.py              # Skill: Feature engineering
│   │   ├── weights.py              # Weight config dict
│   │   └── modifiers.py            # Event-type post-encoding transforms
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── synthetic.py            # Skill: Synthetic data generation
│   │   └── anonymiser.py           # Skill: PII / data handling
│   │
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── similarity.py           # Skill: Similarity & embedding computation
│   │   ├── assignment.py           # Skill: Constrained group assignment
│   │   └── constraints.py          # Hard constraint definitions (friend pairs, etc.)
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── workflow.py             # Skill: LangGraph agentic workflow
│   │   ├── prompts.py              # LLM system/user prompt templates
│   │   └── schemas.py              # Structured output schemas (Pydantic)
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py              # Skill: Evaluation framework — proxy metrics
│   │   └── feedback.py             # Post-event rating ingestion + reweighting
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app entrypoint
│       ├── routes/
│       │   ├── events.py
│       │   ├── users.py
│       │   └── matching.py
│       └── middleware.py           # Rate limiting, CORS, spend-cap guard
│
├── frontend/
│   ├── operator/                   # Prong 1 — private admin dashboard
│   │   ├── src/
│   │   │   ├── canvas/             # Skill: Force-directed canvas UI
│   │   │   │   ├── ForceCanvas.tsx
│   │   │   │   ├── AttendeeNode.tsx
│   │   │   │   └── GroupHull.tsx
│   │   │   ├── panels/
│   │   │   │   ├── AttendeeDetail.tsx
│   │   │   │   └── GroupSummary.tsx
│   │   │   ├── store/
│   │   │   │   └── canvas.store.ts # Zustand state — groups, scores, overrides
│   │   │   └── App.tsx
│   │   └── package.json
│   │
│   └── demo/                       # Prong 2 — public portfolio demo
│       ├── src/
│       │   ├── canvas/             # Shared components (symlink or package)
│       │   ├── synthetic-seed.ts   # Loads fake attendees, no API auth needed
│       │   └── App.tsx
│       └── package.json
│
├── tests/
│   ├── features/
│   │   ├── test_encoder.py         # AC-1, AC-2
│   │   ├── test_weights.py         # AC-2
│   │   └── test_modifiers.py       # AC-5
│   ├── data/
│   │   └── test_synthetic.py
│   ├── matching/
│   │   ├── test_similarity.py
│   │   └── test_assignment.py
│   ├── agent/
│   │   └── test_workflow.py
│   └── evaluation/
│       └── test_metrics.py
│
├── notebooks/                      # Exploratory work, not shipped
│   ├── 01-feature-exploration.ipynb
│   ├── 02-similarity-validation.ipynb
│   └── 03-assignment-tuning.ipynb
│
├── data/
│   ├── synthetic/                  # Generated fake attendees (gitignored if large)
│   └── schemas/
│       └── quiz_response.json      # JSON schema for raw input validation
│
├── .env.example                    # API keys, DB URL — never commit .env
├── .gitignore
├── pyproject.toml                  # Python deps (uv or poetry)
└── README.md
```

---

## `.paul/SPECIAL-FLOWS.md` starter

Copy this into `.paul/SPECIAL-FLOWS.md` after running `/paul:init`:

```markdown
# Required skills

Load the relevant skill(s) before running /paul:apply for any phase.
Skills are stored in `.claude/skills/` after being added.

| Skill file | Work type | Phase | Priority |
|------------|-----------|-------|----------|
| `SKILL-feature-engineering.md` | Feature vector construction | 01-foundation | required |
| `SKILL-synthetic-data.md` | Fake user generation for dev/test | 01-foundation | required |
| `SKILL-similarity.md` | Cosine similarity + affinity matrix | 02-core-algorithm | required |
| `SKILL-assignment.md` | Constrained group matching | 02-core-algorithm | required |
| `SKILL-langgraph.md` | Agentic review workflow | 03-agent-layer | required |
| `SKILL-evaluation.md` | Proxy metrics + feedback loop | 04-evaluation | required |
| `SKILL-force-canvas.md` | D3 force UI, physics, node drag | 05-frontend | required |
| `SKILL-api.md` | FastAPI wrapper + deployment | 06-api | required |
| `SKILL-pii.md` | PII handling + anonymisation | 01-foundation | required |
```

---

## `.paul/PROJECT.md` starter

```markdown
# Blom matching system

## What this is
An automated group-matching pipeline for Blom Social (blom.social).
Replaces manual attendee grouping with an algorithm-driven assignment
system backed by a human-in-the-loop LLM review layer.

## Two delivery prongs
1. **Operator tool** — private admin dashboard for the Blom founder.
   Real attendee data, write-back to DB, drag-and-drop group canvas.
2. **Portfolio demo** — public-facing version on nitinmohan.dev.
   Synthetic anonymised data, same UI, no auth required.

## Core tech
- Python backend: FastAPI, LangGraph, NumPy
- Frontend: React + D3 force simulation + Zustand
- DB: TBD with Blom founder (likely Supabase or Firebase)
- Deployment: Railway (backend) + Vercel (frontend)

## Key constraints
- No real PII in the demo prong under any circumstances
- Spend cap on all LLM API calls — hard limit enforced at provider level
- Operator tool must work for corpus sizes 10–500 without re-architecture
- Matching must be explainable in plain English (LLM review layer)

## Out of scope (v1)
- Mobile app integration
- Real-time collaborative editing of groups
- User-facing match explanations (operator-only for now)
```

---

## `.paul/ROADMAP.md` starter

```markdown
# Roadmap

## Phase 01 — Foundation
- Synthetic data generation
- Feature engineering pipeline
- PII anonymisation utilities
- Unit tests for all of the above

## Phase 02 — Core algorithm
- Cosine similarity + affinity matrix
- Constrained group assignment (greedy)
- Hard constraint handling (friend pairs, group size)
- Integration tests with synthetic data

## Phase 03 — Agent layer
- LangGraph review workflow
- LLM explanation generation
- Structured output schemas
- Human override parsing
- LangSmith trace setup

## Phase 04 — Evaluation
- Proxy metrics (within-group similarity distribution, flag rate)
- Post-event feedback ingestion
- Feature reweighting from feedback signal

## Phase 05 — Frontend
- Force-directed canvas (shared component library)
- Operator tool (Prong 1) — with DB write-back
- Portfolio demo (Prong 2) — synthetic seed, no auth

## Phase 06 — API + deployment
- FastAPI routes
- Rate limiting + spend-cap middleware
- Railway deploy (backend)
- Vercel deploy (frontend × 2)
```

---

## Quick-start bash block

Run this from your project root after `npx paul-framework --local`:

```bash
mkdir -p .paul/phases \
  config \
  src/{features,data,matching,agent,evaluation,api/routes} \
  frontend/operator/src/{canvas,panels,store} \
  frontend/demo/src/canvas \
  tests/{features,data,matching,agent,evaluation} \
  notebooks \
  data/{synthetic,schemas} \
  .claude/skills

# Create Python package markers
touch src/__init__.py \
  src/features/__init__.py \
  src/data/__init__.py \
  src/matching/__init__.py \
  src/agent/__init__.py \
  src/evaluation/__init__.py \
  src/api/__init__.py

# Copy skill files into the skills directory
# (after generating each one)
# cp SKILL-*.md .claude/skills/

echo "Directory structure ready. Run /paul:init inside Claude Code next."
```
