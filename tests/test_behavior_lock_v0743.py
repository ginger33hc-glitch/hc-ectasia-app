"""Behavior-lock tests for the v0.7.43 production contract.

These tests intentionally characterize decision-critical HC behavior before any
architecture refactor. Refactoring must preserve these outputs unless a clinical
policy change is explicitly approved.
"""
import canonical_engine

core = canonical_engine.core


def test_canonical_version_lock():
    assert canonical_engine.CANONICAL_VERSION == "0.7.43"


def test_hc_age_boundaries():
    assert [(age, core.age_points(age)) for age in (18, 19, 20, 21, 30)] == [
        (18, 3), (19, 2), (20, 2), (21, 0), (30, 0)
    ]


def test_hc_pachymetry_boundaries():
    assert [(p, core.lasik_pachy_points(p)) for p in (480, 481, 499, 500, 510, 511)] == [
        (480, None), (481, 2), (499, 2), (500, 1), (510, 1), (511, 0)
    ]


def test_final_bad_d_boundaries():
    assert [(x, core.bad_classification(x, final=True)) for x in (1.6, 1.61, 2.99, 3.0)] == [
        (1.6, "NORMAL"), (1.61, "SUSPICIOUS"), (2.99, "SUSPICIOUS"), (3.0, "ABNORMAL")
    ]


def test_randleman_topography_mapping():
    expected = {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }
    assert {k: core.lasik_topography_points(k) for k in expected} == expected


def test_status_aggregation_order():
    assert core.combine_status("PASS", "PASS WITH CAUTION") == "PASS WITH CAUTION"
    assert core.combine_status("PASS WITH CAUTION", "CAUTION — DEFER") == "CAUTION — DEFER"
    assert core.combine_status("PASS WITH CAUTION", "DO NOT PROCEED") == "DO NOT PROCEED"
    assert core.combine_status("CAUTION — DEFER", "DO NOT PROCEED") == "DO NOT PROCEED"


def test_safety_constants():
    assert core.PRK_EPITHELIUM_UM == 50
    assert core.FINAL_KMEAN_MIN_D == 36.0
    assert core.FINAL_KMEAN_MAX_D == 48.0


def test_required_runtime_layers_are_installed():
    assert core._erss_visual_morphology_policy_installed
    assert core._randleman_bad_independence_installed
    assert core._hc_final_decision_hierarchy_installed
    assert core._hc_status_rank_policy_installed
    assert core._hc_lasik_fallback_installed


def test_canonical_runtime_invariants():
    assert canonical_engine.runtime_invariants() is True
