"""Behavior-lock tests for the canonical CER-AI production contract.

These tests characterize decision-critical CER-AI behavior. Refactoring must preserve these
outputs unless a clinical policy change is explicitly approved.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

import canonical_engine
import hc_final_decision_policy as final_policy
import status_rank_policy

core = canonical_engine.core


def test_canonical_version_lock():
    assert canonical_engine.CANONICAL_VERSION == "0.7.71"


def test_hc_age_boundaries():
    assert [(age, core.age_points(age)) for age in (18, 19, 20, 21, 30)] == [
        (18, 3), (19, 2), (20, 2), (21, 0), (30, 0)
    ]


def test_hc_pachymetry_boundaries():
    assert [(p, core.lasik_pachy_points(p)) for p in (479, 480, 481, 499, 500, 509, 510, 511)] == [
        (479, None), (480, 2), (481, 2), (499, 2), (500, 1), (509, 1), (510, 0), (511, 0)
    ]


def test_final_bad_d_boundaries():
    assert [(x, core.bad_classification(x, final=True)) for x in (1.6, 1.6001, 2.5999, 2.6)] == [
        (1.6, "NORMAL"), (1.6001, "SUSPICIOUS"), (2.5999, "SUSPICIOUS"), (2.6, "ABNORMAL")
    ]


def test_randleman_topography_mapping():
    expected = {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }
    assert {k: core.lasik_topography_points(k) for k in expected} == expected


def test_status_aggregation_order_for_all_known_statuses():
    rank = status_rank_policy._STATUS_RANK
    statuses = tuple(rank)
    for current in statuses:
        for new in statuses:
            actual = core.combine_status(current, new)
            expected = new if rank[new] > rank[current] else current
            assert actual == expected


def _run_final_policy(monkeypatch, upstream, bad_status="NORMAL", erss_total=0):
    result = dict(upstream)
    result.setdefault("hard_stops", [])
    result.setdefault("missing", [])
    result.setdefault("reasons", [])
    result.setdefault("randleman_erss", {"total": erss_total})
    monkeypatch.setattr(final_policy, "_previous_assess_eye", lambda *args, **kwargs: result)
    monkeypatch.setattr(core, "bad_classification", lambda value, final=False: bad_status)
    return final_policy.assess_eye_with_hc_final_hierarchy({"BAD_D": 1.0}, {}, 30, {})


def test_final_hierarchy_preserves_caution_when_principal_scores_are_below_3(monkeypatch):
    for bad_status in ("NORMAL", "SUSPICIOUS"):
        for erss_total in (0, 1, 2):
            out = _run_final_policy(monkeypatch, {"status": "CAUTION"}, bad_status, erss_total)
            assert out["status"] == "CAUTION"


def test_final_hierarchy_erss_3_is_caution(monkeypatch):
    out = _run_final_policy(monkeypatch, {"status": "PASS"}, "NORMAL", 3)
    assert out["status"] == "CAUTION"


def test_final_hierarchy_preserves_upstream_erss_4_hard_stop(monkeypatch):
    out = _run_final_policy(
        monkeypatch,
        {"status": "STOP-DEFER", "hard_stops": ["Validated LASIK ERSS high-risk category (score >=4)."]},
        "NORMAL",
        4,
    )
    assert out["status"] == "STOP-DEFER"
    assert out["hard_stops"]


def test_final_hierarchy_abnormal_bad_is_hard_stop(monkeypatch):
    out = _run_final_policy(monkeypatch, {"status": "PASS"}, "ABNORMAL", 0)
    assert out["status"] == "STOP-DEFER"
    assert any("Final BAD-D abnormal" in reason for reason in out["hard_stops"])


def test_visual_morphology_is_neutralized_before_clinical_assessment(monkeypatch):
    captured = {}

    def upstream(eye, *args, **kwargs):
        captured.update(eye)
        return {
            "status": "PASS",
            "hard_stops": [],
            "missing": [],
            "reasons": [],
            "values": {"procedure": "LASIK"},
            "randleman_erss": {"total": 0},
        }

    monkeypatch.setattr(final_policy, "_previous_assess_eye", upstream)
    monkeypatch.setattr(core, "bad_classification", lambda value, final=False: "NORMAL")
    out = final_policy.assess_eye_with_hc_final_hierarchy(
        {
            "BAD_D": 1.0,
            "morphology": "ABNORMAL_ECTATIC",
            "morphology_confidence": "HIGH",
            "asymmetric_bow_tie": "YES",
            "srax": "YES",
            "srax_deg": 35.0,
            "inferior_opposite_steepening_D": 2.0,
            "morphology_evidence": ["visual-map classification"],
        },
        {"procedure": "LASIK"},
        30,
        {},
    )
    assert captured["morphology"] == "UNCERTAIN"
    assert captured["morphology_confidence"] == "UNREADABLE"
    assert captured["asymmetric_bow_tie"] == "UNCERTAIN"
    assert captured["srax"] == "UNCERTAIN"
    assert captured["srax_deg"] is None
    assert captured["inferior_opposite_steepening_D"] is None
    assert out["status"] == "PASS"


def test_final_hierarchy_never_overrides_missing_or_hard_stop(monkeypatch):
    missing = _run_final_policy(monkeypatch, {"status": "DATA INSUFFICIENT", "missing": ["BAD-D"]}, "NORMAL", 0)
    assert missing["status"] == "DATA INSUFFICIENT"
    stopped = _run_final_policy(monkeypatch, {"status": "STOP-DEFER", "hard_stops": ["independent stop"]}, "NORMAL", 0)
    assert stopped["status"] == "STOP-DEFER"


def test_prk_ewss_is_not_a_decision_pathway(monkeypatch):
    upstream = {
        "status": "STOP-DEFER",
        "values": {"procedure": "PRK"},
        "score": {"rows": {"age": 2}, "total": 4, "category": "HIGH_CONCERN"},
        "instrument": "PRK-EWSS v1.0 provisional evidence-weighted triage score; not validated",
        "reasons": ["PRK-EWSS v1.0 provisional high-concern category (score >=4)."],
        "warnings": ["CER-AI SCORE — SOURCE & BREAKDOWN: PRK-EWSS v1.0 provisional evidence-weighted triage score"],
    }
    out = _run_final_policy(monkeypatch, upstream)
    assert out["status"] == "PASS"
    assert out["score"]["total"] is None
    assert out["score"]["category"] == "NOT_APPLICABLE"
    assert all("PRK-EWSS" not in str(item) for item in out.get("reasons", []))
    assert all("PRK-EWSS" not in str(item) for item in out.get("warnings", []))
    assert out["prk_ewss_removed"] is True


def test_prk_ewss_removal_never_cancels_independent_hard_stop(monkeypatch):
    upstream = {
        "status": "STOP-DEFER",
        "values": {"procedure": "PRK"},
        "score": {"rows": {}, "total": 5, "category": "HIGH_CONCERN"},
        "reasons": ["PRK-EWSS v1.0 provisional high-concern category (score >=4)."],
        "hard_stops": ["independent tissue safety stop"],
    }
    out = _run_final_policy(monkeypatch, upstream)
    assert out["status"] == "STOP-DEFER"
    assert "independent tissue safety stop" in out["hard_stops"]


def test_secondary_review_alone_does_not_override_principal_hierarchy(monkeypatch):
    out = _run_final_policy(
        monkeypatch,
        {"status": "CAUTION", "warnings": ["secondary contextual finding"]},
        "SUSPICIOUS",
        2,
    )
    assert out["status"] == "CAUTION"
    assert out["warnings"] == ["secondary contextual finding"]


def test_safety_constants():
    assert core.PRK_EPITHELIUM_UM == 50
    assert core.FINAL_KMEAN_MIN_D == 36.0
    assert core.FINAL_KMEAN_MAX_D == 48.0


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


def test_required_runtime_layers_are_installed():
    assert core._cerai_erss_numeric_extraction_installed
    assert core._erss_topography_evidence_policy_installed
    assert core._randleman_bad_independence_installed
    assert core._hc_final_decision_hierarchy_installed
    assert core._hc_status_rank_policy_installed
    assert core._hc_inter_eye_tomography_policy_installed
    assert core._hc_lasik_fallback_installed
    assert "ERSS VISUAL MORPHOLOGY DISABLED:" in core.PROMPT


def test_canonical_runtime_invariants():
    assert canonical_engine.runtime_invariants() is True
