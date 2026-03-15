"""NL override parser — converts free-text operator instructions into OperatorOverride objects.

Uses ChatAnthropic with structured output to extract move instructions, then filters
any override referencing user/group IDs not present in the current assignment.
"""
from __future__ import annotations

import logging
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agent.schemas import OperatorOverride
from src.matching.assignment import GroupAssignment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal schema (LLM output)
# ---------------------------------------------------------------------------


class OverrideParseResult(BaseModel):
    overrides: list[OperatorOverride]
    parse_confidence: Literal["high", "medium", "low"]
    unparsed_intent: str | None


# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

OVERRIDE_SYSTEM_PROMPT = """You are a structured data extractor. The user will
give you plain-English instructions for moving attendees between groups.
Extract each move as a structured override. Only output moves that reference
valid user IDs and group IDs from the context provided.
If an instruction is ambiguous or references unknown IDs, set unparsed_intent."""

OVERRIDE_USER_TEMPLATE = """Assignment context:
{group_context}

Operator instructions:
{operator_notes}

Extract all valid move instructions as OperatorOverride objects.
Ignore any instruction referencing IDs not listed above."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_group_context(assignment: GroupAssignment) -> str:
    lines = []
    for group in assignment.groups:
        member_list = ", ".join(group.user_ids)
        lines.append(f"{group.group_id}: [{member_list}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def parse_operator_overrides(
    notes: str,
    assignment: GroupAssignment,
) -> list[OperatorOverride]:
    """Parse free-text operator notes into validated OperatorOverride objects.

    LLM extracts structured overrides; any override referencing a user_id or
    group_id not present in `assignment` is silently dropped.
    Returns empty list if notes is blank or LLM extracts nothing valid.
    """
    if not notes.strip():
        return []

    group_context = _build_group_context(assignment)
    user_prompt = OVERRIDE_USER_TEMPLATE.format(
        group_context=group_context,
        operator_notes=notes,
    )

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=300)
    chain = llm.with_structured_output(OverrideParseResult)
    parse_result: OverrideParseResult = await chain.ainvoke(
        [SystemMessage(content=OVERRIDE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )

    # Build valid ID sets for filtering
    valid_user_ids: set[str] = set()
    valid_group_ids: set[str] = set()
    for group in assignment.groups:
        valid_group_ids.add(group.group_id)
        for uid in group.user_ids:
            valid_user_ids.add(uid)

    filtered: list[OperatorOverride] = []
    for override in parse_result.overrides:
        if (
            override.pipeline_user_id in valid_user_ids
            and override.from_group_id in valid_group_ids
            and override.to_group_id in valid_group_ids
            and override.from_group_id != override.to_group_id
        ):
            filtered.append(override)
        else:
            logger.warning("Override filtered: invalid or duplicate group IDs")

    return filtered
