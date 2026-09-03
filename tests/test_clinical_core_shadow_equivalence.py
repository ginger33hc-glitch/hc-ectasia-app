"""Shadow-mode parity harness for the Phase 2 linear clinical pipeline."""

import canonical_engine
import clinical_disposition
import nice_scoring
import ps3_policy
from clinical_core.erss import erss_disposition
from clinical_core.pipeline import ClinicalCoreInput, evaluate_normalized_case
from clinical_core.ps3 import PS3EyeInput

core = canonical_engine.core


def _production_shadow_reference(inp: ClinicalCoreInput):
    procedure = inp.procedure.upper()
    rsb = None
    if procedure == "LASIK" and None not in (inp.thinnest_um, inp.flap_um, inp.ablation_um):
        rsb = inp.thinnest_um - inp.flap_um - inp.ablation_um

    erss_total = None
    erss_status = "PASS"
    if procedure == "LASIK":
        srax_deg = inp.derived_srax_deg
        topo = core.scoring_morphology({
            "I_S": inp.i_s_d,
            "I_S_status": "CONFIDENT" if inp.i_s_d is not None else "NOT_SHOWN",
            "table_verified_numeric_fields": ["I_S"] if inp.i_s_d is not None else [],
            "data_conflicts": [],
            "field_provenance": {"I_S": [{"source": "SHADOW"}]} if inp.i_s_d is not None else {},
            "_erss_i_s_gate_required": True,
            "srax_deg": srax_deg,
            "srax": None if srax_deg is None else ("YES" if srax_deg > 20.0 else "NO"),
        })
        topo_points = core.lasik_topography_points(topo["category"]) if topo["category"] != "UNCERTAIN" else None
        rows = (
            core.age_points(inp.age_years),
            core.lasik_pachy_points(inp.thinnest_um),
            topo_points,
            core.lasik_rsb_points(rsb) if rsb is not None else None,
            core.lasik_mrse_points(inp.manifest_mrse_d),
        )
        if None not in rows:
            erss_total = sum(rows)
        erss_status = erss_disposition(erss_total)

    bad_class = core.bad_classification(inp.final_bad_d, final=True) if inp.final_bad_d is not None else "UNAVAILABLE"
    bad_status = {"NORMAL": "PASS", "SUSPICIOUS": "CAUTION", "ABNORMAL": "STOP-DEFER"}.get(bad_class, "DATA INSUFFICIENT")
    nice = nice_scoring.score_nice(inp.nice_k2_d, inp.nice_central_pachy_um, inp.nice_b_ele_th_um, inp.i_s_d)
    nice_status = "DATA INSUFFICIENT" if nice["total"] is None else "STOP-DEFER" if nice["total"] >= 9 else "CAUTION" if nice["total"] >= 5 else "PASS"
    ps3_result = ps3_policy.evaluate_ps3(inp.ps3_eye, inp.ps3_inter_eye) if inp.ps3_eye is not None else None
    if ps3_result is None:
        ps3_status = "DATA INSUFFICIENT"
    else:
        proc_value = {"LASIK": ps3_result.disposition.lasik, "PRK": ps3_result.disposition.prk, "SMILE": ps3_result.disposition.smile}.get(procedure)
        ps3_status = "STOP-DEFER" if proc_value == ps3_policy.DEFER else "PASS" if proc_value == ps3_policy.ALLOWED else "DATA INSUFFICIENT"

    safety_status = "PASS"
    if inp.thinnest_um is not None and inp.thinnest_um < 480:
        safety_status = "STOP-DEFER"
    if inp.intended_sphere_d is not None and (inp.intended_sphere_d < -10 or inp.intended_sphere_d > 6):
        safety_status = "STOP-DEFER"
    if procedure == "LASIK" and rsb is not None and rsb < 300:
        safety_status = "STOP-DEFER"
    if procedure == "LASIK" and None not in (inp.thinnest_um, inp.flap_um, inp.ablation_um):
        if 100 * (inp.flap_um + inp.ablation_um) / inp.thinnest_um >= 40:
            safety_status = "STOP-DEFER"
    if procedure == "PRK" and None not in (inp.thinnest_um, inp.ablation_um):
        if inp.thinnest_um - core.PRK_EPITHELIUM_UM - inp.ablation_um < 310:
            safety_status = "STOP-DEFER"
    if None not in (inp.preop_kmean_d, inp.intended_mrse_d):
        final_k = inp.preop_kmean_d + core.CORNEAL_EFFECT_PER_INTENDED_MRSE_D * inp.intended_mrse_d
        if final_k < core.FINAL_KMEAN_MIN_D or final_k > core.FINAL_KMEAN_MAX_D:
            safety_status = "STOP-DEFER"

    overall = "PASS"
    for status in (erss_status, bad_status, nice_status, ps3_status, safety_status):
        overall = clinical_disposition.combine_status(overall, status)
    return {"erss_total": erss_total, "erss_status": erss_status, "bad_class": bad_class, "bad_status": bad_status, "nice_total": nice["total"], "nice_status": nice_status, "ps3_status": ps3_status, "safety_status": safety_status, "status": overall}


def _ps3_normal():
    return PS3EyeInput(
        anterior_km_d=47.0,
        thinnest_um=520.0,
        topographic_astig_d=1.0,
        topographic_steep_axis_deg=90.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=90.0,
        ppi_avg=1.0,
        srax="NO",
        srax_deg=0.0,
        bfte_front_um=10.0,
        bfte_back_um=10.0,
    )


def _base(**overrides):
    values = dict(
        procedure="LASIK", age_years=35, thinnest_um=540.0, i_s_d=0.5,
        derived_srax_deg=0.0, manifest_mrse_d=-3.0, intended_sphere_d=-3.0,
        flap_um=100.0, ablation_um=60.0, preop_kmean_d=43.0, intended_mrse_d=-3.0,
        final_bad_d=1.0, nice_k2_d=44.0, nice_central_pachy_um=530.0,
        nice_b_ele_th_um=10.0, ps3_eye=_ps3_normal(),
    )
    values.update(overrides)
    return ClinicalCoreInput(**values)


def test_shadow_parity_reassuring_lasik():
    inp = _base(); new = evaluate_normalized_case(inp); old = _production_shadow_reference(inp)
    assert new["erss"]["total"] == old["erss_total"]
    assert new["erss_status"] == old["erss_status"]
    assert new["bad_d"]["classification"] == old["bad_class"]
    assert new["nice"]["total"] == old["nice_total"]
    assert new["ps3_status"] == old["ps3_status"]
    assert new["procedural_safety"]["status"] == old["safety_status"]
    assert new["status"] == old["status"]


def test_shadow_parity_bad_d_hard_stop():
    inp = _base(final_bad_d=2.6)
    assert evaluate_normalized_case(inp)["status"] == _production_shadow_reference(inp)["status"] == "STOP-DEFER"


def test_shadow_parity_nice_caution():
    inp = _base(nice_k2_d=46.0, nice_central_pachy_um=510.0, nice_b_ele_th_um=16.0, i_s_d=1.2)
    new = evaluate_normalized_case(inp); old = _production_shadow_reference(inp)
    assert new["nice_status"] == old["nice_status"]
    assert new["status"] == old["status"]


def test_shadow_parity_erss_high_risk():
    inp = _base(age_years=18, i_s_d=1.2, manifest_mrse_d=-10.0)
    new = evaluate_normalized_case(inp); old = _production_shadow_reference(inp)
    assert new["erss"]["total"] == old["erss_total"]
    assert new["erss_status"] == old["erss_status"]
    assert new["status"] == old["status"]


def test_shadow_parity_lasik_tissue_stop():
    inp = _base(thinnest_um=500.0, flap_um=100.0, ablation_um=100.0)
    new = evaluate_normalized_case(inp); old = _production_shadow_reference(inp)
    assert new["procedural_safety"]["LASIK_PTA_percent"] == 40.0
    assert new["procedural_safety"]["status"] == old["safety_status"] == "STOP-DEFER"
    assert new["status"] == old["status"]


def test_shadow_parity_prk_structural_stop():
    inp = _base(procedure="PRK", flap_um=None, thinnest_um=520.0, ablation_um=161.0, ps3_eye=_ps3_normal())
    new = evaluate_normalized_case(inp); old = _production_shadow_reference(inp)
    assert new["procedural_safety"]["PRK_RST_um"] == 309.0
    assert new["procedural_safety"]["status"] == old["safety_status"] == "STOP-DEFER"
    assert new["status"] == old["status"]
