"""Architecture locks for the canonical production composition root."""
import ast
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace

from fastapi import FastAPI

import assessment_workflow
import canonical_engine
import runtime_composition


ROOT = Path(__file__).resolve().parents[1]


def _startup_subprocess(source):
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "CERAI_NAMED_USERS_ENABLED": "0",
            "CERAI_ARCHIVE_ENABLED": "0",
            "CERAI_ARCHIVE_REQUIRED": "0",
        }
    )
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _local_imports(filename):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_canonical_engine_imports_only_surviving_runtime_and_canonical_owners():
    imports = _local_imports("canonical_engine.py")
    assert "runtime_composition" in imports
    assert "assessment_workflow" in imports
    assert "canonical_runtime_service" in imports
    assert "clinical_core.bad" in imports
    assert "clinical_core.erss" in imports
    assert "clinical_core.rules" in imports
    assert "clinical_core.safety" in imports

    retired = {
        "clean_engine",
        "hc_age_policy",
        "hc_bad_final_policy",
        "pachymetry_policy",
        "randleman_bad_independence",
        "hc_final_decision_policy",
        "inter_eye_tomography_policy",
        "ps3_runtime_policy",
        "erss_auto_read_policy",
        "erss_topography_evidence_policy",
        "erss_visual_morphology_policy",
        "microkeratome_planning_policy",
        "lasik_planning",
        "nice_policy",
        "nice_scoring",
    }
    assert not (imports & retired)


def test_every_runtime_topic_is_owned_by_one_phase():
    owners = {}
    for phase, modules in runtime_composition.COMPOSITION_PHASES.items():
        for module in modules:
            assert module not in owners, f"{module} is owned by both {owners[module]} and {phase}"
            owners[module] = phase

    assert owners["assessment_workflow"] == "canonical_workflow"
    assert "pentacam_targeted_reread" not in owners
    assert "geometric_srax_policy" not in owners
    extraction_source = inspect.getsource(canonical_engine.core.extract_one_image)
    assessment_source = inspect.getsource(canonical_engine.core._run_image_assessment)
    assert "pentacam_targeted_reread.enrich_extraction(" not in extraction_source
    assert "geometric_srax_policy.enrich_extraction(" not in extraction_source
    gate = assessment_source.index("mandatory_source_set_policy.validate_preassessment_requirements(")
    assert gate < assessment_source.index("pentacam_targeted_reread.enrich_extraction")
    assert gate < assessment_source.index("geometric_srax_policy.enrich_extraction")
    assert owners["reports"] == "canonical_reporting"
    assert "report_export_guard" not in owners
    assert "ps3_report_policy" not in owners
    assert "microkeratome_report_policy" not in owners
    assert owners["operational_security"] == "access_and_persistence"


def test_runtime_manifest_contains_no_retired_clinical_wrapper():
    modules = {name for values in runtime_composition.COMPOSITION_PHASES.values() for name in values}
    retired = {
        "hc_age_policy",
        "hc_bad_final_policy",
        "pachymetry_policy",
        "randleman_bad_independence",
        "hc_final_decision_policy",
        "inter_eye_tomography_policy",
        "ps3_runtime_policy",
        "erss_auto_read_policy",
        "erss_topography_evidence_policy",
        "erss_topography_guard",
        "erss_visual_morphology_policy",
        "microkeratome_planning_policy",
        "lasik_planning",
        "nice_policy",
        "nice_scoring",
        "report_export_guard",
        "ps3_report_policy",
        "microkeratome_report_policy",
        "critical_score_highlight",
    }
    assert not (modules & retired)


def test_compose_does_not_install_or_call_a_clinical_scorer():
    source = inspect.getsource(runtime_composition.compose)
    assert "hc_engine" not in source
    assert "assess_eye" not in source
    assert "nice_policy" not in source
    assert "ps3_runtime_policy" not in source
    assert "hc_final_decision_policy" not in source
    assert "microkeratome_planning_policy" not in source
    assert "pentacam_targeted_reread.install" not in source
    assert "geometric_srax_policy.install" not in source


def test_active_runtime_exposes_exact_manifest():
    assert canonical_engine.core._cerai_composition_phases == runtime_composition.COMPOSITION_PHASES


def test_readiness_install_is_idempotent_for_routes():
    core = SimpleNamespace(app=FastAPI())

    assessment_workflow.install(core)
    assessment_workflow.install(core)

    route_counts = {}
    for route in core.app.routes:
        for method in getattr(route, "methods", set()) or set():
            key = method, getattr(route, "path", "")
            route_counts[key] = route_counts.get(key, 0) + 1
    assert route_counts[("POST", "/assessment/complete")] == 1
    assert route_counts[("POST", "/assessment/source-region")] == 1


def test_production_workflow_uses_direct_canonical_runtime():
    source = inspect.getsource(assessment_workflow._respond)
    assert "evaluate_case(" in source
    assert "core.hc_engine" not in source
    assert "apply_extracted_corrections" not in source


def test_uncomposed_app_target_refuses_asgi_startup():
    result = _startup_subprocess(
        "from fastapi.testclient import TestClient\n"
        "import app\n"
        "with TestClient(app.app):\n"
        "    pass\n"
    )

    assert result.returncode != 0
    assert "uncomposed app:app target is not a clinical runtime" in result.stderr


def test_canonical_app_target_allows_asgi_startup():
    result = _startup_subprocess(
        "from fastapi.testclient import TestClient\n"
        "import canonical_engine\n"
        "with TestClient(canonical_engine.app) as client:\n"
        "    assert client.get('/').status_code == 200\n"
    )

    assert result.returncode == 0, result.stderr


def test_railway_start_command_uses_canonical_bootstrap():
    config = tomllib.loads((ROOT / "railway.toml").read_text(encoding="utf-8"))
    assert config["deploy"]["startCommand"] == "python start.py"
