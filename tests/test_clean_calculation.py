from clean_engine.calculation import CalculationInput, calculate


def base(**changes):
    values = dict(
        procedure="LASIK", pachy_thinnest_um=520, morphology="NORMAL_SYMMETRIC",
        intended_sphere_d=-3.0, intended_cylinder_magnitude_d=0.0, intended_mrse_d=-3.0,
        preop_kmean_d=43.0, ablation_um=60.0, flap_um=100.0, laser_platform="EX500",
        use_lasik_fallback_planning=False,
    )
    values.update(changes)
    return CalculationInput(**values)


def test_direct_lasik_calculation_is_pure_and_explicit():
    out = calculate(base())
    assert out.values.lasik_rsb_um == 360.0
    assert out.values.lasik_pta_percent == (160.0 / 520.0) * 100.0
    assert out.values.final_kmean_d == 40.6
    assert out.planning_sequence == ()


def test_prk_calculation_uses_locked_50_um_epithelium_convention():
    out = calculate(base(procedure="PRK", flap_um=None))
    assert out.values.prk_rst_um == 410.0
    assert out.values.prk_pta_percent == (110.0 / 520.0) * 100.0
    assert out.values.final_kmean_d == 40.6


def test_lasik_fallback_returns_typed_plan_sequence():
    out = calculate(base(
        use_lasik_fallback_planning=True,
        ablation_um=None,
        intended_sphere_d=-10.0,
        intended_mrse_d=-10.0,
    ))
    assert tuple(step.plan_name for step in out.planning_sequence) in {
        ("Plan A",), ("Plan A", "Plan B"), ("Plan A", "Plan B", "Plan C")
    }
    assert out.planning_sequence[0].optical_zone_mm == 6.5


def test_independent_hard_stop_prevents_unnecessary_fallback():
    out = calculate(base(
        use_lasik_fallback_planning=True,
        pachy_thinnest_um=480.0,
        ablation_um=None,
    ))
    assert tuple(step.plan_name for step in out.planning_sequence) == ("Plan A",)


def test_final_kmean_is_unavailable_without_both_required_inputs():
    assert calculate(base(preop_kmean_d=None)).values.final_kmean_d is None
    assert calculate(base(intended_mrse_d=None)).values.final_kmean_d is None
