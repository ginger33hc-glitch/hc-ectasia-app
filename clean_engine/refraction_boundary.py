"""Refraction compatibility boundary for clean-engine migration.

This module does not normalize raw refraction. Canonical production already performs
signed-cylinder transposition before assessment. The clean migration accepts only
that normalized minus-cylinder representation and explicitly rejects patterns whose
legacy clinical pathway is not yet modeled equivalently.
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class RefractionCompatibility:
    supported: bool
    category: str
    reasons: Tuple[str, ...] = ()


def classify_normalized_refraction(
    sphere_d: Optional[float], cylinder_magnitude_d: Optional[float]
) -> str:
    if not isinstance(sphere_d, (int, float)) or isinstance(sphere_d, bool):
        return "UNAVAILABLE"
    if not isinstance(cylinder_magnitude_d, (int, float)) or isinstance(cylinder_magnitude_d, bool):
        return "UNAVAILABLE"
    sphere = float(sphere_d)
    cylinder = float(cylinder_magnitude_d)
    if cylinder < 0:
        return "INVALID_NORMALIZED_CYLINDER"
    second = sphere - cylinder
    eps = 1e-9
    sphere = 0.0 if abs(sphere) <= eps else sphere
    second = 0.0 if abs(second) <= eps else second
    if sphere > 0 and second > 0:
        return "HYPEROPIC"
    if sphere > 0 and second < 0:
        return "MIXED_ASTIGMATISM"
    if sphere < 0 and second < 0:
        return "MYOPIC"
    if sphere > 0 and second == 0:
        return "SIMPLE_HYPEROPIC_ASTIGMATISM"
    if sphere == 0 and second < 0:
        return "SIMPLE_MYOPIC_ASTIGMATISM"
    if sphere == 0 and second == 0:
        return "PLANO"
    return "UNCLASSIFIED"


def clean_refraction_compatibility(
    sphere_d: Optional[float], cylinder_magnitude_d: Optional[float]
) -> RefractionCompatibility:
    category = classify_normalized_refraction(sphere_d, cylinder_magnitude_d)
    if category in {"MYOPIC", "SIMPLE_MYOPIC_ASTIGMATISM", "PLANO"}:
        return RefractionCompatibility(True, category)
    if category == "UNAVAILABLE":
        return RefractionCompatibility(False, category, ("normalized refraction unavailable",))
    if category == "INVALID_NORMALIZED_CYLINDER":
        return RefractionCompatibility(False, category, ("clean boundary requires nonnegative cylinder magnitude",))
    return RefractionCompatibility(
        False,
        category,
        ("legacy hyperopic/mixed clinical pathway is not yet modeled equivalently in the clean engine",),
    )
