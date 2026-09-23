"""Independent CER-AI IOL selection module.

This package owns its input contract, extraction schema, rule engine, and web
routes. It does not import or modify the refractive-surgery clinical engine.
"""

from .engine import evaluate_case
from .models import IOLCaseInput, IOLPowerPlanInput
from .power import plan_iol_power

__all__ = ["IOLCaseInput", "IOLPowerPlanInput", "evaluate_case", "plan_iol_power"]
