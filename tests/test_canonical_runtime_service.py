import inspect
import json

from canonical_runtime_service import POST_REFRACTIVE, evaluate_case


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
        "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0,
        "B_Ele_Th_um": 10.0,
        "srax": "NO",
        "srax_deg": 10.0,
    }
    values.update(overrides)
    return values


def _plan(procedure="LASIK", **overrides):
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
    }
    values.update(overrides)
    return values


def _case(od=None, os=None):
    return {"eyes": [od or _eye("OD"), os or _eye("OS")]}


def test_case_runtime_evaluates_od_then_os_and_returns_json_safe_payload():
    result = evaluate_case(
        _case(),
        35,
        {"OD": _plan(), "OS": _plan()},
        software_version="test",
    )
    assert [eye["eye"] for eye in result["eyes"]] == ["OD", "OS"]
    assert result["status"] == "PASS"
    assert all(eye["status"] == "PASS" for eye in result["eyes"])
    assert result["engine"] == "CERAI_CANONICAL_CLINICAL_CORE"
    assert result["version"] == "test"
    json.dumps(result)


def test_abnormal_od_cannot_be_diluted_by_normal_os():
    od = _eye("OD", BAD_D=2.6)
    result = evaluate_case(_case(od=od), 35, {"OD": _plan(), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "STOP-DEFER"
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == "STOP-DEFER"
    assert by_eye["OD"]["bad_summary"] == {"value": 2.6, "category": "ABNORMAL"}


def test_missing_od_value_never_cross_fills_from_os():
    od = _eye("OD", I_S=None)
    os = _eye("OS", I_S=0.0)
    result = evaluate_case(_case(od=od, os=os), 35, {"OD": _plan(), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert "Randleman: topography" in by_eye["OD"]["missing"]
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == "ASSESSMENT INCOMPLETE"


def test_prior_refractive_surgery_never_enters_virgin_core():
    result = evaluate_case(
        _case(),
        35,
        {"OD": _plan(prior="PRK"), "OS": _plan()},
    )
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == POST_REFRACTIVE
    assert by_eye["OD"]["canonical_result"] is None
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == POST_REFRACTIVE


def test_unsupported_procedure_is_incomplete_not_pass():
    result = evaluate_case(_case(), 35, {"OD": _plan(procedure="OTHER"), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert by_eye["OD"]["missing"] == ["procedure"]


def test_runtime_service_contains_no_installer_or_clinical_threshold_table():
    import canonical_runtime_service as module
    source = inspect.getsource(module)
    assert "def install(" not in source
    assert "core.hc_engine =" not in source
    assert "BAD_D >=" not in source
    assert "I_S >=" not in source
    assert "RSB <" not in source
