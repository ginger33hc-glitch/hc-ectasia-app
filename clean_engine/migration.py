"""Explicit migration seam for future production cutover.

Production remains on the canonical runtime. This module defines the single clean
entrypoint that a later, explicitly approved production adapter can call without
importing clean-engine internals.
"""
from .input_adapter import ReconciledEyeInput
from .service import CleanAssessment, assess_reconciled


def run_clean_assessment(inp: ReconciledEyeInput) -> CleanAssessment:
    """Run the stable migration-facing clean assessment contract."""
    return assess_reconciled(inp)
