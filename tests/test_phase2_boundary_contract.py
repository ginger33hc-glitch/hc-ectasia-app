"""Phase 2 boundary locks before clinical-core runtime cutover."""

from pathlib import Path

import pytest

import mandatory_source_set_policy
from assessment_workflow import _contact_lens_washout
from clinical_core.readiness import contact_lens_washout


def _source(screen, eye=None, *, document_type="PENTACAM_TOPOGRAPHY", laterality=None):
    eyes = [] if eye is None else [{"eye": eye, "screen_types": [screen]}]
    return {
        "document_context": {
            "document_type": document_type,
            "laterality": laterality or eye or "UNKNOWN",
        },
        "eyes": eyes,
        "treatment_corrections": [],
    }


def _mandatory_set(include_card=False):
    items = [
        _source("4 Maps Refractive", "OD"),
        _source("FOUR_MAPS_REFRACTIVE", "OS"),
        _source("Belin/Ambrósio Enhanced Ectasia Display", "OD"),
        _source("BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY", "OS"),
        _source("Show 2 Exams Topometric", "OD"),
    ]
    if include_card:
        items.append(_source("EXCIMER_LASER_TREATMENT_CARD", document_type="TREATMENT_CARD"))
    return items


def test_mandatory_source_gate_stays_outside_clinical_core():
    summary = mandatory_source_set_policy.validate_source_set(_mandatory_set())
    assert summary["mandatory_count"] == 5
    assert summary["missing"] == []

    summary_with_card = mandatory_source_set_policy.validate_source_set(_mandatory_set(include_card=True))
    assert summary_with_card["uploaded_count"] == 6
    assert summary_with_card["treatment_card_count"] == 1


def test_missing_source_still_blocks_before_scoring():
    items = _mandatory_set()
    items.pop()
    with pytest.raises(Exception) as exc:
        mandatory_source_set_policy.validate_source_set(items)
    assert getattr(exc.value, "status_code", None) == 422


def test_more_than_six_images_still_rejected():
    items = _mandatory_set(include_card=True) + [_source("EXTRA", "OD")]
    with pytest.raises(Exception) as exc:
        mandatory_source_set_policy.validate_source_set(items)
    assert getattr(exc.value, "status_code", None) == 422


@pytest.mark.parametrize(
    "modifiers",
    [
        {"contact_lens_type": "NONE", "contact_lens_discontinuation_days": None},
        {"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 9},
        {"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 10},
        {"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 20},
        {"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 21},
        {"contact_lens_type": "UNKNOWN", "contact_lens_discontinuation_days": None},
    ],
)
def test_pure_readiness_matches_server_gate(modifiers):
    assert contact_lens_washout(modifiers) == _contact_lens_washout(modifiers)


def test_clinical_core_does_not_own_transport_report_or_archive_layers():
    root = Path("clinical_core")
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    forbidden_imports = (
        "import reports",
        "from reports",
        "import case_archive",
        "from case_archive",
        "import assessment_workflow",
        "from assessment_workflow",
        "import mandatory_source_set_policy",
        "from mandatory_source_set_policy",
        "from fastapi",
        "import fastapi",
    )
    for token in forbidden_imports:
        assert token not in text


def test_pipeline_documents_external_boundaries_explicitly():
    text = Path("clinical_core/pipeline.py").read_text(encoding="utf-8")
    for phrase in (
        "readiness",
        "identity/source validation",
        "contact-lens washout",
        "clinical eligibility",
        "planning fallback",
        "reporting",
        "archive",
    ):
        assert phrase in text
