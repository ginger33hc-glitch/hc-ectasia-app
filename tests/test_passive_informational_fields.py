import canonical_engine
import pentacam_targeted_reread as targeted
from pentacam_field_registry import (
    EXTRACTION_NUMERIC_FIELDS,
    PASSIVE_INFORMATIONAL_FIELDS,
    TARGET_FIELDS,
)


def _result(filename, value, *, missing=False):
    return {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_id": "P1",
            "patient_last_name": "Patient",
            "patient_first_name": "Test",
            "patient_name": "Test Patient",
            "patient_name_source": "PENTACAM_FIRST_LAST_NAME_FIELDS",
            "patient_age_years": 40,
            "exam_date": "2026-09-08",
            "exam_time": "10:00",
            "laterality": "OD",
            "pentacam_qs": "OK",
            "missing_or_unreadable": [],
            "source_filename": filename,
        },
        "eyes": [{
            "eye": "OD",
            "screen_types": ["FOUR_MAPS_REFRACTIVE"],
            "quality": "ADEQUATE",
            "missing_or_unreadable": ["corneal_volume_mm3"] if missing else [],
            "table_verified_numeric_fields": ["corneal_volume_mm3"] if value is not None else [],
            "keratometry_source": "OTHER_PENTACAM_SOURCE",
            "canonical_source_ids": {},
            "corneal_volume_mm3": value,
            "srax": "UNCERTAIN",
            "srax_deg": None,
            "_source_filename": filename,
        }],
        "treatment_corrections": [],
        "laser_plans": [],
        "global_warnings": [],
    }


def test_passive_fields_remain_in_primary_schema_but_not_targeted_reread():
    assert set(PASSIVE_INFORMATIONAL_FIELDS).issubset(EXTRACTION_NUMERIC_FIELDS)
    assert set(PASSIVE_INFORMATIONAL_FIELDS).isdisjoint(TARGET_FIELDS)
    result = _result("od.png", None)
    assert not set(PASSIVE_INFORMATIONAL_FIELDS) & set(
        targeted.missing_targets_by_eye(result).get("OD", [])
    )


def test_unreadable_passive_field_is_ignored_without_warning_or_missing_state():
    merged = canonical_engine.core.merge_extractions([
        _result("od.png", None, missing=True),
    ])
    eye = merged["eyes"][0]
    assert "corneal_volume_mm3" not in eye["missing_or_unreadable"]
    assert not merged["global_warnings"]


def test_conflicting_passive_values_do_not_create_a_clinical_data_conflict():
    merged = canonical_engine.core.merge_extractions([
        _result("od-a.png", 58.2),
        _result("od-b.png", 58.8),
    ])
    eye = merged["eyes"][0]
    assert eye["corneal_volume_mm3"] == 58.2
    assert not eye["data_conflicts"]
    assert not merged["global_warnings"]
