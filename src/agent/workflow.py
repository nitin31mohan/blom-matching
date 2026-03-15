"""LangGraph review workflow for the Blom matching agent layer.

Four-node StateGraph:
  explain_groups → flag_review → (human_checkpoint | compile_output) → END

explain_groups: parallel async LLM calls to generate GroupExplanation per group.
flag_review:    determines whether human review is needed.
human_checkpoint: pauses via interrupt() for operator input.
compile_output: applies overrides and assembles ReviewedResult.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from langsmith import get_current_run_tree, traceable

from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_member_profiles
from src.agent.schemas import (
    GroupExplanation,
    GroupExplanationSchema,
    OperatorOverride,
    ReviewedResult,
)
from src.features.encoder import UserFeatureVector
from src.matching.assignment import GroupAssignment, apply_override
from src.matching.constraints import ConstraintError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    assignment: GroupAssignment
    feature_vectors: list[UserFeatureVector]
    event_type: str
    group_explanations: list[GroupExplanation]
    requires_human: bool
    flagged_groups: list[str]
    operator_notes: str
    overrides: list[OperatorOverride]
    reviewed_result: ReviewedResult | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fit_label(cohesion: float) -> str:
    if cohesion >= 0.68:
        return "great"
    if cohesion >= 0.42:
        return "okay"
    return "poor"


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def explain_groups(state: AgentState) -> dict:
    """Generate plain-English explanations for every group concurrently."""
    assignment = state["assignment"]
    feature_vectors = state["feature_vectors"]
    event_type = state["event_type"]

    fv_map: dict[str, UserFeatureVector] = {fv.user_id: fv for fv in feature_vectors}

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=400)
    llm_structured = llm.with_structured_output(GroupExplanationSchema)

    async def _explain_one(group) -> GroupExplanation:
        cohesion = group.cohesion_score
        flags_list = ", ".join(group.flags) if group.flags else "none"
        member_profiles_table = format_member_profiles(list(group.user_ids), fv_map)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            event_type=event_type,
            group_label=group.group_id,
            group_size=len(group.user_ids),
            cohesion_score=cohesion,
            fit_label=_fit_label(cohesion),
            flags_list=flags_list,
            member_profiles_table=member_profiles_table,
        )
        result: GroupExplanationSchema = await llm_structured.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
        )
        return GroupExplanation(
            group_id=group.group_id,
            summary=result.summary,
            compatibility=result.compatibility,
            flags_explained=result.flags_explained,
            confidence=result.confidence,
            suggested_action=result.suggested_action,
        )

    coroutines = [_explain_one(group) for group in assignment.groups]
    explanations: list[GroupExplanation] = await asyncio.gather(*coroutines)

    return {"group_explanations": list(explanations)}


def flag_review(state: AgentState) -> dict:
    """Decide whether human review is needed based on cohesion and confidence."""
    assignment = state["assignment"]
    explanations = state["group_explanations"]

    flagged: list[str] = []
    requires_human = False

    # Condition 2: any group with poor fit_color
    for group in assignment.groups:
        if group.fit_color == "#ef4444":
            flagged.append(group.group_id)
            requires_human = True

    # Condition 1: any explanation with low confidence
    for exp in explanations:
        if exp.confidence == "low" and exp.group_id not in flagged:
            flagged.append(exp.group_id)
            requires_human = True

    # Condition 3: >25% of groups with medium confidence
    if not requires_human:
        n_groups = len(explanations)
        n_medium = sum(1 for exp in explanations if exp.confidence == "medium")
        if n_groups > 0 and n_medium / n_groups > 0.25:
            requires_human = True

    return {"requires_human": requires_human, "flagged_groups": flagged}


def human_checkpoint(state: AgentState) -> dict:
    """Pause workflow for operator review. Resume with operator_notes + overrides."""
    operator_input = interrupt(
        {
            "flagged_groups": state["flagged_groups"],
            "explanations": [e.model_dump() for e in state["group_explanations"]],
        }
    )
    return {
        "operator_notes": operator_input.get("operator_notes", ""),
        "overrides": operator_input.get("overrides", []),
    }


async def compile_output(state: AgentState) -> dict:
    """Apply any overrides and assemble the final ReviewedResult."""
    from src.agent.override_parser import parse_operator_overrides

    assignment = state["assignment"]
    feature_vectors = state["feature_vectors"]
    operator_notes = state.get("operator_notes") or ""
    explicit_overrides: list[OperatorOverride] = state.get("overrides") or []

    parsed_overrides: list[OperatorOverride] = []
    if operator_notes.strip():
        parsed_overrides = await parse_operator_overrides(operator_notes, assignment)

    overrides = explicit_overrides + parsed_overrides

    # Build empty partner_map — override validation is the API layer's responsibility
    partner_map: dict[str, str] = {}

    from src.matching.similarity import build_affinity_matrix

    affinity = build_affinity_matrix(feature_vectors)

    current_assignment = assignment
    applied: list[OperatorOverride] = []
    for override in overrides:
        try:
            current_assignment = apply_override(
                assignment=current_assignment,
                affinity=affinity,
                feature_vectors=feature_vectors,
                move_user_id=override.pipeline_user_id,
                from_group_id=override.from_group_id,
                to_group_id=override.to_group_id,
                partner_map=partner_map,
            )
            applied.append(override)
        except ConstraintError as exc:
            logger.warning("Override skipped (ConstraintError): %s", exc)

    reviewed_result = ReviewedResult(
        event_id=current_assignment.event_id,
        groups=[g.model_dump() for g in current_assignment.groups],
        explanations=state["group_explanations"],
        operator_notes=state.get("operator_notes") or "",
        overrides_applied=applied,
        workflow_trace_id="local",  # replaced in run_review_workflow via get_current_run_tree()
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    return {"reviewed_result": reviewed_result}


# ---------------------------------------------------------------------------
# Graph assembly (module-level — compiled once)
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)
builder.add_node("explain_groups", explain_groups)
builder.add_node("flag_review", flag_review)
builder.add_node("human_checkpoint", human_checkpoint)
builder.add_node("compile_output", compile_output)

builder.set_entry_point("explain_groups")
builder.add_edge("explain_groups", "flag_review")
builder.add_conditional_edges(
    "flag_review",
    lambda s: "human_checkpoint" if s["requires_human"] else "compile_output",
)
builder.add_edge("human_checkpoint", "compile_output")
builder.add_edge("compile_output", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer, interrupt_before=["human_checkpoint"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@traceable(name="blom_review_workflow")
async def run_review_workflow(
    assignment: GroupAssignment,
    feature_vectors: list[UserFeatureVector],
    event_type: str = "social",
    thread_id: str | None = None,
) -> ReviewedResult:
    """Run the full review workflow.

    Returns ReviewedResult on the clean path (no flags).
    Raises GraphInterrupt on the flagged path — caller must handle and resume.
    """
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    initial_state: AgentState = {
        "assignment": assignment,
        "feature_vectors": feature_vectors,
        "event_type": event_type,
        "group_explanations": [],
        "requires_human": False,
        "flagged_groups": [],
        "operator_notes": "",
        "overrides": [],
        "reviewed_result": None,
    }
    final = await graph.ainvoke(initial_state, config=config)
    result: ReviewedResult = final["reviewed_result"]

    run_tree = get_current_run_tree()
    if run_tree is not None:
        result = result.model_copy(update={"workflow_trace_id": str(run_tree.id)})

    return result
