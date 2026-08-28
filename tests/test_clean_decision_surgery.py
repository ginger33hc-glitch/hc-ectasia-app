"""Phase 2 tests for pure decision and surgical layers."""
import pytest
import lasik_planning as legacy_lasik

from clean_engine.decision import DecisionInput, decide
from clean_engine import surgery


def test_clean_final_hierarchy_matrix():
    for bad in ("NORMAL", "SUSPICIOUS"):
        for erss in (0, 1, 2):
            out = decide(DecisionInput("REVIEW — NOT CLEARED", bad, erss))
            assert out.status == "PASS WITH CAUTION"
    assert decide(DecisionInput("PASS", "NORMAL", 3)).status == "CAUTION — DEFER"
    assert decide(DecisionInput("PASS", "ABNORMAL", 0)).status == "DO NOT PROCEED"
    assert decide(DecisionInput("DO NOT PROCEED", "NORMAL", 0, has_hard_stop=True)).status == "DO NOT PROCEED"
    assert decide(DecisionInput("DATA INSUFFICIENT", "NORMAL", 0, decision_critical_incomplete=True)).status == "DATA INSUFFICIENT"


def test_lasik_plan_sequence_matches_legacy_runtime_exactly():
    clean = [(p.name, p.flap_um, p.optical_zone_mm, p.transition_zone_mm) for p in surgery.LASIK_PLANS]
    legacy = [(p["name"], p["flap_um"], p["optical_zone_mm"], p["transition_zone_mm"]) for p in legacy_lasik.LASIK_PLANS]
    assert clean == legacy


def test_clean_pta_cutoff_matches_legacy_runtime_boundary():
    for value in (None, 0, 39.999, 40.0, 40.001, 100.0):
        legacy = legacy_lasik._pta_cutoff({"values": {"LASIK_PTA_percent": value}})
        assert surgery.lasik_pta_cutoff(value) == legacy


def test_legacy_independent_hard_stop_marker_contract_is_characterized():
    for marker in legacy_lasik._INDEPENDENT_HARD_STOP_MARKERS:
        assert legacy_lasik._independent_hard_stop({"hard_stops": [f"prefix {marker} suffix"]})
    assert not legacy_lasik._independent_hard_stop({"hard_stops": ["ordinary LASIK tissue-load failure"]})


def test_exact_480_marker_mismatch_is_documented_not_silently_changed():
    # Current active pachymetry policy emits <=480 while legacy fallback searches for <480.
    # Preserve this characterization until migration replaces string matching with typed stops.
    assert not legacy_lasik._independent_hard_stop({
        "hard_stops": ["HC operational hard stop: thinnest preoperative cornea <=480 µm."]
    })


def outcome(index, status="PASS WITH CAUTION", pta=35.0, hard_stop=False):
    return surgery.LasikPlanOutcome(surgery.LASIK_PLANS[index], status, pta, hard_stop)


def test_lasik_fallback_stops_when_plan_a_is_acceptable():
    seq = surgery.select_lasik_sequence([outcome(0), outcome(1), outcome(2)])
    assert [x.plan.name for x in seq] == ["Plan A"]


def test_lasik_failure_falls_back_a_to_b_and_preserves_a():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="DO NOT PROCEED", pta=35.0),
        outcome(1, status="PASS WITH CAUTION", pta=35.0),
        outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B"]
    assert surgery.final_lasik_status(seq) == "PASS WITH CAUTION"


def test_pta_at_exactly_40_triggers_fallback():
    seq = surgery.select_lasik_sequence([
        outcome(0, pta=40.0),
        outcome(1, pta=39.999),
        outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B"]


def test_independent_hard_stop_prevents_parameter_fallback():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="DO NOT PROCEED", pta=45.0, hard_stop=True),
        outcome(1), outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A"]
    assert surgery.final_lasik_status(seq) == "DO NOT PROCEED"


def test_plan_c_pta_cutoff_forces_final_do_not_proceed():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="DO NOT PROCEED", pta=42.0),
        outcome(1, status="DO NOT PROCEED", pta=41.0),
        outcome(2, status="PASS WITH CAUTION", pta=40.0),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B", "Plan C"]
    assert surgery.final_lasik_status(seq) == "DO NOT PROCEED"


def test_lasik_calculations():
    assert surgery.lasik_rsb_um(520, 100, 80) == 340
    assert surgery.lasik_pta_percent(500, 100, 100) == 40.0
    assert surgery.lasik_pta_cutoff(39.999) is False
    assert surgery.lasik_pta_cutoff(40.0) is True


def test_prk_calculations_use_locked_50um_epithelium():
    assert surgery.prk_rst_um(500, 100) == 350
    assert surgery.prk_pta_percent(500, 100) == 30.0


def test_final_kmean_uses_locked_point_8_coefficient_and_inclusive_range():
    assert surgery.final_kmean_d(44, -5) == pytest.approx(40.0)
    assert surgery.final_kmean_d(44, 5) == pytest.approx(48.0)
    assert surgery.final_kmean_within_hc_range(36.0)
    assert surgery.final_kmean_within_hc_range(48.0)
    assert not surgery.final_kmean_within_hc_range(35.999)
    assert not surgery.final_kmean_within_hc_range(48.001)
