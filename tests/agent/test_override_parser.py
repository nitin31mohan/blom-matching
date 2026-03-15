"""Tests for NL override parser — AC-4, AC-4b, AC-4c.

All LLM calls are mocked; no real API calls are made.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.override_parser import OverrideParseResult, parse_operator_overrides
from src.agent.schemas import OperatorOverride
from src.data.synthetic import generate_event_fixture
from src.features.encoder import build_feature_vector
from src.matching.assignment import assign_groups
from src.matching.similarity import build_affinity_matrix


# ---------------------------------------------------------------------------
# Shared fixture helpers (local copy — test files must not import each other)
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


def _make_parse_result(overrides: list[OperatorOverride]) -> OverrideParseResult:
    return OverrideParseResult(
        overrides=overrides,
        parse_confidence="high",
        unparsed_intent=None,
    )


# ---------------------------------------------------------------------------
# AC-4: NL override parser produces valid structured overrides
# ---------------------------------------------------------------------------


async def test_parse_returns_valid_override():
    """AC-4: parse_operator_overrides returns correct OperatorOverride for a valid move."""
    assignment, _ = _build_assignment_and_fvs(n_attendees=8, seed=42)

    # Pick real user from group-01 and verify group-02 exists
    groups = {g.group_id: g for g in assignment.groups}
    assert "group-01" in groups, "group-01 must exist"
    assert "group-02" in groups, "group-02 must exist"

    uid = list(groups["group-01"].user_ids)[0]
    notes = f"Move user {uid} from group-01 to group-02"

    expected_override = OperatorOverride(
        pipeline_user_id=uid,
        from_group_id="group-01",
        to_group_id="group-02",
    )
    mock_result = _make_parse_result([expected_override])

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_result)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)

    with patch("src.agent.override_parser.ChatAnthropic", return_value=mock_llm):
        result = await parse_operator_overrides(notes, assignment)

    assert len(result) == 1
    assert result[0].pipeline_user_id == uid
    assert result[0].from_group_id == "group-01"
    assert result[0].to_group_id == "group-02"


# ---------------------------------------------------------------------------
# AC-4b: Invalid IDs from LLM are filtered out
# ---------------------------------------------------------------------------


async def test_parse_filters_invalid_user_id():
    """AC-4b: An OperatorOverride with a fake user_id is silently dropped."""
    assignment, _ = _build_assignment_and_fvs(n_attendees=8, seed=42)

    groups = {g.group_id: g for g in assignment.groups}
    assert "group-01" in groups and "group-02" in groups

    bad_override = OperatorOverride(
        pipeline_user_id="fake-user-id",
        from_group_id="group-01",
        to_group_id="group-02",
    )
    mock_result = _make_parse_result([bad_override])

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_result)
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)

    with patch("src.agent.override_parser.ChatAnthropic", return_value=mock_llm):
        result = await parse_operator_overrides("Move fake-user-id from group-01 to group-02", assignment)

    assert result == []


# ---------------------------------------------------------------------------
# AC-4c: Empty notes returns empty list without calling LLM
# ---------------------------------------------------------------------------


async def test_parse_empty_notes_returns_empty():
    """AC-4c: Blank operator notes return [] with no LLM call."""
    assignment, _ = _build_assignment_and_fvs(n_attendees=8, seed=42)

    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_chain)

    with patch("src.agent.override_parser.ChatAnthropic", return_value=mock_llm):
        result = await parse_operator_overrides("", assignment)

    assert result == []
    mock_chain.ainvoke.assert_not_called()
