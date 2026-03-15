from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class GroupExplanationSchema(BaseModel):
    """Structured LLM output for one group explanation."""

    summary: str
    compatibility: str
    flags_explained: list[str]
    confidence: Literal["high", "medium", "low"]
    suggested_action: str | None


class GroupExplanation(BaseModel):
    """Full explanation record attached to a group_id."""

    group_id: str
    summary: str
    compatibility: str
    flags_explained: list[str]
    confidence: Literal["high", "medium", "low"]
    suggested_action: str | None


class OperatorOverride(BaseModel):
    """A single structured override to apply to the assignment."""

    pipeline_user_id: str
    from_group_id: str
    to_group_id: str


class ReviewedResult(BaseModel):
    """Final output of the review workflow."""

    event_id: str
    groups: list[dict]
    explanations: list[GroupExplanation]
    operator_notes: str
    overrides_applied: list[OperatorOverride]
    workflow_trace_id: str
    reviewed_at: str
