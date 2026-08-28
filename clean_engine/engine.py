"""Explicit deterministic orchestration for the parallel clean engine.

Pipeline: validate -> calculate -> score -> hard stops -> final decision.
This module remains isolated from production until full equivalence is proven.
"""
from .calculation import CalculationInput, calculate
from .finalization import FinalizationInput, finalize
from .hard_stops import HardStopInput, evaluate_hard_stops
from .models import AssessmentResult, EyeInput
from .policy import final_bad_d_classification
from .scoring import ScoringInput, calculate_scores
from .validation import ValidationInput, validate_decision_inputs


def assess(inp: EyeInput) -> AssessmentResult:
    procedure = (inp.procedure or "").upper()
    missing = tuple(validate_decision_inputs(ValidationInput(
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        bad_d=inp.bad_d,
        morphology=inp.morphology,
        procedure=procedure,
    )))
    warnings = ()

    calculation = calculate(CalculationInput(
        procedure=procedure,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        morphology=inp.morphology,
        intended_sphere_d=inp.intended_sphere_d,
        intended_cylinder_magnitude_d=inp.intended_cylinder_magnitude_d,
        intended_mrse_d=inp.intended_mrse_d,
        preop_kmean_d=inp.preop_kmean_d,
        ablation_um=inp.ablation_um,
        flap_um=inp.flap_um,
        laser_platform=inp.laser_platform,
        use_lasik_fallback_planning=inp.use_lasik_fallback_planning,
    ))
    calc = calculation.values

    scores, prk_scores = calculate_scores(ScoringInput(
        procedure=procedure,
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        morphology=inp.morphology,
        intended_mrse_d=inp.intended_mrse_d,
        lasik_rsb_um=calc.lasik_rsb_um,
        prk_pta_percent=calc.prk_pta_percent,
    ))

    bad_status = final_bad_d_classification(inp.bad_d)
    hard_stops = tuple(calculation.planning_hard_stops) + evaluate_hard_stops(HardStopInput(
        procedure=procedure,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        morphology=inp.morphology,
        bad_d_status=bad_status,
        intended_sphere_d=inp.intended_sphere_d,
        lasik_rsb_um=calc.lasik_rsb_um,
        prk_rst_um=calc.prk_rst_um,
        final_kmean_d=calc.final_kmean_d,
        lasik_erss_total=scores.erss_total,
    ))

    final = finalize(FinalizationInput(
        procedure=procedure,
        bad_d_status=bad_status,
        lasik_erss_total=scores.erss_total,
        prk_scores=prk_scores,
        hard_stops=hard_stops,
        missing=missing,
    ))
    return AssessmentResult(
        final.status, bad_status, calc, scores, hard_stops, missing,
        warnings, calculation.planning_sequence, prk_scores,
    )
