from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import operational_security
from iol_module.engine import evaluate_case
from iol_module.lens_catalog import LENSES, get_lens
from iol_module.escrs_transfer import build_biomdirect, create_escrs_transfer
from iol_module.models import EscrsTransferInput, IOLCaseInput, IOLPowerPlanInput
from iol_module.power import plan_iol_power


def base_payload():
    return {
        "patient_name": "Test Patient", "patient_age_years": 66, "eye": "OS",
        "near_demand": "HIGH", "night_driving": "OCCASIONAL", "halo_tolerance": "HIGH",
        "total_corneal_hoa_4mm_um": 0.299, "angle_kappa_mm": 0.2,
        "angle_alpha_mm": 0.2, "pentacam_pupil_3d_mm": 3.0,
        "iolm500_k1_d": 42.0, "iolm500_k1_axis_deg": 12,
        "iolm500_k2_d": 42.9, "iolm500_k2_axis_deg": 102,
        "iolm500_measurement_source": "IOLMASTER_500_EXTRACTED",
        "surgeon_k1_d": None, "surgeon_k2_d": None, "astigmatism_type": None,
        "retina_status": "NONE", "macular_pathology_present": False,
        "glaucoma_status": "NONE", "ocular_surface_status": "NONE",
        "post_treatment_measurements_stable": None,
    }


def result(overrides=None):
    payload = base_payload(); payload.update(overrides or {})
    return evaluate_case(IOLCaseInput.model_validate(payload))


def power_payload(**overrides):
    payload = {
        "patient_name": "Test Patient", "biological_sex": "Female", "eye": "OD",
        "selected_lens_id": "clareon-mono-sy60wf", "axial_length_mm": 24.2,
        "acd_mm": 2.21, "k1_d": 42.0, "k1_axis_deg": 20,
        "k2_d": 42.5, "k2_axis_deg": 110, "astigmatism_type": None,
        "prior_corneal_surgery": "NONE",
        "historical_data_available": False, "incision_axis_deg": None,
        "sia_d": None, "sia_axis_deg": None, "cct_um": 573,
        "lens_thickness_mm": None, "wtw_mm": 11.7,
    }
    payload.update(overrides)
    return IOLPowerPlanInput.model_validate(payload)


def test_balanced_positive_profile_recommends_multifocal():
    recommendation = result()
    assert recommendation.formatted_recommendation == "Multifocal"
    assert recommendation.eligible_categories == ["MULTIFOCAL", "EDOF", "MONOFOCAL"]


@pytest.mark.parametrize("hoa,main,warning", [(0.300, "MULTIFOCAL", "WARN_HOA_MODERATE"), (0.509, "MULTIFOCAL", "WARN_HOA_MODERATE"), (0.510, "MONOFOCAL", "WARN_HOA_HIGH")])
def test_hoa_boundaries(hoa, main, warning):
    recommendation = result({"total_corneal_hoa_4mm_um": hoa})
    assert recommendation.main_category == main
    assert warning in recommendation.warning_codes


@pytest.mark.parametrize("pupil,expected", [(1.999, "EDOF"), (2.0, "MULTIFOCAL"), (4.0, "MULTIFOCAL"), (4.001, "EDOF")])
def test_pupil_3d_boundaries(pupil, expected):
    assert result({"pentacam_pupil_3d_mm": pupil}).main_category == expected


def test_toric_threshold_uses_active_iolmaster_k_difference_and_regularity():
    non_toric = result({"iolm500_k2_d": 42.999})
    toric = result({"iolm500_k2_d": 43.0, "astigmatism_type": "REGULAR"})
    irregular = result({"iolm500_k2_d": 43.0, "astigmatism_type": "IRREGULAR"})
    assert non_toric.toric_modifier == "NON_TORIC"
    assert toric.formatted_recommendation == "Toric Multifocal"
    assert toric.toric_evaluation_required is True
    assert irregular.main_category == "EDOF"
    assert irregular.toric_modifier == "NON_TORIC"


def test_surgeon_k_power_override_retains_locked_iolmaster_axes():
    recommendation = result({"surgeon_k1_d": 41.8, "surgeon_k2_d": 42.9, "astigmatism_type": "REGULAR"})
    assert recommendation.active_astigmatism_d == pytest.approx(1.1)
    assert recommendation.k1_axis_deg == 12
    assert recommendation.k2_axis_deg == 102


def test_missing_regularity_at_inclusive_threshold_fails_closed():
    payload = deepcopy(base_payload()); payload["iolm500_k2_d"] = 43.0
    with pytest.raises(ValidationError):
        IOLCaseInput.model_validate(payload)


def test_catalog_includes_surgeon_supplied_toric_models():
    assert len(LENSES) == 20
    assert get_lens("tecnis-eyhance-gib00").name == "TECNIS Eyhance GIB00"
    assert get_lens("clareon-panoptix-cnwtt0").name.startswith("CLAREON")
    assert {get_lens(lens_id).a_constant for lens_id in
            ("clareon-panoptix-toric-cnwtt3", "clareon-toric-cnw0t8")} == {119.1}
    assert get_lens("tecnis-eyhance-toric-diu525").a_constant == 119.3
    assert get_lens("enova-advance-toric").a_constant == 118.0


def test_embedded_toric_calculation_precedes_optional_manufacturer_comparison():
    case = power_payload(selected_lens_id="clareon-panoptix-toric-cnwtt3", k2_d=43.0,
                         astigmatism_type="REGULAR", incision_axis_deg=110, sia_axis_deg=110, sia_d=0.25,
                         posterior_cornea={"eye":"OD", "source":"PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
                                            "k1_d":-5.8, "k2_d":-6.1, "k1_axis_deg":20,
                                            "k2_axis_deg":110, "rh_mm":6.7, "rv_mm":6.5})
    response = [{"IOLs": [{"Predictions": [{"IOL": 21.0, "Rx": 0.01, "IsBestOption": True}]}]}]
    fake = BytesIO(__import__("json").dumps(response).encode()); fake.__enter__ = lambda value: value; fake.__exit__ = lambda *args: None
    with patch("iol_module.power.urlopen", return_value=fake):
        plan = plan_iol_power(case)
    assert plan.route == "MANUFACTURER_TORIC"
    assert plan.calculation_status == "TEST_ONLY"
    assert plan.toric_status == "TEST_ONLY"
    assert len(plan.toric_candidates) == 5
    assert {candidate["model"] for candidate in plan.toric_candidates} == {
        "CNWTT2", "CNWTT3", "CNWTT4", "CNWTT5", "CNWTT6"}
    assert 0 <= plan.toric_candidates[0]["marker_axis_deg"] < 180
    assert plan.toric_candidates[0]["residual_spectacle_cylinder_d"] >= 0
    assert plan.calculator_url == "https://www.myalcon-toriccalc.com/"
    assert plan.predictions[0]["IOL"] == 21.0
    assert "not clinically validated" in plan.message


def test_toric_missing_same_eye_posterior_preserves_sphere_but_has_no_axis():
    case = power_payload(selected_lens_id="clareon-panoptix-toric-cnwtt3", k2_d=43.0,
                         astigmatism_type="REGULAR", incision_axis_deg=110, sia_d=0.25)
    response = [{"IOLs": [{"Predictions": [{"IOL": 21.0, "Rx": 0.01, "IsBestOption": True}]}]}]
    fake = BytesIO(__import__("json").dumps(response).encode())
    with patch("iol_module.power.urlopen", return_value=fake):
        plan = plan_iol_power(case)
    assert plan.toric_status == "INPUTS_INCOMPLETE"
    assert plan.toric_candidates == []
    assert plan.predictions[0]["IOL"] == 21.0
    assert plan.calculator_url == "https://www.myalcon-toriccalc.com/"


def test_toric_fixed_incision_and_sia_reject_inconsistent_user_inputs():
    inputs = dict(selected_lens_id="clareon-panoptix-toric-cnwtt3", k2_d=43.0,
                  astigmatism_type="REGULAR", incision_axis_deg=110, sia_d=0.25)
    with pytest.raises(ValidationError):
        power_payload(**{**inputs, "incision_axis_deg":120})
    with pytest.raises(ValidationError):
        power_payload(**{**inputs, "sia_d":0.2})


def test_unverified_manufacturer_toric_route_fails_closed():
    case = power_payload(selected_lens_id="enova-adc-advance", k2_d=43.0, astigmatism_type="REGULAR", incision_axis_deg=110, sia_d=0.25)
    response = [{"IOLs": [{"Predictions": [{"IOL": 20.5, "Rx": -0.1}]}]}]
    fake = BytesIO(__import__("json").dumps(response).encode()); fake.__enter__ = lambda value: value; fake.__exit__ = lambda *args: None
    with patch("iol_module.power.urlopen", return_value=fake):
        plan = plan_iol_power(case)
    assert plan.calculation_status == "CALCULATION_UNAVAILABLE"
    assert plan.toric_status == "UNSUPPORTED"
    assert plan.calculator_url is None
    assert plan.predictions[0]["IOL"] == 20.5


def test_post_refractive_overrides_standard_and_toric_routes():
    plan = plan_iol_power(power_payload(prior_corneal_surgery="MYOPIC_LASIK_PRK", historical_data_available=False))
    assert plan.route == "BARRETT_TRUE_K_EXTERNAL"
    assert "no-history" in plan.message
    assert plan.calculator_url == "https://iolcalc.ascrs.org/"


def test_non_toric_standard_eye_uses_cooke_k6_and_exposes_external_verification():
    response = [{"IOLs": [{"Predictions": [{"IOL": 21.0, "Rx": 0.01, "IsBestOption": True}]}]}]
    fake = BytesIO(__import__("json").dumps(response).encode()); fake.__enter__ = lambda value: value; fake.__exit__ = lambda *args: None
    with patch("iol_module.power.urlopen", return_value=fake):
        plan = plan_iol_power(power_payload())
    assert plan.route == "COOKE_K6"
    assert plan.calculation_status == "COMPLETED"
    assert plan.predictions[0]["IsBestOption"] is True
    assert plan.escrs_url == "https://iolcalculator.escrs.org/"
    assert plan.inputs["biological_sex"] == "Female"


def test_short_eye_requires_real_lens_thickness_and_wtw():
    with pytest.raises(ValidationError):
        power_payload(axial_length_mm=21.9, lens_thickness_mm=None)


@pytest.mark.parametrize("acd,target", [(2.49, 0.0), (2.5, -0.25), (3.5, -0.25), (3.51, -0.5)])
@pytest.mark.parametrize("al,check", [(21.99, True), (22.0, False), (26.0, False), (26.01, True)])
def test_acd_target_and_axial_length_second_formula_are_independent(acd, target, al, check):
    case = power_payload(acd_mm=acd, axial_length_mm=al, lens_thickness_mm=4.5)
    response = [{"IOLs": [{"Predictions": [{"IOL": 21.0, "Rx": 0.01}]}]}]
    fake = BytesIO(__import__("json").dumps(response).encode())
    fake.__enter__ = lambda value: value
    fake.__exit__ = lambda *args: None
    with patch("iol_module.power.urlopen", return_value=fake) as mocked:
        plan = plan_iol_power(case)
    assert plan.target_refraction_d == target
    assert plan.target_locked is True
    assert plan.second_formula_required is check
    assert plan.inputs["target_refraction_d"] == target
    assert __import__("json").loads(mocked.call_args.args[0].data)["Eyes"][0]["TgtRx"] == target


def test_power_route_requires_surgeon_selected_biological_sex():
    with pytest.raises(ValidationError):
        power_payload(biological_sex="")
    with pytest.raises(ValidationError):
        power_payload(biological_sex="Unknown")


def test_extraction_contract_encodes_pentacam_complement_and_no_tcrp_authority():
    source = Path("iol_module/extraction.py").read_text(encoding="utf-8")
    assert "IOLMASTER_500_BIOMETRY" in source
    assert "cct_pachy_vertex_um" in source and "hwtw_mm" in source and "acd_internal_mm" in source
    assert "ACD (Int.)" in source and "ACD (Ext.)" in source
    assert "tcrp_astigmatism_d" not in source.lower()


def test_toric_posterior_source_has_separate_same_eye_fields():
    from iol_module.extraction import EXTRACTION_SCHEMA

    fields = EXTRACTION_SCHEMA["properties"]
    assert "PENTACAM_4_MAPS_REFRACTIVE" in fields["document_type"]["enum"]
    assert set(fields["cornea_back"]["required"]) == {
        "k1_d", "k2_d", "k1_axis_deg", "k2_axis_deg", "rh_mm", "rv_mm"
    }
    assert "cornea_back" not in fields["pentacam"]["properties"]


def test_posterior_cornea_cannot_be_taken_from_fellow_eye():
    posterior = {
        "eye": "OS", "source": "PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
        "k1_d": -5.8, "k2_d": -6.1, "k1_axis_deg": 10,
        "k2_axis_deg": 100, "rh_mm": 6.7, "rv_mm": 6.5,
    }
    with pytest.raises(ValidationError):
        power_payload(posterior_cornea=posterior)
    case = power_payload(eye="OS", posterior_cornea=posterior)
    assert case.posterior_cornea.k1_d == -5.8
    with pytest.raises(ValidationError):
        power_payload(eye="OS", posterior_cornea={**posterior, "k2_axis_deg": 40})


def test_iol_module_is_first_class_and_routes_are_protected():
    sources = "\n".join(path.read_text(encoding="utf-8") for path in Path("iol_module").glob("*.py"))
    assert "clinical_core" not in sources
    assert "monkey" not in sources.lower()
    for path in ("/iol/extract", "/iol/evaluate", "/iol/lenses", "/iol/power/plan", "/iol/escrs-transfer"):
        assert path in operational_security.PROTECTED_PATHS


def test_mobile_ui_contains_both_sources_and_no_browser_credential_storage():
    html = Path("static/iol.html").read_text(encoding="utf-8")
    script = Path("static/iol.js").read_text(encoding="utf-8")
    assert 'name="viewport"' in html and "IOLMaster 500" in html and "Pentacam Cataract Pre-Op" in html
    assert "ACD (Int.)" in html and "TCRP is not used" in html
    assert "localStorage" not in script and "sessionStorage" not in script
    assert "Final responsibility rests with the surgeon at all times and under all circumstances." in html


def test_escrs_transfer_is_deidentified_and_kane_is_removed():
    html = Path("static/iol.html").read_text(encoding="utf-8")
    script = Path("static/iol.js").read_text(encoding="utf-8")
    power = Path("iol_module/power.py").read_text(encoding="utf-8")
    transfer = script[script.index("function escrsTransferPayload"):script.index('$("iolForm").addEventListener')]
    assert '<select id="biologicalSex" required>' in html
    assert "patient_name" not in transfer and "patient_id" not in transfer
    assert 'fetch("/iol/escrs-transfer"' in script
    assert "downloadEscrsBiometry" not in script and "createObjectURL" not in script
    assert "Kane" not in html and "Kane" not in script and "KANE_URL" not in power


def test_escrs_biompin_handoff_uses_deidentified_biomdirect_and_query_parameter():
    case = EscrsTransferInput.model_validate({
        "biological_sex": "Female", "eye": "OD", "axial_length_mm": 23.5,
        "acd_internal_mm": 2.21, "k1_d": 42.6, "k2_d": 42.8,
        "cct_um": 573, "lens_thickness_mm": 4.5, "wtw_mm": 11.7,
    })
    document = build_biomdirect(case)
    assert document["data"]["patient"] == {"gender": "Female"}
    assert document["data"]["right_eye"]["ACD"] == 2.21
    assert document["data"]["left_eye"] == {}
    assert "name" not in document["data"]["patient"] and "id" not in document["data"]["patient"]

    response = BytesIO(b'{"biompin":{"pin":"lunar-rocket-731904","expires_at":"2026-10-24T00:00:00Z"}}')
    response.__enter__ = lambda value: value
    response.__exit__ = lambda *args: None
    with patch("iol_module.escrs_transfer.urlopen", return_value=response) as mocked:
        result = create_escrs_transfer(case)
    request = mocked.call_args.args[0]
    assert b'name="biompin"\r\n\r\ntrue' in request.data
    assert b'"patient":{"gender":"Female"}' in request.data
    assert b"Test Patient" not in request.data
    assert result["escrs_url"] == "https://iolcalculator.escrs.org/?biompin=lunar-rocket-731904"


def test_pentacam_is_the_only_operative_eye_source():
    html = Path("static/iol.html").read_text(encoding="utf-8")
    script = Path("static/iol.js").read_text(encoding="utf-8")
    assert '<select id="eye" required disabled>' in html
    assert "IOLMaster is bilateral" in html
    assert "const pentacamEyes = new Set()" in script
    assert '$("eye").value = [...pentacamEyes][0]' in script
    assert "originals.OD ? \"OD\"" not in script
    assert "pentacamEyeConfirmed" in script
    assert "Conflicting Pentacam laterality was detected" in script
