"""Contract tests for the non-authoritative shadow comparison service."""
import ast
from pathlib import Path

from clean_engine.input_adapter import ReconciledEyeInput
from clean_engine.shadow_service import compare_canonical_with_clean


def clean_case(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK",
        ablation_um=60, flap_um=100, preop_kmean_d=43,
        intended_mrse_d=-3, intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0, laser_platform="EX500",
    )
    values.update(changes)
    return ReconciledEyeInput(**values)


def canonical_case(**changes):
    result = {
        "status": "PASS WITH CAUTION",
        "hard_stops": [],
        "missing": [],
        "bad_d_status": "NORMAL",
        "score": {"total": 0},
        "values": {"procedure": "LASIK"},
    }
    result.update(changes)
    return result


def test_service_records_equivalence_without_selecting_a_result():
    canonical = canonical_case()
    before = repr(canonical)
    out = compare_canonical_with_clean(canonical, clean_case())
    assert out.equivalent is True
    assert out.differences == ()
    assert out.canonical.status == "PASS WITH CAUTION"
    assert out.clean.status == "PASS WITH CAUTION"
    assert repr(canonical) == before


def test_service_records_divergence_and_preserves_both_outputs():
    canonical = canonical_case(status="CAUTION — DEFER")
    out = compare_canonical_with_clean(canonical, clean_case())
    assert out.equivalent is False
    assert out.differences == ("status",)
    assert out.canonical.status == "CAUTION — DEFER"
    assert out.clean.status == "PASS WITH CAUTION"


def test_service_preserves_adverse_clean_state_as_comparison_evidence_only():
    canonical = canonical_case()
    out = compare_canonical_with_clean(canonical, clean_case(pachy_thinnest_um=480))
    assert out.equivalent is False
    assert out.clean.status == "DO NOT PROCEED"
    assert "hard_stops" in out.differences
    assert out.canonical.status == "PASS WITH CAUTION"


def test_shadow_service_has_only_neutral_migration_boundary_dependencies():
    tree = ast.parse(Path("clean_engine/shadow_service.py").read_text(encoding="utf-8"))
    imports = {
        node.module for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imports == {
        "typing", "canonical_adapter", "input_adapter", "migration", "shadow"
    }


def test_shadow_service_does_not_import_authoritative_runtime_or_policy_layers():
    tree = ast.parse(Path("clean_engine/shadow_service.py").read_text(encoding="utf-8"))
    imported = {
        node.module for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden = {
        "canonical_engine", "app", "bootstrap", "policy", "decision",
        "engine", "finalization", "hard_stops", "reports",
    }
    assert imported.isdisjoint(forbidden)
