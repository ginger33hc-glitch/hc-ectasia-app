"""Behavior-lock tests for the v0.7.43 production contract.

These tests characterize decision-critical HC behavior before architecture refactor.
Refactoring must preserve these outputs unless a clinical policy change is explicitly approved.
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
    assert canonical_engine.CANONICAL_VERSION == "0.7.43"


def test_hc_age_boundaries():
    assert [(age, core.age_points(age)) for age in (18, 19, 20, 21, 30)] == [
        (18, 3), (19, 2), (20, 2), (21, 0), (30, 0)
    ]


def test_hc_pachymetry_boundaries():
    assert [(p, core.lasik_pachy_points(p)) for p in (479, 480, 499, 500, 510, 511)] == [
        (479, None), (480, 2), (499, 2), (500, 1), (510, 1), (511, 0)
    ]


def test_final_bad_d_boundaries():
    assert [(x, core.bad_classification(x, final=True)) for x in (1.6, 1.6001, 2.99, 3.0)] == [
        (1.6, "NORMAL"), (1.6001, "SUSPICIOUS"), (2.99, "SUSPICIOUS"), (3.0, "ABNORMAL")
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


def test_final_hierarchy_bad_normal_or_suspicious_and_erss_below_3_passes_with_caution(monkeypatch):
    for bad_status in ("NORMAL", "SUSPICIOUS"):
        for erss_total in (0, 1, 2):
            out = _run_final_policy(monkeypatch, {"status": "REVIEW — NOT CLEARED"}, bad_status, erss_total)
            assert out["status"] == "PASS WITH CAUTION"


def test_final_hierarchy_erss_3_is_adverse(monkeypatch):
    out = _run_final_policy(monkeypatch, {"status": "PASS"}, "NORMAL", 3)
    assert out["status"] == "CAUTION — DEFER"


def test_final_hierarchy_preserves_upstream_erss_4_hard_stop(monkeypatch):
    out = _run_final_policy(
        monkeypatch,
        {"status": "DO NOT PROCEED", "hard_stops": ["Validated LASIK ERSS high-risk category (score >=4)."]},
        "NORMAL",
        4,
    )
    assert out["status"] == "DO NOT PROCEED"
    assert out["hard_stops"]


def test_final_hierarchy_abnormal_bad_is_hard_stop(monkeypatch):
    out = _run_final_policy(monkeypatch, {"status": "PASS"}, "ABNORMAL", 0)
    assert out["status"] == "DO NOT PROCEED"
    assert any("Final BAD-D abnormal" in reason for reason in out["hard_stops"])


def test_final_hierarchy_never_overrides_missing_or_hard_stop(monkeypatch):
    missing = _run_final_policy(monkeypatch, {"status": "DATA INSUFFICIENT", "missing": ["BAD-D"]}, "NORMAL", 0)
    assert missing["status"] == "DATA INSUFFICIENT"
    stopped = _run_final_policy(monkeypatch, {"status": "DO NOT PROCEED", "hard_stops": ["independent stop"]}, "NORMAL", 0)
    assert stopped["status"] == "DO NOT PROCEED"


def test_secondary_review_alone_does_not_override_principal_hierarchy(monkeypatch):
    out = _run_final_policy(
        monkeypatch,
        {"status": "REVIEW — NOT CLEARED", "warnings": ["secondary contextual finding"]},
        "SUSPICIOUS",
        2,
    )
    assert out["status"] == "PASS WITH CAUTION"
    assert out["warnings"] == ["secondary contextual finding"]


def test_safety_constants():
    assert core.PRK_EPITHELIUM_UM == 50
    assert core.FINAL_KMEAN_MIN_D == 36.0
    assert core.FINAL_KMEAN_MAX_D == 48.0


def test_runtime_html_maps_pass_with_caution_to_green_pass_class():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'if(s === "PASS" || s === "PASS WITH CAUTION") return "pass";' in html


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
    assert core._erss_visual_morphology_policy_installed
    assert core._randleman_bad_independence_installed
    assert core._hc_final_decision_hierarchy_installed
    assert core._hc_status_rank_policy_installed
    assert core._hc_lasik_fallback_installed


def test_canonical_runtime_invariants():
    assert canonical_engine.runtime_invariants() is True
