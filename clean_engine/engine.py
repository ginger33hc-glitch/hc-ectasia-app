"""Explicit deterministic orchestration for the parallel clean engine.

Pipeline: validate -> calculate -> score -> hard stops -> final decision.
This module remains isolated from production until full equivalence is proven.
"""
from .decision import DecisionInput, decide
from .models import AssessmentResult, CalculatedValues, EyeInput, LasikPlanningStep, PrkScoreValues, ScoreValues
from .policy import (
    POLICY, age_points, final_bad_d_classification, lasik_mrse_points,
    lasik_pachymetry_points, lasik_rsb_points, randleman_topography_points,
)
from .prk import prk_morphology_points, prk_pachymetry_points, prk_pta_evidence_gap, prk_score_category, prk_score_total
from .status import combine_status
from .surgery import (
    LasikPlanOutcome, evaluate_lasik_fallback, final_kmean_d, final_lasik_status,
    lasik_pta_percent, lasik_rsb_um, plan_specific_ablation, prk_pta_percent,
    prk_rst_um,
)


def assess(inp: EyeInput) -> AssessmentResult:
    procedure = (inp.procedure or "").upper()
    missing, hard_stops, warnings = [], [], []
    planning_sequence = ()

    for name, value in (("age_years", inp.age_years), ("pachy_thinnest_um", inp.pachy_thinnest_um), ("bad_d", inp.bad_d)):
        if value is None:
            missing.append(name)
    if randleman_topography_points(inp.morphology) is None:
        missing.append("morphology")
    if procedure not in {"LASIK", "PRK"}:
        missing.append("procedure")

    calc = CalculatedValues()
    if procedure == "LASIK" and inp.use_lasik_fallback_planning and inp.pachy_thinnest_um is not None:
        independent = (
            inp.pachy_thinnest_um <= POLICY.pachymetry_hard_stop_um
            or inp.morphology == "ABNORMAL_ECTATIC"
            or (inp.intended_sphere_d is not None and (inp.intended_sphere_d < -10.0 or inp.intended_sphere_d > 6.0))
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
        planning_sequence = tuple(steps)
        selected = outcomes[-1]
        if selected.ablation_um is not None:
            calc = CalculatedValues(
                lasik_rsb_um=lasik_rsb_um(inp.pachy_thinnest_um, selected.plan.flap_um, selected.ablation_um),
                lasik_pta_percent=selected.pta_percent,
            )
        if final_lasik_status(outcomes) == "DO NOT PROCEED" and calc.lasik_pta_percent is not None and calc.lasik_pta_percent >= POLICY.lasik_pta_cutoff_percent:
            hard_stops.append("LASIK_PTA_GE_40_AFTER_FALLBACK")
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

    if inp.preop_kmean_d is not None and inp.intended_mrse_d is not None:
        calc = CalculatedValues(calc.lasik_rsb_um, calc.lasik_pta_percent, calc.prk_rst_um, calc.prk_pta_percent, final_kmean_d(inp.preop_kmean_d, inp.intended_mrse_d))

    age, pachy, topo = age_points(inp.age_years), lasik_pachymetry_points(inp.pachy_thinnest_um), randleman_topography_points(inp.morphology)
    rsb = lasik_rsb_points(calc.lasik_rsb_um) if procedure == "LASIK" else None
    mrse = lasik_mrse_points(inp.intended_mrse_d) if procedure == "LASIK" else None
    erss_total = None if procedure != "LASIK" or None in (age, pachy, topo, rsb, mrse) else int(age + pachy + topo + rsb + mrse)
    scores = ScoreValues(age, pachy, topo, rsb, mrse, erss_total)

    prk_scores = PrkScoreValues()
    if procedure == "PRK":
        prk_total = prk_score_total(inp.age_years, inp.pachy_thinnest_um, inp.morphology)
        prk_scores = PrkScoreValues(
            age_points=age_points(inp.age_years),
            pachymetry_points=prk_pachymetry_points(inp.pachy_thinnest_um),
            morphology_points=prk_morphology_points(inp.morphology),
            total=prk_total,
            category=prk_score_category(prk_total),
            pta_evidence_gap=prk_pta_evidence_gap(calc.prk_pta_percent),
        )

    bad_status = final_bad_d_classification(inp.bad_d)
    if inp.pachy_thinnest_um is not None and inp.pachy_thinnest_um <= POLICY.pachymetry_hard_stop_um:
        hard_stops.append("PACHYMETRY_LE_480")
    if inp.morphology == "ABNORMAL_ECTATIC": hard_stops.append("ABNORMAL_ECTATIC_TOPOGRAPHY")
    if bad_status == "ABNORMAL": hard_stops.append("FINAL_BAD_D_ABNORMAL")
    if inp.intended_sphere_d is not None:
        if inp.intended_sphere_d < -10.0: hard_stops.append("INTENDED_SPHERE_LT_MINUS_10")
        if inp.intended_sphere_d > 6.0: hard_stops.append("INTENDED_SPHERE_GT_PLUS_6")
    if procedure == "LASIK" and calc.lasik_rsb_um is not None and calc.lasik_rsb_um < POLICY.lasik_rsb_hard_stop_um:
        hard_stops.append("LASIK_RSB_LT_300")
    if procedure == "PRK" and calc.prk_rst_um is not None and calc.prk_rst_um < POLICY.prk_rst_hard_stop_um:
        hard_stops.append("PRK_RST_LT_310")
    if calc.final_kmean_d is not None and not (POLICY.final_kmean_min_d <= calc.final_kmean_d <= POLICY.final_kmean_max_d):
        hard_stops.append("FINAL_KMEAN_OUTSIDE_36_48")
    if erss_total is not None and erss_total >= 4: hard_stops.append("ERSS_GE_4")

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
