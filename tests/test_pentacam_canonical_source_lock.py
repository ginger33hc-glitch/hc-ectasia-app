from pathlib import Path

import canonical_engine
import pentacam_targeted_reread as targeted_reread
from pentacam_canonical_source_lock import (
    BAD,
    BAD_CENTER,
    BAD_PPI,
    BAD_STRIP,
    CANONICAL_FIELD_SOURCES,
    FOURMAPS,
    FOUR_MAPS_LOWER_LEFT,
    SHOW2,
    SHOW_2_CORNEA_BACK,
    SHOW_2_CORNEA_FRONT,
    SHOW_2_INDICES,
    canonical_source_id,
    derivation_is_allowed,
    source_family,
    source_is_allowed,
)


def eye(**values):
    base = {
        "eye": "OD",
        "screen_types": ["SHOW_2_EXAMS_TOPOMETRIC"],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": list(values),
        "map_fallback_numeric_fields": [],
        "keratometry_source": "NOT_SHOWN",
        "canonical_source_ids": {},
        "morphology": "UNCERTAIN",
        "morphology_evidence": [],
        "asymmetric_bow_tie": "UNCERTAIN",
        "srax": "UNCERTAIN",
        "srax_deg": None,
        "inferior_opposite_steepening_D": None,
        "anterior_pattern": "UNREADABLE",
        "posterior_pattern": "UNREADABLE",
    }
    base.update(values)
    return base


def payload(source_eye):
    return {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_id": "P1",
            "patient_first_name": "Test",
            "patient_last_name": "Patient",
            "patient_name": "Test Patient",
            "patient_age_years": 30,
            "exam_date": "2026-09-07",
            "exam_time": "10:00",
            "laterality": "OD",
            "pentacam_qs": "OK",
            "source_filename": "show2.png",
        },
        "eyes": [source_eye],
        "treatment_corrections": [],
        "global_warnings": [],
    }


def test_all_owner_locked_fields_forbid_derivation():
    assert CANONICAL_FIELD_SOURCES
    assert all(not derivation_is_allowed(field) for field in CANONICAL_FIELD_SOURCES)


def test_cornea_front_is_exact_source_for_anterior_keratometry():
    for field in (
        "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D",
        "topographic_astig_D", "topographic_steep_axis_deg",
    ):
        assert canonical_source_id(field) == SHOW_2_CORNEA_FRONT
        assert source_family(field) == SHOW2


def test_cornea_back_is_exact_source_for_posterior_values():
    assert canonical_source_id("Rmin_mm") == SHOW_2_CORNEA_BACK
    assert canonical_source_id("posterior_Kmean_D") == SHOW_2_CORNEA_BACK
    assert source_family("Rmin_mm") == SHOW2
    assert source_is_allowed("Rmin_mm", SHOW_2_CORNEA_BACK)
    assert not source_is_allowed("Rmin_mm", SHOW_2_CORNEA_FRONT)


def test_show2_indices_are_exact_center_index_sources():
    for field in ("ISV", "IVA", "KI", "CKI", "IHA", "IHD", "TKC", "KISA", "I_S", "topometric_RMin"):
        assert canonical_source_id(field) == SHOW_2_INDICES
        assert source_family(field) == SHOW2


def test_four_maps_lower_left_fields_are_exact_sources():
    for field in ("central_pachy_um", "pachy_thinnest_um", "Kmax_D", "corneal_diameter_mm"):
        assert canonical_source_id(field) == FOUR_MAPS_LOWER_LEFT
        assert source_family(field) == FOURMAPS


def test_bad_fields_are_exact_box_sources():
    for field in ("F_Ele_Th_um", "B_Ele_Th_um"):
        assert canonical_source_id(field) == BAD_CENTER
        assert source_family(field) == BAD
    for field in ("PPI_min", "PPI_avg", "PPI_max", "ARTmax_um"):
        assert canonical_source_id(field) == BAD_PPI
        assert source_family(field) == BAD
    for field in ("Df", "Db", "Dp", "Dt", "Da", "BAD_D"):
        assert canonical_source_id(field) == BAD_STRIP
        assert source_family(field) == BAD


def test_retired_source_enforcement_wrapper_is_physically_absent():
    assert not Path("pentacam_canonical_source_enforcement.py").exists()
    phase_names = {
        name
        for values in canonical_engine.composition.COMPOSITION_PHASES.values()
        for name in values
    }
    assert "pentacam_canonical_source_enforcement" not in phase_names


def test_exact_source_metadata_rejects_wrong_source_before_merge():
    source_eye = eye(I_S=1.2)
    source_eye["canonical_source_ids"]["I_S"] = BAD_STRIP
    merged = canonical_engine.core.merge_extractions([payload(source_eye)])
    od = merged["eyes"][0]
    assert od["I_S"] is None
    assert "I_S" in od["missing_or_unreadable"]


def test_exact_source_metadata_keeps_matching_source_before_merge():
    source_eye = eye(I_S=-0.18)
    source_eye["canonical_source_ids"]["I_S"] = SHOW_2_INDICES
    merged = canonical_engine.core.merge_extractions([payload(source_eye)])
    od = merged["eyes"][0]
    assert od["I_S"] == -0.18
    assert od["field_provenance"]["I_S"][0]["source"] == SHOW_2_INDICES


def test_targeted_reread_uses_exact_subpanel_source_contract():
    assert targeted_reread.source_supports_field(
        "SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Cornea Back"
    )
    assert not targeted_reread.source_supports_field(
        "SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Cornea Front"
    )
    assert targeted_reread.source_supports_field(
        "SHOW_2_EXAMS_TOPOMETRIC", "topometric_RMin", "Indices (in 8 mm zone)"
    )
