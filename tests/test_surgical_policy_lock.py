"""Behavior locks for decision-critical surgical-planning policy.

This phase deliberately locks public policy functions/constants without changing
production behavior. End-to-end surgical fixtures are added only after their
current payload contract is characterized.
"""
import canonical_engine
import lasik_planning

core = canonical_engine.core


def test_lasik_plan_sequence_is_locked():
    assert lasik_planning.LASIK_PLANS == (
        {"name": "Plan A", "flap_um": 100.0, "optical_zone_mm": 6.5, "transition_zone_mm": 9.0},
        {"name": "Plan B", "flap_um": 100.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
        {"name": "Plan C", "flap_um": 90.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
    )


def test_lasik_pta_cutoff_is_inclusive_40_percent():
    assert lasik_planning.LASIK_PTA_CUTOFF_PERCENT == 40.0
    assert lasik_planning._pta_cutoff({"values": {"LASIK_PTA_percent": 39.999}}) is False
    assert lasik_planning._pta_cutoff({"values": {"LASIK_PTA_percent": 40.0}}) is True
    assert lasik_planning._pta_cutoff({"values": {"LASIK_PTA_percent": 40.001}}) is True


def test_independent_hard_stop_prevents_fallback():
    for stop in (
        "CER-AI operational hard stop: thinnest preoperative cornea <480 µm.",
        "Definite KC/FFKC/PMD",
        "intended sphere <−10.00 D",
        "intended sphere >+6.00 D",
        "postoperative Kmean <36.00 D",
        "postoperative Kmean >48.00 D",
    ):
        assert lasik_planning._independent_hard_stop({"hard_stops": [stop]}) is True


def test_prk_epithelium_and_final_k_safety_constants_are_locked():
    assert core.PRK_EPITHELIUM_UM == 50
    assert core.CORNEAL_EFFECT_PER_INTENDED_MRSE_D == 0.8
    assert core.FINAL_KMEAN_MIN_D == 36.0
    assert core.FINAL_KMEAN_MAX_D == 48.0


def test_hc_pachymetry_480_scores_and_479_fails():
    assert core.lasik_pachy_points(479) is None
    assert core.lasik_pachy_points(480) == 2


def test_final_bad_d_abnormal_boundary_remains_inclusive():
    assert core.bad_classification(2.5999, final=True) == "SUSPICIOUS"
    assert core.bad_classification(2.6, final=True) == "ABNORMAL"


def test_hard_stop_status_outranks_every_favorable_status():
    assert core.combine_status("PASS", "STOP-DEFER") == "STOP-DEFER"
    assert core.combine_status("PASS", "STOP-DEFER") == "STOP-DEFER"
