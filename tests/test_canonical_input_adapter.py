"""Acceptance locks for the reconciled-data canonical input adapter."""
from copy import deepcopy

import pytest

from canonical_input_adapter import (
    build_clinical_core_input,
    resolve_case_plans,
    resolve_eye_plan,
)
from clinical_core.pipeline import evaluate_normalized_case


def _eye(name="OD"):
    return {
        "eye": name,
        "Kmean_D": 44.0,
        "K2_D": 44.5,
        "central_pachy_um": 535.0,
        "pachy_thinnest_um": 530.0,
        "BAD_D": 1.2,
        "I_S": 0.4,
        "KISA": 1.0,
        "Kmax_D": 47.0,
        "topographic_astig_D": 1.0,
        "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "PPI_avg": 1.0,
        "posterior_Kmean_D": -6.0,
        "F_Ele_Th_um": 2.0,
        "B_Ele_Th_um": 10.0,
        "table_verified_numeric_fields": ["K2_D", "I_S", "central_pachy_um", "B_Ele_Th_um"],
        "surgeon_verified_numeric_fields": [],
        "data_conflicts": [],
        "nice_raw_k2_readings": [47.5],
        "nice_candidates": [{
            "eye": name,
            "central_pachy_um": 499.0,
            "central_status": "CONFIDENT",
            "central_landmark": "PUPIL_CENTER_PLUS",
            "B_Ele_Th_um": 25.0,
            "b_ele_th_status": "CONFIDENT",
            "b_ele_th_landmark": "B_ELE_TH_LABELED_BOX",
            "b_ele_th_page": "BAD_DISPLAY",
            "evidence": "legacy candidate that must not be consumed",
        }],
    }


def _plan():
    return {
        "procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0, "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0, "intended_axis_deg": 90.0,
        "manifest_cylinder_magnitude_D": 1.0,
    }


def _card(eye="OD", sphere=-3.0, cylinder=-1.5, axis=80.0, *, axis_status="CONFIDENT"):
    return {
        "eye": eye, "source_document": "EXCIMER_LASER_FOLLOW_UP_CARD",
        "source_label": "DUZELTME_MIKTARI", "sphere_D": sphere,
        "cylinder_D": cylinder, "axis_deg": axis,
        "sphere_cylinder_status": "CONFIDENT", "axis_status": axis_status,
        "raw_text": None, "missing_or_unreadable": [],
    }


def test_adapter_maps_reconciled_canonical_values_to_linear_input():
    od = _eye("OD"); os = _eye("OS"); extracted = {"eyes": [od, os]}
    inp = build_clinical_core_input(od, _plan(), age_years=30, extracted=extracted)
    assert inp.procedure == "LASIK"
    assert inp.age_years == 30
    assert inp.thinnest_um == 530.0
    assert inp.i_s_d == 0.4
    assert inp.manifest_mrse_d == -2.5
    assert inp.intended_mrse_d == -2.5
    assert inp.intended_sphere_d == -2.0
    assert inp.intended_cylinder_d == -1.0
    assert inp.intended_axis_deg == 90.0
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


def test_legacy_nice_specific_candidates_cannot_override_canonical_fields():
    eye = _eye(); inp = build_clinical_core_input(eye, _plan(), age_years=30)
    assert inp.nice_k2_d == 44.5
    assert inp.nice_central_pachy_um == 535.0
    assert inp.nice_b_ele_th_um == 10.0


def test_plus_cylinder_is_normalized_once_before_core_input():
    plan = _plan(); plan.update({
        "manifest_entered_sphere_D": -4.0, "manifest_cylinder_signed_D": +2.0,
        "manifest_axis_deg": 10.0, "intended_entered_sphere_D": -4.0,
        "intended_cylinder_signed_D": +2.0, "intended_axis_deg": 10.0,
    })
    inp = build_clinical_core_input(_eye(), plan, age_years=30)
    assert inp.manifest_mrse_d == pytest.approx(-3.0)
    assert inp.intended_mrse_d == pytest.approx(-3.0)
    assert inp.intended_sphere_d == pytest.approx(-2.0)
    assert inp.intended_cylinder_d == pytest.approx(-2.0)
    assert inp.intended_axis_deg == pytest.approx(100.0)


def test_only_a_bad_axis_at_disparity_threshold_is_selected_for_verification():
    from canonical_input_adapter import astigmatic_disparity_verification_eyes, resolve_case_plans

    eye = _eye("OS")
    eye.update(topographic_astig_D=3.1, bad_flat_axis_deg=13.1)
    extracted = {"eyes": [eye]}
    plan = _plan()
    plan.update(manifest_cylinder_signed_D=-3.1, manifest_axis_deg=2.0)
    plans = {"OS": plan}
    resolved = resolve_case_plans(extracted, plans)
    assert astigmatic_disparity_verification_eyes(extracted, resolved) == {"OS"}

    eye["bad_flat_axis_deg"] = 1.1
    assert astigmatic_disparity_verification_eyes(extracted, resolved) == set()


def test_confident_treatment_card_defaults_both_roles_when_surrounding_plan_is_blank():
    plan = {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0}
    extracted = {"eyes": [_eye("OD")], "treatment_corrections": [_card()]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["manifest_entered_sphere_D"] == -3.0
    assert resolved["manifest_cylinder_signed_D"] == -1.5
    assert resolved["manifest_axis_deg"] == 80.0
    assert resolved["intended_entered_sphere_D"] == -3.0
    assert resolved["intended_cylinder_signed_D"] == -1.5
    assert resolved["intended_axis_deg"] == 80.0
    assert resolved["manifest_source"] == "TREATMENT_CARD_DUZELTME_MIKTARI"
    assert resolved["intended_source"] == "TREATMENT_CARD_DUZELTME_MIKTARI"


@pytest.mark.parametrize("sphere", [-3.0, -1.0, 3.0])
def test_any_sphere_only_card_defaults_zero_cylinder_and_axis(sphere):
    plan = {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0}
    card = _card(sphere=sphere, cylinder=0.0, axis=None, axis_status="UNREADABLE")
    extracted = {"eyes": [_eye("OD")], "treatment_corrections": [card]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["manifest_entered_sphere_D"] == sphere
    assert resolved["manifest_cylinder_signed_D"] == 0.0
    assert resolved["manifest_axis_deg"] == 0.0
    assert resolved["intended_entered_sphere_D"] == sphere
    assert resolved["intended_cylinder_signed_D"] == 0.0
    assert resolved["intended_axis_deg"] == 0.0


def test_explicit_zero_manifest_cylinder_defaults_blank_intended_cylinder_and_axis():
    plan = {
        "procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": 0.0,
        "intended_entered_sphere_D": -2.0,
    }
    resolved = resolve_eye_plan(plan, extracted={"eyes": [_eye("OD")]}, eye_name="OD")
    assert resolved["manifest_axis_deg"] == 0.0
    assert resolved["intended_cylinder_signed_D"] == 0.0
    assert resolved["intended_axis_deg"] == 0.0


def test_explicit_zero_manifest_cylinder_overwrites_intended_cylinder_and_axis():
    plan = {
        "procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": 0.0,
        "intended_entered_sphere_D": -2.0, "intended_cylinder_signed_D": -0.5,
        "intended_axis_deg": 90.0,
    }
    resolved = resolve_eye_plan(plan, extracted={"eyes": [_eye("OD")]}, eye_name="OD")
    assert resolved["manifest_axis_deg"] == 0.0
    assert resolved["intended_cylinder_signed_D"] == 0.0
    assert resolved["intended_axis_deg"] == 0.0


def test_explicit_intended_role_outranks_treatment_card_for_that_role_only():
    plan = {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0,
            "intended_entered_sphere_D": -2.0, "intended_cylinder_signed_D": -0.5,
            "intended_axis_deg": 70.0}
    extracted = {"eyes": [_eye("OD")], "treatment_corrections": [_card()]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["manifest_entered_sphere_D"] == -3.0
    assert resolved["intended_entered_sphere_D"] == -2.0
    assert resolved["intended_cylinder_signed_D"] == -0.5
    assert resolved["intended_axis_deg"] == 70.0
    assert "intended_source" not in resolved
    assert "correction_warnings" not in resolved


def test_explicit_manifest_and_intended_values_create_no_card_conflict():
    plan = _plan()
    extracted = {"eyes": [_eye("OD")], "treatment_corrections": [_card(sphere=-8.0)]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["manifest_entered_sphere_D"] == plan["manifest_entered_sphere_D"]
    assert resolved["intended_entered_sphere_D"] == plan["intended_entered_sphere_D"]
    assert "manifest_source" not in resolved
    assert "intended_source" not in resolved
    assert "correction_warnings" not in resolved


def test_wholly_blank_intended_role_defaults_from_manifest_without_card():
    plan = _plan()
    for key in ("intended_entered_sphere_D", "intended_cylinder_signed_D", "intended_axis_deg"):
        plan.pop(key)
    resolved = resolve_eye_plan(plan, extracted={"eyes": [_eye()]}, eye_name="OD")
    assert resolved["intended_entered_sphere_D"] == plan["manifest_entered_sphere_D"]
    assert resolved["intended_cylinder_signed_D"] == plan["manifest_cylinder_signed_D"]
    assert resolved["intended_axis_deg"] == plan["manifest_axis_deg"]
    assert resolved["intended_source"] == "DEFAULTED_FROM_MANIFEST"


def test_partial_intended_role_never_falls_back_to_manifest_or_card():
    plan = _plan(); plan["intended_entered_sphere_D"] = -1.5
    plan.pop("intended_cylinder_signed_D"); plan.pop("intended_axis_deg")
    extracted = {"eyes": [_eye()], "treatment_corrections": [_card()]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["intended_entered_sphere_D"] == -1.5
    assert "intended_cylinder_signed_D" not in resolved
    inp = build_clinical_core_input(_eye(), plan, age_years=30, extracted=extracted)
    assert inp.intended_mrse_d is None


def test_ambiguous_multiple_card_corrections_are_not_silently_selected():
    plan = {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0}
    extracted = {"eyes": [_eye()], "treatment_corrections": [_card(sphere=-3.0), _card(sphere=-4.0)]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert "manifest_entered_sphere_D" not in resolved
    assert "intended_entered_sphere_D" not in resolved


def test_card_axis_uncertainty_preserves_sphere_cylinder_but_remains_incomplete_for_nonzero_cylinder():
    plan = {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0}
    extracted = {"eyes": [_eye()], "treatment_corrections": [_card(axis_status="UNCERTAIN")]}
    resolved = resolve_eye_plan(plan, extracted=extracted, eye_name="OD")
    assert resolved["manifest_entered_sphere_D"] == -3.0
    assert resolved["manifest_cylinder_signed_D"] == -1.5
    assert "manifest_axis_deg" not in resolved
    inp = build_clinical_core_input(_eye(), plan, age_years=30, extracted=extracted)
    assert inp.manifest_mrse_d is None
    assert inp.intended_mrse_d is None


def test_resolve_case_plans_is_eye_specific_and_does_not_cross_fill():
    plans = {"OD": {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0},
             "OS": {"procedure": "LASIK", "prior": "no", "flap_um": 100.0, "ablation_um": 80.0}}
    extracted = {"eyes": [_eye("OD"), _eye("OS")],
                 "treatment_corrections": [_card("OD", sphere=-3.0), _card("OS", sphere=-5.0)]}
    resolved = resolve_case_plans(extracted, plans)
    assert resolved["OD"]["manifest_entered_sphere_D"] == -3.0
    assert resolved["OS"]["manifest_entered_sphere_D"] == -5.0


def test_surgeon_confirmed_i_s_overrides_extracted_i_s_for_core_input():
    plan = _plan(); plan["surgeon_I_S_D"] = 1.2
    inp = build_clinical_core_input(_eye(), plan, age_years=30)
    assert inp.i_s_d == 1.2


def test_adapter_does_not_mutate_production_payloads():
    eye = _eye(); plan = _plan(); extracted = {"eyes": [eye, _eye("OS")]}
    before = deepcopy((eye, plan, extracted))
    build_clinical_core_input(eye, plan, age_years=30, extracted=extracted)
    assert (eye, plan, extracted) == before


def test_adapter_output_can_run_through_linear_pipeline_without_transport_state():
    eye = _eye(); extracted = {"eyes": [eye, _eye("OS")]}
    inp = build_clinical_core_input(eye, _plan(), age_years=30, extracted=extracted)
    result = evaluate_normalized_case(inp)
    assert result["procedure"] == "LASIK"
    assert result["status"] in {"PASS", "CAUTION", "STOP-DEFER", "ASSESSMENT INCOMPLETE"}
