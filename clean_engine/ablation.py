"""Pure ablation selection for the parallel clean engine.

Mirrors the locked runtime estimate_ablation contract without warnings/UI coupling.
"""
from dataclasses import dataclass
from typing import Optional


EX500_RATES_UM_PER_D = {6.0: 12.0, 6.5: 15.0, 7.0: 16.33}


@dataclass(frozen=True)
class AblationResult:
    ablation_um: Optional[float]
    source: str


def select_ablation(
    *,
    actual_ablation_um: Optional[float],
    intended_sphere_d: Optional[float],
    intended_cylinder_magnitude_d: Optional[float],
    optical_zone_mm: Optional[float],
    laser_platform: Optional[str],
) -> AblationResult:
    if isinstance(actual_ablation_um, (int, float)) and not isinstance(actual_ablation_um, bool):
        value = float(actual_ablation_um)
        if 0 <= value <= 400:
            return AblationResult(value, "ACTUAL")
        return AblationResult(None, "INVALID_ACTUAL")
    if actual_ablation_um is not None:
        return AblationResult(None, "INVALID_ACTUAL")

    numeric_sphere = isinstance(intended_sphere_d, (int, float)) and not isinstance(intended_sphere_d, bool)
    numeric_cylinder = isinstance(intended_cylinder_magnitude_d, (int, float)) and not isinstance(intended_cylinder_magnitude_d, bool)
    if numeric_sphere and float(intended_sphere_d) > 0:
        return AblationResult(None, "ACTUAL_REQUIRED_HYPEROPIC_OR_MIXED")

    platform = str(laser_platform or "").lower().replace(" ", "")
    is_ex500 = "alcon" in platform and "ex500" in platform
    rate = EX500_RATES_UM_PER_D.get(optical_zone_mm) if is_ex500 else None
    if numeric_sphere and numeric_cylinder and rate is not None:
        value = (abs(float(intended_sphere_d)) + abs(float(intended_cylinder_magnitude_d))) * rate
        return AblationResult(value, "HC_EX500_ESTIMATE")
    return AblationResult(None, "UNAVAILABLE")
