"""Step-1 locks for canonical EX500 displayed Maximal Ablation resolution."""

from canonical_input_adapter import build_clinical_core_input, resolve_case_plans, resolve_eye_plan


def _plan(ablation=80.0):
    return {
        "procedure": "LASIK", "prior": "no", "flap_um": 100.0,
        "ablation_um": ablation,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": 0.0,
        "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": 0.0,
    }


def _eye(name="OD"):
    return {
        "eye": name, "Kmean_D": 43.0, "K2_D": 44.0,
        "central_pachy_um": 540.0, "pachy_thinnest_um": 530.0,
        "BAD_D": 1.0, "I_S": 0.0, "B_Ele_Th_um": 10.0,
        "F_Ele_Th_um": 5.0, "PPI_avg": 1.0,
        "topographic_astig_D": 0.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0, "srax_deg": 0.0,
    }


def _ex500(eye="OD", value=92.0, *, profile=92.0, max_status="CONFIDENT", profile_status="CONFIDENT"):
    return {
        "eye": eye,
        "platform": "ALCON_WAVELIGHT_EX500",
        "max_ablation_um": value,
        "max_ablation_status": max_status,
        "profile_max_ablation_um": profile,
        "profile_max_status": profile_status,
    }


def test_single_confident_ex500_value_replaces_entered_ablation_at_canonical_plan_resolution():
    extracted = {"eyes": [_eye()], "laser_plans": [_ex500(value=92.0)]}
    resolved = resolve_eye_plan(_plan(80.0), extracted=extracted, eye_name="OD")
    assert resolved["ablation_um"] == 92.0
    assert resolved["max_ablation_um"] == 92.0
    assert resolved["ablation_source"] == "ALCON_WAVELIGHT_EX500_DISPLAYED_MAXIMAL_ABLATION"
    assert resolved["laser_platform"] == "Alcon WaveLight EX500"
    assert any("replaced" in warning for warning in resolved["correction_warnings"])
    inp = build_clinical_core_input(_eye(), _plan(80.0), age_years=30, extracted=extracted)
    assert inp.ablation_um == 92.0


def test_ex500_profile_conflict_never_overwrites_existing_plan_ablation():
    extracted = {"eyes": [_eye()], "laser_plans": [_ex500(value=92.0, profile=100.0)]}
    resolved = resolve_eye_plan(_plan(80.0), extracted=extracted, eye_name="OD")
    assert resolved["ablation_um"] == 80.0
    assert "ablation_source" not in resolved
    assert any("DATA CONFLICT" in warning for warning in resolved["correction_warnings"])


def test_multiple_distinct_confident_ex500_values_never_choose_one():
    extracted = {
        "eyes": [_eye()],
        "laser_plans": [_ex500(value=90.0, profile=90.0), _ex500(value=95.0, profile=95.0)],
    }
    resolved = resolve_eye_plan(_plan(80.0), extracted=extracted, eye_name="OD")
    assert resolved["ablation_um"] == 80.0
    assert "ablation_source" not in resolved
    assert any("multiple confident" in warning for warning in resolved["correction_warnings"])


def test_ex500_resolution_is_eye_specific_and_never_cross_fills():
    extracted = {
        "eyes": [_eye("OD"), _eye("OS")],
        "laser_plans": [_ex500("OD", 91.0, profile=91.0), _ex500("OS", 103.0, profile=103.0)],
    }
    resolved = resolve_case_plans(extracted, {"OD": _plan(80.0), "OS": _plan(80.0)})
    assert resolved["OD"]["ablation_um"] == 91.0
    assert resolved["OS"]["ablation_um"] == 103.0


def test_uncertain_ex500_value_is_not_promoted_to_canonical_plan_input():
    extracted = {
        "eyes": [_eye()],
        "laser_plans": [_ex500(value=92.0, max_status="UNCERTAIN", profile_status="NOT_SHOWN")],
    }
    resolved = resolve_eye_plan(_plan(80.0), extracted=extracted, eye_name="OD")
    assert resolved["ablation_um"] == 80.0
    assert "ablation_source" not in resolved
