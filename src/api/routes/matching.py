# ruff: noqa: ARG001
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Header, Request

from src.api.state import SESSION_STORE, SessionNotFoundError
from src.api.middleware import limiter
from src.api.routes._auth import require_operator_key
from src.api.schemas import OverrideRequest, ResumeRequest, RunMatchingRequest
from src.data.synthetic import generate_event_fixture
from src.data.anonymiser import strip_pii
from src.features.encoder import build_feature_vector
from src.matching import build_affinity_matrix, assign_groups

router = APIRouter(prefix="/matching", tags=["matching"])

# Trait field order must match TRAIT_KEYS in frontend/operator/src/lib/fit.ts:
# [Social energy, Openness, Conscientiousness, Agreeableness, Eco values]
_TRAIT_FIELDS = [
    "energised_meeting_people",
    "enjoys_unfamiliar_experiences",
    "shows_up_on_time",
    "keeps_atmosphere_harmonious",
    "eco_friendly_choices",
]


def _get_session(session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    session = SESSION_STORE.get(session_token)
    if session is None:
        raise SessionNotFoundError("Session not found")
    return session


@router.post("/{event_id}/run", dependencies=[Depends(require_operator_key)])
@limiter.limit("30/minute")
async def run_matching(
    request: Request,
    event_id: str,
    body: RunMatchingRequest,
    session: dict = Depends(_get_session),
) -> dict:
    # 1. Generate deterministic synthetic fixture (seed=42 for demo stability)
    n_attendees = 16
    # n_groups overrides target_group_size: distribute attendees evenly across requested groups
    effective_target = (
        math.ceil(n_attendees / body.n_groups)
        if body.n_groups and body.n_groups > 0
        else body.target_group_size
    )
    fixture = generate_event_fixture(
        event_type="social",
        n_attendees=n_attendees,
        target_group_size=effective_target,
        seed=42,
    )

    # 2. Strip PII; track friend_pair_id before it is dropped
    anon_attendees = []
    friend_pair_ids: dict[str, str | None] = {}
    for raw in fixture.attendees:
        anon = strip_pii(raw.model_dump())
        anon_attendees.append(anon)
        # friend_pair_id is not in QUIZ_FIELDS — capture before strip_pii drops it
        friend_pair_ids[anon.pipeline_user_id] = raw.friend_pair_id

    # 3. Encode feature vectors
    # encoder_config uses "matching" key (build_feature_vector reads matching.sensitive_field_mode)
    all_quiz = [a.quiz_responses for a in anon_attendees]
    encoder_config = {"matching": {"sensitive_field_mode": body.sensitive_field_mode}}
    feature_vectors = [
        build_feature_vector(
            user_quiz=a.quiz_responses,
            user_id=a.pipeline_user_id,
            event_id=event_id,
            all_users_quiz=all_quiz,
            config=encoder_config,
        )
        for a in anon_attendees
    ]

    # 4. Build affinity matrix + assign groups
    # assignment_config uses "assignment" key (assign_groups reads assignment.target_group_size etc.)
    k_groups = math.ceil(n_attendees / effective_target)
    assignment_config = {
        "assignment": {
            "group_size_min": 2,
            # cap at ceil(N/K)+1 so no group grows disproportionately large
            "group_size_max": math.ceil(n_attendees / k_groups) + 1,
            "target_group_size": effective_target,
        }
    }
    affinity = build_affinity_matrix(feature_vectors)
    assignment = assign_groups(affinity, feature_vectors, friend_pair_ids, assignment_config)

    # 5. Build lookup: pipeline_user_id → group_id
    uid_to_group: dict[str, str] = {}
    for group in assignment.groups:
        for uid in group.user_ids:
            uid_to_group[uid] = group.group_id

    # 6. Build per-attendee payload for the frontend Attendee[] type
    attendees_out = []
    for anon in anon_attendees:
        pid = anon.pipeline_user_id
        traits = [
            int(anon.quiz_responses.get(field) or 3)
            for field in _TRAIT_FIELDS
        ]
        attendees_out.append({
            "pipeline_user_id": pid,
            "display_name": anon.display_name,
            "group_id": uid_to_group.get(pid, ""),
            "traits": traits,
        })

    # 7. Stash initial assignment in session (mutable dict — no re-store needed)
    session["initial_assignment"] = assignment.model_dump()

    return {
        "status": "ok",
        "event_id": event_id,
        "assignment": assignment.model_dump(),
        "attendees": attendees_out,
    }


@router.post("/{event_id}/override", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def apply_override(  # noqa: ARG001
    request: Request,
    event_id: str,
    body: OverrideRequest,
    session: dict = Depends(_get_session),
) -> dict:
    return {"status": "not_implemented", "event_id": event_id}


@router.post("/{event_id}/writeback", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def writeback(  # noqa: ARG001
    request: Request,
    event_id: str,
    session: dict = Depends(_get_session),
) -> dict:
    return {"status": "not_implemented", "event_id": event_id}


@router.post("/{event_id}/resume", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def resume_workflow(  # noqa: ARG001
    request: Request,
    event_id: str,
    body: ResumeRequest,
    session: dict = Depends(_get_session),
) -> dict:
    return {"status": "not_implemented", "event_id": event_id}
