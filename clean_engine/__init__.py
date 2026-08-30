"""Parallel clean architecture for CER-AI.

Not production-wired until equivalence testing is complete.
External callers may use the domain EyeInput -> assess -> AssessmentResult API,
or the migration-facing ReconciledEyeInput -> assess_reconciled -> CleanAssessment
service boundary when upstream reconciliation has already been completed.
"""
from .engine import assess
from .input_adapter import ReconciledEyeInput
from .models import AssessmentResult, EyeInput
from .policy import HCPolicy, POLICY
from .service import CleanAssessment, assess_reconciled

__all__ = [
    "EyeInput",
    "AssessmentResult",
    "assess",
    "ReconciledEyeInput",
    "CleanAssessment",
    "assess_reconciled",
    "POLICY",
    "HCPolicy",
]
