"""Explicit deterministic orchestration for the parallel clean engine.

Pipeline: validate -> calculate -> score -> hard stops -> final decision.
This module remains isolated from production until full equivalence is proven.
"""
from .calculation import CalculationInput, calculate
from .decision import DecisionInput, decide
from .hard_stops import HardStopInput, evaluate_hard_stops
from .models import AssessmentResult, EyeInput
from .policy import final_bad_d_classification
from .scoring import ScoringInput, calculate_scores
from .status import combine_status
from .validation import ValidationInput, validate_decision_inputs


def assess(inp: EyeInput) -> AssessmentResult:
    procedure = (inp.procedure or "").upper()
    missing = list(validate_decision_inputs(ValidationInput(
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        bad_d=inp.bad_d,
        morphology=inp.morphology,
        procedure=procedure,
    )))
    warnings = []

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
    planning_sequence = calculation.planning_sequence
    hard_stops = list(calculation.planning_hard_stops)

    scores, prk_scores = calculate_scores(ScoringInput(
        procedure=procedure,
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        morphology=inp.morphology,
        intended_mrse_d=inp.intended_mrse_d,
        lasik_rsb_um=calc.lasik_rsb_um,
        prk_pta_percent=calc.prk_pta_percent,
    ))
    erss_total = scores.erss_total

    bad_status = final_bad_d_classification(inp.bad_d)
    hard_stops.extend(evaluate_hard_stops(HardStopInput(
        procedure=procedure,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        morphology=inp.morphology,
        bad_d_status=bad_status,
        intended_sphere_d=inp.intended_sphere_d,
        lasik_rsb_um=calc.lasik_rsb_um,
        prk_rst_um=calc.prk_rst_um,
        final_kmean_d=calc.final_kmean_d,
        lasik_erss_total=erss_total,
    )))

    upstream = "DO NOT PROCEED" if hard_stops else ("DATA INSUFFICIENT" if missing else "PASS")
    if procedure == "PRK" and not hard_stops and not missing:
        if prk_scores.category == "HIGH_CONCERN":
            upstream = combine_status(upstream, "DO NOT PROCEED")
        elif prk_scores.category == "CAUTION":
            upstream = combine_status(upstream, "CAUTION — STOP/DEFER")
        if prk_scores.pta_evidence_gap:
            upstream = combine_status(upstream, "REVIEW — NOT CLEARED")

    decision = decide(DecisionInput(upstream, bad_status, erss_total, bool(hard_stops), bool(missing)))
    return AssessmentResult(
        decision.status, bad_status, calc, scores, tuple(hard_stops), tuple(missing),
        tuple(warnings), planning_sequence, prk_scores,
    )
