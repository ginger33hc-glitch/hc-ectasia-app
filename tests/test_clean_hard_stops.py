"""Boundary and composition tests for the clean hard-stop policy layer."""
from clean_engine.hard_stops import HardStopInput, evaluate_hard_stops


def base(**changes):
    values = dict(
        procedure="LASIK", pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC",
        bad_d_status="NORMAL", intended_sphere_d=-3, lasik_rsb_um=360,
        prk_rst_um=None, final_kmean_d=42, lasik_erss_total=0,
    )
    values.update(changes)
    return HardStopInput(**values)


def test_favorable_input_has_no_hard_stops():
    assert evaluate_hard_stops(base()) == ()


def test_pachymetry_boundary_is_inclusive_at_480():
    assert "PACHYMETRY_LE_480" in evaluate_hard_stops(base(pachy_thinnest_um=480))
    assert "PACHYMETRY_LE_480" not in evaluate_hard_stops(base(pachy_thinnest_um=480.001))


def test_refractive_magnitude_boundaries_are_strict():
    assert "INTENDED_SPHERE_LT_MINUS_10" not in evaluate_hard_stops(base(intended_sphere_d=-10))
    assert "INTENDED_SPHERE_LT_MINUS_10" in evaluate_hard_stops(base(intended_sphere_d=-10.001))
    assert "INTENDED_SPHERE_GT_PLUS_6" not in evaluate_hard_stops(base(intended_sphere_d=6))
    assert "INTENDED_SPHERE_GT_PLUS_6" in evaluate_hard_stops(base(intended_sphere_d=6.001))


def test_lasik_rsb_boundary_is_strictly_below_300():
    assert "LASIK_RSB_LT_300" not in evaluate_hard_stops(base(lasik_rsb_um=300))
    assert "LASIK_RSB_LT_300" in evaluate_hard_stops(base(lasik_rsb_um=299.999))


def test_prk_rst_boundary_is_strictly_below_310():
    common = dict(procedure="PRK", lasik_rsb_um=None, lasik_erss_total=None)
    assert "PRK_RST_LT_310" not in evaluate_hard_stops(base(prk_rst_um=310, **common))
    assert "PRK_RST_LT_310" in evaluate_hard_stops(base(prk_rst_um=309.999, **common))


def test_final_k_boundaries_are_inclusive():
    assert "FINAL_KMEAN_OUTSIDE_36_48" not in evaluate_hard_stops(base(final_kmean_d=36))
    assert "FINAL_KMEAN_OUTSIDE_36_48" not in evaluate_hard_stops(base(final_kmean_d=48))
    assert "FINAL_KMEAN_OUTSIDE_36_48" in evaluate_hard_stops(base(final_kmean_d=35.999))
    assert "FINAL_KMEAN_OUTSIDE_36_48" in evaluate_hard_stops(base(final_kmean_d=48.001))


def test_bad_and_ectatic_are_independent_stops():
    stops = evaluate_hard_stops(base(morphology="ABNORMAL_ECTATIC", bad_d_status="ABNORMAL"))
    assert "ABNORMAL_ECTATIC_TOPOGRAPHY" in stops
    assert "FINAL_BAD_D_ABNORMAL" in stops


def test_lasik_score_stop_consumes_shared_score_policy():
    assert "ERSS_GE_4" not in evaluate_hard_stops(base(lasik_erss_total=3))
    assert "ERSS_GE_4" in evaluate_hard_stops(base(lasik_erss_total=4))


def test_prk_never_receives_lasik_erss_hard_stop_marker():
    stops = evaluate_hard_stops(base(procedure="PRK", lasik_rsb_um=None, prk_rst_um=350, lasik_erss_total=9))
    assert "ERSS_GE_4" not in stops


def test_marker_order_is_stable_for_reporting():
    stops = evaluate_hard_stops(base(
        pachy_thinnest_um=480, morphology="ABNORMAL_ECTATIC", bad_d_status="ABNORMAL",
        intended_sphere_d=-10.001, lasik_rsb_um=299, final_kmean_d=35.9, lasik_erss_total=4,
    ))
    assert stops == (
        "PACHYMETRY_LE_480", "ABNORMAL_ECTATIC_TOPOGRAPHY", "FINAL_BAD_D_ABNORMAL",
        "INTENDED_SPHERE_LT_MINUS_10", "LASIK_RSB_LT_300", "FINAL_KMEAN_OUTSIDE_36_48", "ERSS_GE_4",
    )
