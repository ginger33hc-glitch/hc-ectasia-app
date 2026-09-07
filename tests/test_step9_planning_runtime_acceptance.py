"""Official Step 9 runtime acceptance for procedure planning."""
from canonical_runtime_service import evaluate_case


def _eye(name="OD", **overrides):
    values = {
        "eye": name,
        "Kmean_D": 44.0,
        "K2_D": 44.0,
        "central_pachy_um": 550.0,
        "pachy_thinnest_um": 545.0,
        "BAD_D": 1.0,
        "Df": -0.2, "Db": 0.4, "Dp": 0.3, "Dt": 0.2, "Da": 0.5,
        "ARTmax_um": 380.0,
        "PPI_min": 0.7, "PPI_avg": 1.0, "PPI_max": 1.2,
        "I_S": 0.0,
        "topographic_astig_D": 1.0,
        "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0,
        "B_Ele_Th_um": 10.0,
        "srax": "NO", "srax_deg": 10.0,
    }
    values.update(overrides)
    return values


def _plan(procedure="LASIK", **overrides):
    values = {
        "prior": "no",
        "procedure": procedure,
        "flap_um": 100.0 if procedure == "LASIK" else 100.0,
        "ablation_um": None if procedure == "LASIK" else 50.0,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0,
        "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": 0.0,
        "intended_axis_deg": 0.0,
        "stable": "yes", "progression": "no", "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers():
    return {
        "eye_rubbing": "no", "family_history": "no", "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no", "collagen_tissue_disease": "no", "drug_usage": "no",
        "dry_eye": "no", "systemic_disease": "no",
    }


def _evaluate(*, od_eye=None, od_plan=None, os_plan=None):
    result = evaluate_case(
        {"eyes": [od_eye or _eye("OD"), _eye("OS")]},
        35,
        {"OD": od_plan or _plan(), "OS": os_plan or _plan()},
        _modifiers(),
        software_version="step9-runtime-acceptance",
    )
    return result, {eye["eye"]: eye for eye in result["eyes"]}


def test_plan_a_safe_is_selected_first_and_later_plans_are_not_evaluated():
    result, by_eye = _evaluate()
    planning = by_eye["OD"]["planning"]
    assert planning["selected_plan"] == "Plan A"
    assert [item["plan"] for item in planning["sequence"]] == ["Plan A"]
    assert planning["sequence"][0]["safe"] is True
    assert result["effective_eye_plans"]["OD"]["plan_name"] == "Plan A"
    assert result["effective_eye_plans"]["OD"]["flap_um"] == 100.0
    assert result["effective_eye_plans"]["OD"]["optical_zone_mm"] == 6.5
    assert result["effective_eye_plans"]["OD"]["transition_zone_mm"] == 9.0


def test_plan_a_unsafe_plan_b_safe_selects_b_and_keeps_a_rejection_reason():
    # Myopic MRSE -9 D -> A estimated ablation 135 µm, B 108 µm.
    eye = _eye("OD", Kmean_D=44.0, pachy_thinnest_um=520.0)
    plan = _plan(intended_entered_sphere_D=-9.0, intended_cylinder_signed_D=0.0)
    _, by_eye = _evaluate(od_eye=eye, od_plan=plan)
    planning = by_eye["OD"]["planning"]
    assert planning["selected_plan"] == "Plan B"
    assert [item["plan"] for item in planning["sequence"]] == ["Plan A", "Plan B"]
    assert planning["sequence"][0]["safe"] is False
    assert planning["sequence"][0]["rejection_reasons"]
    assert planning["sequence"][1]["safe"] is True
    assert planning["sequence"][0]["ablation_um"] == 135.0
    assert planning["sequence"][1]["ablation_um"] == 108.0


def test_plan_c_is_selected_only_after_a_and_b_fail():
    # Intended sphere -10.00 D remains within the hard-stop boundary; -0.20 D cylinder
    # makes MRSE -10.10 D. At CCT 520, B RSB is 298.8 and C RSB is 308.8 µm.
    eye = _eye("OD", Kmean_D=45.0, pachy_thinnest_um=520.0)
    plan = _plan(
        intended_entered_sphere_D=-10.0,
        intended_cylinder_signed_D=-0.2,
        intended_axis_deg=90.0,
    )
    _, by_eye = _evaluate(od_eye=eye, od_plan=plan)
    planning = by_eye["OD"]["planning"]
    assert planning["selected_plan"] == "Plan C"
    assert [item["plan"] for item in planning["sequence"]] == ["Plan A", "Plan B", "Plan C"]
    assert [item["safe"] for item in planning["sequence"]] == [False, False, True]
    assert planning["sequence"][2]["flap_um"] == 90.0


def test_no_plan_selected_when_even_plan_c_fails_same_canonical_safety_engine():
    eye = _eye("OD", Kmean_D=45.0, pachy_thinnest_um=510.0)
    plan = _plan(
        intended_entered_sphere_D=-10.0,
        intended_cylinder_signed_D=-0.2,
        intended_axis_deg=90.0,
    )
    result, by_eye = _evaluate(od_eye=eye, od_plan=plan)
    planning = by_eye["OD"]["planning"]
    assert planning["selected_plan"] is None
    assert [item["plan"] for item in planning["sequence"]] == ["Plan A", "Plan B", "Plan C"]
    assert all(item["safe"] is False for item in planning["sequence"])
    assert by_eye["OD"]["status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


def test_prk_forces_flap_none_and_mmc_boundary_is_exact():
    result, by_eye = _evaluate(
        od_plan=_plan(
            "PRK",
            intended_entered_sphere_D=-3.99,
            intended_cylinder_signed_D=0.0,
            intended_axis_deg=0.0,
        ),
        os_plan=_plan("PRK"),
    )
    assert result["effective_eye_plans"]["OD"]["flap_um"] is None
    assert result["effective_eye_plans"]["OD"]["flap_status"] == "NOT_APPLICABLE"
    assert by_eye["OD"]["planning"]["mmc_guidance"] == "RECOMMENDED"

    result, by_eye = _evaluate(
        od_plan=_plan(
            "PRK",
            intended_entered_sphere_D=-4.0,
            intended_cylinder_signed_D=0.0,
            intended_axis_deg=0.0,
        ),
        os_plan=_plan("PRK"),
    )
    assert by_eye["OD"]["planning"]["mmc_guidance"] == "MANDATORY"


def test_hyperopic_prk_mmc_is_mandatory_and_mixed_requires_review():
    _, hyperopic = _evaluate(
        od_plan=_plan(
            "PRK",
            intended_entered_sphere_D=2.0,
            intended_cylinder_signed_D=0.0,
            intended_axis_deg=0.0,
        ),
        os_plan=_plan("PRK"),
    )
    assert hyperopic["OD"]["planning"]["mmc_guidance"] == "MANDATORY"

    _, mixed = _evaluate(
        od_plan=_plan(
            "PRK",
            intended_entered_sphere_D=1.0,
            intended_cylinder_signed_D=-3.0,
            intended_axis_deg=90.0,
        ),
        os_plan=_plan("PRK"),
    )
    assert mixed["OD"]["planning"]["mmc_guidance"] == "REVIEW_REQUIRED"


def test_lasik_requires_fresh_flap_selection_before_automatic_a_b_c_planning():
    result, by_eye = _evaluate(od_plan=_plan("LASIK", flap_um=None))
    planning = by_eye["OD"]["planning"]
    assert planning["selected_plan"] is None
    assert planning["sequence"] == []
    assert "LASIK flap selection required" in planning["rejection_reasons"][0]
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert result["effective_eye_plans"]["OD"].get("flap_um") is None


def test_hyperopic_lasik_does_not_use_myopic_ablation_estimate_for_fallbacks():
    plan = _plan(
        "LASIK",
        ablation_um=70.0,
        intended_entered_sphere_D=2.0,
        intended_cylinder_signed_D=0.0,
        intended_axis_deg=0.0,
    )
    _, by_eye = _evaluate(od_plan=plan)
    planning = by_eye["OD"]["planning"]
    # The entered actual ablation may be used for default Plan A, but no automatic B/C
    # myopic linear estimate is permitted for hyperopic treatment.
    assert planning["sequence"][0]["plan"] == "Plan A"
    assert planning["sequence"][0]["ablation_source"] != "CERAI_MYOPIC_ESTIMATE"
    for item in planning["sequence"][1:]:
        assert item["ablation_source"] == "ACTUAL_PLAN_MAX_ABLATION_REQUIRED"
