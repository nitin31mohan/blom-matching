# Roadmap: Blom Matching System

## Overview

Six-phase build from data foundation through core algorithm, LLM agent layer, evaluation, frontend (operator + demo), and API deployment. Each phase has a clear dependency on the prior one's output.

## Current Milestone

**v0.1 Initial Release**
Status: In progress
Phases: 0 of 6 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 01 | Foundation | 3 | ✅ Complete | 2026-03-15 |
| 02 | Core Algorithm | 2 | ✅ Complete | 2026-03-15 |
| 03 | Agent Layer | 2 | ✅ Complete | 2026-03-15 |
| 04 | Evaluation | 2 | ✅ Complete | 2026-03-15 |
| 05 | Frontend | 7 | ✅ Complete | 2026-03-15 |
| 06 | API + Deployment | 2 | Not started | - |

## Phase Details

### Phase 01: Foundation

**Goal:** Stable Attendee schema, synthetic data generator, PII anonymiser, and feature engineering pipeline — all unit-tested.
**Depends on:** Nothing (first phase)
**Research:** Unlikely (internal design)

**Scope:**
- Attendee Pydantic model + JSON Schema
- Synthetic data generator (deterministic, scales to 500)
- PII anonymisation utilities (name hashing, field stripping)
- Feature engineering pipeline (encoder, weights, modifiers)
- Unit tests for all of the above

**Plans:**
- [x] 01-01: Attendee schema + synthetic data generation
- [x] 01-02: PII anonymisation utilities
- [x] 01-03: Feature engineering pipeline

### Phase 02: Core Algorithm

**Goal:** Cosine similarity affinity matrix and constrained group assignment, tested with synthetic data.
**Depends on:** Phase 01 (Attendee model + feature vectors)
**Research:** Unlikely (standard algorithms)

**Scope:**
- Cosine similarity computation + affinity matrix
- Constrained greedy group assignment
- Hard constraint handling (friend pairs, group size bounds)
- Integration tests with synthetic data

**Plans:**
- [x] 02-01: Similarity computation + affinity matrix
- [x] 02-02: Constrained group assignment

### Phase 03: Agent Layer

**Goal:** LangGraph agentic workflow that reviews groups, generates plain-English explanations, and parses human overrides.
**Depends on:** Phase 02 (group assignment output)
**Research:** Likely (LangGraph API, LangSmith setup)

**Scope:**
- LangGraph review workflow
- LLM prompt templates + structured output schemas (Pydantic)
- Human override parsing
- LangSmith trace setup

**Plans:**
- [x] 03-01: LangGraph workflow + prompt templates
- [x] 03-02: Override parsing + LangSmith integration

### Phase 04: Evaluation

**Goal:** Proxy metrics framework and feedback ingestion loop for reweighting features post-event.
**Depends on:** Phase 02 (group output schema)
**Research:** Unlikely

**Scope:**
- Within-group similarity distribution metric
- Flag rate tracking
- Post-event feedback ingestion + feature reweighting

**Plans:**
- [x] 04-01: Proxy metrics implementation ✅
- [x] 04-02: Feedback ingestion + reweighting ✅

### Phase 05: Frontend

**Goal:** Force-directed canvas UI shared between operator tool (Prong 1) and portfolio demo (Prong 2).
**Depends on:** Phase 02 (group output schema for canvas data shape)
**Research:** Likely (D3 force simulation API)

**Scope:**
- ForceCanvas, AttendeeNode, GroupHull shared components
- Operator tool with DB write-back
- Portfolio demo with synthetic seed, no auth

**Plans:**
- [x] 05-01: Bootstrap + shared canvas components ✅
- [x] 05-02: Zustand store + basic panels (foundation) ✅
- [x] 05-03: Full prototype port — attractors, throw, reassign, live fit, header, trait panel ✅
- [x] 05-04: Two-axis algorithm upgrade (valuesCohesion + dominanceBalance, activity profiles, view toggle) ✅
- [x] 05-05: Freeze/approve/straggler workflow — board lock, late sign-up placement, visual indicators ✅
- [x] 05-06: Group deletion + touch/pointer events — drag-to-bin, dynamic GROUP_LAYOUT, tablet-friendly ✅
- [x] 05-07: Portfolio demo (Prong 2) — synthetic seed, no auth ✅

### Phase 06: API + Deployment

**Goal:** FastAPI wrapper, rate limiting + spend-cap middleware, Railway + Vercel deployment.
**Depends on:** Phases 02–05
**Research:** Unlikely (standard FastAPI patterns)

**Scope:**
- FastAPI routes (events, users, matching)
- Rate limiting + CORS + spend-cap middleware
- Railway deploy (backend), Vercel deploy (frontend × 2)

**Plans:**
- [ ] 06-01: FastAPI routes + middleware
- [ ] 06-02: Railway + Vercel deployment

---
*Roadmap created: 2026-03-15*
*Last updated: 2026-03-15 — Phase 05 complete*
