"""Behavior locks for the authoritative CER-AI production contract.

Step-60 retirement record:
- Old authority: ``app.py`` scoring helpers plus ``hc_final_decision_policy`` and
  related installer markers.
- New authority: ``clinical_core`` + ``canonical_runtime_service`` with one
  ``finalize_disposition`` owner.
- Reason: the Monday clean-architecture specification explicitly supersedes the
  wrapper-on-wrapper clinical runtime. Tests protect the surviving canonical
  behavior and explicitly reject retired clinical wrappers.
"""
import hashlib
import inspect
from pathlib import Path
import subprocess
import sys

import canonical_engine
import assessment_workflow
import runtime_composition
from clinical_core.bad import final_bad_d_classification
from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from clinical_core.erss import erss_topography_points
from clinical_core.rules import erss_age_points, erss_pachymetry_points
from clinical_core.safety import FINAL_KMEAN_MAX_D, FINAL_KMEAN_MIN_D, PRK_EPITHELIUM_UM

core = canonical_engine.core


def test_canonical_version_lock():
    assert canonical_engine.CANONICAL_VERSION == "0.7.71"


def test_canonical_age_boundaries():
    assert [(age, erss_age_points(age)) for age in (18, 19, 20, 21, 30)] == [
        (18, 3), (19, 2), (20, 2), (21, 0), (30, 0)
    ]


def test_canonical_pachymetry_boundaries():
    assert [(p, erss_pachymetry_points(p)) for p in (479, 480, 481, 499, 500, 509, 510, 511)] == [
        (479, None), (480, 2), (481, 2), (499, 2), (500, 1), (509, 1), (510, 0), (511, 0)
    ]


def test_final_bad_d_boundaries():
    assert [(x, final_bad_d_classification(x)) for x in (1.6, 1.6001, 2.5999, 2.6)] == [
        (1.6, "NORMAL"), (1.6001, "SUSPICIOUS"), (2.5999, "SUSPICIOUS"), (2.6, "ABNORMAL")
    ]


def test_randleman_topography_mapping():
    expected = {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }
    assert {key: erss_topography_points(key) for key in expected} == expected


def test_stop_dominates_and_all_stop_drivers_are_retained():
    result = finalize_disposition((
        DecisionFinding("a", CAUTION, "caution"),
        DecisionFinding("b", STOP_DEFER, "stop one"),
        DecisionFinding("c", STOP_DEFER, "stop two"),
        DecisionFinding("d", ASSESSMENT_INCOMPLETE, "missing"),
    ))
    assert result.status == STOP_DEFER
    assert [finding.key for finding in result.stop_drivers] == ["b", "c"]


def test_incomplete_prevents_pass_when_no_stop_exists():
    result = finalize_disposition((
        DecisionFinding("pass", PASS),
        DecisionFinding("missing", ASSESSMENT_INCOMPLETE),
    ))
    assert result.status == ASSESSMENT_INCOMPLETE


def test_multiple_cautions_do_not_escalate_to_stop():
    result = finalize_disposition((
        DecisionFinding("one", CAUTION),
        DecisionFinding("two", CAUTION),
        DecisionFinding("three", PASS),
    ))
    assert result.status == CAUTION
    assert result.stop_drivers == ()
    assert len(result.caution_drivers) == 2


def test_all_pass_findings_remain_pass():
    result = finalize_disposition((DecisionFinding("one", PASS), DecisionFinding("two", PASS)))
    assert result.status == PASS


def test_safety_constants():
    assert PRK_EPITHELIUM_UM == 50.0
    assert FINAL_KMEAN_MIN_D == 36.0
    assert FINAL_KMEAN_MAX_D == 48.0


def test_runtime_html_maps_three_clinical_dispositions_separately():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'if(s === "PASS") return "pass";' in html
    assert 'if(s === "CAUTION") return "caution";' in html
    assert 'if(s === "STOP-DEFER") return "fail";' in html


def test_canonical_import_does_not_mutate_frontend_assets():
    path = Path("static/index.html")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    subprocess.run(
        [sys.executable, "-c", "import canonical_engine; canonical_engine.runtime_invariants()"],
        check=True,
    )
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert after == before


def test_production_workflow_calls_direct_canonical_runtime_not_legacy_engine():
    source = inspect.getsource(assessment_workflow._respond)
    assert "evaluate_case(" in source
    assert "core.hc_engine" not in source
    assert "apply_extracted_corrections" not in source
    assert assessment_workflow._respond.__module__ == "assessment_workflow"


def test_retired_erss_clinical_wrappers_are_absent_from_composition():
    names = {name for values in runtime_composition.COMPOSITION_PHASES.values() for name in values}
    assert "erss_topography_evidence_policy" not in names
    assert "erss_auto_read_policy" not in names
    assert "erss_numeric_extraction_policy" not in names


def test_required_nonclinical_runtime_boundaries_are_installed():
    assert not hasattr(core, "_cerai_erss_numeric_extraction_installed")
    assert not Path("erss_numeric_extraction_policy.py").exists()
    assert core._cerai_mandatory_source_set_installed
    assert core._hc_readiness_installed
    assert "ERSS VISUAL MORPHOLOGY DISABLED:" in core.PROMPT


def test_canonical_runtime_invariants():
    assert canonical_engine.runtime_invariants() is True
