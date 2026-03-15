from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.routes._auth import require_operator_key

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/{event_id}", dependencies=[Depends(require_operator_key)])
async def get_evaluation(event_id: str) -> dict:
    return {"event_id": event_id, "metrics": {}}


@router.post("/{event_id}/ingest-ratings", dependencies=[Depends(require_operator_key)])
async def ingest_ratings(event_id: str) -> dict:
    return {"status": "not_implemented", "event_id": event_id}
