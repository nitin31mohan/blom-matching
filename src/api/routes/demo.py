from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.middleware import limiter
from src.api.schemas import DemoOverrideRequest

router = APIRouter(prefix="/demo", tags=["demo"])

_SEED_PATH = Path(__file__).parents[3] / "data" / "synthetic" / "demo_seed.json"

# In-memory override state — resets on server restart by design
DEMO_STATE: dict = {}


@router.get("/seed")
@limiter.limit("20/minute")
async def get_demo_seed(request: Request) -> JSONResponse:  # noqa: ARG001
    data = json.loads(_SEED_PATH.read_text())
    return JSONResponse(content=data)


@router.post("/override")
@limiter.limit("30/minute")
async def apply_demo_override(request: Request, body: DemoOverrideRequest) -> dict:  # noqa: ARG001
    DEMO_STATE[body.pipeline_user_id] = body.to_group_id
    return {"overrides": DEMO_STATE}
