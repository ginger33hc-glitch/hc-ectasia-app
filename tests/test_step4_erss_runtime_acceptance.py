"""Official Step 4 runtime acceptance: I-S -> SRAX -> Randleman/ERSS.

These tests exercise the case-level canonical runtime, not only isolated scoring helpers.
"""
from canonical_runtime_service import evaluate_case


def _eye(name="OD", *, i_s=0.0, srax_deg=10.0):
    return {
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
        "I_S": i_s,
        "topographic_astig_D": 1.0,
        "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0,
        "B_Ele_Th_um": 10.0,
        "srax": "UNCERTAIN" if srax_deg is None else ("YES" if srax_deg > 20.0 else "NO"),
        "srax_deg": srax_deg,
    }


def _plan():
    return {
        "prior": "no",
        "procedure": "LASIK",
        "flap_um": 100.0,
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
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }


def _evaluate(i_s, srax_deg):
    extracted = {"eyes": [_eye("OD", i_s=i_s, srax_deg=srax_deg), _eye("OS", i_s=0.0, srax_deg=10.0)]}
    result = evaluate_case(
        extracted,
        35,
        {"OD": _plan(), "OS": _plan()},
        _modifiers(),
        software_version="step4-runtime-acceptance",
    )
    return {eye["eye"]: eye for eye in result["eyes"]}["OD"]


def test_i_s_1_01_sets_three_point_topography_without_requiring_srax():
    od = _evaluate(1.01, None)
    assert od["score"]["rows"]["topography"] == 3
    assert od["score"]["category"] == "INFERIOR_STEEPENING_SRA"
    assert "Randleman: SRAX" not in od["missing"]


def test_i_s_1_40_sets_four_point_topography_without_requiring_srax():
    od = _evaluate(1.40, None)
    assert od["score"]["rows"]["topography"] == 4
    assert od["score"]["category"] == "ABNORMAL_ECTATIC"
    assert "Randleman: SRAX" not in od["missing"]


def test_srax_runtime_boundary_is_strictly_greater_than_20():
    expected = {19.9: 1, 20.0: 1, 20.1: 3}
    actual = {
        value: _evaluate(0.51, value)["score"]["rows"]["topography"]
        for value in expected
    }
    assert actual == expected


def test_negative_i_s_stays_non_inferior_even_with_large_srax():
    od = _evaluate(-0.94, 45.0)
    assert od["score"]["category"] == "ASYMMETRIC_BOWTIE"
    assert od["score"]["rows"]["topography"] == 1
    assert "Randleman: SRAX" not in od["missing"]


def test_i_s_and_srax_remain_one_topography_row_not_additive():
    od = _evaluate(0.51, 20.1)
    assert od["score"]["rows"]["topography"] == 3
    assert od["score"]["total"] == 3


def test_missing_i_s_is_incomplete_even_when_srax_is_positive():
    od = _evaluate(None, 30.0)
    assert od["score"]["rows"]["topography"] is None
    assert od["score"]["total"] is None
    assert "Randleman: I_S" in od["missing"]
