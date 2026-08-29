"""Contract tests for the extraction/reconciliation -> clean-engine boundary."""
from dataclasses import fields
from pathlib import Path

from clean_engine.input_adapter import ReconciledEyeInput, to_eye_input
from clean_engine.models import EyeInput


def test_reconciled_adapter_preserves_every_eye_input_field():
    source = ReconciledEyeInput(
        age_years=31,
        pachy_thinnest_um=522,
        bad_d=1.4,
        morphology="ASYMMETRIC_BOWTIE",
        procedure="lasik",
        prior_refractive_surgery=False,
        ablation_um=61,
        flap_um=100,
        preop_kmean_d=43.5,
        manifest_mrse_d=-3.25,
        intended_mrse_d=-3.25,
        intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0.5,
        laser_platform="Alcon EX500",
    )
    adapted = to_eye_input(source)
    assert isinstance(adapted, EyeInput)
    for field in fields(EyeInput):
        assert getattr(adapted, field.name) == getattr(source, field.name)


def test_adapter_is_structural_and_does_not_reconcile_or_infer_values():
    source = ReconciledEyeInput(
        age_years=None,
        pachy_thinnest_um=None,
        bad_d=None,
        morphology="UNREADABLE",
        procedure="PRK",
    )
    adapted = to_eye_input(source)
    assert adapted.age_years is None
    assert adapted.pachy_thinnest_um is None
    assert adapted.bad_d is None
    assert adapted.morphology == "UNREADABLE"


def test_clean_engine_orchestrator_has_no_raw_extraction_dependency():
    text = Path("clean_engine/engine.py").read_text(encoding="utf-8")
    forbidden = (
        "merge_extractions", "table_verified_numeric_fields",
        "map_fallback_numeric_fields", "field_provenance", "data_conflicts",
        "treatment_corrections", "document_context",
    )
    for marker in forbidden:
        assert marker not in text


def test_adapter_has_no_dependency_on_legacy_runtime_or_extraction_modules():
    text = Path("clean_engine/input_adapter.py").read_text(encoding="utf-8")
    for marker in ("canonical_engine", "app", "merge_policy", "extraction_guard"):
        assert marker not in text
