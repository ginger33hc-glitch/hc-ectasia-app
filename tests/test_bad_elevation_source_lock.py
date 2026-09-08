from pathlib import Path

import canonical_engine
import pentacam_targeted_reread as targeted_reread
from pentacam_canonical_source_lock import (
    BAD_ELEVATION_ROW,
    canonical_source_id,
    canonical_source_region,
)


def _eye(**values):
    eye = {
        "eye": "OD",
        "screen_types": ["BELIN_AMBROSIO_DISPLAY"],
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
        "_source_filename": "od-bad.png",
    }
    eye.update(values)
    return eye


def _payload(eye):
    return {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_id": "P1",
            "patient_first_name": "Test",
            "patient_last_name": "Patient",
            "patient_name": "Test Patient",
            "patient_name_source": "PENTACAM_FIRST_LAST_NAME_FIELDS",
            "patient_age_years": 30,
            "exam_date": "2026-09-07",
            "exam_time": "10:00",
            "laterality": "OD",
            "pentacam_qs": "OK",
            "missing_or_unreadable": [],
            "source_filename": "od-bad.png",
        },
        "eyes": [eye],
        "treatment_corrections": [],
        "global_warnings": [],
    }


def test_bad_elevation_fields_have_one_canonical_source():
    assert canonical_source_id("F_Ele_Th_um") == BAD_ELEVATION_ROW
    assert canonical_source_id("B_Ele_Th_um") == BAD_ELEVATION_ROW
    assert canonical_source_region("F_Ele_Th_um") == {
        "screen": "Belin/Ambrósio Display",
        "box": (
            "central results table — elevation label/value row immediately above Progression Index "
            "→ F.Ele.Th — adjacent signed µm value"
        ),
    }
    assert canonical_source_region("B_Ele_Th_um")["box"].endswith(
        "B.Ele.Th — adjacent signed µm value"
    )
    assert not Path("ps3_extraction_policy.py").exists()


def test_wrong_screen_elevation_fields_fail_closed_before_merge():
    eye = _eye(F_Ele_Th_um=99, B_Ele_Th_um=88)
    eye["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": "FOUR_MAPS_REFRACTIVE_LOWER_LEFT_LABELED_BOX",
        "B_Ele_Th_um": "FOUR_MAPS_REFRACTIVE_LOWER_LEFT_LABELED_BOX",
    }
    merged = canonical_engine.core.merge_extractions([_payload(eye)])
    od = merged["eyes"][0]
    assert od["F_Ele_Th_um"] is None
    assert od["B_Ele_Th_um"] is None
    assert "F_Ele_Th_um" in od["missing_or_unreadable"]
    assert "B_Ele_Th_um" in od["missing_or_unreadable"]


def test_bad_display_elevation_fields_survive_with_exact_source_provenance():
    eye = _eye(F_Ele_Th_um=7, B_Ele_Th_um=12)
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": BAD_ELEVATION_ROW,
        "B_Ele_Th_um": BAD_ELEVATION_ROW,
    }
    merged = canonical_engine.core.merge_extractions([_payload(eye)])
    od = merged["eyes"][0]
    assert od["F_Ele_Th_um"] == 7
    assert od["B_Ele_Th_um"] == 12
    assert od["field_provenance"]["F_Ele_Th_um"][0]["source"] == BAD_ELEVATION_ROW
    assert od["field_provenance"]["B_Ele_Th_um"][0]["source"] == BAD_ELEVATION_ROW


def test_targeted_reread_rejects_elevation_maps_for_bad_box_fields():
    assert not targeted_reread.source_supports_field(
        "FOUR_MAPS_REFRACTIVE", "F_Ele_Th_um", "Elevation (Front)"
    )
    assert not targeted_reread.source_supports_field(
        "FOUR_MAPS_REFRACTIVE", "B_Ele_Th_um", "Elevation (Back)"
    )
    assert targeted_reread.source_supports_field("BAD_DISPLAY", "F_Ele_Th_um", "")
    assert targeted_reread.source_supports_field("BAD_DISPLAY", "B_Ele_Th_um", "")
