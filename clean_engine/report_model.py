"""Presentation-neutral report model for clean assessment results.

This layer translates domain output into a stable payload without renderer,
formatting, color, or UI logic. Presentation implementations consume it later.
"""
from dataclasses import dataclass
from typing import Tuple

from .models import AssessmentResult, CalculatedValues, LasikPlanningStep, PrkScoreValues, ScoreValues
from .status import presentation_class


@dataclass(frozen=True)
class ReportModel:
    status: str
    presentation_class: str
    bad_d_status: str
    calculations: CalculatedValues
    lasik_scores: ScoreValues
    prk_scores: PrkScoreValues
    hard_stops: Tuple[str, ...]
    missing: Tuple[str, ...]
    warnings: Tuple[str, ...]
    lasik_planning_sequence: Tuple[LasikPlanningStep, ...]


def build_report_model(result: AssessmentResult) -> ReportModel:
    """Build an immutable, renderer-independent report payload."""
    return ReportModel(
        status=result.status,
        presentation_class=presentation_class(result.status),
        bad_d_status=result.bad_d_status,
        calculations=result.calculations,
        lasik_scores=result.scores,
        prk_scores=result.prk_scores,
        hard_stops=result.hard_stops,
        missing=result.missing,
        warnings=result.warnings,
        lasik_planning_sequence=result.lasik_planning_sequence,
    )
