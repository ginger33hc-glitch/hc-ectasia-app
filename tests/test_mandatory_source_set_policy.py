import pytest
from fastapi import HTTPException

import mandatory_source_set_policy as policy


def result(screen_type, eye=None, document_type="PENTACAM_TOPOGRAPHY"):
    eyes = [] if eye is None else [{"eye": eye, "screen_types": [screen_type]}]
    return {
        "document_context": {"document_type": document_type},
        "eyes": eyes,
        "treatment_corrections": [],
    }


def complete_set(include_card=False):
    items = [
        result("FOUR_MAPS_REFRACTIVE", "OD"),
        result("FOUR_MAPS_REFRACTIVE", "OS"),
        result("BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY", "OD"),
        result("BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY", "OS"),
        result("SHOW_2_EXAMS_TOPOMETRIC", "OD"),
    ]
    if include_card:
        items.append(result("EXCIMER_LASER_TREATMENT_CARD", None, "TREATMENT_CARD"))
    return items


def test_five_mandatory_images_are_accepted_without_treatment_card():
    summary = policy.validate_source_set(complete_set(False))
    assert summary["mandatory_count"] == 5
    assert summary["missing"] == []
    assert summary["uploaded_count"] == 5


def test_optional_treatment_card_makes_six_images_and_is_accepted():
    summary = policy.validate_source_set(complete_set(True))
    assert summary["mandatory_count"] == 5
    assert summary["treatment_card_count"] == 1
    assert summary["uploaded_count"] == 6


def test_missing_mandatory_image_stops_before_assessment():
    items = complete_set(False)
    items.pop(3)  # OS BAD Display
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert exc.value.status_code == 422
    assert "Assessment not started" in exc.value.detail
    assert "OS Belin/Ambrosio Display" in exc.value.detail


def test_duplicate_page_does_not_substitute_for_missing_page():
    items = complete_set(False)
    items[3] = result("FOUR_MAPS_REFRACTIVE", "OS")
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert "OS Belin/Ambrosio Display" in exc.value.detail


def test_more_than_six_images_is_rejected():
    items = complete_set(True) + [result("FOUR_MAPS_REFRACTIVE", "OD")]
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert exc.value.status_code == 422
    assert "at most 6 images" in exc.value.detail
