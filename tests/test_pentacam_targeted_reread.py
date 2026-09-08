"""Current targeted-reread regression surface after canonical extraction flattening.

The historical module is retained only as a source of extraction-focused fixtures/tests.
Wrapper-era completion, NICE-side-channel, and extractor-wrapper tests are explicitly
retired and replaced with direct canonical enrichment assertions below.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import canonical_engine
from pentacam_canonical_source_lock import BAD_CENTER, BAD_PPI, FOUR_MAPS_LOWER_LEFT

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
    "test_landmark_labels_and_existing_central_reading_control_targets",
    "test_only_canonical_b_ele_th_reading_suppresses_targeted_reread",
    "test_bad_display_b_ele_th_box_feeds_only_nice_posterior_input",
    "test_wrapper_runs_for_missing_age_even_when_no_eye_numeric_field_is_missing",
    "test_wrapper_fails_open_to_original_extraction_when_crop_decode_fails",
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
image_bytes = _legacy.image_bytes


def _axis_result(value):
    result = pentacam_result(bad_flat_axis_deg=value)
    eye = result["eyes"][0]
    eye["canonical_source_ids"] = {"bad_flat_axis_deg": BAD_CENTER}
    eye["table_verified_numeric_fields"] = ["bad_flat_axis_deg"]
    eye["missing_or_unreadable"] = []
    return result


def test_disparity_verification_replaces_bad_axis_from_same_canonical_box(monkeypatch):
    result = _axis_result(13.1)
    response = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading("bad_flat_axis_deg", 1.1, "Axis", tile="UPPER_RIGHT")],
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args, **kwargs: response)

    targeted.verify_astigmatic_disparity_bad_flat_axes(Core, result, b"image", "os-bad.png", {"OD"})

    eye = result["eyes"][0]
    assert eye["bad_flat_axis_deg"] == 1.1
    assert eye["astigmatic_disparity_verification_evidence"]["bad_flat_axis_deg"] == {
        "file": "os-bad.png",
        "primary_value": 13.1,
        "verified_value": 1.1,
        "status": "VERIFIED",
    }
    assert any("from 13.1° to 1.1°" in warning for warning in result["global_warnings"])


def test_unresolved_disparity_axis_does_not_retain_unverified_warning_value(monkeypatch):
    result = _axis_result(13.1)
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args, **kwargs: {
        "screen_family": "BAD_DISPLAY", "readings": [], "warnings": [],
    })

    targeted.verify_astigmatic_disparity_bad_flat_axes(Core, result, b"image", "os-bad.png", {"OD"})

    eye = result["eyes"][0]
    assert eye["bad_flat_axis_deg"] is None
    assert eye["astigmatic_disparity_verification_evidence"]["bad_flat_axis_deg"]["status"] == "UNRESOLVED"
    assert any("surgeon confirmation is recommended" in warning for warning in result["global_warnings"])


def test_canonical_eye_fields_suppress_duplicate_targeted_reread_requests():
    result = pentacam_result()
    eye = result["eyes"][0]
    assert "central_pachy_um" in targeted.missing_targets_by_eye(result)["OD"]
    assert "B_Ele_Th_um" in targeted.missing_targets_by_eye(result)["OD"]

    eye["central_pachy_um"] = 542
    eye["B_Ele_Th_um"] = 23
    eye["table_verified_numeric_fields"] = ["central_pachy_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "central_pachy_um": FOUR_MAPS_LOWER_LEFT,
        "B_Ele_Th_um": BAD_CENTER,
    }
    remaining = targeted.missing_targets_by_eye(result).get("OD", [])
    assert "central_pachy_um" not in remaining
    assert "B_Ele_Th_um" not in remaining
    assert not result.get("nice_readings")


def test_pupil_center_reread_writes_direct_canonical_eye_field_and_numeric_prompt():
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
    eye = result["eyes"][0]
    assert eye["central_pachy_um"] == 548
    assert eye["canonical_source_ids"]["central_pachy_um"] == FOUR_MAPS_LOWER_LEFT
    assert "central_pachy_um" in eye["table_verified_numeric_fields"]
    assert not result.get("nice_readings")

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


def test_bad_display_b_ele_th_reread_writes_direct_canonical_eye_field():
    result = pentacam_result()
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading(
            "B_Ele_Th_um", 23, "B. Ele.Th", tile="LOWER_LEFT",
            source_box=[120, 120, 880, 320],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, reread, {"OD": ["B_Ele_Th_um"]}, "od.png")
    eye = result["eyes"][0]
    assert eye["B_Ele_Th_um"] == 23
    assert eye["canonical_source_ids"]["B_Ele_Th_um"] == BAD_CENTER
    assert "B_Ele_Th_um" in eye["table_verified_numeric_fields"]
    assert not result.get("nice_readings")


def test_dedicated_bad_cell_consensus_corrects_primary_and_localizer_errors(monkeypatch):
    result = pentacam_result(F_Ele_Th_um=41, B_Ele_Th_um=93)
    eye = result["eyes"][0]
    eye["table_verified_numeric_fields"] = ["F_Ele_Th_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": BAD_CENTER,
        "B_Ele_Th_um": BAD_CENTER,
    }
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading(
                "F_Ele_Th_um", 13, "F. Ele.Th", tile="UPPER_RIGHT",
                source_box=[100, 100, 400, 250],
            ),
            reading(
                "B_Ele_Th_um", 9, "B. Ele.Th", tile="UPPER_RIGHT",
                source_box=[500, 100, 800, 250],
            ),
        ],
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args, **kwargs: payload)
    monkeypatch.setattr(targeted, "render_source_region", lambda *args, **kwargs: b"crop")
    runs = iter([
        {("OD", "F_Ele_Th_um"): 3, ("OD", "B_Ele_Th_um"): 9},
        {("OD", "F_Ele_Th_um"): 3},
    ])
    monkeypatch.setattr(
        targeted, "confirm_bad_elevation_crops", lambda *args, **kwargs: next(runs),
    )

    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert eye["F_Ele_Th_um"] == 3
    assert eye["B_Ele_Th_um"] == 9
    assert eye["bad_elevation_verification_evidence"] == {
        "F_Ele_Th_um": {
            "file": "od-bad.png", "primary_value": 41,
            "localized_value": 13,
            "confirmation_values": [3, 3],
            "verified_value": 3, "status": "VERIFIED",
        },
        "B_Ele_Th_um": {
            "file": "od-bad.png", "primary_value": 93,
            "localized_value": 9,
            "confirmation_values": [9, None],
            "verified_value": 9, "status": "VERIFIED",
        },
    }
    assert all(
        eye["targeted_reread_evidence"][field][0]["source"]
        == "DEDICATED_BAD_ELEVATION_DIGIT_CONSENSUS"
        for field in targeted.BAD_ELEVATION_FIELDS
    )
    assert any("from 41 to 3" in warning for warning in result["global_warnings"])
    assert any("from 93 to 9" in warning for warning in result["global_warnings"])


def test_unresolved_bad_elevation_does_not_retain_primary_ocr_value(monkeypatch):
    result = pentacam_result(F_Ele_Th_um=41, B_Ele_Th_um=93)
    eye = result["eyes"][0]
    eye["table_verified_numeric_fields"] = ["F_Ele_Th_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": BAD_CENTER,
        "B_Ele_Th_um": BAD_CENTER,
    }
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading(
                "F_Ele_Th_um", None, "F. Ele.Th", status="UNREADABLE",
                tile="LOWER_LEFT", source_box=[100, 100, 400, 250],
            ),
            reading(
                "B_Ele_Th_um", None, "B. Ele.Th", status="UNREADABLE",
                tile="LOWER_RIGHT", source_box=[100, 100, 400, 250],
            ),
        ],
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args, **kwargs: payload)

    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert eye["F_Ele_Th_um"] is None
    assert eye["B_Ele_Th_um"] is None
    assert not set(targeted.BAD_ELEVATION_FIELDS) & set(eye["table_verified_numeric_fields"])
    assert not set(targeted.BAD_ELEVATION_FIELDS) & set(eye["canonical_source_ids"])
    assert set(targeted.BAD_ELEVATION_FIELDS) <= set(eye["missing_or_unreadable"])
    assert all(
        eye["bad_elevation_verification_evidence"][field]["status"] == "UNRESOLVED"
        for field in targeted.BAD_ELEVATION_FIELDS
    )


def test_bad_cell_consensus_uses_one_confirmation_when_localizer_agrees(monkeypatch):
    result = pentacam_result(F_Ele_Th_um=3, B_Ele_Th_um=9)
    eye = result["eyes"][0]
    eye["table_verified_numeric_fields"] = ["F_Ele_Th_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": BAD_CENTER,
        "B_Ele_Th_um": BAD_CENTER,
    }
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading(
                "F_Ele_Th_um", 3, "F. Ele.Th", tile="UPPER_RIGHT",
                source_box=[100, 100, 400, 250],
            ),
            reading(
                "B_Ele_Th_um", 9, "B. Ele.Th", tile="UPPER_RIGHT",
                source_box=[500, 100, 800, 250],
            ),
        ],
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args, **kwargs: payload)
    monkeypatch.setattr(targeted, "render_source_region", lambda *args, **kwargs: b"crop")
    calls = []

    def confirm(*args, **kwargs):
        calls.append(True)
        return {("OD", "F_Ele_Th_um"): 3, ("OD", "B_Ele_Th_um"): 9}

    monkeypatch.setattr(targeted, "confirm_bad_elevation_crops", confirm)
    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert eye["F_Ele_Th_um"] == 3
    assert eye["B_Ele_Th_um"] == 9
    assert len(calls) == 1


def test_bad_cell_confirmation_reads_only_literal_integer_and_warns_about_cell_border():
    captured = {}
    response_payload = {
        "readings": [{
            "eye": "OS", "field": "F_Ele_Th_um",
            "observed_value_text": "3", "value": 3, "status": "CONFIDENT",
        }],
        "warnings": [],
    }

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=json.dumps(response_payload))

    core = Core()
    core.openai_client = lambda: SimpleNamespace(responses=SimpleNamespace(create=create))
    confirmed = targeted.confirm_bad_elevation_crops(
        core, {("OS", "F_Ele_Th_um"): image_bytes(180, 80)},
    )

    assert confirmed == {("OS", "F_Ele_Th_um"): 3}
    prompt = captured["input"][0]["content"][0]["text"]
    assert "thin vertical edge of the white value cell is a border, not" in prompt.casefold()
    assert "do not" in prompt.casefold() and "infer" in prompt.casefold()


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


def test_direct_enrichment_runs_for_missing_age_without_missing_eye_numeric_fields(monkeypatch):
    original = pentacam_result()
    original["document_context"]["patient_age_years"] = None
    for field in targeted.TARGET_FIELDS:
        original["eyes"][0][field] = 1.0
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [],
        "patient_age_reading": {
            "value": 61,
            "status": "CONFIDENT",
            "printed_label": "Age",
            "source_tile": "TOP_HEADER",
            "source_box": [0, 0, 100, 100],
        },
        "pentacam_qs_reading": {
            "value": None,
            "status": "NOT_SHOWN",
            "printed_label": None,
            "source_tile": "ORIGINAL",
            "source_box": None,
        },
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args: payload)
    result = targeted.enrich_extraction(Core, original, b"not-an-image", "od.png")
    assert result is original
    assert result["document_context"]["patient_age_years"] == 61


def test_direct_enrichment_fails_open_when_crop_decode_fails():
    original = pentacam_result()
    result = targeted.enrich_extraction(Core, original, b"not-an-image", "od.png")
    assert result is original
    assert any(
        "targeted pentacam numeric reread failed" in warning.casefold()
        for warning in result["global_warnings"]
    )
    assert not hasattr(targeted, "make_targeted_extractor")
    assert not hasattr(targeted, "install")


def test_confident_four_maps_exam_date_reread_is_evidence_until_case_reconciliation():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    result["document_context"]["exam_date"] = "23/09/2026"
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [],
        "exam_date_reading": {
            "value": "03/09/2026",
            "status": "CONFIDENT",
            "printed_label": "Date",
            "source_tile": "TOP_HEADER",
            "source_box": [20, 20, 300, 120],
        },
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {}, "od-four-maps.png", exam_date_requested=True,
    )
    context = result["document_context"]
    assert context["exam_date"] == "23/09/2026"
    assert context["targeted_exam_date_reread_evidence"] == {
        "file": "od-four-maps.png",
        "source": "TARGETED_FOUR_MAPS_HEADER_REREAD",
        "tile": "TOP_HEADER",
        "printed_label": "Date",
        "value": "03/09/2026",
        "promoted": False,
    }


PENTACAM_SOURCE_LOCK_RETIRED_TARGETED_TESTS = tuple(sorted(_RETIRED))
del _name, _value
