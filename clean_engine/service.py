"""Application service for the clean clinical pipeline.

The service boundary accepts only reconciled/adjudicated values. Raw extraction
payloads and presentation rendering stay outside the clinical engine.
"""
from dataclasses import dataclass

from .engine import assess
from .input_adapter import ReconciledEyeInput, to_eye_input
from .models import AssessmentResult
from .report_model import ReportModel, build_report_model


@dataclass(frozen=True)
class CleanAssessment:
    result: AssessmentResult
    report: ReportModel


def assess_reconciled(inp: ReconciledEyeInput) -> CleanAssessment:
    """Run the complete clean boundary from reconciled input to report payload."""
    result = assess(to_eye_input(inp))
    return CleanAssessment(result=result, report=build_report_model(result))
