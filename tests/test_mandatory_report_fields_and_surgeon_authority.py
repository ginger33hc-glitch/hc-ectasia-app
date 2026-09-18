import inspect
from pathlib import Path

import app
import pentacam_targeted_reread as targeted
from pentacam_canonical_source_lock import CANONICAL_FIELD_SOURCES
from pentacam_field_registry import (
    COMPLETION_NUMERIC_FIELDS,
    CONDITIONAL_REPORT_FIELDS,
    DECISION_REQUIRED_FIELDS,
    INITIAL_PASS_ONLY_CANONICAL_FIELDS,
    TARGET_FIELDS,
)


def _context(**values):
    context = {
        "document_type": "PENTACAM_TOPOGRAPHY",
        "patient_first_name": "Image",
        "patient_last_name": "Patient",
        "patient_name": "Image Patient",
        "patient_name_source": "PENTACAM_FIRST_LAST_NAME_FIELDS",
        "patient_age_years": 51,
        "patient_date_of_birth": "01/01/1975",
        "exam_date": "2026-09-17",
        "exam_time": "10:00",
        "laterality": "OD",
        "pentacam_qs": "OK",
        "missing_or_unreadable": [],
    }
    context.update(values)
    return context


def _result():
    return {
        "document_context": _context(),
        "eyes": [{
            "eye": "OD",
            "screen_types": ["SHOW_2_EXAMS_TOPOMETRIC"],
            "I_S": 1.2,
            "table_verified_numeric_fields": ["I_S"],
            "canonical_source_ids": {"I_S": "SHOW_2_EXAMS_TOPOMETRIC_CENTER_INDICES_8MM"},
            "missing_or_unreadable": [],
        }],
        "treatment_corrections": [],
        "laser_plans": [],
        "global_warnings": [],
    }


def test_only_clinical_dependencies_are_targeted_or_completed():
    assert TARGET_FIELDS == DECISION_REQUIRED_FIELDS
    assert set(COMPLETION_NUMERIC_FIELDS) == (
        set(DECISION_REQUIRED_FIELDS) | set(CONDITIONAL_REPORT_FIELDS)
    )
    assert set(INITIAL_PASS_ONLY_CANONICAL_FIELDS) == (
        set(CANONICAL_FIELD_SOURCES)
        - set(DECISION_REQUIRED_FIELDS)
        - set(CONDITIONAL_REPORT_FIELDS)
    )


def test_optional_initial_pass_fields_never_become_reread_targets():
    result = _result()
    result["eyes"][0].update({field: None for field in CANONICAL_FIELD_SOURCES})
    requested = set(targeted.missing_targets_by_eye(result)["OD"])
    assert requested == {
        "K2_D", "Kmean_D", "posterior_Kmean_D", "I_S",
    }
    assert not requested & set(INITIAL_PASS_ONLY_CANONICAL_FIELDS)
    assert not requested & set(CONDITIONAL_REPORT_FIELDS)


def test_preentered_name_age_and_i_s_generate_no_read_instructions():
    authority = app.surgeon_image_authority(
        37,
        {"OD": {"surgeon_I_S_D": 0.8}, "OS": {}},
        {"name": "Surgeon Name", "id": "SURGEON-ID"},
    )
    prompt = app.surgeon_authority_prompt(authority)
    assert "Do not inspect or transcribe any image name" in prompt
    assert "patient ID" not in prompt
    assert "Do not inspect or transcribe image age or date of birth" in prompt
    assert "Do not inspect or transcribe OD I_S" in prompt

    result = app.apply_surgeon_image_authority(_result(), authority)
    context = result["document_context"]
    assert context["patient_name"] is None
    assert context["patient_age_years"] is None
    assert context["patient_date_of_birth"] is None
    eye = result["eyes"][0]
    assert eye["I_S"] is None
    assert "I_S" not in eye["table_verified_numeric_fields"]
    assert eye["canonical_source_ids"]["I_S"] is None


def test_surgoen_i_s_is_excluded_from_targeted_reread():
    result = _result()
    result["eyes"][0]["I_S"] = None
    ordinary = targeted.missing_targets_by_eye(result)["OD"]
    authoritative = targeted.missing_targets_by_eye(
        result, {"OD": {"I_S"}},
    )["OD"]
    assert "I_S" in ordinary
    assert "I_S" not in authoritative


def test_manual_identity_does_not_trigger_image_identity_confirmation():
    first = _result()
    second = _result()
    second["document_context"].update({
        "laterality": "OS",
        "patient_first_name": None,
        "patient_last_name": None,
        "patient_name": None,
    })
    second["eyes"][0]["eye"] = "OS"
    merged = app.merge_extractions(
        [first, second], {"patient": {"name"}, "eyes": {}},
    )
    assert merged["surgeon_authoritative_patient_fields"] == ["name"]
    assert not any("IDENTITY NOT VERIFIED" in item for item in merged["identity_warnings"])


def test_patient_id_is_outside_the_active_extraction_contract():
    context_schema = app.SCHEMA["properties"]["document_context"]
    assert "patient_id" not in context_schema["properties"]
    assert "patient_id" not in context_schema["required"]
    assert "patient ID is the sole" not in app.PROMPT
    assert "Do not inspect or transcribe patient ID" in app.PROMPT
    clinical_ui = Path("static/index.html").read_text(encoding="utf-8")
    archive_ui = Path("static/archive.html").read_text(encoding="utf-8")
    assert 'id="patient_id"' not in clinical_ui
    assert 'id="reportPatientId"' not in clinical_ui
    assert 'id="patient_id"' not in archive_ui


def test_passive_astigmatic_disparity_does_not_schedule_an_ai_reread():
    source = inspect.getsource(app._run_image_assessment)
    assert "astigmatic_disparity_verification_eyes" not in source
    assert "verify_astigmatic_disparity_bad_flat_axes" not in source
    assert not hasattr(targeted, "verify_astigmatic_disparity_bad_flat_axes")
