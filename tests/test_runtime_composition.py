from pathlib import Path
import ast

import runtime_composition

ROOT = Path(__file__).resolve().parents[1]


def _local_imports(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if (ROOT / f"{name.replace('.', '/')}.py").exists() or (ROOT / name.replace('.', '/')).is_dir():
                    names.add(name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if (ROOT / f"{node.module.replace('.', '/')}.py").exists() or (ROOT / node.module.replace('.', '/')).is_dir():
                names.add(node.module)
    return names


def test_canonical_engine_has_one_composition_dependency():
    assert _local_imports("canonical_engine.py") == {"runtime_composition"}


def test_policy_leaf_modules_do_not_hide_install_order():
    assert _local_imports("critical_score_highlight.py") == set()
    assert _local_imports("pachymetry_policy.py") == {"bootstrap"}
    assert _local_imports("hc_final_decision_policy.py") == {"bootstrap", "clinical_disposition"}
    assert _local_imports("hc_age_policy.py") == set()
    assert _local_imports("status_rank_policy.py") == {"clinical_disposition"}
    assert _local_imports("erss_visual_morphology_policy.py") == set()
    assert _local_imports("erss_auto_read_policy.py") == set()
    # derived_srax is a pure arithmetic utility, not a runtime/composition owner.
    assert _local_imports("erss_topography_evidence_policy.py") == {"derived_srax"}
    assert _local_imports("microkeratome_planning_policy.py") == {
        "planning.microkeratome",
        "typing",
    }
    assert _local_imports("inter_eye_tomography_policy.py") == {
        "inter_eye_tomography"
    }


def test_every_runtime_topic_is_owned_by_one_phase():
    owners = {}
    for phase, modules in runtime_composition.COMPOSITION_PHASES.items():
        for module in modules:
            assert module not in owners, f"{module} is owned by both {owners[module]} and {phase}"
            owners[module] = phase


def test_composition_manifest_covers_decision_critical_topics():
    expected = {
        "hc_age_policy",
        "hc_bad_final_policy",
        "pachymetry_policy",
        "randleman_bad_independence",
        "hc_final_decision_policy",
        "status_rank_policy",
        "inter_eye_tomography_policy",
        "microkeratome_planning_policy",
        "nice_policy",
        "merge_policy_base",
        "extraction_guard",
        "erss_topography_guard",
        "erss_visual_morphology_policy",
        "erss_topography_evidence_policy",
        "report_export_guard",
        "critical_score_highlight",
        "assessment_workflow",
        "user_access",
        "operational_security",
        "case_archive",
        "audit_log",
        "case_catalog",
        "historical_report",
        "research_export",
        "named_user_ui",
        "pentacam_targeted_reread",
        "erss_auto_read_policy",
    }
    actual = {
        module
        for modules in runtime_composition.COMPOSITION_PHASES.values()
        for module in modules
    }
    assert expected <= actual
