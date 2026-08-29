"""Hard barrier keeping the replacement engine out of the canonical runtime."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports_clean_engine(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "clean_engine" or alias.name.startswith("clean_engine.") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "clean_engine" or str(node.module or "").startswith("clean_engine."):
                return True
    return False


def test_root_production_modules_cannot_import_clean_engine():
    offenders = [
        path.name for path in sorted(ROOT.glob("*.py"))
        if _imports_clean_engine(path)
    ]
    assert offenders == []


def test_canonical_workflow_does_not_execute_clean_migration_entrypoint():
    workflow = (ROOT / ".github" / "workflows" / "canonical-runtime.yml").read_text(encoding="utf-8")
    assert "run_clean_assessment" not in workflow
    assert "assess_reconciled" not in workflow
