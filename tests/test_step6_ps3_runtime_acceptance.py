"""Official Step 6 runtime acceptance for canonical PS3 behavior."""
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


def _plan(procedure="LASIK"):
    return {
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


def _evaluate(*, procedure="LASIK", od=None, os=None):
    result = evaluate_case(
        {"eyes": [od or _eye("OD"), os or _eye("OS")]},
        35,
        {"OD": _plan(procedure), "OS": _plan(procedure)},
        _modifiers(),
        software_version="step6-runtime-acceptance",
    )
    return result, {eye["eye"]: eye for eye in result["eyes"]}


def test_ps3_runtime_complete_normal_is_allowed_for_all_procedures():
    result, by_eye = _evaluate()
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["complete"] is True
    assert ps3["moderate_count"] == 0
    assert ps3["high_count"] == 0
    assert ps3["disposition"] == {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "ALLOWED"}
    assert by_eye["OD"]["status"] == "PASS"
    assert result["status"] == "PASS"


def test_low_cylinder_od_axis_discrepancy_has_no_ps3_risk_in_runtime_and_report():
    plans = {"OD": _plan(), "OS": _plan()}
    plans["OD"].update(manifest_entered_sphere_D=-1.25,
                       manifest_cylinder_signed_D=-0.50, manifest_axis_deg=120)
    result = evaluate_case(
        {"eyes": [_eye("OD", topographic_astig_D=0.4, topographic_steep_axis_deg=84.5), _eye("OS")]},
        21, plans, _modifiers(),
    )
    od = result["eyes"][0]
    assert od["ps3"]["complete"]
    assert od["ps3"]["moderate_count"] == od["ps3"]["high_count"] == 0
    assert od["ps3"]["disposition"]["lasik"] == "ALLOWED"
    report_finding = next(item for item in od["report_payload"]["ps3"]["findings"] if item["key"] == "astigmatic_study")
    assert report_finding["status"] == "NOT_REQUIRED"
    assert "no PS3 risk factor" in report_finding["detail"]


def test_ps3_runtime_one_moderate_defers_lasik_only():
    result, by_eye = _evaluate(od=_eye("OD", Kmean_D=49.0))
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["complete"] is True
    assert ps3["moderate_count"] == 1
    assert ps3["high_count"] == 0
    assert ps3["disposition"] == {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "DEFER"}
    assert by_eye["OD"]["lasik_assessment"]["status"] == "STOP-DEFER"
    assert by_eye["OD"]["status"] == "PASS"
    assert result["effective_eye_plans"]["OD"]["procedure"] == "PRK"
    assert result["status"] == "PASS"


def test_ps3_runtime_same_single_moderate_allows_prk():
    result, by_eye = _evaluate(procedure="PRK", od=_eye("OD", Kmean_D=49.0))
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["moderate_count"] == 1
    assert ps3["disposition"]["prk"] == "ALLOWED"
    assert by_eye["OD"]["status"] == "PASS"
    assert result["status"] == "PASS"


def test_ps3_runtime_two_moderates_defer_all_procedures():
    result, by_eye = _evaluate(procedure="PRK", od=_eye("OD", Kmean_D=49.0, pachy_thinnest_um=490.0))
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["moderate_count"] >= 2
    assert ps3["disposition"] == {"prk": "DEFER", "smile": "DEFER", "lasik": "DEFER"}
    assert by_eye["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_ps3_runtime_one_high_defer_all_procedures():
    result, by_eye = _evaluate(procedure="PRK", od=_eye("OD", B_Ele_Th_um=15.1))
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["high_count"] >= 1
    assert ps3["disposition"] == {"prk": "DEFER", "smile": "DEFER", "lasik": "DEFER"}
    assert by_eye["OD"]["status"] == "STOP-DEFER"


def test_ps3_runtime_incomplete_never_reports_reassuring_clearance():
    result, by_eye = _evaluate(procedure="PRK", od=_eye("OD", PPI_avg=None))
    ps3 = by_eye["OD"]["ps3"]
    assert ps3["complete"] is False
    assert "ppi_average" in ps3["missing_keys"]
    assert ps3["disposition"]["prk"] == "INCOMPLETE"
    assert "PS3: ppi_average" in by_eye["OD"]["missing"]
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert result["status"] == "ASSESSMENT INCOMPLETE"


def test_ps3_runtime_srax_exact_20_is_negative_but_20_1_is_high():
    _, at_20 = _evaluate(procedure="PRK", od=_eye("OD", srax_deg=20.0))
    finding_20 = next(item for item in at_20["OD"]["ps3"]["findings"] if item["key"] == "srax")
    assert finding_20["status"] == "NORMAL"

    result, over_20 = _evaluate(procedure="PRK", od=_eye("OD", srax_deg=20.1))
    finding_20_1 = next(item for item in over_20["OD"]["ps3"]["findings"] if item["key"] == "srax")
    assert finding_20_1["status"] == "HIGH"
    assert over_20["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"
