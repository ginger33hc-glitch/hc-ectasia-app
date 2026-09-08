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


def _numeric_result(filename, field, value, screen, verified=True, source_id=None):
    e = _eye()
    e["screen_types"] = [screen]
    e["keratometry_source"] = (
        "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
        if screen == "SHOW_2_EXAMS_TOPOMETRIC" else "OTHER_PENTACAM_SOURCE"
    )
    e[field] = value
    e["table_verified_numeric_fields"] = [field] if verified else []
    if source_id is not None:
        e["canonical_source_ids"][field] = source_id
    return _result(e, filename)


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
    assert "numeric_reconciliation" not in od


def test_unverified_rmin_is_rejected_even_with_correct_source_identity():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "Rmin_mm", 5.33, "SHOW_2_EXAMS_TOPOMETRIC",
            verified=False, source_id=SHOW_2_CORNEA_BACK,
        ),
    ])
    od = merged["eyes"][0]
    assert od["Rmin_mm"] is None
    assert "Rmin_mm" in od.get("missing_or_unreadable", [])


def test_unverified_k1_is_never_accepted_even_with_source_identity():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "K1_D", 44.6, "SHOW_2_EXAMS_TOPOMETRIC",
            verified=False, source_id=SHOW_2_CORNEA_FRONT,
        ),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] is None
    assert "K1_D" in od.get("missing_or_unreadable", [])


def test_canonical_k1_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result(
            "show2.jpg", "K1_D", 44.5, "SHOW_2_EXAMS_TOPOMETRIC",
            source_id=SHOW_2_CORNEA_FRONT,
        ),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 44.5
    assert "numeric_reconciliation" not in od


def test_canonical_bad_ppi_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result("bad.jpg", "PPI_avg", 1.00, "BAD_DISPLAY", source_id=BAD_PPI),
    ])
    od = merged["eyes"][0]
    assert od["PPI_avg"] == 1.00
    assert "numeric_reconciliation" not in od


def test_canonical_four_maps_kmax_direct_read_is_retained():
    merged = core.merge_extractions([
        _numeric_result(
            "fourmaps.jpg", "Kmax_D", 47.8, "FOUR_MAPS_REFRACTIVE",
            source_id=FOUR_MAPS_LOWER_LEFT,
        ),
    ])
    assert merged["eyes"][0]["Kmax_D"] == 47.8

def test_close_same_source_k1_disagreement_remains_conflict():
    merged = core.merge_extractions([
        _numeric_result("show2a.jpg", "K1_D", 44.50, "SHOW_2_EXAMS_TOPOMETRIC", source_id=SHOW_2_CORNEA_FRONT),
        _numeric_result("show2b.jpg", "K1_D", 44.60, "SHOW_2_EXAMS_TOPOMETRIC", source_id=SHOW_2_CORNEA_FRONT),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] is None
    assert any(str(item).startswith("K1_D:") for item in od.get("data_conflicts", []))


def test_sub_one_percent_same_source_ppi_disagreement_remains_conflict():
    merged = core.merge_extractions([
        _numeric_result("bad1.jpg", "PPI_avg", 1.000, "BAD_DISPLAY", source_id=BAD_PPI),
        _numeric_result("bad2.jpg", "PPI_avg", 1.005, "BAD_DISPLAY", source_id=BAD_PPI),
    ])
    od = merged["eyes"][0]
    assert od["PPI_avg"] is None
    assert any(str(item).startswith("PPI_avg:") for item in od.get("data_conflicts", []))


def test_srax_disagreement_remains_unresolved_after_a_third_read():
    first = _eye()
    first.update({"srax": "NO", "srax_deg": 10.0})
    second = _eye()
    second.update({"srax": "YES", "srax_deg": 25.0})
    third = _eye()
    third.update({"srax": "NO", "srax_deg": 10.0})
    merged = core.merge_extractions([
        _result(first, "fourmaps-1.jpg"),
        _result(second, "fourmaps-2.jpg"),
        _result(third, "fourmaps-3.jpg"),
    ])
    od = merged["eyes"][0]
    assert od["srax"] is None
    assert od["srax_deg"] is None
    assert any(str(item).startswith("srax:") for item in od["data_conflicts"])
    assert any(str(item).startswith("srax_deg:") for item in od["data_conflicts"])
