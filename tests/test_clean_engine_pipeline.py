"""Pipeline-level safety tests for the isolated clean engine."""
from clean_engine.engine import assess
from clean_engine.models import EyeInput


def base(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK", ablation_um=60,
        flap_um=100, preop_kmean_d=44, intended_mrse_d=-3,
        intended_sphere_d=-3, intended_cylinder_magnitude_d=1,
        laser_platform="Alcon EX500",
    )
    values.update(changes)
    return EyeInput(**values)


def test_complete_favorable_case_is_pass_with_caution():
    out = assess(base())
    assert out.status == "PASS WITH CAUTION"
    assert not out.hard_stops and not out.missing


def test_fallback_plan_a_success_stops_after_a():
    out = assess(base(use_lasik_fallback_planning=True, ablation_um=60))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.lasik_planning_sequence[0].ablation_source == "ACTUAL"
    assert out.calculations.lasik_rsb_um == 360


def test_fallback_plan_a_rsb_failure_is_rescued_by_plan_b_recalculation():
    out = assess(base(use_lasik_fallback_planning=True, pachy_thinnest_um=500, ablation_um=101, intended_sphere_d=-3, intended_cylinder_magnitude_d=1))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A", "Plan B"]
    assert out.lasik_planning_sequence[0].rsb_um == 299
    assert out.lasik_planning_sequence[1].ablation_um == 48
    assert out.lasik_planning_sequence[1].rsb_um == 352
    assert out.calculations.lasik_rsb_um == 352


def test_fallback_independent_pachymetry_stop_never_advances_to_plan_b():
    out = assess(base(use_lasik_fallback_planning=True, pachy_thinnest_um=480))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.status == "DO NOT PROCEED" and "PACHYMETRY_LE_480" in out.hard_stops


def test_fallback_independent_ectatic_topography_never_advances_to_plan_b():
    out = assess(base(use_lasik_fallback_planning=True, morphology="ABNORMAL_ECTATIC", ablation_um=121))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.status == "DO NOT PROCEED"
    assert "ABNORMAL_ECTATIC_TOPOGRAPHY" in out.hard_stops


def test_fallback_independent_myopic_magnitude_stop_never_advances_to_plan_b():
    out = assess(base(use_lasik_fallback_planning=True, intended_sphere_d=-10.001, ablation_um=121))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.status == "DO NOT PROCEED"
    assert "INTENDED_SPHERE_LT_MINUS_10" in out.hard_stops


def test_fallback_independent_hyperopic_magnitude_stop_never_advances_to_plan_b():
    out = assess(base(use_lasik_fallback_planning=True, intended_sphere_d=6.001, intended_mrse_d=5, ablation_um=121))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.status == "DO NOT PROCEED"
    assert "INTENDED_SPHERE_GT_PLUS_6" in out.hard_stops


def test_fallback_independent_final_k_stop_never_advances_to_plan_b():
    # Plan A also fails tissue geometry, proving fallback would otherwise advance.
    out = assess(base(use_lasik_fallback_planning=True, preop_kmean_d=44, intended_mrse_d=5.001, intended_sphere_d=5, ablation_um=121))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A"]
    assert out.calculations.final_kmean_d > 48
    assert out.status == "DO NOT PROCEED"
    assert "FINAL_KMEAN_OUTSIDE_36_48" in out.hard_stops


def test_fallback_plan_c_pta_at_40_is_final_hard_stop():
    out = assess(base(use_lasik_fallback_planning=True, pachy_thinnest_um=500, ablation_um=120, intended_sphere_d=-5.5, intended_cylinder_magnitude_d=5.5))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A", "Plan B", "Plan C"]
    assert out.lasik_planning_sequence[-1].pta_percent == 44.4
    assert "LASIK_PTA_GE_40_AFTER_FALLBACK" in out.hard_stops and out.status == "DO NOT PROCEED"


def test_fallback_hyperopic_plan_b_cannot_invent_ablation():
    out = assess(base(use_lasik_fallback_planning=True, pachy_thinnest_um=500, ablation_um=101, intended_sphere_d=2, intended_mrse_d=1.5, intended_cylinder_magnitude_d=1))
    assert [x.plan_name for x in out.lasik_planning_sequence] == ["Plan A", "Plan B"]
    assert out.lasik_planning_sequence[1].ablation_um is None
    assert out.lasik_planning_sequence[1].ablation_source == "ACTUAL_REQUIRED_HYPEROPIC_OR_MIXED"


def test_pipeline_exposes_and_sums_all_five_lasik_erss_components():
    out = assess(base(age_years=19, pachy_thinnest_um=505, morphology="ASYMMETRIC_BOWTIE", flap_um=100, ablation_um=145, intended_mrse_d=-9, intended_sphere_d=-9))
    assert (out.scores.age_points, out.scores.pachymetry_points, out.scores.topography_points, out.scores.rsb_points, out.scores.mrse_points, out.scores.erss_total) == (2, 1, 1, 2, 1, 7)


def test_prk_does_not_receive_lasik_erss_components_or_total():
    out = assess(base(procedure="PRK", flap_um=None))
    assert out.scores.rsb_points is None and out.scores.mrse_points is None and out.scores.erss_total is None


def test_prk_score_two_has_no_score_escalation():
    out = assess(base(procedure="PRK", flap_um=None, pachy_thinnest_um=520, morphology="ASYMMETRIC_BOWTIE", age_years=30, ablation_um=60))
    assert out.prk_scores.total == 2
    assert out.prk_scores.category == "NO_SCORE_ESCALATION"
    assert out.status == "PASS"


def test_prk_score_three_defers():
    out = assess(base(procedure="PRK", flap_um=None, pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC", age_years=18, ablation_um=60))
    assert out.prk_scores.total == 3
    assert out.prk_scores.category == "CAUTION"
    assert out.status == "CAUTION — STOP/DEFER"


def test_prk_score_four_or_more_is_score_driven_stop_not_independent_hard_stop():
    out = assess(base(procedure="PRK", flap_um=None, pachy_thinnest_um=520, morphology="INFERIOR_STEEPENING_SRA", age_years=30, ablation_um=60))
    assert out.prk_scores.total == 5
    assert out.prk_scores.category == "HIGH_CONCERN"
    assert "PRK_SCORE_GE_4" not in out.hard_stops
    assert out.status == "DO NOT PROCEED"


def test_prk_pta_exact_35_28_is_not_evidence_gap_but_above_is_review():
    exact_ablation = 0.3528 * 500 - 50
    exact = assess(base(procedure="PRK", flap_um=None, pachy_thinnest_um=500, ablation_um=exact_ablation, age_years=30))
    assert exact.calculations.prk_pta_percent == 35.28
    assert exact.prk_scores.pta_evidence_gap is False
    above = assess(base(procedure="PRK", flap_um=None, pachy_thinnest_um=500, ablation_um=exact_ablation + 0.001, age_years=30))
    assert above.prk_scores.pta_evidence_gap is True
    assert above.status == "REVIEW — NOT CLEARED"
    assert "PRK_PTA_EVIDENCE_GAP" not in above.hard_stops


def test_pachymetry_480_is_independent_hard_stop():
    out = assess(base(pachy_thinnest_um=480))
    assert out.status == "DO NOT PROCEED" and "PACHYMETRY_LE_480" in out.hard_stops


def test_lasik_rsb_just_below_300_is_hard_stop_and_300_is_not():
    assert "LASIK_RSB_LT_300" in assess(base(pachy_thinnest_um=500, flap_um=100, ablation_um=100.001)).hard_stops
    assert "LASIK_RSB_LT_300" not in assess(base(pachy_thinnest_um=500, flap_um=100, ablation_um=100)).hard_stops


def test_prk_rst_just_below_310_is_hard_stop_and_310_is_not():
    assert "PRK_RST_LT_310" in assess(base(procedure="PRK", pachy_thinnest_um=500, flap_um=None, ablation_um=140.001)).hard_stops
    assert "PRK_RST_LT_310" not in assess(base(procedure="PRK", pachy_thinnest_um=500, flap_um=None, ablation_um=140)).hard_stops


def test_bad_d_3_is_hard_stop():
    out = assess(base(bad_d=3.0)); assert out.status == "DO NOT PROCEED" and "FINAL_BAD_D_ABNORMAL" in out.hard_stops


def test_lasik_score_two_has_no_score_escalation():
    out = assess(base(age_years=19, pachy_thinnest_um=520))
    assert out.scores.erss_total == 2
    assert out.status == "PASS WITH CAUTION"


def test_lasik_score_three_defers_and_four_stops():
    score3 = assess(base(age_years=18, pachy_thinnest_um=520)); assert score3.scores.erss_total == 3 and score3.status == "CAUTION — DEFER"
    score4 = assess(base(age_years=18, pachy_thinnest_um=500)); assert score4.scores.erss_total == 4 and score4.status == "DO NOT PROCEED"


def test_missing_principal_input_never_passes():
    out = assess(base(bad_d=None)); assert out.status == "DATA INSUFFICIENT" and "bad_d" in out.missing


def test_final_kmean_boundaries_are_inclusive():
    assert "FINAL_KMEAN_OUTSIDE_36_48" not in assess(base(preop_kmean_d=40, intended_mrse_d=-5)).hard_stops
    assert "FINAL_KMEAN_OUTSIDE_36_48" not in assess(base(preop_kmean_d=44, intended_mrse_d=5)).hard_stops
    assert "FINAL_KMEAN_OUTSIDE_36_48" in assess(base(preop_kmean_d=44, intended_mrse_d=5.001)).hard_stops


def test_myopic_refractive_magnitude_boundary_is_strict():
    assert "INTENDED_SPHERE_LT_MINUS_10" not in assess(base(intended_sphere_d=-10.0)).hard_stops
    assert "INTENDED_SPHERE_LT_MINUS_10" in assess(base(intended_sphere_d=-10.001)).hard_stops


def test_hyperopic_refractive_magnitude_boundary_is_strict():
    assert "INTENDED_SPHERE_GT_PLUS_6" not in assess(base(intended_sphere_d=6.0)).hard_stops
    assert "INTENDED_SPHERE_GT_PLUS_6" in assess(base(intended_sphere_d=6.001)).hard_stops
