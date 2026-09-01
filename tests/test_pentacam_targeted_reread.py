import base64
from io import BytesIO
import json
from types import SimpleNamespace

from PIL import Image

import pentacam_targeted_reread as targeted


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
):
    return {
        "eye": eye,
        "field": field,
        "value": value,
        "status": status,
        "printed_label": label,
        "group_label": group,
        "source_tile": tile,
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
