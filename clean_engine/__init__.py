"""Parallel clean architecture for HC Ectasia App.

Not production-wired until equivalence testing is complete.
External callers should use the typed EyeInput -> assess -> AssessmentResult API.
"""
from .engine import assess
from .models import AssessmentResult, EyeInput
from .policy import HCPolicy, POLICY

__all__ = ["EyeInput", "AssessmentResult", "assess", "POLICY", "HCPolicy"]
