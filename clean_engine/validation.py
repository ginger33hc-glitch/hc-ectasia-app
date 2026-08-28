"""Typed decision-critical input validation for the parallel clean engine."""
from dataclasses import dataclass
from typing import Optional, Tuple

from .policy import randleman_topography_points


@dataclass(frozen=True)
class ValidationInput:
    age_years: Optional[float]
    pachy_thinnest_um: Optional[float]
    bad_d: Optional[float]
    morphology: str
    procedure: str


def validate_decision_inputs(inp: ValidationInput) -> Tuple[str, ...]:
    """Return missing/unsupported principal inputs in deterministic order."""
    missing = []
    for name, value in (
        ("age_years", inp.age_years),
        ("pachy_thinnest_um", inp.pachy_thinnest_um),
        ("bad_d", inp.bad_d),
    ):
        if value is None:
            missing.append(name)
    if randleman_topography_points(inp.morphology) is None:
        missing.append("morphology")
    if (inp.procedure or "").upper() not in {"LASIK", "PRK"}:
        missing.append("procedure")
    return tuple(missing)
