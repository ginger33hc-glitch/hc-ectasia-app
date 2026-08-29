import pytest

from clean_engine.microkeratome_planning import MicrokeratomePlanningInput, plan_microkeratome


def base(**kw):
    data = dict(assessment_status="PASS", procedure="LASIK", steepest_k_d=44.0,
                flattest_k_d=42.0, w2w_mm=11.2, pachy_um=540, t_zone_mm=8.0,
                planned_flap_um=100, max_ablation_um=60)
    data.update(kw)
    return MicrokeratomePlanningInput(**data)


def test_module_is_post_pass_only():
    assert not plan_microkeratome(base(assessment_status="CAUTION")).applicable
    assert not plan_microkeratome(base(procedure="PRK")).applicable


def test_pass_with_caution_is_the_active_favorable_gate():
    plan = plan_microkeratome(base(assessment_status="PASS WITH CAUTION"))
    assert plan.applicable
    assert plan.assessment_gate == "PASS WITH CAUTION"


def test_nomogram_mid_range_small_cornea():
    p = plan_microkeratome(base())
    assert p.vacuum_ring_mm == 8.5
    assert p.vacuum_pressure_mmhg == "550"
    assert p.ring_tzone_clearance_mm == 0.5


def test_k_point_50_rounds_up():
    p = plan_microkeratome(base(steepest_k_d=46.5, flattest_k_d=44.0))
    assert p.vacuum_ring_mm == 8.0


def test_large_w2w_changes_ring():
    p = plan_microkeratome(base(w2w_mm=11.5))
    assert p.vacuum_ring_mm == 9.0


def test_delta_k_strictly_over_four_uses_perpendicular_hinge():
    p = plan_microkeratome(base(steepest_k_d=46.1, flattest_k_d=42.0, steep_axis_deg=20))
    assert p.delta_k_d == 4.1
    assert "Perpendicular" in p.primary_hinge
    assert "110" in p.primary_hinge


def test_delta_k_exact_four_does_not_trigger_hc_rule():
    p = plan_microkeratome(base(steepest_k_d=46.0, flattest_k_d=42.0))
    assert p.delta_k_d == 4.0
    assert p.primary_hinge is None


def test_anatomic_exception_requires_rsb_pta_clearance():
    blocked = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42,
        pachy_um=480, planned_flap_um=100, max_ablation_um=80,
        perpendicular_hinge_anatomically_possible=False))
    assert blocked.alternative_hinge is None
    assert blocked.alternative_safety == "NOT_ALLOWED"
    allowed = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42,
        perpendicular_hinge_anatomically_possible=False))
    assert allowed.alternative_hinge == "+10 blade; temporal or nasal hinge"
    assert allowed.alternative_rsb_um == 370
    assert allowed.alternative_pta_percent == pytest.approx(31.481, abs=0.001)


def test_unknown_anatomy_exposes_only_a_conditional_safe_alternative():
    plan = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42))
    assert plan.primary_hinge == "Perpendicular to steep axis"
    assert plan.alternative_hinge == "+10 blade; temporal or nasal hinge"
    assert any("only if the surgeon determines" in note for note in plan.notes)


def test_plus_ten_alternative_uses_inclusive_rsb_and_exclusive_pta_boundaries():
    rsb_boundary = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, pachy_um=490,
        planned_flap_um=100, max_ablation_um=80,
    ))
    assert rsb_boundary.alternative_rsb_um == 300
    assert rsb_boundary.alternative_safety == "ALLOWED"

    pta_boundary = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, pachy_um=500,
        planned_flap_um=100, max_ablation_um=90,
    ))
    assert pta_boundary.alternative_pta_percent == 40.0
    assert pta_boundary.alternative_safety == "NOT_ALLOWED"


def test_manual_blade_rules_can_coexist_and_are_not_silently_resolved():
    p = plan_microkeratome(base(steepest_k_d=39, flattest_k_d=37, pachy_um=500))
    assert "-10 blade" in p.blade_recommendations
    assert "+10 blade" in p.blade_recommendations
    assert "+20 blade" in p.blade_recommendations


def test_hyperopic_low_hinge_k_rule():
    p = plan_microkeratome(base(hyperopic=True, hinge_site_lowest_k_d=37))
    assert "+10 blade" in p.blade_recommendations
    assert any("hinge-site lowest K" in n for n in p.notes)
