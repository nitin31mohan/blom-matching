from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.routes._auth import require_operator_key
from src.api.routes.matching import _get_session
from src.api.schemas import UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/{pipeline_user_id}", dependencies=[Depends(require_operator_key)])
async def update_user(
    pipeline_user_id: str,
    _body: UserUpdateRequest,
    _session: dict = Depends(_get_session),
) -> dict:
    return {"updated": pipeline_user_id}
