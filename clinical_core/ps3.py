"""Clinical-core façade for the already-pure PS3 evaluator.

`ps3_policy.py` is already side-effect free and independent of the runtime
composition layer. Re-exporting it here avoids maintaining a duplicate PS3
implementation while giving the new clinical core one stable namespace.
"""
from ps3_policy import (
    ALLOWED,
    DEFER,
    HIGH,
    MODERATE,
    NORMAL,
    NOT_EVALUATED,
    PS3EyeInput,
    PS3Finding,
    PS3InterEyeInput,
    PS3ProcedureDisposition,
    PS3Result,
    evaluate_ps3,
)

__all__ = [
    "ALLOWED",
    "DEFER",
    "HIGH",
    "MODERATE",
    "NORMAL",
    "NOT_EVALUATED",
    "PS3EyeInput",
    "PS3Finding",
    "PS3InterEyeInput",
    "PS3ProcedureDisposition",
    "PS3Result",
    "evaluate_ps3",
]
