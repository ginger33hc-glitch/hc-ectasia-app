import base64
from io import BytesIO
import json
from types import SimpleNamespace
from time import monotonic

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
import pytest

import assessment_workflow
import pentacam_targeted_reread as targeted


def test_completion_requests_only_manifest_when_intended_is_wholly_blank():
    missing = [
        ("OD", "preoperative manifest sphere for LASIK ERSS MRSE"),
        ("OD", "preoperative manifest cylinder magnitude for LASIK ERSS MRSE"),
        ("OD", "intended sphere"),
        ("OD", "intended cylinder magnitude"),
    ]
    plans = {"OD": {
        "manifest_entered_sphere_D": None,
        "manifest_cylinder_signed_D": None,
        "intended_entered_sphere_D": None,
        "intended_cylinder_signed_D": None,
    }}
    assert assessment_workflow.completion_items(missing, plans) == missing[:2]

    plans["OD"]["intended_entered_sphere_D"] = -2.0
    assert assessment_workflow.completion_items(missing, plans) == missing


class Core:
    MODEL = "gpt-5.6-terra"

    @staticmethod
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def data_url(raw, filename):
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def image_bytes(width=1000, height=800):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


def pentacam_result(**values):
    eye = {
        "eye": "OD",
        "screen_types": ["PENTACAM_BAD_DISPLAY"],
        "keratometry_source": "NOT_SHOWN",
        "table_verified_numeric_fields": [],
        "missing_or_unreadable": list(targeted.TARGET_FIELDS),
    }
    eye.update({field: None for field in targeted.TARGET_FIELDS})
    eye.update(values)
    return {
        "document_context": {"document_type": "PENTACAM_TOPOGRAPHY"},
        "eyes": [eye],
        "global_warnings": [],
    }


def reading(
    field, value, label, *, eye="OD", status="CONFIDENT", tile="LOWER_RIGHT", group=None,
    source_box=None,
):
    return {
        "eye": eye,
        "field": field,
        "value": value,
        "status": status,
        "printed_label": label,
        "group_label": group,
        "source_tile": tile,
        "source_box": source_box,
    }


def test_tiles_cover_source_with_overlap_and_are_valid_png_images():
    tiles = targeted.build_overlapping_tiles(image_bytes())
    assert [name for name, _ in tiles] == [
        "UPPER_LEFT", "UPPER_RIGHT", "LOWER_LEFT", "LOWER_RIGHT",
    ]
    sizes = []
    for _, raw in tiles:
        with Image.open(BytesIO(raw)) as tile:
            sizes.append(tile.size)
            assert tile.format == "PNG"
    assert sizes == [(580, 464)] * 4
    assert sizes[0][0] * 2 > 1000
    assert sizes[0][1] * 2 > 800


def test_only_null_fields_are_requested_and_non_pentacam_is_ignored():
    result = pentacam_result(ARTmax_um=401.0, PPI_max=None)
    requested = targeted.missing_targets_by_eye(result)
    assert "PPI_max" in requested["OD"]
    assert "ARTmax_um" not in requested["OD"]
    result["document_context"]["document_type"] = "TREATMENT_CARD"
    result["eyes"][0]["screen_types"] = ["TREATMENT_CARD"]
    assert targeted.missing_targets_by_eye(result) == {}


def test_targeted_reread_does_not_seek_keratometry_on_other_pentacam_screens():
    result = pentacam_result()
    missing = targeted.missing_targets_by_eye(result)["OD"]
    assert not set(targeted.CORNEA_FRONT_KERATOMETRY_FIELDS) & set(missing)

    result["eyes"][0]["keratometry_source"] = (
        "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
    )
    missing = targeted.missing_targets_by_eye(result)["OD"]
    assert set(targeted.CORNEA_FRONT_KERATOMETRY_FIELDS) <= set(missing)


def test_landmark_labels_and_existing_central_reading_control_targets():
    assert targeted.label_supports_field("pachy_thinnest_um", "Thinnest Locat.")
    assert not targeted.label_supports_field("pachy_thinnest_um", "Pachy Vertex N.")
    assert not targeted.label_supports_field("pachy_thinnest_um", "Corneal Thickness 521")
    assert targeted.label_supports_field("central_pachy_um", "Pupil Center +")
    assert not targeted.label_supports_field("central_pachy_um", "Pachy Vertex N.")
    assert targeted.label_supports_field("Kmax_D", "KMax")
    assert targeted.label_supports_field("Kmean_D", "Km")
    assert targeted.label_supports_field("ARTmax_um", "ARTmax")
    assert targeted.label_supports_field("B_Ele_Th_um", "B. Ele.Th")
    assert not targeted.label_supports_field("B_Ele_Th_um", "Elevation (Back)")
    assert targeted.label_supports_field("corneal_diameter_mm", "HWTW")
    assert not targeted.label_supports_field("corneal_diameter_mm", "HTWT")

    result = pentacam_result()
    assert "central_pachy_um" in targeted.missing_targets_by_eye(result)["OD"]
    result["nice_readings"] = [{
        "eye": "OD", "central_pachy_um": 542, "central_status": "CONFIDENT",
        "central_landmark": "PUPIL_CENTER_PLUS",
    }]
    assert "central_pachy_um" not in targeted.missing_targets_by_eye(result)["OD"]


def test_targeted_keratometry_requires_show2_screen_and_cornea_front_group():
    result = pentacam_result()
    requested = {"OD": ["K1_D", "Kmean_D"]}
    wrong_screen = {
        "screen_family": "TOPOMETRIC_KC",
        "readings": [reading("K1_D", 49.0, "K1", group="Cornea Front")],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, wrong_screen, requested, "other.jpg")
    assert result["eyes"][0]["K1_D"] is None

    wrong_panel = {
        "screen_family": "SHOW_2_EXAMS_TOPOMETRIC",
        "readings": [reading("K1_D", 48.0, "K1", group="True Net Power")],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, wrong_panel, requested, "show2.jpg")
    assert result["eyes"][0]["K1_D"] is None

    canonical = {
        "screen_family": "SHOW_2_EXAMS_TOPOMETRIC",
        "readings": [
            reading("K1_D", 42.1, "K1", group="Cornea Front"),
            reading("Kmean_D", 42.4, "Km", group="Cornea Front"),
        ],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, canonical, requested, "show2.jpg")
    eye = result["eyes"][0]
    assert eye["K1_D"] == 42.1
    assert eye["Kmean_D"] == 42.4
    assert eye["keratometry_source"] == "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"


def test_only_canonical_b_ele_th_reading_suppresses_targeted_reread():
    result = pentacam_result()
    assert "B_Ele_Th_um" in targeted.missing_targets_by_eye(result)["OD"]
    result["nice_readings"] = [{
        "eye": "OD",
        "B_Ele_Th_um": 23,
        "b_ele_th_status": "CONFIDENT",
        "b_ele_th_landmark": "B_ELE_TH_LABELED_BOX",
        "b_ele_th_page": "BAD_DISPLAY",
    }]
    assert "B_Ele_Th_um" not in targeted.missing_targets_by_eye(result)["OD"]
    result["nice_readings"][0]["b_ele_th_landmark"] = "OTHER"
    assert "B_Ele_Th_um" in targeted.missing_targets_by_eye(result)["OD"]


def test_patient_age_request_is_patient_level_and_only_for_pentacam():
    result = pentacam_result()
    result["document_context"]["patient_age_years"] = None
    assert targeted.patient_age_is_missing(result)
    result["document_context"]["patient_age_years"] = 42
    assert not targeted.patient_age_is_missing(result)
    result["document_context"]["document_type"] = "TREATMENT_CARD"
    assert not targeted.patient_age_is_missing(result)


def test_confident_labeled_patient_age_fills_context_once_and_records_evidence():
    result = pentacam_result()
    result["document_context"].update(
        patient_age_years=None,
        missing_or_unreadable=["patient_age_years"],
    )
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [],
        "patient_age_reading": {
            "value": 61,
            "status": "CONFIDENT",
            "printed_label": "Age [y]",
            "source_tile": "TOP_HEADER",
        },
        "warnings": [],
    }
    output = targeted.apply_targeted_readings(
        Core, result, reread, {}, "od.png", patient_age_requested=True
    )
    context = output["document_context"]
    assert context["patient_age_years"] == 61
    assert context["targeted_age_reread_evidence"] == {
        "file": "od.png",
        "source": "TARGETED_PENTACAM_DEMOGRAPHIC_REREAD",
        "tile": "TOP_HEADER",
        "printed_label": "Age [y]",
        "value": 61,
    }
    assert "patient_age_years" not in context["missing_or_unreadable"]


def test_patient_age_rejects_dob_or_implausible_value_and_never_overwrites():
    for label, value in (("Date of Birth", 61), ("Age", 17), ("Age", 121)):
        result = pentacam_result()
        result["document_context"]["patient_age_years"] = None
        reread = {
            "screen_family": "BAD_DISPLAY",
            "readings": [],
            "patient_age_reading": {
                "value": value,
                "status": "CONFIDENT",
                "printed_label": label,
                "source_tile": "TOP_HEADER",
            },
            "warnings": [],
        }
        targeted.apply_targeted_readings(
            Core, result, reread, {}, "od.png", patient_age_requested=True
        )
        assert result["document_context"]["patient_age_years"] is None

    result = pentacam_result()
    result["document_context"]["patient_age_years"] = 60
    reread["patient_age_reading"].update(value=61, printed_label="Age")
    targeted.apply_targeted_readings(
        Core, result, reread, {}, "od.png", patient_age_requested=True
    )
    assert result["document_context"]["patient_age_years"] == 60


def test_confident_labeled_reread_fills_only_requested_null_and_records_evidence():
    result = pentacam_result(ARTmax_um=399.0)
    requested = {"OD": ["PPI_max"]}
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading("PPI_max", 1.42, "PPI Max"),
            reading("ARTmax_um", 350.0, "ARTmax"),
        ],
        "warnings": [],
    }
    output = targeted.apply_targeted_readings(Core, result, reread, requested, "od.png")
    eye = output["eyes"][0]
    assert eye["PPI_max"] == 1.42
    assert eye["ARTmax_um"] == 399.0
    assert "PPI_max" in eye["table_verified_numeric_fields"]
    assert "PPI_max" not in eye["missing_or_unreadable"]
    assert eye["targeted_reread_evidence"]["PPI_max"] == [{
        "file": "od.png",
        "source": "TARGETED_LABELED_TILE_REREAD",
        "tile": "LOWER_RIGHT",
        "printed_label": "PPI Max",
        "group_label": None,
        "value": 1.42,
    }]


def test_uncertain_wrong_eye_and_ambiguous_label_are_never_accepted():
    result = pentacam_result()
    requested = {"OD": ["PPI_max", "ARTmax_um", "I_S"]}
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading("PPI_max", 1.2, "PPI Max", status="UNCERTAIN"),
            reading("ARTmax_um", 400, "ARTmax", eye="OS"),
            reading("I_S", 1.1, "ISV"),
        ],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, reread, requested, "od.png")
    eye = result["eyes"][0]
    assert eye["PPI_max"] is None
    assert eye["ARTmax_um"] is None
    assert eye["I_S"] is None
    assert any("rejected OD I_S" in warning for warning in result["global_warnings"])


def test_conflicting_confident_rereads_leave_field_empty():
    result = pentacam_result()
    requested = {"OD": ["PPI_max"]}
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [
            reading("PPI_max", 1.42, "PPI Max", tile="LOWER_LEFT"),
            reading("PPI_max", 1.24, "PPI Max", tile="LOWER_RIGHT"),
        ],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, reread, requested, "od.png")
    assert result["eyes"][0]["PPI_max"] is None
    assert any("reread conflict" in warning for warning in result["global_warnings"])


def test_unreadable_labeled_field_records_localized_completion_region():
    result = pentacam_result()
    requested = {"OD": ["PPI_max"]}
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading(
            "PPI_max", None, "PPI Max", status="UNREADABLE",
            source_box=[100, 200, 700, 500],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, reread, requested, "od.png")
    assert result["eyes"][0]["PPI_max"] is None
    assert result["eyes"][0]["unreadable_source_regions"]["PPI_max"] == {
        "file": "od.png",
        "tile": "LOWER_RIGHT",
        "source_box": [100, 200, 700, 500],
        "printed_label": "PPI Max",
    }


def test_pupil_center_reread_feeds_nice_and_unreadable_region_reaches_form():
    result = pentacam_result()
    requested = {"OD": ["central_pachy_um"]}
    confident = {
        "screen_family": "PACHYMETRY",
        "readings": [reading(
            "central_pachy_um", 548, "Pupil Center +", tile="UPPER_RIGHT",
            source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, confident, requested, "od.png")
    assert result["nice_readings"][-1]["central_pachy_um"] == 548
    assert result["nice_readings"][-1]["central_status"] == "CONFIDENT"
    assert result["nice_readings"][-1]["central_landmark"] == "PUPIL_CENTER_PLUS"
    assert result["eyes"][0]["central_pachy_um"] is None

    unreadable = pentacam_result()
    reread = {
        "screen_family": "PACHYMETRY",
        "readings": [reading(
            "central_pachy_um", None, "Pupil Center +", status="UNREADABLE",
            tile="UPPER_RIGHT", source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, unreadable, reread, requested, "od.png")
    item = assessment_workflow._request("OD", "NICE: central_pachy_um", unreadable)
    assert item["source_region"] is True
    assert item["form_id"] == "od_nice_central"


def test_bad_display_b_ele_th_box_feeds_only_nice_posterior_input():
    result = pentacam_result()
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading(
            "B_Ele_Th_um", 23, "B. Ele.Th", tile="LOWER_LEFT",
            source_box=[120, 120, 880, 320],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {"OD": ["B_Ele_Th_um"]}, "od.png"
    )
    nice = result["nice_readings"][-1]
    assert nice["B_Ele_Th_um"] == 23
    assert nice["b_ele_th_status"] == "CONFIDENT"
    assert nice["b_ele_th_landmark"] == "B_ELE_TH_LABELED_BOX"
    assert nice["b_ele_th_page"] == "BAD_DISPLAY"
    assert nice["central_pachy_um"] is None
    assert nice["central_landmark"] == "UNREADABLE"
    assert result["eyes"][0]["targeted_reread_evidence"]["B_Ele_Th_um"][0]["source"] == "TARGETED_LABELED_TILE_REREAD"


def test_elevation_back_map_cannot_substitute_for_b_ele_th_box():
    result = pentacam_result()
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "B_Ele_Th_um", 23, "Elevation (Back)", tile="LOWER_RIGHT",
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {"OD": ["B_Ele_Th_um"]}, "od.png"
    )
    assert not result.get("nice_readings")
    assert any("verified BAD Display" in warning for warning in result["global_warnings"])


def test_unreadable_b_ele_th_box_region_is_shown_beside_surgeon_input():
    result = pentacam_result()
    reread = {
        "screen_family": "BAD_DISPLAY",
        "readings": [reading(
            "B_Ele_Th_um", None, "B. Ele.Th", status="UNREADABLE",
            tile="LOWER_LEFT", source_box=[120, 120, 880, 320],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {"OD": ["B_Ele_Th_um"]}, "od.png"
    )
    assert not result.get("nice_readings")
    region = result["eyes"][0]["unreadable_source_regions"]["B_Ele_Th_um"]
    assert region == {
        "file": "od.png",
        "tile": "LOWER_LEFT",
        "source_box": [120, 120, 880, 320],
        "printed_label": "B. Ele.Th",
    }
    item = assessment_workflow._request("OD", "NICE: B_Ele_Th_um", result)
    assert item["source_region"] is True
    assert item["form_id"] == "od_nice_pe"


def test_circle_marked_thinnest_location_is_retained_as_labeled_row():
    result = pentacam_result()
    reread = {
        "screen_family": "PACHYMETRY",
        "readings": [reading(
            "pachy_thinnest_um", 501, "Thinnest Locat.", tile="LOWER_RIGHT",
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


def test_source_region_renderer_returns_tight_png_crop():
    raw = image_bytes(1000, 800)
    rendered = targeted.render_source_region(
        raw, "LOWER_RIGHT", [100, 200, 700, 500]
    )
    with Image.open(BytesIO(rendered)) as region:
        assert region.format == "PNG"
        assert region.width < 580
        assert region.height < 464


def test_source_region_endpoint_uses_opaque_post_body_and_no_store_cache():
    token = "synthetic-source-region-session"
    extracted = pentacam_result()
    extracted["eyes"][0]["unreadable_source_regions"] = {
        "PPI_max": {
            "file": "od.png",
            "tile": "LOWER_RIGHT",
            "source_box": [100, 200, 700, 500],
            "printed_label": "PPI Max",
        }
    }
    assessment_workflow._sessions[token] = {
        "extracted": extracted,
        "expires": monotonic() + 60,
        "ready": None,
        "source_images": [(image_bytes(), "od.png")],
        "region_requests": {("OD", "PPI_max")},
    }
    core = SimpleNamespace(app=FastAPI())
    assessment_workflow.install(core)
    try:
        response = TestClient(core.app).post(
            "/assessment/source-region",
            json={"assessment_token": token, "eye": "OD", "key": "PPI_max"},
        )
    finally:
        assessment_workflow._sessions.pop(token, None)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    with Image.open(BytesIO(response.content)) as region:
        assert region.format == "PNG"


def test_grouped_progression_heading_supports_plain_max_label_but_not_plain_max_alone():
    assert targeted.label_supports_field("PPI_max", "Max", "Progression Index")
    assert not targeted.label_supports_field("PPI_max", "Max", None)
    assert targeted.label_supports_field("K1_axis_deg", "K1 @", None)
    assert not targeted.label_supports_field("K1_axis_deg", "K1", None)


def test_targeted_call_uses_original_and_four_crops_with_focused_settings(monkeypatch):
    captured = {}
    payload = {"screen_family": "BAD_DISPLAY", "readings": [], "warnings": []}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=json.dumps(payload))

    core = Core()
    core.openai_client = lambda: SimpleNamespace(responses=SimpleNamespace(create=create))
    result = targeted.targeted_reread(core, image_bytes(), "od.png", {"OD": ["PPI_max"]})
    assert result == payload
    content = captured["input"][0]["content"]
    images = [item for item in content if item["type"] == "input_image"]
    assert len(images) == 5
    assert all(item["detail"] == "original" for item in images)
    assert captured["reasoning"] == {"effort": "medium"}
    assert captured["text"]["verbosity"] == "high"
    assert captured["text"]["format"]["strict"] is True


def test_targeted_call_states_b_ele_th_bad_display_box_only_rule(monkeypatch):
    captured = {}
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [],
        "patient_age_reading": {
            "value": None, "status": "NOT_SHOWN", "printed_label": None,
            "source_tile": "ORIGINAL", "source_box": None,
        },
        "warnings": [],
    }

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=json.dumps(payload))

    core = Core()
    core.openai_client = lambda: SimpleNamespace(responses=SimpleNamespace(create=create))
    targeted.targeted_reread(core, image_bytes(), "od.png", {"OD": ["B_Ele_Th_um"]})
    prompt = captured["input"][0]["content"][0]["text"]
    assert "explicitly printed \"B. Ele.Th\" box" in prompt
    assert "Never use an Elevation (Back) map" in prompt
    assert "B_Ele_Th_um" in prompt


def test_age_reread_adds_dedicated_top_header_crop(monkeypatch):
    captured = {}
    payload = {
        "screen_family": "BAD_DISPLAY",
        "readings": [],
        "patient_age_reading": {
            "value": None,
            "status": "UNREADABLE",
            "printed_label": "Age",
            "source_tile": "TOP_HEADER",
        },
        "warnings": [],
    }

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=json.dumps(payload))

    core = Core()
    core.openai_client = lambda: SimpleNamespace(responses=SimpleNamespace(create=create))
    targeted.targeted_reread(core, image_bytes(), "od.png", {}, True)
    content = captured["input"][0]["content"]
    images = [item for item in content if item["type"] == "input_image"]
    assert len(images) == 6
    assert "patient_age_years is requested" in content[0]["text"]


def test_targeted_qs_reread_accepts_only_explicit_labeled_ok_and_updates_eye():
    result = pentacam_result()
    result["document_context"]["pentacam_qs"] = "UNREADABLE"
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [],
        "pentacam_qs_reading": {
            "value": "OK",
            "status": "CONFIDENT",
            "printed_label": "QS",
            "source_tile": "UPPER_LEFT",
            "source_box": [40, 300, 250, 430],
        },
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {}, "od.png", pentacam_qs_requested=True
    )
    assert result["document_context"]["pentacam_qs"] == "OK"
    assert result["eyes"][0]["_pentacam_qs"] == "OK"
    assert result["document_context"]["targeted_qs_reread_evidence"]["file"] == "od.png"


def test_unreadable_labeled_qs_is_retained_as_nonblocking_warning_source():
    result = pentacam_result()
    result["document_context"]["pentacam_qs"] = "UNREADABLE"
    result["document_contexts"] = [{
        "document_type": "PENTACAM_TOPOGRAPHY",
        "source_filename": "od.png",
        "pentacam_qs": "UNREADABLE",
    }]
    result["critical_input_issues"] = [
        "Pentacam acquisition requires a same-exam explicit QS: OK; a non-OK QS cannot be overridden."
    ]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [],
        "pentacam_qs_reading": {
            "value": None,
            "status": "UNREADABLE",
            "printed_label": "QS",
            "source_tile": "UPPER_LEFT",
            "source_box": [40, 300, 250, 430],
        },
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {}, "od.png", pentacam_qs_requested=True
    )
    assert result["eyes"][0]["unreadable_source_regions"]["pentacam_qs"]["file"] == "od.png"
    decision = {"critical_input_issues": result["critical_input_issues"], "eyes": [{"eye": "OD", "missing": ["explicit Pentacam QS: OK"]}]}
    assert assessment_workflow.missing_items(decision) == []


def test_qs_cannot_be_manually_rewritten_even_though_it_no_longer_blocks():
    result = pentacam_result()
    result["eyes"][0]["unreadable_source_regions"] = {
        "pentacam_qs": {
            "file": "od.png", "tile": "UPPER_LEFT",
            "source_box": [40, 300, 250, 430], "printed_label": "QS",
        }
    }
    result["document_contexts"] = [{
        "document_type": "PENTACAM_TOPOGRAPHY",
        "source_filename": "od.png",
        "pentacam_qs": "NOT_OK",
    }]
    with pytest.raises(Exception, match="Manual override"):
        assessment_workflow._overrides(result, {"OD": {"pentacam_qs": "OK"}})


def test_wrapper_runs_for_missing_age_even_when_no_eye_numeric_field_is_missing(monkeypatch):
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
        },
        "warnings": [],
    }
    monkeypatch.setattr(targeted, "targeted_reread", lambda *args: payload)
    wrapper = targeted.make_targeted_extractor(Core, lambda raw, filename: original)
    output = wrapper(image_bytes(), "od.png")
    assert output["document_context"]["patient_age_years"] == 61


def test_wrapper_fails_open_to_original_extraction_when_crop_decode_fails(monkeypatch):
    original = pentacam_result()
    wrapper = targeted.make_targeted_extractor(Core, lambda raw, filename: original)
    output = wrapper(b"not-an-image", "od.png")
    assert output is original
    assert any("original extraction retained" in warning for warning in output["global_warnings"])


def test_targeted_tile_evidence_survives_canonical_merge():
    import canonical_engine
    from tests.test_hc_engine import normal_eye

    eye = normal_eye()
    eye["PPI_max"] = 1.42
    eye["table_verified_numeric_fields"] = sorted(
        set(eye["table_verified_numeric_fields"]) | {"PPI_max"}
    )
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
    extraction = {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_first_name": "Test",
            "patient_last_name": "Patient",
            "patient_name": "Test Patient",
            "patient_id": "P-1",
            "exam_date": "2026-09-01",
            "source_filename": "od-bad.png",
        },
        "eyes": [eye],
        "treatment_corrections": [],
        "laser_plans": [],
        "global_warnings": [],
    }
    merged_eye = canonical_engine.core.merge_extractions([extraction])["eyes"][0]
    assert merged_eye["field_provenance"]["PPI_max"] == eye["targeted_reread_evidence"]["PPI_max"]
