"""Contract for the future production cutover seam."""
import ast
from pathlib import Path

from clean_engine.input_adapter import ReconciledEyeInput
from clean_engine.migration import run_clean_assessment
from clean_engine.service import CleanAssessment


def case(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK", prior_refractive_surgery=False,
        ablation_um=60, flap_um=100, preop_kmean_d=43,
        manifest_mrse_d=-3, intended_mrse_d=-3, intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0, laser_platform="EX500",
    )
    values.update(changes)
    return ReconciledEyeInput(**values)


def test_migration_seam_returns_complete_clean_assessment():
    out = run_clean_assessment(case())
    assert isinstance(out, CleanAssessment)
    assert out.result.status == "PASS WITH CAUTION"
    assert out.report.status == out.result.status


def test_migration_seam_preserves_adverse_and_incomplete_states():
    stopped = run_clean_assessment(case(pachy_thinnest_um=479))
    assert stopped.result.status == "DO NOT PROCEED"
    assert "PACHYMETRY_LT_480" in stopped.result.hard_stops

    incomplete = run_clean_assessment(case(bad_d=None))
    assert incomplete.result.status == "DATA INSUFFICIENT"
    assert "bad_d" in incomplete.result.missing


def test_migration_seam_depends_only_on_public_clean_boundary_modules():
    tree = ast.parse(Path("clean_engine/migration.py").read_text(encoding="utf-8"))
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports == {"input_adapter", "service"}


def test_migration_seam_has_no_legacy_or_presentation_dependency():
    text = Path("clean_engine/migration.py").read_text(encoding="utf-8")
    forbidden = (
        "canonical_engine", "bootstrap", "hc_final_decision_policy",
        "reports", "report_export_guard", "static", "app.py",
    )
    for marker in forbidden:
        assert marker not in text
