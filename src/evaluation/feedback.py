"""Post-event feedback ingestion and weight adjustment suggestions."""

from __future__ import annotations

from scipy.stats import spearmanr
from pydantic import BaseModel, field_validator

from src.matching.assignment import GroupAssignment


class AttendeeRating(BaseModel):
    pipeline_user_id: str
    group_id: str
    satisfaction: int  # 1–5 inclusive

    @field_validator("satisfaction")
    @classmethod
    def _validate_satisfaction(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError(f"satisfaction must be 1–5, got {v}")
        return v


class EventFeedback(BaseModel):
    event_id: str
    ratings: list[AttendeeRating]
    collected_at: str  # ISO 8601


def group_satisfaction_scores(feedback: EventFeedback) -> dict[str, float]:
    """Compute mean satisfaction score per group_id."""
    grouped: dict[str, list[int]] = {}
    for r in feedback.ratings:
        grouped.setdefault(r.group_id, []).append(r.satisfaction)
    return {gid: sum(vals) / len(vals) for gid, vals in grouped.items()}


def cohesion_satisfaction_correlation(
    assignment: GroupAssignment, feedback: EventFeedback
) -> float:
    """Spearman rank correlation between group cohesion and satisfaction scores."""
    sat_scores = group_satisfaction_scores(feedback)
    assignment_group_ids = {g.group_id for g in assignment.groups}
    common = assignment_group_ids & sat_scores.keys()

    if len(common) < 2:
        return 0.0

    cohesion_values = []
    satisfaction_values = []
    for g in assignment.groups:
        if g.group_id in common:
            cohesion_values.append(g.cohesion_score)
            satisfaction_values.append(sat_scores[g.group_id])

    return float(spearmanr(cohesion_values, satisfaction_values).statistic)


def suggest_weight_adjustments(
    current_weights: dict[str, float],
    rank_corr: float,
    delta: float = 0.05,
) -> dict[str, float]:
    """Suggest weight nudges toward uniform when correlation is low."""
    if rank_corr >= 0.5:
        return dict(current_weights)

    max_key = max(current_weights, key=current_weights.__getitem__)
    min_key = min(current_weights, key=current_weights.__getitem__)

    if max_key == min_key:
        return dict(current_weights)

    result = dict(current_weights)
    result[max_key] = result[max_key] - delta
    result[min_key] = result[min_key] + delta

    return {k: max(0.5, min(2.0, v)) for k, v in result.items()}
