"""Phase 3 locks for the production-to-linear normalized adapter."""
from copy import deepcopy

from clinical_core.pipeline import evaluate_normalized_case
from phase3_normalized_adapter import build_clinical_core_input


def _eye(name="OD"):
    return {
        "eye": name,
        "Kmean_D": 44.0,
        "K2_D": 44.5,
        "pachy_thinnest_um": 530.0,
        "BAD_D": 1.2,
        "I_S": 0.4,
        "KISA": 1.0,
        "Kmax_D": 47.0,
        "topographic_astig_D": 1.0,
        "topographic_steep_axis_deg": 90.0,
        "PPI_avg": 1.0,
        "posterior_Kmean_D": -6.0,
        "F_Ele_Th_um": 2.0,
        "B_Ele_Th_um": 4.0,
        "table_verified_numeric_fields": ["K2_D", "I_S"],
        "surgeon_verified_numeric_fields": [],
        "data_conflicts": [],
        "nice_raw_k2_readings": [44.5],
        "nice_candidates": [
            {
                "eye": name,
                "central_pachy_um": 535.0,
                "central_status": "CONFIDENT",
                "central_landmark": "PUPIL_CENTER_PLUS",
                "B_Ele_Th_um": 10.0,
                "b_ele_th_status": "CONFIDENT",
                "b_ele_th_landmark": "B_ELE_TH_LABELED_BOX",
                "b_ele_th_page": "BAD_DISPLAY",
                "evidence": "test",
            }
        ],
    }


def _plan():
    return {
        "procedure": "LASIK",
        "prior": "no",
        "flap_um": 100.0,
        "ablation_um": 80.0,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": -1.0,
        "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0,
        "manifest_cylinder_magnitude_D": 1.0,
        "manifest_axis_deg": 90.0,
    }


def test_adapter_maps_reconciled_production_values_to_linear_input():
    od = _eye("OD")
    os = _eye("OS")
    extracted = {"eyes": [od, os]}
    inp = build_clinical_core_input(od, _plan(), age_years=30, extracted=extracted)

    assert inp.procedure == "LASIK"
    assert inp.age_years == 30
    assert inp.thinnest_um == 530.0
    assert inp.i_s_d == 0.4
    assert inp.manifest_mrse_d == -2.5
    assert inp.intended_mrse_d == -2.5
    assert inp.intended_sphere_d == -2.0
    assert inp.flap_um == 100.0
    assert inp.ablation_um == 80.0
    assert inp.preop_kmean_d == 44.0
    assert inp.final_bad_d == 1.2
    assert inp.nice_k2_d == 44.5
    assert inp.nice_central_pachy_um == 535.0
    assert inp.nice_b_ele_th_um == 10.0
    assert inp.ps3_eye.anterior_km_d == 44.0
    assert inp.ps3_inter_eye.od_anterior_km_d == 44.0
    assert inp.ps3_inter_eye.os_anterior_km_d == 44.0


def test_surgeon_confirmed_i_s_overrides_extracted_i_s_for_core_input():
    plan = _plan()
    plan["surgeon_I_S_D"] = 1.2
    inp = build_clinical_core_input(_eye(), plan, age_years=30)
    assert inp.i_s_d == 1.2


def test_adapter_does_not_mutate_production_payloads():
    eye = _eye()
    plan = _plan()
    extracted = {"eyes": [eye, _eye("OS")]}
    before = deepcopy((eye, plan, extracted))

    build_clinical_core_input(eye, plan, age_years=30, extracted=extracted)

    assert (eye, plan, extracted) == before


def test_adapter_output_can_run_through_linear_pipeline_without_transport_state():
    eye = _eye()
    extracted = {"eyes": [eye, _eye("OS")]}
    inp = build_clinical_core_input(eye, _plan(), age_years=30, extracted=extracted)
    result = evaluate_normalized_case(inp)
    assert result["procedure"] == "LASIK"
    assert result["status"] in {"PASS", "CAUTION", "STOP-DEFER", "DATA INSUFFICIENT"}
