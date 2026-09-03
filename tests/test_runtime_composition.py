"""Architecture locks for the canonical production composition root."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace

from fastapi import FastAPI
import canonical_engine
import assessment_workflow
import critical_score_highlight
import erss_auto_read_policy
import erss_topography_evidence_policy
import erss_visual_morphology_policy
import hc_age_policy
import inter_eye_tomography_policy
import microkeratome_planning_policy
import nice_policy
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


def test_canonical_engine_has_one_composition_dependency():
    assert _local_imports("canonical_engine.py") == {"runtime_composition"}


def test_policy_leaf_modules_do_not_hide_install_order():
    assert _local_imports("critical_score_highlight.py") == set()
    assert _local_imports("pachymetry_policy.py") == {"bootstrap"}
    assert _local_imports("hc_final_decision_policy.py") == {"bootstrap", "clinical_disposition"}
    assert _local_imports("hc_age_policy.py") == set()
    assert _local_imports("erss_visual_morphology_policy.py") == set()
    assert _local_imports("erss_auto_read_policy.py") == set()
    assert _local_imports("erss_topography_evidence_policy.py") == set()
    assert _local_imports("srax_completion_policy.py") == set()
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
    assert owners["pentacam_targeted_reread"] == "pentacam_extraction"
    assert owners["assessment_workflow"] == "reporting_and_readiness"
    assert owners["srax_completion_policy"] == "reporting_and_readiness"
    assert owners["operational_security"] == "access_and_persistence"
    assert owners["hc_final_decision_policy"] == "clinical_policy"


def test_active_runtime_exposes_exact_manifest():
    assert canonical_engine.core._cerai_composition_phases == runtime_composition.COMPOSITION_PHASES


def test_nice_install_is_idempotent_for_schema_prompt_and_engine_wrapper():
    core = SimpleNamespace(
        SCHEMA={"properties": {}, "required": []},
        PROMPT="base prompt",
        hc_engine=lambda *args, **kwargs: {"eyes": [], "status": "PASS"},
        APP_VERSION="test",
    )

    nice_policy.install(core)
    installed_engine = core.hc_engine
    nice_policy.install(core)

    assert core.hc_engine is installed_engine
    assert core.SCHEMA["required"].count("nice_readings") == 1
    assert core.PROMPT.count("NICE SEPARATE INPUT READING") == 1


def test_age_policy_install_is_explicit_and_idempotent():
    core = SimpleNamespace(age_points=lambda age: 99)
    audit_owner = SimpleNamespace(
        _score_audit=lambda result: {"source": "base", "total": 0}
    )

    hc_age_policy.install(core, score_audit_owner=audit_owner)
    installed_age_points = core.age_points
    installed_score_audit = audit_owner._score_audit
    hc_age_policy.install(core, score_audit_owner=audit_owner)

    assert core.age_points is installed_age_points
    assert audit_owner._score_audit is installed_score_audit
    assert [core.age_points(age) for age in (17, 18, 19, 20, 21)] == [
        None,
        3,
        2,
        2,
        0,
    ]
    audit = audit_owner._score_audit({"values": {"procedure": "LASIK"}})
    assert audit["source"] == "base; CER-AI-modified age bands"


def test_report_builder_install_is_explicit_and_idempotent():
    def original_pdf(payload):
        return b"original-pdf"

    def original_docx(payload):
        return b"original-docx"

    def active_pdf(payload):
        return b"active-pdf"

    def active_docx(payload):
        return b"active-docx"

    core = SimpleNamespace(build_pdf=original_pdf, build_docx=original_docx)
    report_builders = SimpleNamespace(build_pdf=active_pdf, build_docx=active_docx)

    critical_score_highlight.install(core, report_builders)
    critical_score_highlight.install(
        core,
        SimpleNamespace(build_pdf=original_pdf, build_docx=original_docx),
    )

    assert core.build_pdf is active_pdf
    assert core.build_docx is active_docx


def test_visual_morphology_install_is_explicit_and_idempotent():
    core = SimpleNamespace()
    erss_runtime = SimpleNamespace(core=core, ERSS_PROMPT="legacy")

    erss_visual_morphology_policy.install(erss_runtime)
    installed_prompt = erss_runtime.ERSS_PROMPT
    erss_visual_morphology_policy.install(erss_runtime)

    assert installed_prompt == erss_visual_morphology_policy.ERSS_PROMPT
    assert erss_runtime.ERSS_PROMPT == installed_prompt
    assert core._erss_visual_morphology_policy_installed is True


def test_microkeratome_install_is_explicit_and_idempotent(monkeypatch):
    existing_core = microkeratome_planning_policy.core
    existing_previous = microkeratome_planning_policy._previous_hc_engine
    monkeypatch.setattr(microkeratome_planning_policy, "core", existing_core)
    monkeypatch.setattr(
        microkeratome_planning_policy,
        "_previous_hc_engine",
        existing_previous,
    )

    def upstream(*args, **kwargs):
        return {"eyes": []}

    core = SimpleNamespace(hc_engine=upstream)
    microkeratome_planning_policy.install(core)
    installed_engine = core.hc_engine
    microkeratome_planning_policy.install(core)

    assert installed_engine is microkeratome_planning_policy.hc_engine_with_microkeratome_planning
    assert core.hc_engine is installed_engine
    assert microkeratome_planning_policy._previous_hc_engine is upstream


def test_inter_eye_install_is_explicit_and_idempotent(monkeypatch):
    existing_previous = inter_eye_tomography_policy._previous_hc_engine
    monkeypatch.setattr(
        inter_eye_tomography_policy,
        "_previous_hc_engine",
        existing_previous,
    )

    def upstream(*args, **kwargs):
        return {"eyes": []}

    core = SimpleNamespace(hc_engine=upstream)
    compatibility_owner = SimpleNamespace(hc_engine=None)
    inter_eye_tomography_policy.install(
        core,
        compatibility_owner=compatibility_owner,
    )
    installed_engine = core.hc_engine
    inter_eye_tomography_policy.install(
        core,
        compatibility_owner=compatibility_owner,
    )

    assert installed_engine is inter_eye_tomography_policy.hc_engine_with_inter_eye_tomography
    assert core.hc_engine is installed_engine
    assert compatibility_owner.hc_engine is installed_engine
    assert inter_eye_tomography_policy._previous_hc_engine is upstream


def test_erss_auto_read_install_is_explicit_and_idempotent(monkeypatch):
    existing_previous = erss_auto_read_policy._previous_hc_engine
    monkeypatch.setattr(
        erss_auto_read_policy,
        "_previous_hc_engine",
        existing_previous,
    )

    def upstream(*args, **kwargs):
        return {"eyes": []}

    core = SimpleNamespace(hc_engine=upstream)
    erss_auto_read_policy.install(core)
    installed_engine = core.hc_engine
    erss_auto_read_policy.install(core)

    assert installed_engine is erss_auto_read_policy.hc_engine_with_erss_auto_read
    assert core.hc_engine is installed_engine
    assert erss_auto_read_policy._previous_hc_engine is upstream


def test_erss_evidence_install_is_explicit_and_idempotent(monkeypatch):
    for name in (
        "core",
        "_previous_scoring_morphology",
        "_previous_required_tomography_missing",
        "_previous_assess_eye",
    ):
        monkeypatch.setattr(
            erss_topography_evidence_policy,
            name,
            getattr(erss_topography_evidence_policy, name),
        )

    def scoring(eye):
        return {"category": "NORMAL_SYMMETRIC"}

    def missing(eye):
        return []

    def assess(eye, plan, age, modifiers):
        return {"status": "PASS"}

    core = SimpleNamespace(
        scoring_morphology=scoring,
        required_tomography_missing=missing,
        assess_eye=assess,
    )
    erss_topography_evidence_policy.install(core)
    installed_assess_eye = core.assess_eye
    erss_topography_evidence_policy.install(core)

    assert core.scoring_morphology is erss_topography_evidence_policy.scoring_morphology_with_i_s_evidence_gate
    assert core.required_tomography_missing is erss_topography_evidence_policy.required_tomography_missing_with_i_s
    assert installed_assess_eye is erss_topography_evidence_policy.assess_eye_with_i_s_evidence
    assert core.assess_eye is installed_assess_eye
    assert erss_topography_evidence_policy._previous_assess_eye is assess


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
