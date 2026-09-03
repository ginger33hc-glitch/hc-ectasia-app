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


def test_legacy_bad_component_signature_recognizes_od_page_even_if_screen_type_is_imperfect():
    legacy_bad = {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "laterality": "OD",
        },
        "eyes": [
            {
                "eye": "OD",
                "screen_types": ["PENTACAM_TOPOGRAPHY"],
                "table_verified_numeric_fields": ["Df", "Db", "Dp", "Dt", "Da"],
                "Df": -0.93,
                "Db": 0.73,
                "Dp": 0.47,
                "Dt": -0.56,
                "Da": 0.41,
            }
        ],
        "treatment_corrections": [],
    }
    summary = policy.classify_source_set([legacy_bad])
    assert summary["present"]["OD Belin/Ambrosio Display"] is True


def test_mandatory_install_adds_explicit_legacy_bad_display_recognition_prompt(monkeypatch):
    class Core:
        PROMPT = "base"
        merge_extractions = staticmethod(lambda results: {})

        async def _run_image_assessment(self, *args, **kwargs):
            return None

    core = Core()
    monkeypatch.setattr(policy, "_previous_merge_extractions", None)
    monkeypatch.setattr(policy, "_previous_run_image_assessment", None)
    policy.install(core)
    assert "Belin/Ambrosio Display" in core.PROMPT
    assert "BELIN_AMBROSIO_DISPLAY" in core.PROMPT
