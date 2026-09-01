"""Architecture locks for the canonical production composition root."""
import ast
from pathlib import Path

import canonical_engine
import runtime_composition


ROOT = Path(__file__).resolve().parents[1]


def _local_imports(filename):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_canonical_engine_has_one_composition_dependency():
    assert _local_imports("canonical_engine.py") == {"runtime_composition"}


def test_policy_leaf_modules_do_not_hide_install_order():
    assert _local_imports("critical_score_highlight.py") == {"bootstrap", "reports"}
    assert _local_imports("pachymetry_policy.py") == {"bootstrap"}
    assert _local_imports("hc_final_decision_policy.py") == {"bootstrap"}


def test_every_runtime_topic_is_owned_by_one_phase():
    owners = {}
    for phase, modules in runtime_composition.COMPOSITION_PHASES.items():
        for module in modules:
            assert module not in owners, f"{module} is owned by both {owners[module]} and {phase}"
            owners[module] = phase
    assert owners["pentacam_targeted_reread"] == "pentacam_extraction"
    assert owners["assessment_workflow"] == "reporting_and_readiness"
    assert owners["operational_security"] == "access_and_persistence"
    assert owners["hc_final_decision_policy"] == "clinical_policy"


def test_active_runtime_exposes_exact_manifest():
    assert canonical_engine.core._cerai_composition_phases == runtime_composition.COMPOSITION_PHASES
