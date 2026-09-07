"""Current targeted-reread regression surface after the canonical source lock.

The historical module is retained only as a source of extraction-focused fixtures/tests.
Wrapper-era completion tests that depended on removed morphology/NICE form IDs or the
legacy HC-engine fixture are explicitly retired and replaced with canonical assertions below.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import canonical_engine
from pentacam_canonical_source_lock import BAD_PPI

_LEGACY_PATH = Path(__file__).with_name("legacy_pentacam_targeted_reread_tests.py")
_SPEC = importlib.util.spec_from_file_location("cerai_legacy_pentacam_targeted_reread_tests", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load historical Pentacam targeted-reread regression module")
_legacy = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _legacy
_SPEC.loader.exec_module(_legacy)

_RETIRED = {
    "test_completion_requests_only_manifest_when_intended_is_wholly_blank",
    "test_pupil_center_reread_feeds_nice_and_unreadable_region_reaches_form",
    "test_circle_marked_thinnest_location_is_retained_as_labeled_row",
    "test_unreadable_b_ele_th_box_region_is_shown_beside_surgeon_input",
    "test_targeted_tile_evidence_survives_canonical_merge",
}
for _name in _RETIRED:
    if not hasattr(_legacy, _name):
        raise RuntimeError(f"Retired targeted-reread test missing: {_name}")
    delattr(_legacy, _name)

for _name, _value in vars(_legacy).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

pentacam_result = _legacy.pentacam_result
reading = _legacy.reading
targeted = _legacy.targeted
Core = _legacy.Core
assessment_workflow = _legacy.assessment_workflow


def test_pupil_center_reread_uses_four_maps_lower_left_source_and_canonical_numeric_prompt():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    requested = {"OD": ["central_pachy_um"]}
    confident = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "central_pachy_um", 548, "Pupil Center +", tile="LOWER_LEFT",
            source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, confident, requested, "od.png")
    assert result["nice_readings"][-1]["central_pachy_um"] == 548
    assert result["nice_readings"][-1]["central_status"] == "CONFIDENT"
    assert result["nice_readings"][-1]["central_landmark"] == "PUPIL_CENTER_PLUS"

    unreadable = pentacam_result()
    unreadable["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "central_pachy_um", None, "Pupil Center +", status="UNREADABLE",
            tile="LOWER_LEFT", source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, unreadable, reread, requested, "od.png")
    item = assessment_workflow._request("OD", "NICE: central_pachy_um", unreadable)
    assert item["kind"] == "number"
    assert item["key"] == "central_pachy_um"
    assert item["destination"] == "measurement"
    assert item["source_region"] is True
    assert "form_id" not in item


def test_unreadable_b_ele_th_uses_canonical_numeric_prompt_with_source_region():
    result = pentacam_result()
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading(
            "B_Ele_Th_um", None, "B. Ele.Th", status="UNREADABLE",
            tile="LOWER_LEFT", source_box=[120, 120, 880, 320],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, reread, {"OD": ["B_Ele_Th_um"]}, "od.png")
    item = assessment_workflow._request("OD", "NICE: B_Ele_Th_um", result)
    assert item["kind"] == "number"
    assert item["key"] == "B_Ele_Th_um"
    assert item["source_region"] is True
    assert "form_id" not in item


def test_circle_marked_thinnest_location_is_retained_only_from_four_maps_lower_left():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "pachy_thinnest_um", 501, "Thinnest Locat.", tile="LOWER_LEFT",
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {"OD": ["pachy_thinnest_um"]}, "od.png"
    )
    eye = result["eyes"][0]
    assert eye["pachy_thinnest_um"] == 501
    assert "pachy_thinnest_um" in eye["table_verified_numeric_fields"]
    assert "pachy_thinnest_um" not in eye.get("map_fallback_numeric_fields", [])


def test_targeted_tile_evidence_survives_canonical_merge_without_legacy_hc_fixture():
    result = pentacam_result(PPI_max=1.42)
    eye = result["eyes"][0]
    eye["table_verified_numeric_fields"] = ["PPI_max"]
    eye["canonical_source_ids"] = {"PPI_max": BAD_PPI}
    eye["targeted_reread_evidence"] = {
        "PPI_max": [{
            "file": "od-bad.png",
            "source": "TARGETED_LABELED_TILE_REREAD",
            "tile": "LOWER_RIGHT",
            "printed_label": "PPI Max",
            "group_label": None,
            "value": 1.42,
        }]
    }
    eye["_source_filename"] = "od-bad.png"
    eye["_pentacam_qs"] = "OK"
    result["document_context"].update({
        "patient_first_name": "Test",
        "patient_last_name": "Patient",
        "patient_name": "Test Patient",
        "patient_id": "P-1",
        "exam_date": "2026-09-01",
        "source_filename": "od-bad.png",
    })
    merged_eye = canonical_engine.core.merge_extractions([result])["eyes"][0]
    assert merged_eye["field_provenance"]["PPI_max"] == eye["targeted_reread_evidence"]["PPI_max"]


PENTACAM_SOURCE_LOCK_RETIRED_TARGETED_TESTS = tuple(sorted(_RETIRED))
del _name, _value
