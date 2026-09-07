"""Pure Belin/Ambrosio BAD evaluation for CER-AI.

Final BAD-D is the only BAD decision signal. Df/Db/Dp/Dt/Da, ARTmax and PPI are
contextual values only and never independently change disposition in this module.
No BAD value is reconstructed from another value.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

NORMAL = "NORMAL"
SUSPICIOUS = "SUSPICIOUS"
ABNORMAL = "ABNORMAL"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class BADContext:
    df: Optional[float] = None
    db: Optional[float] = None
    dp: Optional[float] = None
    dt: Optional[float] = None
    da: Optional[float] = None
    artmax_um: Optional[float] = None
    ppi_min: Optional[float] = None
    ppi_avg: Optional[float] = None
    ppi_max: Optional[float] = None


@dataclass(frozen=True)
class BADResult:
    final_d: Optional[float]
    classification: str
    context: BADContext


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def final_bad_d_classification(value) -> str:
    if not _finite(value):
        return UNAVAILABLE
    value = float(value)
    if value <= 1.60:
        return NORMAL
    if value < 2.60:
        return SUSPICIOUS
    return ABNORMAL


def evaluate_bad(final_d, *, context: BADContext | None = None) -> BADResult:
    """Evaluate only readable Final D; adjunct values are preserved unchanged."""
    numeric_final = float(final_d) if _finite(final_d) else None
    return BADResult(
        final_d=numeric_final,
        classification=final_bad_d_classification(final_d),
        context=context or BADContext(),
    )
