from dataclasses import FrozenInstanceError
import ast
from pathlib import Path
import pytest

from clean_engine.input_adapter import ReconciledEyeInput
from clean_engine.service import CleanAssessment, assess_reconciled


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


def test_service_composes_reconciled_input_assessment_and_report():
    out = assess_reconciled(case())
    assert isinstance(out, CleanAssessment)
    assert out.result.status == "PASS WITH CAUTION"
    assert out.report.status == out.result.status
    assert out.report.calculations is out.result.calculations
    assert out.report.lasik_scores is out.result.scores


def test_service_preserves_hard_stop_and_missing_precedence():
    stopped = assess_reconciled(case(pachy_thinnest_um=479))
    assert stopped.result.status == "DO NOT PROCEED"
    assert "PACHYMETRY_LT_480" in stopped.report.hard_stops

    missing = assess_reconciled(case(bad_d=None))
    assert missing.result.status == "DATA INSUFFICIENT"
    assert "bad_d" in missing.report.missing


def test_service_preserves_prk_score_policy():
    caution = assess_reconciled(case(
        procedure="PRK", flap_um=None, age_years=18,
        pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC",
    ))
    assert caution.result.prk_scores.total == 3
    assert caution.result.status == "CAUTION — STOP/DEFER"
    assert caution.report.presentation_class == "caution"


def test_service_output_is_immutable():
    out = assess_reconciled(case())
    with pytest.raises(FrozenInstanceError):
        out.result = out.result


def test_service_imports_only_clean_boundary_dependencies():
    tree = ast.parse(Path("clean_engine/service.py").read_text(encoding="utf-8"))
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports == {"dataclasses", "engine", "input_adapter", "models", "report_model"}
