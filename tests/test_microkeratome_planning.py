from clean_engine.microkeratome_planning import MicrokeratomePlanningInput, plan_microkeratome


def base(**kw):
    data = dict(assessment_status="PASS", procedure="LASIK", steepest_k_d=44.0,
                flattest_k_d=42.0, w2w_mm=11.2, pachy_um=540, t_zone_mm=8.0)
    data.update(kw)
    return MicrokeratomePlanningInput(**data)


def test_module_is_post_pass_only():
    assert not plan_microkeratome(base(assessment_status="CAUTION")).applicable
    assert not plan_microkeratome(base(procedure="PRK")).applicable


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
        perpendicular_hinge_anatomically_possible=False, rsb_pta_allow_alternative=False))
    assert blocked.alternative_hinge is None
    allowed = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42,
        perpendicular_hinge_anatomically_possible=False, rsb_pta_allow_alternative=True))
    assert allowed.alternative_hinge == "+10 blade; temporal or nasal hinge"


def test_manual_blade_rules_can_coexist_and_are_not_silently_resolved():
    p = plan_microkeratome(base(steepest_k_d=39, flattest_k_d=37, pachy_um=500))
    assert "-10 blade" in p.blade_recommendations
    assert "+10 blade" in p.blade_recommendations
    assert "+20 blade" in p.blade_recommendations


def test_hyperopic_low_hinge_k_rule():
    p = plan_microkeratome(base(hyperopic=True, hinge_site_lowest_k_d=37))
    assert "+10 blade" in p.blade_recommendations
    assert any("hinge-site lowest K" in n for n in p.notes)
