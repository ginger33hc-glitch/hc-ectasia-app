from io import BytesIO
from types import SimpleNamespace
from time import monotonic

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import assessment_workflow
from pentacam_source_regions import region_hint


def extracted_with_eyes():
    return {
        "eyes": [
            {
                "eye": "OD",
                "erss_topography_sources": [{
                    "file": "od-four-maps.png",
                    "map_type": "AXIAL_SAGITTAL_FRONT",
                    "map_location": "UPPER_LEFT",
                    "reader": "DEDICATED_CURVATURE_PASS",
                    "morphology_confidence": "UNREADABLE",
                }],
            },
            {
                "eye": "OS",
                "erss_topography_sources": [{
                    "file": "os-four-maps.png",
                    "map_type": "AXIAL_SAGITTAL_FRONT",
                    "map_location": "UPPER_LEFT",
                    "reader": "DEDICATED_CURVATURE_PASS",
                    "morphology_confidence": "LOW",
                }],
            },
        ]
    }


def image_bytes(width=1000, height=800):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


def test_morphology_completion_points_to_eye_specific_upper_left_axial_map():
    extracted = extracted_with_eyes()
    od = region_hint(extracted, "OD", "surgeon_topography_category")
    os = region_hint(extracted, "OS", "surgeon_topography_category")
    assert od == {
        "file": "od-four-maps.png",
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    }
    assert os["file"] == "os-four-maps.png"
    assert os["file"] != od["file"]


def test_topography_request_carries_source_region_without_changing_form_contract():
    item = assessment_workflow._request(
        "OD", "Topography morphology category is required", extracted_with_eyes()
    )
    assert item["kind"] == "form"
    assert item["key"] == "surgeon_topography_category"
    assert item["form_id"] == "od_surgeon_topography"
    assert item["source_region"] is True


def test_unknown_or_cross_eye_morphology_source_is_not_shown():
    extracted = extracted_with_eyes()
    extracted["eyes"][0]["erss_topography_sources"] = [{
        "file": "od-four-maps.png",
        "map_type": "ELEVATION_BACK",
        "map_location": "LOWER_RIGHT",
        "morphology_confidence": "UNREADABLE",
    }]
    assert region_hint(extracted, "OD", "surgeon_topography_category") is None
    assert region_hint(extracted, "OU", "surgeon_topography_category") is None


def test_exact_extractor_box_precedes_canonical_map_panel():
    extracted = extracted_with_eyes()
    exact = {
        "file": "od-detail.png",
        "tile": "UPPER_LEFT",
        "source_box": [100, 200, 600, 500],
        "printed_label": "I-S",
    }
    extracted["eyes"][0]["unreadable_source_regions"] = {"I_S": exact}
    assert region_hint(extracted, "OD", "surgeon_I_S_D") == exact


def test_legacy_region_snapshot_remains_readable_without_becoming_primary_contract():
    extracted = extracted_with_eyes()
    legacy = {
        "file": "od-legacy.png",
        "tile": "LOWER_RIGHT",
        "source_box": [100, 200, 700, 500],
        "printed_label": "PPI Max",
    }
    extracted["eyes"][0]["targeted_unreadable_regions"] = {"PPI_max": legacy}
    assert region_hint(extracted, "OD", "PPI_max") == legacy


def test_pattern_region_requires_one_eye_specific_provenance_file():
    extracted = extracted_with_eyes()
    extracted["eyes"][0]["field_provenance"] = {
        "posterior_pattern": [{"file": "od-four-maps.png"}],
    }
    hint = region_hint(extracted, "OD", "posterior_pattern")
    assert hint["file"] == "od-four-maps.png"
    assert hint["printed_label"].startswith("Elevation (Back)")
    extracted["eyes"][0]["field_provenance"]["posterior_pattern"].append(
        {"file": "od-other.png"}
    )
    assert region_hint(extracted, "OD", "posterior_pattern") is None


def test_generic_unread_regions_survive_multi_image_merge():
    import app

    region = {
        "file": "od-detail.png",
        "tile": "LOWER_LEFT",
        "source_box": [120, 200, 720, 520],
        "printed_label": "ARTmax",
    }
    first = {"eyes": [{"eye": "OD"}], "global_warnings": []}
    second = {
        "eyes": [{"eye": "OD", "unreadable_source_regions": {"ARTmax_um": region}}],
        "global_warnings": [],
    }
    merged = app.merge_extractions([first, second])
    assert merged["eyes"][0]["unreadable_source_regions"]["ARTmax_um"] == region


def test_morphology_source_endpoint_renders_the_canonical_panel():
    token = "synthetic-morphology-source-region-session"
    extracted = extracted_with_eyes()
    assessment_workflow._sessions[token] = {
        "extracted": extracted,
        "expires": monotonic() + 60,
        "ready": None,
        "source_images": [(image_bytes(), "od-four-maps.png")],
        "region_requests": {("OD", "surgeon_topography_category")},
    }
    core = SimpleNamespace(app=FastAPI())
    assessment_workflow.install(core)
    try:
        response = TestClient(core.app).post(
            "/assessment/source-region",
            json={
                "assessment_token": token,
                "eye": "OD",
                "key": "surgeon_topography_category",
            },
        )
    finally:
        assessment_workflow._sessions.pop(token, None)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    with Image.open(BytesIO(response.content)) as region:
        assert region.format == "PNG"
        assert region.width < 600
        assert region.height < 600
