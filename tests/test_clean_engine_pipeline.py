"""Pipeline-level safety tests for the isolated clean engine."""
from clean_engine.engine import assess
from clean_engine.models import EyeInput


def base(**changes):
    values = dict(
        age_years=30,
        pachy_thinnest_um=520,
        bad_d=1.0,
        morphology="NORMAL_SYMMETRIC",
        procedure="LASIK",
        ablation_um=60,
        flap_um=100,
        preop_kmean_d=44,
        intended_mrse_d=-3,
        intended_sphere_d=-3,
    )
    values.update(changes)
    return EyeInput(**values)


def test_complete_favorable_case_is_pass_with_caution():
    out = assess(base())
    assert out.status == "PASS WITH CAUTION"
    assert not out.hard_stops
    assert not out.missing


def test_pipeline_exposes_and_sums_all_five_lasik_erss_components():
    out = assess(base(
        age_years=19,
        pachy_thinnest_um=505,
        morphology="ASYMMETRIC_BOWTIE",
        flap_um=100,
        ablation_um=145,
        intended_mrse_d=-9,
        intended_sphere_d=-9,
    ))
    assert out.scores.age_points == 2
    assert out.scores.pachymetry_points == 1
    assert out.scores.topography_points == 1
    assert out.scores.rsb_points == 2
    assert out.scores.mrse_points == 1
    assert out.scores.erss_total == 7


def test_prk_does_not_receive_lasik_erss_components_or_total():
    out = assess(base(procedure="PRK", flap_um=None))
    assert out.scores.rsb_points is None
    assert out.scores.mrse_points is None
    assert out.scores.erss_total is None


def test_pachymetry_480_is_independent_hard_stop():
    out = assess(base(pachy_thinnest_um=480))
    assert out.status == "DO NOT PROCEED"
    assert "PACHYMETRY_LE_480" in out.hard_stops


def test_lasik_rsb_just_below_300_is_hard_stop_and_300_is_not():
    assert "LASIK_RSB_LT_300" in assess(base(pachy_thinnest_um=500, flap_um=100, ablation_um=100.001)).hard_stops
    assert "LASIK_RSB_LT_300" not in assess(base(pachy_thinnest_um=500, flap_um=100, ablation_um=100)).hard_stops


def test_prk_rst_just_below_310_is_hard_stop_and_310_is_not():
    assert "PRK_RST_LT_310" in assess(base(procedure="PRK", pachy_thinnest_um=500, flap_um=None, ablation_um=140.001)).hard_stops
    assert "PRK_RST_LT_310" not in assess(base(procedure="PRK", pachy_thinnest_um=500, flap_um=None, ablation_um=140)).hard_stops


def test_bad_d_3_is_hard_stop():
    out = assess(base(bad_d=3.0))
    assert out.status == "DO NOT PROCEED"
    assert "FINAL_BAD_D_ABNORMAL" in out.hard_stops


def test_erss_3_defers_but_erss_4_stops():
    score3 = assess(base(age_years=18, pachy_thinnest_um=520))
    assert score3.scores.erss_total == 3
    assert score3.status == "CAUTION — DEFER"
    score4 = assess(base(age_years=18, pachy_thinnest_um=500))
    assert score4.scores.erss_total == 4
    assert score4.status == "DO NOT PROCEED"


def test_missing_principal_input_never_passes():
    out = assess(base(bad_d=None))
    assert out.status == "DATA INSUFFICIENT"
    assert "bad_d" in out.missing


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
