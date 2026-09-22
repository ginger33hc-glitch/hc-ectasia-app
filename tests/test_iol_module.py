from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from iol_module.engine import evaluate_case
from iol_module.models import IOLCaseInput
import operational_security


def base_payload():
    return {
        "patient_name": "Test Patient",
        "patient_age_years": 66,
        "eye": "OS",
        "near_demand": "HIGH",
        "night_driving": "OCCASIONAL",
        "halo_tolerance": "HIGH",
        "total_corneal_hoa_4mm_um": 0.299,
        "angle_kappa_mm": 0.2,
        "angle_alpha_mm": 0.2,
        "pentacam_pupil_3d_mm": 3.0,
        "tcrp_astigmatism_d": 0.9,
        "tcrp_steep_axis_deg": None,
        "astigmatism_type": None,
        "retina_status": "NONE",
        "macular_pathology_present": False,
        "glaucoma_status": "NONE",
        "ocular_surface_status": "NONE",
        "post_treatment_measurements_stable": None,
    }


def result(overrides=None):
    payload = base_payload()
    payload.update(overrides or {})
    return evaluate_case(IOLCaseInput.model_validate(payload))


def test_balanced_positive_profile_recommends_multifocal():
    recommendation = result()
    assert recommendation.formatted_recommendation == "Multifocal"
    assert recommendation.eligible_categories == ["MULTIFOCAL", "EDOF", "MONOFOCAL"]


@pytest.mark.parametrize("hoa,main,warning", [
    (0.300, "MULTIFOCAL", "WARN_HOA_MODERATE"),
    (0.509, "MULTIFOCAL", "WARN_HOA_MODERATE"),
    (0.510, "MONOFOCAL", "WARN_HOA_HIGH"),
])
def test_hoa_boundaries(hoa, main, warning):
    recommendation = result({"total_corneal_hoa_4mm_um": hoa})
    assert recommendation.main_category == main
    assert warning in recommendation.warning_codes


@pytest.mark.parametrize("pupil,expected", [(1.999, "EDOF"), (2.0, "MULTIFOCAL"), (4.0, "MULTIFOCAL"), (4.001, "EDOF")])
def test_pupil_3d_boundaries(pupil, expected):
    assert result({"pentacam_pupil_3d_mm": pupil}).main_category == expected


def test_toric_threshold_uses_tcrp_and_regular_astigmatism():
    non_toric = result({"tcrp_astigmatism_d": 0.999})
    toric = result({
        "tcrp_astigmatism_d": 1.0,
        "tcrp_steep_axis_deg": 92,
        "astigmatism_type": "REGULAR",
    })
    irregular = result({
        "tcrp_astigmatism_d": 1.0,
        "tcrp_steep_axis_deg": 92,
        "astigmatism_type": "IRREGULAR",
    })
    assert non_toric.toric_modifier == "NON_TORIC"
    assert toric.formatted_recommendation == "Toric Multifocal"
    assert irregular.main_category == "EDOF"
    assert irregular.eligible_categories == ["EDOF", "MONOFOCAL"]
    assert "MF_EXCL_IRREGULAR_ASTIG" in irregular.decisive_reason_codes
    assert "WARN_IRREGULAR_ASTIGMATISM" in irregular.warning_codes
    assert irregular.toric_modifier == "NON_TORIC"


def test_irregular_astigmatism_does_not_override_an_independent_monofocal_preference():
    recommendation = result({
        "near_demand": "LOW",
        "tcrp_astigmatism_d": 1.0,
        "tcrp_steep_axis_deg": 92,
        "astigmatism_type": "IRREGULAR",
    })
    assert recommendation.main_category == "MONOFOCAL"
    assert recommendation.toric_modifier == "NON_TORIC"


def test_macular_pathology_and_definite_glaucoma_stop_multifocal_but_allow_edof():
    for override in ({"macular_pathology_present": True}, {"glaucoma_status": "PRESENT"}):
        recommendation = result(override)
        assert recommendation.main_category == "EDOF"
        assert recommendation.eligible_categories == ["EDOF", "MONOFOCAL"]


def test_glaucoma_suspect_is_warning_only():
    recommendation = result({"glaucoma_status": "SUSPECT"})
    assert recommendation.main_category == "MULTIFOCAL"
    assert "WARN_GLAUCOMA_SUSPECT" in recommendation.warning_codes


def test_active_ocular_surface_stops_multifocal_and_resolved_restores_it():
    assert result({"ocular_surface_status": "MODERATE"}).main_category == "EDOF"
    resolved = result({
        "ocular_surface_status": "RESOLVED_AFTER_TREATMENT",
        "post_treatment_measurements_stable": True,
    })
    assert resolved.main_category == "MULTIFOCAL"
    with pytest.raises(ValidationError):
        IOLCaseInput.model_validate({
            **base_payload(),
            "ocular_surface_status": "RESOLVED_AFTER_TREATMENT",
            "post_treatment_measurements_stable": False,
        })


def test_over_70_soft_prefers_edof_without_removing_multifocal():
    recommendation = result({"patient_age_years": 71})
    assert recommendation.main_category == "EDOF"
    assert recommendation.eligible_categories == ["EDOF", "MULTIFOCAL", "MONOFOCAL"]
    assert recommendation.multifocal_eligible is True


def test_missing_toric_fields_fail_closed():
    payload = deepcopy(base_payload())
    payload["tcrp_astigmatism_d"] = 1.0
    with pytest.raises(ValidationError):
        IOLCaseInput.model_validate(payload)


@pytest.mark.parametrize("retired_field", ["pentacam_source_confirmed", "biometry", "q_value"])
def test_retired_confirmation_and_biometry_contracts_are_rejected(retired_field):
    payload = base_payload()
    payload[retired_field] = True if retired_field.endswith("confirmed") else (
        0.1 if retired_field == "q_value" else {}
    )
    with pytest.raises(ValidationError):
        IOLCaseInput.model_validate(payload)


def test_iol_module_is_first_class_and_does_not_import_refractive_clinical_core():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("iol_module").glob("*.py")
    )
    assert "clinical_core" not in sources
    assert "monkey" not in sources.lower()
    assert "/iol/extract" in operational_security.PROTECTED_PATHS
    assert "/iol/evaluate" in operational_security.PROTECTED_PATHS


def test_iol_mobile_ui_contains_required_sources_and_no_browser_credential_storage():
    html = Path("static/iol.html").read_text(encoding="utf-8")
    script = Path("static/iol.js").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "Pentacam Cataract Pre-Op" in html
    assert "Pupil Dia (3D)" in html
    assert "TCRP only" in html
    assert "Corneal Q" not in html
    assert "q_value" not in script
    assert "Final responsibility rests with the surgeon at all times and under all circumstances." in html
    assert "biometr" not in (html + script).lower()
    assert "Confirmed" not in html
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_iol_extraction_contract_is_pentacam_only():
    source = Path("iol_module/extraction.py").read_text(encoding="utf-8")
    models = Path("iol_module/models.py").read_text(encoding="utf-8")
    assert "BIOMETRY" not in source
    assert "biometr" not in (source + models).lower()
    assert "q_value" not in (source + models)
