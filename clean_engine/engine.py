"""Explicit deterministic orchestration for the parallel clean engine.

Pipeline: validate -> calculate -> score -> hard stops -> final decision.
This module remains isolated from production until full equivalence is proven.
"""
from .calculation import CalculationInput, calculate
from .finalization import FinalizationInput, finalize
from .hard_stops import HardStopInput, evaluate_hard_stops
from .models import AssessmentResult, CalculatedValues, EyeInput, PrkScoreValues, ScoreValues
from .policy import final_bad_d_classification
from .scoring import ScoringInput, calculate_scores
from .validation import ValidationInput, finite_number_or_none, validate_decision_inputs


def assess(inp: EyeInput) -> AssessmentResult:
    procedure = (inp.procedure or "").upper()
    if inp.prior_refractive_surgery is True:
        return AssessmentResult(
            "POST-REFRACTIVE PATHWAY REQUIRED",
            final_bad_d_classification(inp.bad_d),
            CalculatedValues(),
            ScoreValues(None, None, None, None, None, None),
            prk_scores=PrkScoreValues(),
        )
    missing = tuple(validate_decision_inputs(ValidationInput(
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        bad_d=inp.bad_d,
        morphology=inp.morphology,
        procedure=procedure,
        prior_refractive_surgery=inp.prior_refractive_surgery,
        ablation_um=inp.ablation_um,
        flap_um=inp.flap_um,
        preop_kmean_d=inp.preop_kmean_d,
        manifest_mrse_d=inp.manifest_mrse_d,
        intended_mrse_d=inp.intended_mrse_d,
        intended_sphere_d=inp.intended_sphere_d,
        intended_cylinder_magnitude_d=inp.intended_cylinder_magnitude_d,
        laser_platform=inp.laser_platform,
    )))
    warnings = ()
    age = finite_number_or_none(inp.age_years)
    pachy = finite_number_or_none(inp.pachy_thinnest_um)
    bad_d = finite_number_or_none(inp.bad_d)
    ablation = finite_number_or_none(inp.ablation_um)
    flap = finite_number_or_none(inp.flap_um)
    preop_kmean = finite_number_or_none(inp.preop_kmean_d)
    manifest_mrse = finite_number_or_none(inp.manifest_mrse_d)
    intended_mrse = finite_number_or_none(inp.intended_mrse_d)
    intended_sphere = finite_number_or_none(inp.intended_sphere_d)
    intended_cylinder = finite_number_or_none(inp.intended_cylinder_magnitude_d)
    if "intended_mrse_consistency" in missing:
        intended_mrse = None

    calculation = calculate(CalculationInput(
        procedure=procedure,
        pachy_thinnest_um=pachy,
        morphology=inp.morphology,
        intended_sphere_d=intended_sphere,
        intended_cylinder_magnitude_d=intended_cylinder,
        intended_mrse_d=intended_mrse,
        preop_kmean_d=preop_kmean,
        ablation_um=ablation,
        flap_um=flap,
        laser_platform=inp.laser_platform,
        use_lasik_fallback_planning=procedure == "LASIK",
    ))
    calc = calculation.values

    scores, prk_scores = calculate_scores(ScoringInput(
        procedure=procedure,
        age_years=age,
        pachy_thinnest_um=pachy,
        morphology=inp.morphology,
        manifest_mrse_d=manifest_mrse,
        lasik_rsb_um=calc.lasik_rsb_um,
        prk_pta_percent=calc.prk_pta_percent,
    ))

    bad_status = final_bad_d_classification(bad_d)
    hard_stops = tuple(calculation.planning_hard_stops) + evaluate_hard_stops(HardStopInput(
        procedure=procedure,
        pachy_thinnest_um=pachy,
        morphology=inp.morphology,
        bad_d_status=bad_status,
        intended_sphere_d=intended_sphere,
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
