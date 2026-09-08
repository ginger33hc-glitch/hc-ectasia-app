"""Official Step 8 runtime acceptance for hard stops and tissue safety."""
from canonical_runtime_service import evaluate_case


def _eye(name="OD", **overrides):
    values = {
        "eye": name,
        "Kmean_D": 43.0,
        "K2_D": 44.0,
        "central_pachy_um": 550.0,
        "pachy_thinnest_um": 545.0,
        "BAD_D": 1.0,
        "Df": -0.2,
        "Db": 0.4,
        "Dp": 0.3,
        "Dt": 0.2,
        "Da": 0.5,
        "ARTmax_um": 380.0,
        "PPI_min": 0.7,
        "PPI_avg": 1.0,
        "PPI_max": 1.2,
        "I_S": 0.0,
        "topographic_astig_D": 1.0,
        "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0,
        "B_Ele_Th_um": 10.0,
        "srax": "NO",
        "srax_deg": 10.0,
    }
    values.update(overrides)
    return values


def _plan(procedure="PRK", **overrides):
    values = {
        "prior": "no",
        "procedure": procedure,
        "flap_um": 100.0 if procedure == "LASIK" else None,
        "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0,
        "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0,
        "intended_axis_deg": 90.0,
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers():
    return {
        "eye_rubbing": "no",
        "family_history": "no",
        "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }


def _evaluate(*, procedure="PRK", od_eye=None, od_plan=None):
    result = evaluate_case(
        {"eyes": [od_eye or _eye("OD"), _eye("OS")]},
        35,
        {"OD": od_plan or _plan(procedure), "OS": _plan(procedure)},
        _modifiers(),
        software_version="step8-runtime-acceptance",
    )
    return result, {eye["eye"]: eye for eye in result["eyes"]}


def test_preop_thinnest_480_allowed_but_479_hard_stops():
    _, at_480 = _evaluate(od_eye=_eye("OD", pachy_thinnest_um=480.0))
    assert "preop_thickness" not in at_480["OD"]["hard_stops"]
    assert at_480["OD"]["status"] == "PASS"

    result, at_479 = _evaluate(od_eye=_eye("OD", pachy_thinnest_um=479.0))
    assert "preop_thickness" in at_479["OD"]["hard_stops"]
    assert at_479["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_lasik_rsb_300_allowed_but_299_hard_stops():
    _, at_300 = _evaluate(
        procedure="LASIK",
        od_plan=_plan("LASIK", flap_um=100.0, ablation_um=145.0),
    )
    plan_a_300 = at_300["OD"]["planning"]["sequence"][0]
    assert plan_a_300["ablation_um"] == 145.0
    assert "lasik_rsb" not in plan_a_300["rejection_reasons"]

    _, at_299 = _evaluate(
        procedure="LASIK",
        od_plan=_plan("LASIK", flap_um=100.0, ablation_um=146.0),
    )
    plan_a_299 = at_299["OD"]["planning"]["sequence"][0]
    assert plan_a_299["ablation_um"] == 146.0
    assert "lasik_rsb" in plan_a_299["rejection_reasons"]


def test_prk_rst_310_allowed_but_309_hard_stops():
    _, at_310 = _evaluate(od_plan=_plan("PRK", ablation_um=185.0))
    assert at_310["OD"]["values"]["PRK_RST_um"] == 310.0
    assert "prk_rst" not in at_310["OD"]["hard_stops"]
    assert "prk_pta" in at_310["OD"]["hard_stops"]
    assert at_310["OD"]["status"] == "STOP-DEFER"

    _, safe_310 = _evaluate(
        od_eye=_eye("OD", pachy_thinnest_um=500.0),
        od_plan=_plan("PRK", ablation_um=140.0),
    )
    assert safe_310["OD"]["values"]["PRK_RST_um"] == 310.0
    assert safe_310["OD"]["values"]["PRK_PTA_percent"] == 38.0
    assert safe_310["OD"]["status"] == "PASS"

    result, at_309 = _evaluate(od_plan=_plan("PRK", ablation_um=186.0))
    assert at_309["OD"]["values"]["PRK_RST_um"] == 309.0
    assert "prk_rst" in at_309["OD"]["hard_stops"]
    assert at_309["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_myopic_sphere_minus_10_allowed_but_minus_10_01_hard_stops():
    eye = _eye("OD", Kmean_D=45.0)
    _, at_limit = _evaluate(
        od_eye=eye,
        od_plan=_plan("PRK", intended_entered_sphere_D=-10.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert "sphere_magnitude" not in at_limit["OD"]["hard_stops"]
    assert at_limit["OD"]["status"] == "PASS"

    result, over_limit = _evaluate(
        od_eye=eye,
        od_plan=_plan("PRK", intended_entered_sphere_D=-10.01, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert "sphere_magnitude" in over_limit["OD"]["hard_stops"]
    assert over_limit["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_hyperopic_sphere_plus_6_allowed_but_plus_6_01_hard_stops():
    _, at_limit = _evaluate(
        od_plan=_plan("PRK", intended_entered_sphere_D=6.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert "sphere_magnitude" not in at_limit["OD"]["hard_stops"]
    assert at_limit["OD"]["status"] == "PASS"

    result, over_limit = _evaluate(
        od_plan=_plan("PRK", intended_entered_sphere_D=6.01, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert "sphere_magnitude" in over_limit["OD"]["hard_stops"]
    assert over_limit["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_final_k_36_and_48_allowed_while_35_99_and_48_01_stop():
    _, at_36 = _evaluate(
        od_eye=_eye("OD", Kmean_D=44.0),
        od_plan=_plan("PRK", intended_entered_sphere_D=-10.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert at_36["OD"]["values"]["estimated_final_Kmean_D"] == 36.0
    assert "final_kmean" not in at_36["OD"]["hard_stops"]

    _, below_36 = _evaluate(
        od_eye=_eye("OD", Kmean_D=43.99),
        od_plan=_plan("PRK", intended_entered_sphere_D=-10.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert round(below_36["OD"]["values"]["estimated_final_Kmean_D"], 2) == 35.99
    assert "final_kmean" in below_36["OD"]["hard_stops"]

    _, at_48 = _evaluate(
        od_eye=_eye("OD", Kmean_D=43.2),
        od_plan=_plan("PRK", intended_entered_sphere_D=6.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert at_48["OD"]["values"]["estimated_final_Kmean_D"] == 48.0
    assert "final_kmean" not in at_48["OD"]["hard_stops"]

    _, above_48 = _evaluate(
        od_eye=_eye("OD", Kmean_D=43.21),
        od_plan=_plan("PRK", intended_entered_sphere_D=6.0, intended_cylinder_signed_D=0.0, intended_axis_deg=0.0),
    )
    assert round(above_48["OD"]["values"]["estimated_final_Kmean_D"], 2) == 48.01
    assert "final_kmean" in above_48["OD"]["hard_stops"]


def test_mixed_astigmatism_never_uses_scalar_final_k_clearance():
    result, by_eye = _evaluate(
        od_plan=_plan("PRK", intended_entered_sphere_D=1.0, intended_cylinder_signed_D=-3.0, intended_axis_deg=90.0),
    )
    od = by_eye["OD"]
    assert od["values"]["intended_refractive_group"] == "MIXED"
    assert od["values"]["estimated_final_Kmean_D"] is None
    assert "Safety: mixed_astigmatism_meridional_final_k_assessment" in od["missing"]
    assert od["status"] == "ASSESSMENT INCOMPLETE"
    assert result["status"] == "ASSESSMENT INCOMPLETE"


def test_pta_at_or_over_40_percent_is_a_lasik_hard_stop():
    _, by_eye = _evaluate(
        procedure="LASIK",
        od_plan=_plan("LASIK", flap_um=100.0, ablation_um=118.0),
    )
    planning = by_eye["OD"]["planning"]
    assert planning["sequence"][0]["safe"] is False
    assert "lasik_pta" in planning["sequence"][0]["rejection_reasons"]
    assert planning["selected_plan"] == "Plan B"
    assert planning["sequence"][1]["safe"] is True
