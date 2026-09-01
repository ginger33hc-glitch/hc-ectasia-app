import base64
from io import BytesIO
import json
from types import SimpleNamespace
from time import monotonic

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

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
    assert result["eyes"][0]["targeted_unreadable_regions"]["PPI_max"] == {
        "file": "od.png",
        "tile": "LOWER_RIGHT",
        "source_box": [100, 200, 700, 500],
        "printed_label": "PPI Max",
    }


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
    extracted["eyes"][0]["targeted_unreadable_regions"] = {
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
