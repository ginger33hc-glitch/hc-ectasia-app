"""Official Step 5 runtime acceptance for the four-input NICE rule."""
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


def _plan():
    return {
        "prior": "no", "procedure": "LASIK", "flap_um": 100.0, "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": -1.0, "manifest_axis_deg": 90.0,
        "intended_entered_sphere_D": -2.0, "intended_cylinder_signed_D": -1.0, "intended_axis_deg": 90.0,
        "stable": "yes", "progression": "no", "cdva_below_20_20": "no",
    }


def _modifiers():
    return {
        "eye_rubbing": "no", "family_history": "no", "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no", "collagen_tissue_disease": "no", "drug_usage": "no",
        "dry_eye": "no", "systemic_disease": "no",
    }


def _evaluate(**od_values):
    result = evaluate_case(
        {"eyes": [_eye("OD", **od_values), _eye("OS")]},
        35,
        {"OD": _plan(), "OS": _plan()},
        _modifiers(),
        software_version="step5-runtime-acceptance",
    )
    return {eye["eye"]: eye for eye in result["eyes"]}["OD"]


def test_nice_runtime_all_low_rows_total_four_no_escalation():
    od = _evaluate(K2_D=44.99, central_pachy_um=521.0, B_Ele_Th_um=15.5, I_S=0.99)
    assert od["nice"]["rows"] == {"K2": 1, "central_pachymetry": 1, "B_Ele_Th": 1, "I_S": 1}
    assert od["nice"]["total"] == 4
    assert od["nice"]["category"] == "NO_NICE_ESCALATION"


def test_nice_runtime_exact_middle_boundaries_total_eight_caution():
    od = _evaluate(K2_D=45.0, central_pachy_um=520.0, B_Ele_Th_um=15.5001, I_S=1.0)
    assert od["nice"]["rows"] == {"K2": 2, "central_pachymetry": 2, "B_Ele_Th": 2, "I_S": 2}
    assert od["nice"]["total"] == 8
    assert od["nice"]["category"] == "CAUTION"


def test_nice_runtime_high_boundaries_stop_at_nine_or_more():
    od = _evaluate(K2_D=47.0001, central_pachy_um=499.999, B_Ele_Th_um=18.0, I_S=1.4001)
    assert od["nice"]["rows"] == {"K2": 3, "central_pachymetry": 3, "B_Ele_Th": 3, "I_S": 3}
    assert od["nice"]["total"] == 12
    assert od["nice"]["category"] == "HARD_STOP"
    assert od["status"] == "STOP-DEFER"


def test_nice_runtime_missing_input_is_explicitly_incomplete_not_reassuring():
    od = _evaluate(central_pachy_um=None)
    assert od["nice"]["total"] is None
    assert od["nice"]["category"] == "INCOMPLETE"
    assert od["nice"]["missing"] == ["central_pachy_um"]
    assert "NICE: central_pachy_um" in od["missing"]
    assert od["status"] == "ASSESSMENT INCOMPLETE"
