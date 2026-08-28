"""Deterministic surgical calculation/planning stage for the parallel clean engine."""
from dataclasses import dataclass
from typing import Optional, Tuple

from .models import CalculatedValues, LasikPlanningStep
from .policy import POLICY
from .surgery import (
    LasikPlanOutcome, evaluate_lasik_fallback, final_kmean_d, final_lasik_status,
    lasik_independent_hard_stop, lasik_pta_percent, lasik_rsb_um,
    plan_specific_ablation, prk_pta_percent, prk_rst_um,
)


@dataclass(frozen=True)
class CalculationInput:
    procedure: str
    pachy_thinnest_um: Optional[float]
    morphology: str
    intended_sphere_d: Optional[float]
    intended_cylinder_magnitude_d: Optional[float]
    intended_mrse_d: Optional[float]
    preop_kmean_d: Optional[float]
    ablation_um: Optional[float]
    flap_um: Optional[float]
    laser_platform: str
    use_lasik_fallback_planning: bool


@dataclass(frozen=True)
class CalculationOutput:
    values: CalculatedValues
    planning_sequence: Tuple[LasikPlanningStep, ...] = ()
    planning_hard_stops: Tuple[str, ...] = ()


def calculate(inp: CalculationInput) -> CalculationOutput:
    procedure = (inp.procedure or "").upper()
    predicted_final_kmean = None
    if inp.preop_kmean_d is not None and inp.intended_mrse_d is not None:
        predicted_final_kmean = final_kmean_d(inp.preop_kmean_d, inp.intended_mrse_d)

    calc = CalculatedValues()
    sequence = ()
    planning_hard_stops = []

    if procedure == "LASIK" and inp.use_lasik_fallback_planning and inp.pachy_thinnest_um is not None:
        independent = lasik_independent_hard_stop(
            pachy_thinnest_um=inp.pachy_thinnest_um,
            morphology=inp.morphology,
            intended_sphere_d=inp.intended_sphere_d,
            final_kmean=predicted_final_kmean,
        )

        def evaluate(plan):
            ablation = plan_specific_ablation(
                plan,
                actual_ablation_um=inp.ablation_um,
                intended_sphere_d=inp.intended_sphere_d,
                intended_cylinder_magnitude_d=inp.intended_cylinder_magnitude_d,
                laser_platform=inp.laser_platform,
                is_fallback_plan=plan.name != "Plan A",
            )
            if ablation.ablation_um is None:
                return LasikPlanOutcome(plan, "DATA INSUFFICIENT", None, independent, None, ablation.source)
            rsb_value = lasik_rsb_um(inp.pachy_thinnest_um, plan.flap_um, ablation.ablation_um)
            pta_value = lasik_pta_percent(inp.pachy_thinnest_um, plan.flap_um, ablation.ablation_um)
            status = "DO NOT PROCEED" if rsb_value < POLICY.lasik_rsb_hard_stop_um else "PASS WITH CAUTION"
            return LasikPlanOutcome(plan, status, pta_value, independent, ablation.ablation_um, ablation.source)

        outcomes = evaluate_lasik_fallback(evaluate)
        steps = []
        for outcome in outcomes:
            rsb_value = None if outcome.ablation_um is None else lasik_rsb_um(inp.pachy_thinnest_um, outcome.plan.flap_um, outcome.ablation_um)
            steps.append(LasikPlanningStep(
                outcome.plan.name, outcome.plan.flap_um, outcome.plan.optical_zone_mm,
                outcome.plan.transition_zone_mm, outcome.ablation_um, outcome.ablation_source,
                rsb_value, outcome.pta_percent, outcome.status,
            ))
        sequence = tuple(steps)
        selected = outcomes[-1]
        if selected.ablation_um is not None:
            calc = CalculatedValues(
                lasik_rsb_um=lasik_rsb_um(inp.pachy_thinnest_um, selected.plan.flap_um, selected.ablation_um),
                lasik_pta_percent=selected.pta_percent,
            )
        if final_lasik_status(outcomes) == "DO NOT PROCEED" and calc.lasik_pta_percent is not None and calc.lasik_pta_percent >= POLICY.lasik_pta_cutoff_percent:
            planning_hard_stops.append("LASIK_PTA_GE_40_AFTER_FALLBACK")
    elif procedure == "LASIK" and inp.pachy_thinnest_um is not None and inp.flap_um is not None and inp.ablation_um is not None:
        calc = CalculatedValues(
            lasik_rsb_um=lasik_rsb_um(inp.pachy_thinnest_um, inp.flap_um, inp.ablation_um),
            lasik_pta_percent=lasik_pta_percent(inp.pachy_thinnest_um, inp.flap_um, inp.ablation_um),
        )
    elif procedure == "PRK" and inp.pachy_thinnest_um is not None and inp.ablation_um is not None:
        calc = CalculatedValues(
            prk_rst_um=prk_rst_um(inp.pachy_thinnest_um, inp.ablation_um),
            prk_pta_percent=prk_pta_percent(inp.pachy_thinnest_um, inp.ablation_um),
        )

    if predicted_final_kmean is not None:
        calc = CalculatedValues(calc.lasik_rsb_um, calc.lasik_pta_percent, calc.prk_rst_um, calc.prk_pta_percent, predicted_final_kmean)

    return CalculationOutput(calc, sequence, tuple(planning_hard_stops))
