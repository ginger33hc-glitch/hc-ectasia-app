"""Typed decision-critical input validation for the parallel clean engine."""
from dataclasses import dataclass
import math
from typing import Optional, Tuple

from .policy import randleman_topography_points


@dataclass(frozen=True)
class ValidationInput:
    age_years: Optional[float]
    pachy_thinnest_um: Optional[float]
    bad_d: Optional[float]
    morphology: str
    procedure: str
    prior_refractive_surgery: Optional[bool] = None
    ablation_um: Optional[float] = None
    flap_um: Optional[float] = None
    preop_kmean_d: Optional[float] = None
    manifest_mrse_d: Optional[float] = None
    intended_mrse_d: Optional[float] = None
    intended_sphere_d: Optional[float] = None
    intended_cylinder_magnitude_d: Optional[float] = None
    laser_platform: Optional[str] = None


def _finite_number(value: object, low: float, high: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and low <= float(value) <= high
    )


def finite_number_or_none(value: object) -> Optional[float]:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ):
        return float(value)
    return None


def validate_decision_inputs(inp: ValidationInput) -> Tuple[str, ...]:
    """Return missing/unsupported principal inputs in deterministic order."""
    missing = []
    for name, value, low, high in (
        ("age_years", inp.age_years, 18, 120),
        ("pachy_thinnest_um", inp.pachy_thinnest_um, 300, 800),
        ("bad_d", inp.bad_d, -10, 20),
        ("preop_kmean_d", inp.preop_kmean_d, 20, 80),
        ("intended_mrse_d", inp.intended_mrse_d, -40, 20),
        ("intended_sphere_d", inp.intended_sphere_d, -30, 20),
        ("intended_cylinder_magnitude_d", inp.intended_cylinder_magnitude_d, 0, 15),
    ):
        if not _finite_number(value, low, high):
            missing.append(name)
    platform = str(inp.laser_platform or "").lower().replace(" ", "")
    estimate_available = (
        inp.ablation_um is None
        and _finite_number(inp.intended_sphere_d, -30, 0)
        and _finite_number(inp.intended_cylinder_magnitude_d, 0, 15)
        and "alcon" in platform
        and "ex500" in platform
    )
    if not estimate_available and not _finite_number(inp.ablation_um, 0, 400):
        missing.append("ablation_um")
    if inp.prior_refractive_surgery is not False:
        missing.append("prior_refractive_surgery")
    if randleman_topography_points(inp.morphology) is None:
        missing.append("morphology")
    procedure = (inp.procedure or "").upper()
    if procedure not in {"LASIK", "PRK"}:
        missing.append("procedure")
    if not str(inp.laser_platform or "").strip():
        missing.append("laser_platform")
    if (
        _finite_number(inp.intended_mrse_d, -40, 20)
        and _finite_number(inp.intended_sphere_d, -30, 20)
        and _finite_number(inp.intended_cylinder_magnitude_d, 0, 15)
        and abs(
            float(inp.intended_mrse_d)
            - (
                float(inp.intended_sphere_d)
                - float(inp.intended_cylinder_magnitude_d) / 2.0
            )
        ) > 0.01
    ):
        missing.append("intended_mrse_consistency")
    if procedure == "LASIK":
        if not _finite_number(inp.manifest_mrse_d, -40, 20):
            missing.append("manifest_mrse_d")
        if inp.flap_um is not None and inp.flap_um not in {90, 100, 110, 120}:
            missing.append("flap_um")
    return tuple(missing)
