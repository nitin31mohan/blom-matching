from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RunMatchingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_group_size: int = 5
    sensitive_field_mode: Literal["neutral", "affinity", "diversity"] = "neutral"
    n_groups: int | None = None        # overrides target_group_size when set


class OverrideRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pipeline_user_id: str
    from_group_id: str
    to_group_id: str
    reason: str = ""


class ResumeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_token: str
    approved: bool
    operator_notes: str = ""
    overrides: list[OverrideRequest] = []


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    quiz_updates: dict[str, int | str]


class DemoOverrideRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pipeline_user_id: str
    to_group_id: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    version: str
    llm_available: bool = True
