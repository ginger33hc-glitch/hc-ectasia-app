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
        "q_value": -0.1,
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
        "pentacam_source_confirmed": True,
        "biometry": {
            "source_confirmed": True,
            "axial_length_mm": 23.7,
            "anterior_chamber_depth_mm": 3.1,
            "lens_thickness_mm": 4.4,
            "white_to_white_mm": 11.8,
        },
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
    assert irregular.main_category == "MONOFOCAL"
    assert irregular.toric_modifier == "NON_TORIC"


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


def test_unconfirmed_sources_and_missing_toric_fields_fail_closed():
    payload = base_payload()
    payload["pentacam_source_confirmed"] = False
    with pytest.raises(ValidationError):
        IOLCaseInput.model_validate(payload)
    payload = deepcopy(base_payload())
    payload["tcrp_astigmatism_d"] = 1.0
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
    assert "IOLMaster 500 or approved biometry image" in html
    assert "Pupil Dia (3D)" in html
    assert "TCRP only" in html
    assert "localStorage" not in script
    assert "sessionStorage" not in script
