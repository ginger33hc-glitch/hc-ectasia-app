from dataclasses import FrozenInstanceError
import pytest

import clean_engine
from clean_engine.report_model import build_report_model


def assessment(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK", prior_refractive_surgery=False,
        ablation_um=60, flap_um=100, preop_kmean_d=43,
        manifest_mrse_d=-3, intended_mrse_d=-3, intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0, laser_platform="EX500",
    )
    values.update(changes)
    return clean_engine.assess(clean_engine.EyeInput(**values))


def test_report_model_preserves_domain_result_without_recalculation():
    result = assessment()
    report = build_report_model(result)
    assert report.status == result.status
    assert report.bad_d_status == result.bad_d_status
    assert report.calculations is result.calculations
    assert report.lasik_scores is result.scores
    assert report.prk_scores is result.prk_scores
    assert report.hard_stops == result.hard_stops
    assert report.missing == result.missing
    assert report.warnings == result.warnings
    assert report.lasik_planning_sequence == result.lasik_planning_sequence


def test_report_model_uses_central_status_presentation_semantics():
    assert build_report_model(assessment()).presentation_class == "pass"
    assert build_report_model(assessment(bad_d=3.0)).presentation_class == "fail"
    assert build_report_model(assessment(age_years=18)).presentation_class == "caution"
    assert build_report_model(assessment(bad_d=None)).presentation_class == "insufficient"


def test_report_model_is_immutable():
    report = build_report_model(assessment())
    with pytest.raises(FrozenInstanceError):
        report.status = "PASS"


def test_report_builder_contains_no_renderer_or_clinical_threshold_logic():
    from pathlib import Path
    text = Path("clean_engine/report_model.py").read_text(encoding="utf-8")
    for marker in ("reportlab", "docx", "html", "<480", "<300", "<310", ">=40", "score_stop"):
        assert marker not in text.lower()
