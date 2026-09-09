"""Architecture acceptance locks for the one-canonical-engine refactor."""

import ast
from pathlib import Path

import canonical_engine
from clinical_core.safety import PTA_LIMIT_PERCENT, pta_hard_stop


REPO = Path(__file__).resolve().parent.parent


def _top_level_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_one_canonical_clinical_runtime_and_no_parallel_engine_remain():
    assert not (REPO / "clean_engine").exists()
    assert not (REPO / "bootstrap.py").exists()
    assert not (REPO / "clinical_disposition.py").exists()
    assert {
        "assess_eye", "hc_engine", "apply_extracted_corrections", "combine_status",
        "normalize_signed_refraction_plan", "validate_plan",
    }.isdisjoint(
        _top_level_functions(REPO / "app.py")
    )
    source = (REPO / "assessment_workflow.py").read_text(encoding="utf-8")
    assert "from canonical_runtime_service import evaluate_case" in source
    assert "evaluate_case(" in source
    assert "core.hc_engine" not in source


def test_no_late_browser_clinical_override_or_report_recalculation_module_remains():
    assert not (REPO / "static" / "hc-reference.js").exists()
    assert not (REPO / "static" / "hc-reference.css").exists()
    html = (REPO / "static" / "index.html").read_text(encoding="utf-8")
    assert "hc-reference" not in html
    assert "surgeon_topography_category" not in html
    assert "topographyRows" not in html
    assert "Visual morphology is not evaluated" in html


def test_report_renderer_has_no_clinical_scorer_or_threshold_owner():
    source = (REPO / "reports.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not any(module.startswith("clinical_core") for module in imported_modules)
    assert {
        "erss_total", "score_nice", "evaluate_ps3", "evaluate_bad",
        "finalize_disposition", "pta_percent", "estimated_final_kmean_d",
    }.isdisjoint(called_names)


def test_merge_has_no_first_highest_lowest_or_tolerance_reconciliation():
    source = (REPO / "app.py").read_text(encoding="utf-8")
    function_source = source[source.index("def merge_extractions("):source.index("\ndef ", source.index("def merge_extractions(") + 10)]
    for forbidden in (
        "conservative limiting value retained", "first value retained", "numeric_tolerance",
        "most concerning", "average(", "conservative =",
    ):
        assert forbidden not in function_source
    assert "value left unresolved for surgeon confirmation" in function_source


def test_pta_boundary_is_a_startup_locked_canonical_rule():
    assert PTA_LIMIT_PERCENT == 40.0
    assert [pta_hard_stop(x) for x in (39.99, 40.0, 40.01)] == [False, True, True]
    assert canonical_engine.runtime_invariants() is True


def test_current_branding_uses_approved_original_logo_asset():
    logo = REPO / "static" / "branding" / "cer-ai-logo-final.png"
    assert logo.exists()
    assert logo.stat().st_size == 87330
    for relative in ("static/index.html", "static/public-home.html"):
        source = (REPO / relative).read_text(encoding="utf-8")
        assert '/static/branding/cer-ai-logo-final.png?v=5' in source
        assert "brand-wordmark" not in source
        assert "CER-AI — Corneal Ectasia Risk Assessment Intelligence" in source
        assert "Cornea Ectasia Risk Assessment Intelligence" not in source
        assert "Risk Analysis Intelligence" not in source
