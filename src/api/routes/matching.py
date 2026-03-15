# ruff: noqa: ARG001
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from src.api.state import SESSION_STORE, SessionNotFoundError
from src.api.middleware import limiter
from src.api.routes._auth import require_operator_key
from src.api.schemas import OverrideRequest, ResumeRequest, RunMatchingRequest

router = APIRouter(prefix="/matching", tags=["matching"])


def _get_session(session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    session = SESSION_STORE.get(session_token)
    if session is None:
        raise SessionNotFoundError("Session not found")
    return session


@router.post("/{event_id}/run", dependencies=[Depends(require_operator_key)])
@limiter.limit("5/minute")
async def run_matching(  # noqa: ARG001
    request: Request,
    event_id: str,
    body: RunMatchingRequest,
    session: dict = Depends(_get_session),
) -> dict:
    return {"status": "not_implemented", "note": "Blom backend integration pending", "event_id": event_id}


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
