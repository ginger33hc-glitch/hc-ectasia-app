"""Migration scenarios for the canonical linear clinical pipeline.

These tests verify accepted Monday behavior. They do not require parity with
accepted production rules including the LASIK PTA plan hard stop.
"""

from clinical_core import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    ClinicalCoreInput,
    PS3EyeInput,
    PS3InterEyeInput,
    STOP_DEFER,
    evaluate_normalized_case,
)


def _ps3_normal(**overrides):
    values = dict(
        anterior_km_d=47.0,
        thinnest_um=520.0,
        ppi_avg=1.0,
        srax="NO",
        srax_deg=0.0,
        f_ele_th_um=10.0,
        b_ele_th_um=10.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def _inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=43.0,
        os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=520.0,
        os_thinnest_um=525.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )


def _base(**overrides):
    values = dict(
        procedure="LASIK",
        age_years=35,
        thinnest_um=540.0,
        i_s_d=0.5,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        intended_cylinder_d=0.0,
        intended_axis_deg=0.0,
        flap_um=100.0,
        ablation_um=60.0,
        preop_kmean_d=43.0,
        intended_mrse_d=-3.0,
        final_bad_d=1.0,
        nice_k2_d=44.0,
        nice_central_pachy_um=530.0,
        nice_b_ele_th_um=10.0,
        ps3_eye=_ps3_normal(),
        ps3_inter_eye=_inter_eye(),
    )
    values.update(overrides)
    return ClinicalCoreInput(**values)


def test_migration_reassuring_lasik_is_pass():
    result = evaluate_normalized_case(_base())
    assert result["erss"]["total"] == 0
    assert result["erss_status"] == "PASS"
    assert result["bad_d"]["classification"] == "NORMAL"
    assert result["nice"]["total"] == 4
    assert result["ps3_status"] == "PASS"
    assert result["procedural_safety"]["status"] == "PASS"
    assert result["status"] == "PASS"


def test_migration_bad_d_hard_stop_is_preserved():
    result = evaluate_normalized_case(_base(final_bad_d=2.6))
    assert result["bad_d"]["classification"] == "ABNORMAL"
    assert result["bad_d"]["status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_migration_nice_caution_remains_caution_not_auto_stop():
    result = evaluate_normalized_case(_base(
        nice_k2_d=46.0,
        nice_central_pachy_um=510.0,
        nice_b_ele_th_um=16.0,
        i_s_d=1.2,
    ))
    assert result["nice_status"] == CAUTION
    assert result["erss_status"] == CAUTION
    assert result["status"] == "PASS WITH CAUTION"


def test_migration_erss_high_risk_still_stops():
    result = evaluate_normalized_case(_base(age_years=18, i_s_d=1.2, manifest_mrse_d=-10.0))
    assert result["erss"]["total"] >= 4
    assert result["erss_status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_lasik_rsb_below_300_is_structural_stop():
    result = evaluate_normalized_case(_base(
        thinnest_um=500.0,
        flap_um=100.0,
        ablation_um=101.0,
        ps3_eye=_ps3_normal(thinnest_um=500.0),
    ))
    assert result["procedural_safety"]["LASIK_RSB_um"] == 299.0
    assert result["procedural_safety"]["hard_stops"]["lasik_rsb"] is True
    assert result["procedural_safety"]["status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_pta_cutoff_is_an_independent_lasik_stop():
    result = evaluate_normalized_case(_base(
        thinnest_um=560.0,
        flap_um=120.0,
        ablation_um=120.0,
        ps3_eye=_ps3_normal(thinnest_um=520.0),
    ))
    assert result["procedural_safety"]["LASIK_PTA_percent"] > 40.0
    assert result["procedural_safety"]["hard_stops"]["lasik_rsb"] is False
    assert result["procedural_safety"]["hard_stops"]["lasik_pta"] is True
    assert result["procedural_safety"]["status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_prk_rst_below_310_is_structural_stop():
    result = evaluate_normalized_case(_base(
        procedure="PRK",
        flap_um=None,
        thinnest_um=520.0,
        ablation_um=161.0,
    ))
    assert result["procedural_safety"]["PRK_RST_um"] == 309.0
    assert result["procedural_safety"]["hard_stops"]["prk_rst"] is True
    assert result["procedural_safety"]["status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_missing_ps3_input_is_assessment_incomplete_not_reassuring():
    result = evaluate_normalized_case(_base(ps3_inter_eye=None))
    assert result["ps3_status"] == ASSESSMENT_INCOMPLETE
    assert result["status"] == ASSESSMENT_INCOMPLETE
