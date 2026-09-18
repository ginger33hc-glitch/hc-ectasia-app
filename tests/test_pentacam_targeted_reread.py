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
from pentacam_canonical_source_lock import (
    BAD_ELEVATION_ROW,
    BAD_PPI,
    FOUR_MAPS_LOWER_LEFT,
)

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
    "test_targeted_reread_does_not_seek_keratometry_on_other_pentacam_screens",
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


def test_canonical_eye_fields_suppress_duplicate_targeted_reread_requests():
    result = pentacam_result()
    eye = result["eyes"][0]
    assert "central_pachy_um" not in targeted.missing_targets_by_eye(result)["OD"]
    assert "B_Ele_Th_um" in targeted.missing_targets_by_eye(result)["OD"]

    eye["central_pachy_um"] = 542
    eye["B_Ele_Th_um"] = 23
    eye["table_verified_numeric_fields"] = ["central_pachy_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "central_pachy_um": FOUR_MAPS_LOWER_LEFT,
        "B_Ele_Th_um": BAD_ELEVATION_ROW,
    }
    remaining = targeted.missing_targets_by_eye(result).get("OD", [])
    assert "central_pachy_um" not in remaining
    assert "B_Ele_Th_um" not in remaining
    assert not result.get("nice_readings")


def test_standard_reread_requests_only_fields_owned_by_the_visible_screen():
    bad = pentacam_result()
    bad_missing = set(targeted.missing_targets_by_eye(bad)["OD"])
    assert {"F_Ele_Th_um", "B_Ele_Th_um", "BAD_D"} <= bad_missing
    assert {"PPI_min", "PPI_max", "ARTmax_um", "Df", "Db", "Dp", "Dt", "Da"} <= bad_missing
    assert "K1_D" not in bad_missing
    assert "central_pachy_um" not in bad_missing

    show2 = pentacam_result()
    show2["eyes"][0]["screen_types"] = ["SHOW_2_EXAMS_TOPOMETRIC"]
    show2_missing = set(targeted.missing_targets_by_eye(show2)["OD"])
    assert {"K2_D", "Kmean_D", "posterior_Kmean_D", "I_S"} <= show2_missing
    assert "K1_D" not in show2_missing
    assert "Rmin_mm" not in show2_missing
    assert "F_Ele_Th_um" not in show2_missing
    assert "central_pachy_um" not in show2_missing


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
    assert eye["canonical_source_ids"]["B_Ele_Th_um"] == BAD_ELEVATION_ROW
    assert "B_Ele_Th_um" in eye["table_verified_numeric_fields"]
    assert not result.get("nice_readings")


def test_bad_elevations_use_the_standard_single_targeted_reread_path(monkeypatch):
    result = pentacam_result()
    eye = result["eyes"][0]
    for field in targeted.TARGET_FIELDS:
        eye[field] = 1.0
    eye["F_Ele_Th_um"] = None
    eye["B_Ele_Th_um"] = None
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(_core, _raw, _filename, requested, *_args):
        calls.append(requested)
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [
                reading("F_Ele_Th_um", 3, "F.Ele.Th", tile="LOWER_RIGHT"),
                reading("B_Ele_Th_um", 8, "B.Ele.Th", tile="LOWER_RIGHT"),
            ],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert calls == [{"OD": ["F_Ele_Th_um", "B_Ele_Th_um"]}]
    assert eye["F_Ele_Th_um"] == 3
    assert eye["B_Ele_Th_um"] == 8
    assert all(
        eye["targeted_reread_evidence"][field][0]["source"]
        == "TARGETED_LABELED_TILE_REREAD"
        for field in ("F_Ele_Th_um", "B_Ele_Th_um")
    )


def _threshold_elevation_result(front=13, back=44):
    result = pentacam_result(F_Ele_Th_um=front, B_Ele_Th_um=back)
    eye = result["eyes"][0]
    eye["table_verified_numeric_fields"] = ["F_Ele_Th_um", "B_Ele_Th_um"]
    eye["canonical_source_ids"] = {
        "F_Ele_Th_um": BAD_ELEVATION_ROW,
        "B_Ele_Th_um": BAD_ELEVATION_ROW,
    }
    eye["missing_or_unreadable"] = []
    return result


def test_threshold_level_bad_elevations_are_read_exactly_three_times(monkeypatch):
    result = _threshold_elevation_result()
    calls = []

    def reread(_core, _raw, _filename, requested, *_args):
        calls.append(requested)
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [
                reading("F_Ele_Th_um", 4, "F.Ele.Th", source_box=[100, 100, 400, 200]),
                reading("B_Ele_Th_um", 4, "B.Ele.Th", source_box=[400, 100, 700, 200]),
            ],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.verify_threshold_level_bad_elevations(Core, result, b"image", "od-bad.png")

    eye = result["eyes"][0]
    assert len(calls) == targeted.BAD_ELEVATION_VERIFICATION_READS == 3
    assert all(call == {"OD": ["F_Ele_Th_um", "B_Ele_Th_um"]} for call in calls)
    assert eye["F_Ele_Th_um"] == eye["B_Ele_Th_um"] == 4
    assert eye["threshold_elevation_verification_evidence"]["B_Ele_Th_um"]["primary_value"] == 44
    assert len(eye["threshold_elevation_verification_evidence"]["B_Ele_Th_um"]["attempts"]) == 3


def test_three_concordant_still_high_bad_elevations_require_surgeon(monkeypatch):
    result = _threshold_elevation_result(front=13, back=16)
    monkeypatch.setattr(targeted, "targeted_reread", lambda *_args: {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading("F_Ele_Th_um", 13, "F.Ele.Th", source_box=[100, 100, 400, 200]),
            reading("B_Ele_Th_um", 16, "B.Ele.Th", source_box=[400, 100, 700, 200]),
        ],
        "warnings": [],
    })

    targeted.verify_threshold_level_bad_elevations(Core, result, b"image", "od-bad.png")

    eye = result["eyes"][0]
    assert eye["F_Ele_Th_um"] is None
    assert eye["B_Ele_Th_um"] is None
    assert {"F_Ele_Th_um", "B_Ele_Th_um"} <= set(eye["missing_or_unreadable"])
    assert not {"F_Ele_Th_um", "B_Ele_Th_um"} & set(eye["table_verified_numeric_fields"])
    assert eye["threshold_elevation_verification_evidence"]["F_Ele_Th_um"]["status"] == "SURGEON_CONFIRMATION_REQUIRED"
    expanded = assessment_workflow._expanded_ps3_missing(
        "OD", "PS3: elevation", {}, result,
    )
    assert expanded == [
        ("OD", "PS3: F_Ele_Th_um"),
        ("OD", "PS3: B_Ele_Th_um"),
    ]
    posterior_request = assessment_workflow._request("OD", "NICE: B_Ele_Th_um", result)
    assert posterior_request["kind"] == "number"
    assert posterior_request["key"] == "B_Ele_Th_um"


def test_discordant_or_unreadable_bad_elevation_rereads_require_surgeon(monkeypatch):
    result = _threshold_elevation_result(front=13, back=10)
    values = iter((4, 5, None))

    def reread(_core, _raw, _filename, _requested, *_args):
        value = next(values)
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [reading(
                "F_Ele_Th_um", value, "F.Ele.Th",
                status="CONFIDENT" if value is not None else "UNREADABLE",
                source_box=[100, 100, 400, 200],
            )],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.verify_threshold_level_bad_elevations(Core, result, b"image", "od-bad.png")

    eye = result["eyes"][0]
    assert eye["F_Ele_Th_um"] is None
    assert eye["B_Ele_Th_um"] == 10
    assert eye["unreadable_source_regions"]["F_Ele_Th_um"]["source_box"] == [100, 100, 400, 200]


def test_bad_elevation_verification_does_not_trigger_at_exact_boundaries(monkeypatch):
    result = _threshold_elevation_result(front=12, back=15)
    monkeypatch.setattr(
        targeted, "targeted_reread",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must not reread")),
    )
    targeted.verify_threshold_level_bad_elevations(Core, result, b"image", "od-bad.png")
    assert result["eyes"][0]["F_Ele_Th_um"] == 12
    assert result["eyes"][0]["B_Ele_Th_um"] == 15


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


def test_direct_enrichment_fails_open_after_five_crop_decode_failures():
    original = pentacam_result()
    result = targeted.enrich_extraction(Core, original, b"not-an-image", "od.png")
    assert result is original
    assert any(
        "had 5 failed attempt(s)" in warning.casefold()
        for warning in result["global_warnings"]
    )
    assert not hasattr(targeted, "make_targeted_extractor")
    assert not hasattr(targeted, "install")


def test_required_field_can_resolve_on_fifth_standard_reread(monkeypatch):
    result = pentacam_result()
    eye = result["eyes"][0]
    for field in targeted.TARGET_FIELDS:
        eye[field] = 1.0
    eye["B_Ele_Th_um"] = None
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(_core, _raw, _filename, requested, *_args):
        calls.append(requested)
        value = 8 if len(calls) == targeted.TARGETED_REREAD_MAX_ATTEMPTS else None
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [reading(
                "B_Ele_Th_um", value, "B.Ele.Th",
                status="CONFIDENT" if value is not None else "UNREADABLE",
            )],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert len(calls) == targeted.TARGETED_REREAD_MAX_ATTEMPTS == 5
    assert all(call == {"OD": ["B_Ele_Th_um"]} for call in calls)
    assert eye["B_Ele_Th_um"] == 8


def test_bad_report_context_receives_exactly_one_focused_reread(monkeypatch):
    result = pentacam_result()
    eye = result["eyes"][0]
    for field in targeted.TARGET_FIELDS:
        eye[field] = 1.0
    eye["Df"] = None
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(_core, _raw, _filename, requested, *_args):
        calls.append(requested)
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [reading("Df", None, "Df", status="UNREADABLE")],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert calls == [{"OD": ["Df"]}]
    assert eye["Df"] is None


def test_focused_retry_requires_regions_for_every_outstanding_target():
    result = pentacam_result()
    eye = result["eyes"][0]
    eye["unreadable_source_regions"] = {
        "F_Ele_Th_um": {
            "file": "od-bad.png",
            "tile": "LOWER_RIGHT",
            "source_box": [100, 120, 320, 210],
        }
    }

    requested = {"OD": ["F_Ele_Th_um", "B_Ele_Th_um"]}
    assert targeted._focused_retry_regions(result, requested, "od-bad.png") == []

    eye["unreadable_source_regions"]["B_Ele_Th_um"] = {
        "file": "od-bad.png",
        "tile": "LOWER_RIGHT",
        "source_box": [100, 120, 320, 210],
    }
    assert targeted._focused_retry_regions(result, requested, "od-bad.png") == [
        {
            "file": "od-bad.png",
            "tile": "LOWER_RIGHT",
            "source_box": [100, 120, 320, 210],
        }
    ]


def test_region_without_exact_box_uses_canonical_tile_fallback_only():
    result = pentacam_result()
    result["eyes"][0]["unreadable_source_regions"] = {
        "B_Ele_Th_um": {
            "file": "od-bad.png",
            "tile": "LOWER_RIGHT",
            "source_box": None,
        }
    }
    requested = {"OD": ["B_Ele_Th_um"]}

    assert targeted._focused_retry_regions(result, requested, "od-bad.png") == []
    assert targeted._canonical_retry_regions(
        requested, pentacam_qs_requested=True,
    ) == [
        {"tile": "LOWER_RIGHT", "source_box": None},
        {"tile": "TOP_HEADER", "source_box": None},
    ]


def test_first_reread_is_full_then_follow_up_uses_canonical_tiles(monkeypatch):
    result = pentacam_result()
    eye = result["eyes"][0]
    for field in targeted.TARGET_FIELDS:
        eye[field] = 1.0
    eye["B_Ele_Th_um"] = None
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(*args):
        calls.append(args)
        value = 8 if len(calls) == 2 else None
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [reading(
                "B_Ele_Th_um", value, "B.Ele.Th",
                status="CONFIDENT" if value is not None else "NOT_SHOWN",
            )],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(Core, result, b"image", "od-bad.png")

    assert len(calls) == 2
    assert len(calls[0]) == 10
    assert calls[1][7] == [{"tile": "LOWER_RIGHT", "source_box": None}]
    assert calls[0][8] is True
    assert calls[1][8] is False
    assert eye["B_Ele_Th_um"] == 8


def test_focused_retry_sends_original_plus_only_exact_unread_region():
    captured = {}

    class FocusedCore(Core):
        @staticmethod
        def openai_client():
            def create(**kwargs):
                captured.update(kwargs)
                return SimpleNamespace(output_text=json.dumps({
                    "screen_family": "BAD_DISPLAY",
                    "readings": [],
                    "warnings": [],
                }))

            return SimpleNamespace(responses=SimpleNamespace(create=create))

    targeted.targeted_reread(
        FocusedCore,
        image_bytes(),
        "od-bad.png",
        {"OD": ["B_Ele_Th_um"]},
        focused_regions=[{
            "file": "od-bad.png",
            "tile": "LOWER_RIGHT",
            "source_box": [100, 120, 320, 210],
        }],
    )

    content = captured["input"][0]["content"]
    images = [item for item in content if item["type"] == "input_image"]
    labels = [item["text"] for item in content if item["type"] == "input_text"]
    assert len(images) == 2
    assert "ORIGINAL complete screen:" in labels
    assert "LOWER_RIGHT focused crop of the same screen:" in labels


def test_repeat_focused_reread_omits_original_and_uses_fast_transcription_settings():
    captured = {}

    class FocusedCore(Core):
        @staticmethod
        def openai_client():
            def create(**kwargs):
                captured.update(kwargs)
                return SimpleNamespace(output_text=json.dumps({
                    "screen_family": "BAD_DISPLAY",
                    "readings": [],
                    "warnings": [],
                }))

            return SimpleNamespace(responses=SimpleNamespace(create=create))

    targeted.targeted_reread(
        FocusedCore,
        image_bytes(),
        "od-bad.png",
        {"OD": ["B_Ele_Th_um"]},
        focused_regions=[{
            "file": "od-bad.png",
            "tile": "LOWER_RIGHT",
            "source_box": [100, 120, 320, 210],
        }],
        include_original=False,
        timeout_seconds=37,
    )

    content = captured["input"][0]["content"]
    images = [item for item in content if item["type"] == "input_image"]
    labels = [item["text"] for item in content if item["type"] == "input_text"]
    assert len(images) == 1
    assert "ORIGINAL complete screen:" not in labels
    assert "LOWER_RIGHT focused crop of the same screen:" in labels
    assert captured["reasoning"] == {"effort": "low"}
    assert captured["text"]["verbosity"] == "low"
    assert captured["timeout"] == 37


def test_expired_assessment_budget_stops_rereads_and_requests_surgeon_confirmation(monkeypatch):
    result = pentacam_result()
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})

    def unexpected_reread(*_args, **_kwargs):
        raise AssertionError("no upstream call may start after the assessment budget")

    monkeypatch.setattr(targeted, "targeted_reread", unexpected_reread)
    targeted.enrich_extraction(
        Core, result, b"image", "od-bad.png",
        deadline_monotonic=targeted.monotonic() - 1,
    )

    assert any(
        "time budget reached" in warning
        and "No value was inferred" in warning
        for warning in result["global_warnings"]
    )


def test_reread_timeout_is_capped_by_remaining_assessment_budget(monkeypatch):
    result = pentacam_result()
    eye = result["eyes"][0]
    for field in targeted.TARGET_FIELDS:
        eye[field] = 1.0
    eye["B_Ele_Th_um"] = None
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(*args):
        calls.append(args)
        return {
            "screen_family": "BAD_DISPLAY",
            "readings": [reading("B_Ele_Th_um", 8, "B.Ele.Th")],
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "monotonic", lambda: 100.0)
    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(
        Core, result, b"image", "od-bad.png", deadline_monotonic=120.0,
    )

    assert len(calls) == 1
    assert calls[0][9] == 20.0
    assert eye["B_Ele_Th_um"] == 8


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
            "printed_label": "Exam Date",
            "source_tile": "FOUR_MAPS_EXAM_DATE",
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
        "source": "FOUR_MAPS_REFRACTIVE_UPPER_LEFT_EXAM_DATE",
        "method": "TARGETED_REREAD",
        "tile": "FOUR_MAPS_EXAM_DATE",
        "printed_label": "Exam Date",
        "value": "03/09/2026",
        "promoted": False,
    }


def test_generic_date_label_is_rejected_for_four_maps_exam_date():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [],
        "exam_date_reading": {
            "value": "03/09/2025",
            "status": "CONFIDENT",
            "printed_label": "Date",
            "source_tile": "FOUR_MAPS_EXAM_DATE",
            "source_box": [20, 20, 300, 120],
        },
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {}, "od-four-maps.png", exam_date_requested=True,
    )
    assert "targeted_exam_date_reread_evidence" not in result["document_context"]
    assert any(
        "date reread rejected" in warning.casefold()
        for warning in result["global_warnings"]
    )


def test_exam_date_conflict_rereads_only_dedicated_upper_left_box(monkeypatch):
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    for field in targeted.TARGET_FIELDS:
        result["eyes"][0][field] = 1.0
    result["document_context"].update({"patient_age_years": 40, "pentacam_qs": "OK"})
    calls = []

    def reread(*args):
        calls.append(args)
        return {
            "screen_family": "FOUR_MAPS_REFRACTIVE",
            "readings": [],
            "exam_date_reading": {
                "value": "03/09/2026",
                "status": "CONFIDENT",
                "printed_label": "Exam Date",
                "source_tile": "FOUR_MAPS_EXAM_DATE",
                "source_box": [20, 20, 300, 120],
            },
            "warnings": [],
        }

    monkeypatch.setattr(targeted, "targeted_reread", reread)
    targeted.enrich_extraction(
        Core, result, b"image", "od-four-maps.png", exam_date_requested=True,
    )

    assert len(calls) == 1
    assert calls[0][7] == [{"tile": "FOUR_MAPS_EXAM_DATE", "source_box": None}]
    assert calls[0][8] is False
    assert result["document_context"]["targeted_exam_date_reread_evidence"]["value"] == "03/09/2026"


def test_primary_prompt_source_locks_exam_date_to_four_maps_exam_date_box():
    assert 'explicitly labeled "Exam Date"' in canonical_engine.core.PROMPT
    assert "return exam_date=null and exam_date_source=NOT_SHOWN" in canonical_engine.core.PROMPT


def test_primary_exam_date_requires_exact_four_maps_source_identifier():
    result = {
        "eyes": [{"eye": "OD", "screen_types": ["FOUR_MAPS_REFRACTIVE"]}],
    }
    exact = canonical_engine.core.enforce_exam_date_source_lock(result, {
        "exam_date": "03/09/2026",
        "exam_date_source": "FOUR_MAPS_REFRACTIVE_UPPER_LEFT_EXAM_DATE",
        "missing_or_unreadable": [],
    })
    assert exact["exam_date"] == "03/09/2026"

    wrong_source = canonical_engine.core.enforce_exam_date_source_lock(result, {
        "exam_date": "03/09/2025",
        "exam_date_source": "NOT_SHOWN",
        "missing_or_unreadable": [],
    })
    assert wrong_source["exam_date"] is None

    other_page = canonical_engine.core.enforce_exam_date_source_lock({
        "eyes": [{"eye": "OD", "screen_types": ["BAD_DISPLAY"]}],
    }, {
        "exam_date": "03/09/2026",
        "exam_date_source": "FOUR_MAPS_REFRACTIVE_UPPER_LEFT_EXAM_DATE",
        "missing_or_unreadable": [],
    })
    assert other_page["exam_date"] is None


def test_primary_schema_requires_exam_date_source_provenance():
    context_schema = canonical_engine.core.SCHEMA["properties"]["document_context"]
    assert "exam_date_source" in context_schema["required"]
    assert context_schema["properties"]["exam_date_source"]["enum"] == [
        "FOUR_MAPS_REFRACTIVE_UPPER_LEFT_EXAM_DATE", "UNREADABLE", "NOT_SHOWN",
    ]


def test_surrogate_age_reread_is_skipped_when_surgeon_age_was_supplied(monkeypatch):
    result = pentacam_result()
    result["document_context"].pop("patient_age_years", None)

    def unexpected_reread(*_args, **_kwargs):
        raise AssertionError("surgeon-entered age must suppress patient-age OCR")

    monkeypatch.setattr(targeted, "targeted_reread", unexpected_reread)
    assert targeted.enrich_extraction(
        Core, result, b"image", "od-four-maps.png", seek_patient_age=False,
    ) is result


PENTACAM_SOURCE_LOCK_RETIRED_TARGETED_TESTS = tuple(sorted(_RETIRED))
del _name, _value
