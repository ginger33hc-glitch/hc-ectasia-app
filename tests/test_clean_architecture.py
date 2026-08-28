"""Architecture contract for the parallel clean clinical engine."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "clean_engine" / "engine.py"


def _engine_tree():
    return ast.parse(ENGINE.read_text(encoding="utf-8"))


def test_engine_is_orchestrator_not_clinical_policy_container():
    source = ENGINE.read_text(encoding="utf-8")
    forbidden_literals = (
        "PACHYMETRY_LE_480", "LASIK_RSB_LT_300", "PRK_RST_LT_310",
        "FINAL_KMEAN_OUTSIDE_36_48", "ERSS_GE_4",
        "LASIK_PTA_GE_40_AFTER_FALLBACK",
    )
    for literal in forbidden_literals:
        assert literal not in source


def test_engine_delegates_each_decision_stage_to_typed_module():
    imports = set()
    for node in _engine_tree().body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert {
        "calculation", "finalization", "hard_stops", "scoring", "validation"
    }.issubset(imports)


def test_engine_does_not_import_low_level_surgical_or_status_policy():
    imports = set()
    for node in _engine_tree().body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert "surgery" not in imports
    assert "status" not in imports
    assert "decision" not in imports


def test_engine_contains_only_assessment_orchestration_function():
    functions = [node.name for node in _engine_tree().body if isinstance(node, ast.FunctionDef)]
    assert functions == ["assess"]
