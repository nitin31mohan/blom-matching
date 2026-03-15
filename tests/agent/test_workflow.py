"""Tests for the LangGraph review workflow — AC-1, AC-2, AC-3, AC-6.

All LLM calls are mocked; no real API calls are made.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.schemas import GroupExplanation, GroupExplanationSchema, ReviewedResult
from src.agent.workflow import explain_groups, flag_review, run_review_workflow
from src.data.synthetic import generate_event_fixture
from src.features.encoder import build_feature_vector
from src.matching.assignment import Group, GroupAssignment, assign_groups
from src.matching.similarity import build_affinity_matrix


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _build_assignment_and_fvs(n_attendees: int = 8, seed: int = 42):
    """Build a real GroupAssignment + feature vector list from synthetic data."""
    fix = generate_event_fixture("social", n_attendees, seed=seed)
    quiz_dicts = [a.__dict__ for a in fix.attendees]
    fvs = [
        build_feature_vector(quiz_dicts[i], a.id, fix.event_id, quiz_dicts)
        for i, a in enumerate(fix.attendees)
    ]
    affinity = build_affinity_matrix(fvs)
    fp_ids = {a.id: a.friend_pair_id for a in fix.attendees}
    assignment = assign_groups(affinity, fvs, fp_ids)
    return assignment, fvs


def _make_good_schema_response() -> GroupExplanationSchema:
    return GroupExplanationSchema(
        summary="Test summary sentence one. Sentence two. Sentence three.",
        compatibility="Good fit overall.",
        flags_explained=[],
        confidence="high",
        suggested_action=None,
    )


def _make_mock_llm(response: GroupExplanationSchema | None = None):
    """Return a mock that mimics ChatAnthropic().with_structured_output().

    The workflow calls: llm.with_structured_output(Schema).ainvoke([...])
    So we need mock_chain.ainvoke to be the async callable.
    """
    resp = response or _make_good_schema_response()
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=resp)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)
    return mock_llm, mock_chain


# ---------------------------------------------------------------------------
# AC-1: Structured output always parseable
# ---------------------------------------------------------------------------


async def test_explain_groups_returns_valid_schema():
    """AC-1: explain_groups converts LLM output into valid GroupExplanation objects."""
    assignment, fvs = _build_assignment_and_fvs(n_attendees=8, seed=42)
    n_groups = len(assignment.groups)
    assert n_groups >= 2, "Need at least 2 groups for this test"

    mock_llm, mock_chain = _make_mock_llm()

    with patch("src.agent.workflow.ChatAnthropic", return_value=mock_llm):
        state = {
            "assignment": assignment,
            "feature_vectors": fvs,
            "event_type": "social",
            "group_explanations": [],
            "requires_human": False,
            "flagged_groups": [],
            "operator_notes": "",
            "overrides": [],
            "reviewed_result": None,
        }
        result = await explain_groups(state)

    explanations = result["group_explanations"]
    assert len(explanations) == n_groups

    for exp in explanations:
        assert isinstance(exp, GroupExplanation)
        assert exp.summary, "summary must be non-empty"
        assert exp.compatibility, "compatibility must be non-empty"
        assert exp.confidence in ("high", "medium", "low")
        assert exp.group_id, "group_id must be set"


# ---------------------------------------------------------------------------
# AC-2: Human checkpoint triggers on low-cohesion or low-confidence groups
# ---------------------------------------------------------------------------


def test_flag_review_triggers_on_low_cohesion():
    """AC-2: flag_review sets requires_human=True when a group has fit_color #ef4444."""
    assignment, fvs = _build_assignment_and_fvs(n_attendees=8, seed=42)

    # Inject a poor-cohesion group into the assignment
    poor_group = Group(
        group_id="group-poor",
        user_ids=tuple(list(assignment.groups[0].user_ids)[:2]),
        cohesion_score=0.2,
        fit_color="#ef4444",
        flags=(),
    )
    existing_groups = list(assignment.groups)
    modified_assignment = GroupAssignment(
        event_id=assignment.event_id,
        groups=tuple(existing_groups + [poor_group]),
        assigned_at=assignment.assigned_at,
        unassigned=assignment.unassigned,
    )

    # All explanations are high-confidence
    explanations = [
        GroupExplanation(
            group_id=g.group_id,
            summary="Test",
            compatibility="Good.",
            flags_explained=[],
            confidence="high",
            suggested_action=None,
        )
        for g in modified_assignment.groups
    ]

    state = {
        "assignment": modified_assignment,
        "feature_vectors": fvs,
        "event_type": "social",
        "group_explanations": explanations,
        "requires_human": False,
        "flagged_groups": [],
        "operator_notes": "",
        "overrides": [],
        "reviewed_result": None,
    }
    result = flag_review(state)

    assert result["requires_human"] is True
    assert "group-poor" in result["flagged_groups"]


def test_flag_review_triggers_on_low_confidence():
    """AC-2: flag_review sets requires_human=True when any explanation has confidence 'low'."""
    assignment, fvs = _build_assignment_and_fvs(n_attendees=8, seed=42)
    groups = list(assignment.groups)

    # All groups have good cohesion but one explanation is low-confidence
    explanations = [
        GroupExplanation(
            group_id=groups[0].group_id,
            summary="Test",
            compatibility="Poor fit.",
            flags_explained=[],
            confidence="low",
            suggested_action="Consider swapping members.",
        ),
    ] + [
        GroupExplanation(
            group_id=g.group_id,
            summary="Test",
            compatibility="Good.",
            flags_explained=[],
            confidence="high",
            suggested_action=None,
        )
        for g in groups[1:]
    ]

    state = {
        "assignment": assignment,
        "feature_vectors": fvs,
        "event_type": "social",
        "group_explanations": explanations,
        "requires_human": False,
        "flagged_groups": [],
        "operator_notes": "",
        "overrides": [],
        "reviewed_result": None,
    }
    result = flag_review(state)

    assert result["requires_human"] is True
    assert groups[0].group_id in result["flagged_groups"]


# ---------------------------------------------------------------------------
# AC-3: Workflow skips checkpoint when all groups are clean
# ---------------------------------------------------------------------------


async def test_workflow_clean_path_no_interrupt():
    """AC-3: ReviewedResult returned directly with no overrides when all groups are clean."""
    # Use 12 attendees for more reliable high-cohesion groups
    assignment, fvs = _build_assignment_and_fvs(n_attendees=12, seed=99)

    # Verify no groups have poor fit_color (precondition for clean path)
    for g in assignment.groups:
        assert g.fit_color != "#ef4444", (
            f"Group {g.group_id} has poor fit_color — clean path test won't work. "
            f"cohesion={g.cohesion_score:.2f}"
        )

    mock_llm, _ = _make_mock_llm()  # returns confidence="high"

    with patch("src.agent.workflow.ChatAnthropic", return_value=mock_llm):
        result = await run_review_workflow(assignment, fvs, event_type="social")

    assert isinstance(result, ReviewedResult)
    assert result.overrides_applied == []
    assert result.reviewed_at  # non-empty ISO timestamp
    assert result.event_id == assignment.event_id


# ---------------------------------------------------------------------------
# AC-6: Parallel LLM calls in explain_groups
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC-5: LangSmith trace ID captured in ReviewedResult
# ---------------------------------------------------------------------------


async def test_workflow_captures_langsmith_run_id():
    """AC-5: workflow_trace_id is set from LangSmith run tree when active."""
    assignment, fvs = _build_assignment_and_fvs(n_attendees=12, seed=99)

    for g in assignment.groups:
        assert g.fit_color != "#ef4444", "Need clean path for this test"

    mock_llm, _ = _make_mock_llm()
    mock_run_tree = MagicMock()
    mock_run_tree.id = "test-run-abc"

    with patch("src.agent.workflow.ChatAnthropic", return_value=mock_llm), \
         patch("src.agent.workflow.get_current_run_tree", return_value=mock_run_tree):
        result = await run_review_workflow(assignment, fvs, event_type="social")

    assert result.workflow_trace_id == "test-run-abc"


async def test_workflow_falls_back_to_local_when_no_run_tree():
    """AC-5b: workflow_trace_id falls back to 'local' when no LangSmith run is active."""
    assignment, fvs = _build_assignment_and_fvs(n_attendees=12, seed=99)

    for g in assignment.groups:
        assert g.fit_color != "#ef4444", "Need clean path for this test"

    mock_llm, _ = _make_mock_llm()

    with patch("src.agent.workflow.ChatAnthropic", return_value=mock_llm), \
         patch("src.agent.workflow.get_current_run_tree", return_value=None):
        result = await run_review_workflow(assignment, fvs, event_type="social")

    assert result.workflow_trace_id == "local"


# ---------------------------------------------------------------------------
# AC-6: Parallel LLM calls in explain_groups
# ---------------------------------------------------------------------------


async def test_explain_groups_calls_llm_in_parallel():
    """AC-6: explain_groups dispatches all LLM calls concurrently via asyncio.gather."""
    # 20 attendees → 4 groups with default target_group_size=5
    assignment, fvs = _build_assignment_and_fvs(n_attendees=20, seed=42)
    n_groups = len(assignment.groups)
    assert n_groups >= 3, f"Need at least 3 groups; got {n_groups}"

    call_count = 0

    async def _fake_ainvoke(_messages):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)  # simulate async latency
        return _make_good_schema_response()

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(side_effect=_fake_ainvoke)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)

    gather_calls: list = []
    original_gather = asyncio.gather

    async def _spy_gather(*coros, **kwargs):
        gather_calls.append(coros)
        return await original_gather(*coros, **kwargs)

    with patch("src.agent.workflow.ChatAnthropic", return_value=mock_llm), \
         patch("src.agent.workflow.asyncio.gather", side_effect=_spy_gather):
        state = {
            "assignment": assignment,
            "feature_vectors": fvs,
            "event_type": "social",
            "group_explanations": [],
            "requires_human": False,
            "flagged_groups": [],
            "operator_notes": "",
            "overrides": [],
            "reviewed_result": None,
        }
        await explain_groups(state)

    # LLM was called exactly N times (once per group)
    assert call_count == n_groups, f"Expected {n_groups} calls, got {call_count}"

    # asyncio.gather was called once with N coroutine arguments
    assert len(gather_calls) == 1
    assert len(gather_calls[0]) == n_groups
