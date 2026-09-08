from contextlib import asynccontextmanager
import asyncio

import pytest
from fastapi import HTTPException

import app
import assessment_workflow
import canonical_engine
import mandatory_source_set_policy as policy
import operational_security


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
    assert summary["confirmed"] is True
    assert all(item["present"] for item in summary["required_sources"])
    assert summary["optional_treatment_card"] == {
        "label": "Excimer laser treatment card", "present": False, "count": 0,
    }


def test_optional_treatment_card_makes_six_images_and_is_accepted():
    summary = policy.validate_source_set(complete_set(True))
    assert summary["mandatory_count"] == 5
    assert summary["treatment_card_count"] == 1
    assert summary["uploaded_count"] == 6
    assert summary["optional_treatment_card"]["present"] is True


def test_missing_mandatory_image_stops_before_assessment():
    items = complete_set(False)
    items.pop(3)  # OS BAD Display
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "MANDATORY_SOURCE_SET_INCOMPLETE"
    assert "Assessment not started" in exc.value.detail["message"]
    assert "OS Belin/Ambrosio Display" in exc.value.detail["message"]
    assert exc.value.detail["source_set"]["confirmed"] is False


def test_duplicate_page_does_not_substitute_for_missing_page():
    items = complete_set(False)
    items[3] = result("FOUR_MAPS_REFRACTIVE", "OS")
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert "OS Belin/Ambrosio Display" in exc.value.detail["message"]


def test_more_than_six_images_is_rejected():
    items = complete_set(True) + [result("FOUR_MAPS_REFRACTIVE", "OD")]
    with pytest.raises(HTTPException) as exc:
        policy.validate_source_set(items)
    assert exc.value.status_code == 422
    assert "at most 6 images" in exc.value.detail


def complete_refraction_plans():
    return {
        eye: {
            "manifest_entered_sphere_D": -2.0,
            "manifest_cylinder_signed_D": -1.0,
            "intended_entered_sphere_D": -2.0,
            "intended_cylinder_signed_D": -1.0,
            "entered_axis_deg": 90.0,
        }
        for eye in ("OD", "OS")
    }


def test_absent_treatment_card_requires_complete_manual_refraction_before_assessment():
    plans = complete_refraction_plans()
    plans["OS"]["intended_entered_sphere_D"] = None
    with pytest.raises(HTTPException) as exc:
        policy.validate_preassessment_requirements(complete_set(False), plans)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "PREASSESSMENT_REFRACTION_REQUIRED"
    assert exc.value.detail["source_set"]["confirmed"] is True
    assert exc.value.detail["source_set"]["optional_treatment_card"]["present"] is False
    assert exc.value.detail["missing_refraction"] == [{
        "eye": "OS", "field": "intended_entered_sphere_D",
        "form_id": "os_sphere", "label": "OS intended sphere",
    }]


def test_absent_card_accepts_complete_bilateral_manifest_and_intended_refraction():
    summary = policy.validate_preassessment_requirements(
        complete_set(False), complete_refraction_plans()
    )
    assert summary["manual_refraction"] == {
        "required": True, "complete": True, "missing": [],
    }


def test_present_card_defers_refraction_resolution_to_canonical_card_adapter():
    summary = policy.validate_preassessment_requirements(complete_set(True), {})
    assert summary["manual_refraction"] == {
        "required": False, "complete": True, "missing": [],
    }


def test_zero_cylinders_do_not_require_an_axis_at_the_intake_gate():
    plans = complete_refraction_plans()
    for plan in plans.values():
        plan["manifest_cylinder_signed_D"] = 0.0
        plan["intended_cylinder_signed_D"] = 0.0
        plan["entered_axis_deg"] = None
    summary = policy.validate_preassessment_requirements(complete_set(False), plans)
    assert summary["manual_refraction"]["complete"] is True


@pytest.mark.parametrize("missing_source", [True, False])
def test_source_or_no_card_refraction_failure_prevents_all_enrichment(
    monkeypatch, missing_source,
):
    sources = complete_set(False)
    if missing_source:
        sources.pop(3)
        plans = complete_refraction_plans()
    else:
        plans = complete_refraction_plans()
        plans["OD"]["manifest_entered_sphere_D"] = None
    payloads = [(b"image", f"source-{index}.png") for index in range(len(sources))]
    by_name = {filename: source for source, (_raw, filename) in zip(sources, payloads)}

    monkeypatch.setattr(app, "extract_one_image", lambda raw, filename: by_name[filename])
    monkeypatch.setattr(operational_security, "admit_analysis", lambda: None)

    @asynccontextmanager
    async def slot():
        yield

    monkeypatch.setattr(operational_security, "analysis_slot", slot)
    monkeypatch.setattr(
        app.pentacam_targeted_reread, "enrich_extraction",
        lambda *args, **kwargs: pytest.fail("targeted reread ran before intake gate"),
    )
    monkeypatch.setattr(
        app.geometric_srax_policy, "enrich_extraction",
        lambda *args, **kwargs: pytest.fail("geometric SRAX ran before intake gate"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(app._run_image_assessment(payloads, 30, plans, {}, {}))
    expected = "MANDATORY_SOURCE_SET_INCOMPLETE" if missing_source else "PREASSESSMENT_REFRACTION_REQUIRED"
    assert exc.value.detail["code"] == expected


def test_complete_intake_runs_post_gate_enrichment_and_enters_workflow(monkeypatch):
    sources = complete_set(False)
    payloads = [(b"image", f"source-{index}.png") for index in range(len(sources))]
    by_name = {filename: source for source, (_raw, filename) in zip(sources, payloads)}
    calls = []

    monkeypatch.setattr(app, "extract_one_image", lambda raw, filename: by_name[filename])
    monkeypatch.setattr(operational_security, "admit_analysis", lambda: None)

    @asynccontextmanager
    async def slot():
        yield

    monkeypatch.setattr(operational_security, "analysis_slot", slot)

    def targeted(core, result, raw, filename, **kwargs):
        calls.append(("targeted", filename, kwargs))
        return result

    def geometric(result, raw, filename):
        calls.append(("geometric", filename))
        return result

    monkeypatch.setattr(app.pentacam_targeted_reread, "enrich_extraction", targeted)
    monkeypatch.setattr(app.geometric_srax_policy, "enrich_extraction", geometric)
    monkeypatch.setattr(app, "merge_extractions", lambda results: {"eyes": [], "items": results})
    monkeypatch.setattr(
        assessment_workflow, "begin",
        lambda core, extracted, age, plans, modifiers, metadata, source_images: {
            "entered_workflow": True, "extracted": extracted,
        },
    )

    result = asyncio.run(app._run_image_assessment(
        payloads, 30, complete_refraction_plans(), {}, {},
    ))
    assert result["entered_workflow"] is True
    assert result["extracted"]["mandatory_source_set"]["confirmed"] is True
    assert len([call for call in calls if call[0] == "targeted"]) == 5
    assert len([call for call in calls if call[0] == "geometric"]) == 5


def test_false_primary_four_maps_date_conflict_requests_only_two_header_rereads(monkeypatch):
    sources = complete_set(False)
    sources[0]["document_context"]["exam_date"] = "23/09/2026"
    sources[1]["document_context"]["exam_date"] = "13/09/2026"
    for source in sources[2:]:
        source["document_context"]["exam_date"] = "03/09/2026"
    payloads = [(b"image", f"source-{index}.png") for index in range(len(sources))]
    by_name = {filename: source for source, (_raw, filename) in zip(sources, payloads)}
    calls = []

    monkeypatch.setattr(app, "extract_one_image", lambda raw, filename: by_name[filename])
    monkeypatch.setattr(operational_security, "admit_analysis", lambda: None)

    @asynccontextmanager
    async def slot():
        yield

    monkeypatch.setattr(operational_security, "analysis_slot", slot)

    def targeted(core, result, raw, filename, **kwargs):
        requested = kwargs.get("exam_date_requested", False)
        calls.append((filename, requested))
        if requested:
            result["document_context"]["targeted_exam_date_reread_evidence"] = {
                "value": "03/09/2026", "promoted": False,
            }
        return result

    monkeypatch.setattr(app.pentacam_targeted_reread, "enrich_extraction", targeted)
    monkeypatch.setattr(app.geometric_srax_policy, "enrich_extraction", lambda result, *_: result)
    monkeypatch.setattr(app, "merge_extractions", lambda results: {"eyes": [], "items": results})
    monkeypatch.setattr(
        assessment_workflow, "begin",
        lambda core, extracted, age, plans, modifiers, metadata, source_images: extracted,
    )

    extracted = asyncio.run(app._run_image_assessment(
        payloads, 30, complete_refraction_plans(), {}, {},
    ))
    assert [requested for _name, requested in calls].count(True) == 2
    four_maps = extracted["items"][:2]
    assert [item["document_context"]["exam_date"] for item in four_maps] == [
        "03/09/2026", "03/09/2026",
    ]
    assert not app.authoritative_exam_date_conflict(four_maps)


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


def test_direct_prompt_owns_explicit_legacy_bad_display_recognition_rule():
    prompt = canonical_engine.core.PROMPT
    assert "Belin/Ambrosio Display" in prompt
    assert "BELIN_AMBROSIO_DISPLAY" in prompt
    assert policy.BAD_DISPLAY_RECOGNITION_PROMPT in prompt
    assert not callable(getattr(policy, "install", None))
