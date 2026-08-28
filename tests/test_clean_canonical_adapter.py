"""Contract tests for the read-only canonical shadow adapter."""
import ast
from pathlib import Path

from clean_engine.canonical_adapter import snapshot_canonical


def test_lasik_canonical_result_maps_without_recalculation():
    result = {
        "status": "PASS WITH CAUTION",
        "hard_stops": [],
        "missing": ["x"],
        "bad_d_status": "SUSPICIOUS",
        "score": {"total": 2, "category": "LOW"},
        "values": {"procedure": "LASIK"},
    }
    snap = snapshot_canonical(result)
    assert snap.status == "PASS WITH CAUTION"
    assert snap.hard_stops == ()
    assert snap.missing == ("x",)
    assert snap.bad_d_status == "SUSPICIOUS"
    assert snap.lasik_erss_total == 2
    assert snap.prk_score_total is None


def test_prk_score_is_kept_separate_from_lasik_erss():
    snap = snapshot_canonical({
        "status": "CAUTION — STOP/DEFER",
        "score": {"total": 3},
        "values": {"procedure": "PRK"},
    })
    assert snap.lasik_erss_total is None
    assert snap.prk_score_total == 3


def test_missing_or_non_numeric_score_is_not_inferred():
    for score in (None, {}, {"total": None}, {"total": "3"}, {"total": True}):
        snap = snapshot_canonical({
            "status": "DATA INSUFFICIENT", "score": score,
            "values": {"procedure": "LASIK"},
        })
        assert snap.lasik_erss_total is None


def test_adapter_does_not_mutate_canonical_payload():
    result = {
        "status": "DO NOT PROCEED",
        "hard_stops": ["independent stop"],
        "missing": [],
        "score": {"total": 4},
        "values": {"procedure": "LASIK"},
    }
    before = repr(result)
    snapshot_canonical(result)
    assert repr(result) == before


def test_adapter_has_no_canonical_runtime_or_policy_dependency():
    tree = ast.parse(Path("clean_engine/canonical_adapter.py").read_text(encoding="utf-8"))
    imports = {
        node.module for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imports == {"typing", "shadow"}
    source = Path("clean_engine/canonical_adapter.py").read_text(encoding="utf-8")
    for marker in ("canonical_engine", "app", "bootstrap", "policy", "decision"):
        assert marker not in source
