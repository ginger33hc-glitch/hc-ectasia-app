"""Acceptance contract for replacing the legacy clinical engine inside assessment_workflow.

These tests are intentionally introduced before the production cutover. They define
what the clean workflow must do once the cutover commit lands.
"""
from pathlib import Path


def test_workflow_cutover_target_has_one_direct_runtime_call_and_no_legacy_engine_call():
    text = Path("assessment_workflow.py").read_text(encoding="utf-8")
    # This contract becomes active when CANONICAL_WORKFLOW_CUTOVER is declared.
    if "CANONICAL_WORKFLOW_CUTOVER = True" not in text:
        return
    assert text.count("evaluate_case(") == 1
    assert "core.hc_engine(" not in text
    assert "core.apply_extracted_corrections(" not in text


def test_workflow_cutover_does_not_reintroduce_visual_morphology_scoring_override():
    text = Path("assessment_workflow.py").read_text(encoding="utf-8")
    if "CANONICAL_WORKFLOW_CUTOVER = True" not in text:
        return
    assert "surgeon_topography_category" not in text
    assert "core.MORPHOLOGY" not in text
    assert "morphology_evidence" not in text


def test_workflow_cutover_uses_canonical_readiness_not_duplicate_contact_lens_rules():
    text = Path("assessment_workflow.py").read_text(encoding="utf-8")
    if "CANONICAL_WORKFLOW_CUTOVER = True" not in text:
        return
    assert "evaluate_precore_readiness" in text
    assert "def _contact_lens_washout(" not in text
    assert "SOFT_CONTACT_LENS_WASHOUT_DAYS" not in text
    assert "RIGID_CONTACT_LENS_WASHOUT_DAYS" not in text


def test_workflow_cutover_keeps_session_and_report_token_transport_outside_clinical_core():
    text = Path("assessment_workflow.py").read_text(encoding="utf-8")
    if "CANONICAL_WORKFLOW_CUTOVER = True" not in text:
        return
    assert "secrets.token_urlsafe" in text
    assert "report_token" in text
    assert "_sessions" in text
