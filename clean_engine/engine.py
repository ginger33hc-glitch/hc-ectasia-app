"""Explicit deterministic orchestration for the parallel clean engine.

Pipeline: validate -> calculate -> score -> hard stops -> final decision.
This module remains isolated from production until full equivalence is proven.
"""
from .decision import DecisionInput, decide
from .models import AssessmentResult, CalculatedValues, EyeInput, ScoreValues
from .policy import POLICY, age_points, final_bad_d_classification, lasik_pachymetry_points, randleman_topography_points
from .surgery import final_kmean_d, lasik_pta_percent, lasik_rsb_um, prk_pta_percent, prk_rst_um


def assess(inp: EyeInput) -> AssessmentResult:
    procedure = (inp.procedure or "").upper()
    missing = []
    hard_stops = []
    warnings = []

    for name, value in (("age_years", inp.age_years), ("pachy_thinnest_um", inp.pachy_thinnest_um), ("bad_d", inp.bad_d)):
        if value is None:
            missing.append(name)
    if randleman_topography_points(inp.morphology) is None:
        missing.append("morphology")
    if procedure not in {"LASIK", "PRK"}:
        missing.append("procedure")

    calc = CalculatedValues()
    if procedure == "LASIK" and inp.pachy_thinnest_um is not None and inp.flap_um is not None and inp.ablation_um is not None:
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
        calc = CalculatedValues(
            lasik_rsb_um=calc.lasik_rsb_um,
            lasik_pta_percent=calc.lasik_pta_percent,
            prk_rst_um=calc.prk_rst_um,
            prk_pta_percent=calc.prk_pta_percent,
            final_kmean_d=final_kmean_d(inp.preop_kmean_d, inp.intended_mrse_d),
        )

    age = age_points(inp.age_years)
    pachy = lasik_pachymetry_points(inp.pachy_thinnest_um)
    topo = randleman_topography_points(inp.morphology)
    erss_total = None if None in (age, pachy, topo) else int(age + pachy + topo)
    scores = ScoreValues(age, pachy, topo, erss_total)
    bad_status = final_bad_d_classification(inp.bad_d)

    if inp.pachy_thinnest_um is not None and inp.pachy_thinnest_um <= POLICY.pachymetry_hard_stop_um:
        hard_stops.append("PACHYMETRY_LE_480")
    if inp.morphology == "ABNORMAL_ECTATIC":
        hard_stops.append("ABNORMAL_ECTATIC_TOPOGRAPHY")
    if bad_status == "ABNORMAL":
        hard_stops.append("FINAL_BAD_D_ABNORMAL")
    if procedure == "LASIK" and calc.lasik_rsb_um is not None and calc.lasik_rsb_um < POLICY.lasik_rsb_hard_stop_um:
        hard_stops.append("LASIK_RSB_LT_300")
    if procedure == "PRK" and calc.prk_rst_um is not None and calc.prk_rst_um < POLICY.prk_rst_hard_stop_um:
        hard_stops.append("PRK_RST_LT_310")
    if calc.final_kmean_d is not None and not (POLICY.final_kmean_min_d <= calc.final_kmean_d <= POLICY.final_kmean_max_d):
        hard_stops.append("FINAL_KMEAN_OUTSIDE_36_48")
    if erss_total is not None and erss_total >= 4:
        hard_stops.append("ERSS_GE_4")

    upstream = "DO NOT PROCEED" if hard_stops else ("DATA INSUFFICIENT" if missing else "PASS")
    decision = decide(DecisionInput(
        upstream_status=upstream,
        bad_d_status=bad_status,
        erss_total=erss_total,
        has_hard_stop=bool(hard_stops),
        decision_critical_incomplete=bool(missing),
    ))
    return AssessmentResult(decision.status, bad_status, calc, scores, tuple(hard_stops), tuple(missing), tuple(warnings))
