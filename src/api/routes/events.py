from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from src.api.state import SESSION_STORE
from src.api.middleware import limiter
from src.api.routes._auth import require_operator_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def list_events(request: Request) -> dict:  # noqa: ARG001
    return {"events": [], "note": "Blom backend not connected in v0.1"}


@router.get("/{event_id}", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def get_event(request: Request, event_id: str) -> dict:  # noqa: ARG001
    return {"event_id": event_id}


@router.post("/{event_id}/load", dependencies=[Depends(require_operator_key)])
@limiter.limit("60/minute")
async def load_event(request: Request, event_id: str) -> dict:  # noqa: ARG001
    if not os.environ.get("BLOM_BACKEND_URL"):
        logger.warning("BLOM_BACKEND_URL not set — Blom backend integration pending")

    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    SESSION_STORE[token] = {
        "event_id": event_id,
        "affinity": None,
        "reverse_map": {},
        "workflow_state": None,
        "created_at": now,
        "last_active": now,
    }
    return {"session_token": token}
