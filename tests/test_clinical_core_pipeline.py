"""Behavior locks for the linear clinical-core pipeline."""

import canonical_engine
from clinical_core import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    ClinicalCoreInput,
    PIPELINE_ORDER,
    PS3EyeInput,
    PS3InterEyeInput,
    STOP_DEFER,
    evaluate_normalized_case,
)

core = canonical_engine.core


def complete_ps3_eye(**overrides):
    values = dict(
        anterior_km_d=43.0,
        thinnest_um=560.0,
        topographic_astig_d=1.0,
        topographic_steep_axis_deg=175.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=5.0,
        ppi_avg=1.0,
        srax="NO",
        srax_deg=10.0,
        f_ele_th_um=8.0,
        b_ele_th_um=10.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def complete_inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=43.0,
        os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=560.0,
        os_thinnest_um=565.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )


def normal_lasik(**overrides):
    values = dict(
        procedure="LASIK",
        age_years=35,
        thinnest_um=560,
        i_s_d=0.0,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        intended_cylinder_d=0.0,
        intended_axis_deg=0.0,
        flap_um=100,
        ablation_um=60,
        preop_kmean_d=42.5,
        intended_mrse_d=-3.0,
        final_bad_d=1.0,
        nice_k2_d=43.0,
        nice_central_pachy_um=565,
        nice_b_ele_th_um=8,
        ps3_eye=complete_ps3_eye(),
        ps3_inter_eye=complete_inter_eye(),
    )
    values.update(overrides)
    return ClinicalCoreInput(**values)


def test_pipeline_order_is_explicit_and_stable():
    assert PIPELINE_ORDER == (
        "normalized_input",
        "erss",
        "bad_d",
        "nice",
        "ps3",
        "procedural_safety",
        "final_disposition",
    )


def test_reassuring_normalized_lasik_case_passes_only_when_all_decision_inputs_complete():
    result = evaluate_normalized_case(normal_lasik())
    assert result["pipeline_order"] == PIPELINE_ORDER
    assert result["erss"]["total"] == 0
    assert result["erss_status"] == "PASS"
    assert result["bad_d"]["status"] == "PASS"
    assert result["nice_status"] == "PASS"
    assert result["ps3_status"] == "PASS"
    assert result["procedural_safety"]["status"] == "PASS"
    assert result["status"] == "PASS"


def test_independent_bad_d_abnormal_outranks_reassuring_erss():
    result = evaluate_normalized_case(normal_lasik(final_bad_d=2.6))
    assert result["erss_status"] == "PASS"
    assert result["bad_d"]["classification"] == "ABNORMAL"
    assert result["bad_d"]["status"] == STOP_DEFER
    assert result["bad_d"]["result"].final_d == 2.6
    assert result["status"] == STOP_DEFER
    assert {driver.key for driver in result["final_disposition"].stop_drivers} == {"bad_d"}


def test_tissue_hard_stop_outranks_incomplete_randleman_row():
    result = evaluate_normalized_case(normal_lasik(
        thinnest_um=479,
        ps3_eye=complete_ps3_eye(thinnest_um=479),
    ))
    assert result["erss_status"] == ASSESSMENT_INCOMPLETE
    assert result["procedural_safety"]["hard_stops"]["preop_thickness"] is True
    assert result["procedural_safety"]["status"] == STOP_DEFER
    assert result["status"] == STOP_DEFER


def test_missing_decision_critical_data_is_assessment_incomplete_not_pass():
    result = evaluate_normalized_case(normal_lasik(nice_b_ele_th_um=None))
    assert result["nice_status"] == ASSESSMENT_INCOMPLETE
    assert result["status"] == ASSESSMENT_INCOMPLETE
    assert {driver.key for driver in result["final_disposition"].incomplete_drivers} == {"nice"}


def test_multiple_cautions_do_not_auto_escalate_to_stop():
    result = evaluate_normalized_case(normal_lasik(
        final_bad_d=2.0,
        nice_k2_d=46.0,
        nice_central_pachy_um=510,
        nice_b_ele_th_um=16.0,
    ))
    assert result["bad_d"]["status"] == CAUTION
    assert result["nice_status"] == CAUTION
    assert result["status"] == CAUTION
    assert {driver.key for driver in result["final_disposition"].caution_drivers} == {"bad_d", "nice"}


def test_multiple_stop_drivers_are_all_retained():
    result = evaluate_normalized_case(normal_lasik(
        final_bad_d=2.6,
        intended_sphere_d=-10.01,
    ))
    assert result["status"] == STOP_DEFER
    assert {driver.key for driver in result["final_disposition"].stop_drivers} == {"bad_d", "procedural_safety"}


def test_pta_is_reported_but_not_a_global_stop_driver():
    result = evaluate_normalized_case(normal_lasik(flap_um=120, ablation_um=120))
    assert result["procedural_safety"]["LASIK_PTA_percent"] > 40
    assert "lasik_pta" not in result["procedural_safety"]["hard_stops"]


def test_erss_rsb_and_mrse_points_match_current_production_functions():
    from clinical_core.erss import erss_mrse_points, erss_rsb_points
    rsb_values = (239.999, 240, 260, 280, 300)
    mrse_values = (-14.001, -14, -12, -10, -8)
    assert [erss_rsb_points(v) for v in rsb_values] == [core.lasik_rsb_points(v) for v in rsb_values]
    assert [erss_mrse_points(v) for v in mrse_values] == [core.lasik_mrse_points(v) for v in mrse_values]


def test_importing_pipeline_does_not_mutate_production_runtime():
    before = (core.assess_eye, core.hc_engine, core.merge_extractions)
    import clinical_core.pipeline  # noqa: F401
    after = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert after == before
