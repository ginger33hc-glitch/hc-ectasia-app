"""Safety locks for Phase 3 non-authoritative shadow evaluation."""
from copy import deepcopy

import canonical_engine
from clinical_core.pipeline import ClinicalCoreInput, evaluate_normalized_case
from clinical_core.ps3 import PS3EyeInput, PS3InterEyeInput
from phase3_shadow_service import evaluate_shadow


def _ps3_eye():
    return PS3EyeInput(
        anterior_km_d=44.0,
        thinnest_um=540.0,
        topographic_astig_d=1.0,
        topographic_steep_axis_deg=90.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=90.0,
        ppi_avg=1.0,
        f_ele_th_um=10.0,
        b_ele_th_um=10.0,
        srax="NO",
        srax_deg=0.0,
    )


def _ps3_inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=44.0,
        os_anterior_km_d=44.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=540.0,
        os_thinnest_um=545.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )


def _input():
    return ClinicalCoreInput(
        procedure="LASIK",
        age_years=30,
        thinnest_um=540,
        i_s_d=0.0,
        derived_srax_deg=None,
        manifest_mrse_d=-2.0,
        intended_sphere_d=-2.0,
        flap_um=100,
        ablation_um=40,
        preop_kmean_d=44.0,
        intended_mrse_d=-2.0,
        final_bad_d=1.0,
        nice_k2_d=44.0,
        nice_central_pachy_um=540,
        nice_b_ele_th_um=10.0,
        ps3_eye=_ps3_eye(),
        ps3_inter_eye=_ps3_inter_eye(),
    )


def _production_from_linear(linear):
    safety = linear["procedural_safety"]
    ps3_selected = {
        "PASS": "ALLOWED",
        "STOP-DEFER": "DEFER",
        "ASSESSMENT INCOMPLETE": "INCOMPLETE",
    }[linear["ps3_status"]]
    return {
        "status": linear["status"],
        "score": {"total": linear["erss"]["total"]},
        "bad_summary": {"category": linear["bad_d"]["classification"]},
        "nice": {"total": linear["nice"]["total"]},
        "ps3": {"disposition": {"lasik": ps3_selected}},
        "values": {
            "LASIK_RSB_um": safety["LASIK_RSB_um"],
            "LASIK_PTA_percent": safety["LASIK_PTA_percent"],
            "estimated_final_Kmean_D": safety["estimated_final_Kmean_D"],
        },
    }


def test_shadow_mode_keeps_legacy_authoritative_on_match():
    inp = _input()
    linear = evaluate_normalized_case(inp)
    production = _production_from_linear(linear)
    before = deepcopy(production)

    shadow = evaluate_shadow(production, inp, procedure="LASIK")

    assert shadow["mode"] == "SHADOW_ONLY"
    assert shadow["authoritative_engine"] == "LEGACY_COMPOSED_RUNTIME"
    assert shadow["authoritative_result"] is production
    assert shadow["cutover_allowed"] is True
    assert production == before


def test_shadow_mode_keeps_legacy_authoritative_on_mismatch():
    inp = _input()
    linear = evaluate_normalized_case(inp)
    production = _production_from_linear(linear)
    production["bad_summary"]["category"] = "ABNORMAL"
    before = deepcopy(production)

    shadow = evaluate_shadow(production, inp, procedure="LASIK")

    assert shadow["authoritative_result"] is production
    assert shadow["cutover_allowed"] is False
    assert "bad_d_classification" in shadow["parity"]["mismatches"]
    assert production == before


def test_runtime_seam_exposes_shadow_without_replacing_clinical_functions():
    core = canonical_engine.core
    before = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert callable(core._cerai_shadow_compare_eye)
    after = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert after == before
