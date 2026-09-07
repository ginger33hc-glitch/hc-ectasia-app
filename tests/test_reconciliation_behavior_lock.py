"""Behavior lock for owner-defined canonical Pentacam numeric sources.

Locked fields are single-source direct transcriptions. A non-null locked value is
accepted only when its exact canonical source id is present; missing or wrong
source identity fails closed and is never reconciled.
"""
import canonical_engine
from pentacam_canonical_source_lock import (
    BAD_PPI,
    BAD_STRIP,
    FOUR_MAPS_LOWER_LEFT,
    LOCKED_FIELDS,
    SHOW_2_CORNEA_BACK,
    SHOW_2_CORNEA_FRONT,
    SHOW_2_INDICES,
)

core = canonical_engine.core


def _eye():
    return {
        "eye": "OD",
        "screen_types": [],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": [],
        "map_fallback_numeric_fields": [],
        "keratometry_source": "NOT_SHOWN",
        "canonical_source_ids": {},
        "data_conflicts": [],
        "field_provenance": {},
        "morphology": "UNCERTAIN",
        "morphology_confidence": "UNREADABLE",
        "morphology_evidence": [],
        "asymmetric_bow_tie": "UNCERTAIN",
        "srax": "UNCERTAIN",
        "srax_deg": None,
        "inferior_opposite_steepening_D": None,
        "anterior_pattern": "UNREADABLE",
        "posterior_pattern": "UNREADABLE",
    }


def _result(eye, filename):
    eye["_source_filename"] = filename
    return {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_id": "1",
            "patient_last_name": "X",
            "patient_first_name": "Y",
            "patient_name": "Y X",
            "patient_name_source": "PENTACAM_FIRST_LAST_NAME_FIELDS",
            "patient_age_years": 30,
            "exam_date": "2026-08-27",
            "exam_time": "10:00",
            "laterality": "OD",
            "pentacam_qs": "OK",
            "missing_or_unreadable": [],
            "source_filename": filename,
        },
        "eyes": [eye],
        "treatment_corrections": [],
        "laser_plans": [],
        "global_warnings": [],
    }


def _numeric_result(filename, field, value, screen, provenance="table", source_id=None):
    e = _eye()
    e["screen_types"] = [screen]
    e["keratometry_source"] = (
        "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
        if screen == "SHOW_2_EXAMS_TOPOMETRIC" else "OTHER_PENTACAM_SOURCE"
    )
    e[field] = value
    e["table_verified_numeric_fields"] = [field] if provenance == "table" else []
    e["map_fallback_numeric_fields"] = [field] if provenance == "fallback" else []
    if source_id is not None:
        e["canonical_source_ids"][field] = source_id
    return _result(e, filename)


def test_locked_fields_are_not_eligible_for_numeric_reconciliation():
    from extraction_guard import EXCLUSIVE_LABELED_BOX_FIELDS
    assert LOCKED_FIELDS - {"topometric_RMin"} <= EXCLUSIVE_LABELED_BOX_FIELDS


def test_locked_value_without_exact_source_id_fails_closed():
    merged = core.merge_extractions([
        _numeric_result("fourmaps.jpg", "Kmax_D", 48.1, "FOUR_MAPS_REFRACTIVE"),
    ])
    od = merged["eyes"][0]
    assert od["Kmax_D"] is None
    assert "Kmax_D" in od.get("missing_or_unreadable", [])


def test_wrong_screen_kmax_is_rejected_instead_of_reconciled():
    merged = core.merge_extractions([
        _numeric_result("bad.jpg", "Kmax_D", 48.1, "BAD_DISPLAY", source_id=BAD_STRIP),
    ])
    od = merged["eyes"][0]
    assert od["Kmax_D"] is None
    assert "Kmax_D" in od.get("missing_or_unreadable", [])


def test_wrong_screen_ppi_is_rejected_instead_of_one_percent_merge():
    merged = core.merge_extractions([
        _numeric_result("show2a.jpg", "PPI_avg", 0.99, "SHOW_2_EXAMS_TOPOMETRIC", source_id=SHOW_2_INDICES),
        _numeric_result("show2b.jpg", "PPI_avg", 1.00, "SHOW_2_EXAMS_TOPOMETRIC", source_id=SHOW_2_INDICES),
    ])
    od = merged["eyes"][0]
    assert od["PPI_avg"] is None
    assert "PPI_avg" not in od.get("numeric_reconciliation", {})


def test_rmin_map_fallback_is_prohibited_even_with_correct_source_identity():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "Rmin_mm", 5.33, "SHOW_2_EXAMS_TOPOMETRIC",
            "fallback", source_id=SHOW_2_CORNEA_BACK,
        ),
    ])
    od = merged["eyes"][0]
    assert od["Rmin_mm"] is None
    assert "Rmin_mm" not in od.get("map_fallback_numeric_fields", [])


def test_k1_map_fallback_is_never_accepted():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "K1_D", 44.6, "SHOW_2_EXAMS_TOPOMETRIC",
            "fallback", source_id=SHOW_2_CORNEA_FRONT,
        ),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] is None
    assert "K1_D" not in od.get("map_fallback_numeric_fields", [])


def test_canonical_k1_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "K1_D", 44.5, "SHOW_2_EXAMS_TOPOMETRIC",
            source_id=SHOW_2_CORNEA_FRONT,
        ),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 44.5
    assert "K1_D" not in od.get("numeric_reconciliation", {})


def test_canonical_bad_ppi_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result("bad.jpg", "PPI_avg", 1.00, "BAD_DISPLAY", source_id=BAD_PPI),
    ])
    od = merged["eyes"][0]
    assert od["PPI_avg"] == 1.00
    assert "PPI_avg" not in od.get("numeric_reconciliation", {})


def test_canonical_four_maps_kmax_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result(
            "fourmaps.jpg", "Kmax_D", 47.8, "FOUR_MAPS_REFRACTIVE",
            source_id=FOUR_MAPS_LOWER_LEFT,
        ),
    ])
    assert merged["eyes"][0]["Kmax_D"] == 47.8
