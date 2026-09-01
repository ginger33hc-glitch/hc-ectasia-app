"""Phase 2 tests for pure decision and surgical layers."""
import pytest
import lasik_planning as legacy_lasik

from clean_engine.decision import DecisionInput, decide
from clean_engine import surgery


def test_clean_final_hierarchy_matrix():
    for bad in ("NORMAL", "SUSPICIOUS"):
        for erss in (0, 1, 2):
            out = decide(DecisionInput("CAUTION", bad, erss))
            assert out.status == "CAUTION"
    assert decide(DecisionInput("PASS", "NORMAL", 3)).status == "STOP-DEFER"
    assert decide(DecisionInput("PASS", "ABNORMAL", 0)).status == "STOP-DEFER"
    assert decide(DecisionInput("STOP-DEFER", "NORMAL", 0, has_hard_stop=True)).status == "STOP-DEFER"
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


def test_clean_independent_hard_stop_uses_confirmed_480_boundary():
    common = dict(morphology="NORMAL_SYMMETRIC", intended_sphere_d=-3.0, final_kmean=42.0)
    assert surgery.lasik_independent_hard_stop(pachy_thinnest_um=479.999, **common)
    assert not surgery.lasik_independent_hard_stop(pachy_thinnest_um=480.0, **common)


def test_clean_independent_hard_stop_recognizes_ectatic_morphology():
    assert surgery.lasik_independent_hard_stop(
        pachy_thinnest_um=520, morphology="ABNORMAL_ECTATIC",
        intended_sphere_d=-3.0, final_kmean=42.0,
    )


def test_clean_independent_hard_stop_refractive_boundaries_are_strict():
    common = dict(pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC", final_kmean=42.0)
    assert not surgery.lasik_independent_hard_stop(intended_sphere_d=-10.0, **common)
    assert surgery.lasik_independent_hard_stop(intended_sphere_d=-10.001, **common)
    assert not surgery.lasik_independent_hard_stop(intended_sphere_d=6.0, **common)
    assert surgery.lasik_independent_hard_stop(intended_sphere_d=6.001, **common)


def test_clean_independent_hard_stop_final_k_boundaries_are_inclusive():
    common = dict(pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC", intended_sphere_d=-3.0)
    assert not surgery.lasik_independent_hard_stop(final_kmean=36.0, **common)
    assert not surgery.lasik_independent_hard_stop(final_kmean=48.0, **common)
    assert surgery.lasik_independent_hard_stop(final_kmean=35.999, **common)
    assert surgery.lasik_independent_hard_stop(final_kmean=48.001, **common)


def outcome(index, status="PASS", pta=35.0, hard_stop=False):
    return surgery.LasikPlanOutcome(surgery.LASIK_PLANS[index], status, pta, hard_stop)


def test_lasik_fallback_stops_when_plan_a_is_acceptable():
    seq = surgery.select_lasik_sequence([outcome(0), outcome(1), outcome(2)])
    assert [x.plan.name for x in seq] == ["Plan A"]


def test_lasik_failure_falls_back_a_to_b_and_preserves_a():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="STOP-DEFER", pta=35.0),
        outcome(1, status="PASS", pta=35.0),
        outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B"]
    assert surgery.final_lasik_status(seq) == "PASS"


def test_typed_evaluator_is_lazy_and_stops_after_acceptable_plan_b():
    called = []
    def evaluator(plan):
        called.append(plan.name)
        if plan.name == "Plan A":
            return surgery.LasikPlanOutcome(plan, "STOP-DEFER", 41.0)
        return surgery.LasikPlanOutcome(plan, "PASS", 39.0)
    seq = surgery.evaluate_lasik_fallback(evaluator)
    assert called == ["Plan A", "Plan B"]
    assert [x.plan.name for x in seq] == called


def test_typed_evaluator_stops_immediately_on_independent_hard_stop():
    called = []
    def evaluator(plan):
        called.append(plan.name)
        return surgery.LasikPlanOutcome(plan, "STOP-DEFER", 45.0, independent_hard_stop=True)
    seq = surgery.evaluate_lasik_fallback(evaluator)
    assert called == ["Plan A"]
    assert surgery.final_lasik_status(seq) == "STOP-DEFER"


def test_plan_a_preserves_actual_laser_ablation():
    result = surgery.plan_specific_ablation(
        surgery.LASIK_PLANS[0], actual_ablation_um=77.0,
        intended_sphere_d=-3.0, intended_cylinder_magnitude_d=1.0,
        laser_platform="Alcon EX500", is_fallback_plan=False,
    )
    assert result.ablation_um == 77.0
    assert result.source == "ACTUAL"


def test_plan_b_c_clear_plan_a_actual_and_recalculate_for_new_zone():
    for plan in surgery.LASIK_PLANS[1:]:
        result = surgery.plan_specific_ablation(
            plan, actual_ablation_um=77.0,
            intended_sphere_d=-3.0, intended_cylinder_magnitude_d=1.0,
            laser_platform="Alcon EX500", is_fallback_plan=True,
        )
        assert result.ablation_um == 48.0
        assert result.source == "HC_EX500_ESTIMATE"


def test_plan_a_and_plan_b_use_different_locked_zone_rates_when_estimating():
    a = surgery.plan_specific_ablation(
        surgery.LASIK_PLANS[0], actual_ablation_um=None,
        intended_sphere_d=-3.0, intended_cylinder_magnitude_d=1.0,
        laser_platform="Alcon EX500", is_fallback_plan=False,
    )
    b = surgery.plan_specific_ablation(
        surgery.LASIK_PLANS[1], actual_ablation_um=None,
        intended_sphere_d=-3.0, intended_cylinder_magnitude_d=1.0,
        laser_platform="Alcon EX500", is_fallback_plan=True,
    )
    assert a.ablation_um == 60.0
    assert b.ablation_um == 48.0


def test_fallback_does_not_invent_ablation_for_hyperopic_positive_sphere():
    result = surgery.plan_specific_ablation(
        surgery.LASIK_PLANS[1], actual_ablation_um=77.0,
        intended_sphere_d=2.0, intended_cylinder_magnitude_d=1.0,
        laser_platform="Alcon EX500", is_fallback_plan=True,
    )
    assert result.ablation_um is None
    assert result.source == "ACTUAL_REQUIRED_HYPEROPIC_OR_MIXED"


def test_pta_at_exactly_40_triggers_fallback():
    seq = surgery.select_lasik_sequence([
        outcome(0, pta=40.0),
        outcome(1, pta=39.999),
        outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B"]


def test_independent_hard_stop_prevents_parameter_fallback():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="STOP-DEFER", pta=45.0, hard_stop=True),
        outcome(1), outcome(2),
    ])
    assert [x.plan.name for x in seq] == ["Plan A"]
    assert surgery.final_lasik_status(seq) == "STOP-DEFER"


def test_plan_c_pta_cutoff_forces_final_do_not_proceed():
    seq = surgery.select_lasik_sequence([
        outcome(0, status="STOP-DEFER", pta=42.0),
        outcome(1, status="STOP-DEFER", pta=41.0),
        outcome(2, status="PASS", pta=40.0),
    ])
    assert [x.plan.name for x in seq] == ["Plan A", "Plan B", "Plan C"]
    assert surgery.final_lasik_status(seq) == "STOP-DEFER"


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
