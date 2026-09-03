"""Safety locks for Phase 3 non-authoritative shadow evaluation."""
from copy import deepcopy

import canonical_engine
from clinical_core.pipeline import ClinicalCoreInput, evaluate_normalized_case
from phase3_shadow_service import evaluate_shadow


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
        ps3_eye=None,
    )


def _production_from_linear(linear):
    safety = linear["procedural_safety"]
    return {
        "status": linear["status"],
        "score": {"total": linear["erss"]["total"]},
        "bad_summary": {"category": linear["bad_d"]["classification"]},
        "nice": {"total": linear["nice"]["total"]},
        "ps3": {"disposition": {}},
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
