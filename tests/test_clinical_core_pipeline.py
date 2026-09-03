"""Behavior locks for the Phase 2 linear clinical-core pipeline."""

import canonical_engine
from clinical_core import (
    ClinicalCoreInput,
    PIPELINE_ORDER,
    PS3EyeInput,
    evaluate_normalized_case,
)

core = canonical_engine.core


def test_pipeline_order_is_explicit_and_stable():
    assert PIPELINE_ORDER == (
        "normalized_input",
        "erss",
        "bad_d",
        "nice",
        "ps3",
        "procedural_safety",
        "disposition_aggregation",
    )


def test_reassuring_normalized_lasik_case_remains_pass():
    result = evaluate_normalized_case(ClinicalCoreInput(
        procedure="LASIK",
        age_years=35,
        thinnest_um=560,
        i_s_d=0.0,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        flap_um=100,
        ablation_um=60,
        preop_kmean_d=42.5,
        intended_mrse_d=-3.0,
        final_bad_d=1.0,
        nice_k2_d=43.0,
        nice_central_pachy_um=565,
        nice_b_ele_th_um=8,
        ps3_eye=PS3EyeInput(anterior_km_d=43.0, thinnest_um=560.0),
    ))
    assert result["pipeline_order"] == PIPELINE_ORDER
    assert result["erss"]["total"] == 0
    assert result["erss_status"] == "PASS"
    assert result["bad_d"]["status"] == "PASS"
    assert result["procedural_safety"]["status"] == "PASS"
    assert result["status"] == "PASS"


def test_independent_bad_d_abnormal_outranks_reassuring_erss():
    result = evaluate_normalized_case(ClinicalCoreInput(
        procedure="LASIK",
        age_years=35,
        thinnest_um=560,
        i_s_d=0.0,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        flap_um=100,
        ablation_um=60,
        preop_kmean_d=42.5,
        intended_mrse_d=-3.0,
        final_bad_d=2.6,
        nice_k2_d=43.0,
        nice_central_pachy_um=565,
        nice_b_ele_th_um=8,
        ps3_eye=PS3EyeInput(anterior_km_d=43.0, thinnest_um=560.0),
    ))
    assert result["erss_status"] == "PASS"
    assert result["bad_d"] == {"classification": "ABNORMAL", "status": "STOP-DEFER"}
    assert result["status"] == "STOP-DEFER"


def test_tissue_hard_stop_outranks_other_favorable_pathways():
    result = evaluate_normalized_case(ClinicalCoreInput(
        procedure="LASIK",
        age_years=35,
        thinnest_um=479,
        i_s_d=0.0,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        flap_um=100,
        ablation_um=60,
        preop_kmean_d=42.5,
        intended_mrse_d=-3.0,
        final_bad_d=1.0,
        nice_k2_d=43.0,
        nice_central_pachy_um=565,
        nice_b_ele_th_um=8,
        ps3_eye=PS3EyeInput(anterior_km_d=43.0, thinnest_um=479.0),
    ))
    assert result["procedural_safety"]["hard_stops"]["preop_thickness"] is True
    assert result["procedural_safety"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_erss_rsb_and_mrse_points_match_frozen_production_functions():
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
