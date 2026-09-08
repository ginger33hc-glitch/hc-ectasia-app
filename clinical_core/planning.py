"""Pure CER-AI procedure-planning policy.

Planning owns plan order and MMC guidance only. It does not contain a second
clinical safety scorer. Every LASIK candidate must be evaluated by the same
canonical safety callback supplied by the clinical pipeline/service.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, Optional

from .refraction import HYPEROPIC, MIXED, MYOPIC

LASIK_PLANS = (
    {"name": "Plan A", "flap_um": 100.0, "optical_zone_mm": 6.5, "transition_zone_mm": 9.0},
    {"name": "Plan B", "flap_um": 100.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
    {"name": "Plan C", "flap_um": 90.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
)

MYOPIC_ABLATION_UM_PER_D = {6.0: 12.0, 6.5: 15.0, 7.0: 16.33}


def estimate_myopic_ablation_um(intended_mrse_d, optical_zone_mm):
    """Return the approved CER-AI myopic EX500 linear estimate.

    This estimate is planning-only and must never be used for hyperopic or mixed
    profiles. Actual planned maximum ablation remains preferred when available.
    """
    if (
        not isinstance(intended_mrse_d, (int, float))
        or isinstance(intended_mrse_d, bool)
        or not isfinite(float(intended_mrse_d))
    ):
        return None
    try:
        zone = float(optical_zone_mm)
    except (TypeError, ValueError):
        return None
    rate = MYOPIC_ABLATION_UM_PER_D.get(zone)
    if rate is None:
        return None
    return abs(float(intended_mrse_d)) * rate

MMC_MANDATORY = "MANDATORY"
MMC_RECOMMENDED = "RECOMMENDED"
MMC_REVIEW_REQUIRED = "REVIEW_REQUIRED"
MMC_NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class PlanEvaluation:
    plan: str
    safe: bool
    rejection_reasons: tuple[str, ...] = ()
    result: Any = None


@dataclass(frozen=True)
class PlanningResult:
    selected_plan: Optional[str]
    sequence: tuple[PlanEvaluation, ...]


def select_first_safe_lasik_plan(
    evaluator: Callable[[dict[str, Any]], PlanEvaluation],
) -> PlanningResult:
    """Evaluate A -> B -> C with one caller-supplied canonical safety engine.

    The first safe candidate is selected. Rejected candidates remain in the
    sequence with reasons. This function never changes a clinical disposition
    and never interprets safety thresholds itself.
    """
    sequence = []
    for spec in LASIK_PLANS:
        evaluation = evaluator(dict(spec))
        if not isinstance(evaluation, PlanEvaluation):
            raise TypeError("LASIK plan evaluator must return PlanEvaluation")
        if evaluation.plan != spec["name"]:
            raise ValueError("LASIK plan evaluator returned mismatched plan identity")
        sequence.append(evaluation)
        if evaluation.safe:
            return PlanningResult(evaluation.plan, tuple(sequence))
    return PlanningResult(None, tuple(sequence))


def mmc_guidance(procedure: str, refractive_group: str, intended_mrse_d) -> str:
    """Return the accepted CER-AI PRK mitomycin-C guidance.

    Myopic PRK |MRSE| >=4.00 D: mandatory.
    Myopic PRK |MRSE| <4.00 D: recommended.
    Hyperopic PRK: mandatory.
    Mixed PRK has no approved scalar rule in the current matrix and therefore
    requires explicit review rather than borrowing the myopic rule.
    """
    if str(procedure or "").strip().upper() != "PRK":
        return MMC_NOT_APPLICABLE
    group = str(refractive_group or "").strip().upper()
    if group == HYPEROPIC:
        return MMC_MANDATORY
    if group == MIXED:
        return MMC_REVIEW_REQUIRED
    if group != MYOPIC:
        return MMC_REVIEW_REQUIRED
    if not isinstance(intended_mrse_d, (int, float)) or isinstance(intended_mrse_d, bool):
        return MMC_REVIEW_REQUIRED
    return MMC_MANDATORY if abs(float(intended_mrse_d)) >= 4.0 else MMC_RECOMMENDED
