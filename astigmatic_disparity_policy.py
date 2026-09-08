"""Non-scoring manifest/tomographic astigmatic-disparity validation.

This comparison is a measurement and treatment-planning quality check. It is
not a PS3 factor and cannot change ectasia scoring or procedural eligibility.
"""
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Optional

NORMAL = "NORMAL"
VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class AstigmaticDisparityResult:
    status: str
    magnitude_difference_d: Optional[float]
    axis_difference_deg: Optional[float]
    detail: str
    affects_ps3: bool = False
    affects_procedure_eligibility: bool = False

    def as_dict(self):
        return asdict(self)


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def axis_difference_deg(first, second):
    """Return the smallest meridional difference on the 0–180° circle."""
    first = _number(first)
    second = _number(second)
    if first is None or second is None:
        return None
    difference = abs((first % 180.0) - (second % 180.0))
    return min(difference, 180.0 - difference)


def evaluate_astigmatic_disparity(
    *,
    tomographic_astig_d,
    tomographic_flat_axis_deg,
    manifest_astig_d,
    manifest_axis_deg,
):
    """Evaluate disparity without contributing to any ectasia-risk score."""
    tomo = _number(tomographic_astig_d)
    manifest = _number(manifest_astig_d)
    if tomo is None or manifest is None:
        return AstigmaticDisparityResult(
            NOT_EVALUATED, None, None,
            "Manifest or tomographic astigmatic magnitude is unavailable; no PS3 consequence.",
        )

    magnitude_difference = abs(abs(manifest) - abs(tomo))
    axis_applicable = abs(tomo) > 1e-12 and abs(manifest) > 1e-12
    axis_difference = None
    if axis_applicable:
        axis_difference = axis_difference_deg(
            tomographic_flat_axis_deg, manifest_axis_deg,
        )

    magnitude_trigger = magnitude_difference >= 1.0
    axis_trigger = axis_difference is not None and axis_difference >= 10.0
    if magnitude_trigger or axis_trigger:
        parts = [f"magnitude difference {magnitude_difference:.2f} D"]
        if axis_difference is not None:
            parts.append(f"axis difference {axis_difference:.1f}°")
        return AstigmaticDisparityResult(
            VALIDATION_REQUIRED,
            round(magnitude_difference, 2),
            round(axis_difference, 1) if axis_difference is not None else None,
            "Astigmatic disparity (" + "; ".join(parts) + ") requires measurement/refraction validation; it is not a PS3 risk factor and does not independently defer LASIK.",
        )

    if axis_applicable and axis_difference is None:
        return AstigmaticDisparityResult(
            NOT_EVALUATED,
            round(magnitude_difference, 2),
            None,
            "Astigmatic axis comparison is unavailable; this passive validation item does not affect PS3 or procedure eligibility.",
        )

    axis_text = (
        f"; axis difference {axis_difference:.1f}°"
        if axis_difference is not None
        else "; axis comparison not applicable because an astigmatic magnitude is zero"
    )
    return AstigmaticDisparityResult(
        NORMAL,
        round(magnitude_difference, 2),
        round(axis_difference, 1) if axis_difference is not None else None,
        f"Astigmatic disparity within validation thresholds: magnitude difference {magnitude_difference:.2f} D{axis_text}; no PS3 consequence.",
    )


def axis_requires_targeted_verification(result: AstigmaticDisparityResult) -> bool:
    return result.axis_difference_deg is not None and result.axis_difference_deg >= 10.0
