"""Pure surgical calculations and LASIK fallback policy for the parallel clean engine."""
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Tuple

from .policy import POLICY


@dataclass(frozen=True)
class LasikPlan:
    name: str
    flap_um: float
    optical_zone_mm: float
    transition_zone_mm: float


@dataclass(frozen=True)
class LasikPlanOutcome:
    plan: LasikPlan
    status: str
    pta_percent: Optional[float]
    independent_hard_stop: bool = False


LASIK_PLANS = (
    LasikPlan("Plan A", 100.0, 6.5, 9.0),
    LasikPlan("Plan B", 100.0, 6.0, 8.5),
    LasikPlan("Plan C", 90.0, 6.0, 8.5),
)


def lasik_rsb_um(cct_um: float, flap_um: float, ablation_um: float) -> float:
    return float(cct_um) - float(flap_um) - float(ablation_um)


def lasik_pta_percent(cct_um: float, flap_um: float, ablation_um: float) -> float:
    return 100.0 * (float(flap_um) + float(ablation_um)) / float(cct_um)


def prk_rst_um(cct_um: float, ablation_um: float) -> float:
    return float(cct_um) - POLICY.prk_epithelium_um - float(ablation_um)


def prk_pta_percent(cct_um: float, ablation_um: float) -> float:
    return 100.0 * (POLICY.prk_epithelium_um + float(ablation_um)) / float(cct_um)


def final_kmean_d(preop_kmean_d: float, intended_mrse_d: float) -> float:
    return float(preop_kmean_d) + POLICY.corneal_effect_per_intended_mrse_d * float(intended_mrse_d)


def final_kmean_within_hc_range(value: float) -> bool:
    return POLICY.final_kmean_min_d <= float(value) <= POLICY.final_kmean_max_d


def lasik_pta_cutoff(pta_percent: Optional[float]) -> bool:
    return isinstance(pta_percent, (int, float)) and not isinstance(pta_percent, bool) and float(pta_percent) >= POLICY.lasik_pta_cutoff_percent


def needs_lasik_fallback(outcome: LasikPlanOutcome) -> bool:
    """Mirror legacy fallback trigger without string-matching clinical reasons."""
    if outcome.independent_hard_stop:
        return False
    return outcome.status == "DO NOT PROCEED" or lasik_pta_cutoff(outcome.pta_percent)


def select_lasik_sequence(outcomes: Sequence[LasikPlanOutcome]) -> Tuple[LasikPlanOutcome, ...]:
    """Return the evaluated A→B→C sequence under the locked fallback contract."""
    selected = []
    for expected_plan, outcome in zip(LASIK_PLANS, outcomes):
        if outcome.plan != expected_plan:
            raise ValueError("LASIK outcomes must be supplied in Plan A, Plan B, Plan C order")
        selected.append(outcome)
        if not needs_lasik_fallback(outcome):
            break
    return tuple(selected)


def evaluate_lasik_fallback(evaluate_plan: Callable[[LasikPlan], LasikPlanOutcome]) -> Tuple[LasikPlanOutcome, ...]:
    """Evaluate Plan A→B→C lazily, stopping exactly when fallback is no longer allowed.

    The callback owns plan-specific clinical calculation (including recalculated
    ablation for the selected optical zone). This function owns only sequencing.
    """
    sequence = []
    for plan in LASIK_PLANS:
        outcome = evaluate_plan(plan)
        if outcome.plan != plan:
            raise ValueError("LASIK evaluator returned an outcome for the wrong plan")
        sequence.append(outcome)
        if not needs_lasik_fallback(outcome):
            break
    return tuple(sequence)


def final_lasik_status(sequence: Sequence[LasikPlanOutcome]) -> str:
    if not sequence:
        raise ValueError("At least one LASIK plan outcome is required")
    last = sequence[-1]
    if lasik_pta_cutoff(last.pta_percent):
        return "DO NOT PROCEED"
    return last.status
