import inspect
import json

import pytest

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
        "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
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
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers(**overrides):
    values = {
        "eye_rubbing": "no",
        "family_history": "no",
        "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }
    values.update(overrides)
    return values


def _case(od=None, os=None):
    return {"eyes": [od or _eye("OD"), os or _eye("OS")]}


def _evaluate(extracted=None, plans=None, modifiers=None, **kwargs):
    return evaluate_case(
        extracted or _case(),
        35,
        plans or {"OD": _plan(), "OS": _plan()},
        modifiers or _modifiers(),
        **kwargs,
    )


def test_case_runtime_evaluates_od_then_os_and_returns_json_safe_payload():
    result = _evaluate(software_version="test")
    assert [eye["eye"] for eye in result["eyes"]] == ["OD", "OS"]
    assert result["status"] == "PASS"
    assert all(eye["status"] == "PASS" for eye in result["eyes"])
    assert result["engine"] == "CERAI_CANONICAL_CLINICAL_CORE"
    assert result["version"] == "test"
    assert set(result["policy_versions"]) == {"clinical", "source_registry", "srax"}
    json.dumps(result)


def test_runtime_creates_one_renderer_neutral_report_payload_from_same_assessment():
    result = _evaluate(software_version="v-test")
    od = result["eyes"][0]
    report = od["report_payload"]
    assert report["eye"] == "OD"
    assert report["status"] == od["status"] == "PASS"
    assert report["randleman"]["total"] == od["score"]["total"]
    assert report["nice"]["total"] == od["nice"]["total"]
    assert report["bad"]["final_d"] == od["bad_summary"]["value"]
    assert report["tissue_safety"]["LASIK_RSB_um"] == od["values"]["LASIK_RSB_um"]
    assert report["versions"]["software"] == "v-test"
    assert report["versions"]["clinical_policy"] == result["policy_versions"]["clinical"]
    assert report["versions"]["source_registry"] == result["policy_versions"]["source_registry"]
    assert report["versions"]["srax_algorithm"] == result["policy_versions"]["srax"]


def test_surgeon_correction_is_labeled_in_canonical_report_payload():
    od = _eye("OD", surgeon_corrections=[{"field": "I_S", "original": 0.9, "value": 0.0}])
    result = _evaluate(extracted=_case(od=od))
    corrections = result["eyes"][0]["report_payload"]["manual_corrections"]
    assert corrections == [{"field": "I_S", "original": 0.9, "value": 0.0, "label": "SURGEON_CONFIRMED"}]


def test_abnormal_od_cannot_be_diluted_by_normal_os():
    od = _eye("OD", BAD_D=2.6)
    result = _evaluate(extracted=_case(od=od))
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "STOP-DEFER"
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == "STOP-DEFER"
    assert by_eye["OD"]["bad_summary"] == {"value": 2.6, "category": "ABNORMAL"}
    assert by_eye["OD"]["report_payload"]["status"] == "STOP-DEFER"


def test_missing_od_value_never_cross_fills_from_os():
    od = _eye("OD", I_S=None)
    os = _eye("OS", I_S=0.0)
    result = _evaluate(extracted=_case(od=od, os=os))
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert "Randleman: I_S" in by_eye["OD"]["missing"]
    assert "NICE: I_S_D" in by_eye["OD"]["missing"]
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == "ASSESSMENT INCOMPLETE"


def test_prior_refractive_surgery_never_enters_virgin_core():
    result = _evaluate(plans={"OD": _plan(prior="PRK"), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == POST_REFRACTIVE
    assert by_eye["OD"]["canonical_result"] is None
    assert by_eye["OD"]["report_payload"] is None
    assert by_eye["OS"]["status"] == "PASS"
    assert result["status"] == POST_REFRACTIVE


def test_unsupported_procedure_is_incomplete_not_pass():
    result = _evaluate(plans={"OD": _plan(procedure="OTHER"), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert by_eye["OD"]["missing"] == ["procedure"]


def test_eligibility_stop_enters_same_eye_final_disposition():
    result = _evaluate(plans={"OD": _plan(stable="no"), "OS": _plan()})
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "STOP-DEFER"
    assert by_eye["OS"]["status"] == "PASS"
    assert any("Refractive instability" in reason for reason in by_eye["OD"]["reasons"])


def test_eligibility_cautions_do_not_auto_stop():
    result = _evaluate(
        plans={"OD": _plan(cdva_below_20_20="yes"), "OS": _plan()},
        modifiers=_modifiers(dry_eye="yes"),
    )
    by_eye = {eye["eye"]: eye for eye in result["eyes"]}
    assert by_eye["OD"]["status"] == "CAUTION"
    assert by_eye["OS"]["status"] == "CAUTION"
    assert result["status"] == "CAUTION"


def test_missing_eligibility_documentation_is_explicitly_incomplete():
    result = _evaluate(modifiers=_modifiers(dry_eye="unknown"))
    assert result["status"] == "ASSESSMENT INCOMPLETE"
    assert all("Clinical eligibility: dry_eye" in eye["missing"] for eye in result["eyes"])


def test_eye_rubbing_and_family_history_remain_notes_only():
    result = _evaluate(modifiers=_modifiers(eye_rubbing="yes", family_history="yes"))
    assert result["status"] == "PASS"
    assert all(len(eye["clinical_modifiers"]) == 2 for eye in result["eyes"])


def test_missing_safety_dependency_is_exposed_in_runtime_missing_list():
    plans = {"OD": _plan(intended_cylinder_signed_D=None), "OS": _plan()}
    result = _evaluate(plans=plans)
    od = result["eyes"][0]
    assert od["status"] == "ASSESSMENT INCOMPLETE"
    assert "Safety: intended_cylinder_d" in od["missing"]


def test_patient_modifiers_are_required_not_silently_assumed_reassuring():
    try:
        evaluate_case(_case(), 35, {"OD": _plan(), "OS": _plan()}, None)
    except TypeError as exc:
        assert "patient_modifiers" in str(exc)
    else:
        raise AssertionError("Missing patient modifiers must not be treated as reassuring")


def test_runtime_service_contains_no_installer_or_clinical_threshold_table():
    import canonical_runtime_service as module
    source = inspect.getsource(module)
    assert "def install(" not in source
    assert "core.hc_engine =" not in source
    assert "BAD_D >=" not in source
    assert "I_S >=" not in source
    assert "RSB <" not in source


def test_prk_uses_shared_myopic_estimate_and_complete_erss_in_final_combination():
    plans = {name: _plan('PRK', ablation_um=None, optical_zone_mm=6.5,
                        intended_entered_sphere_D=-1.5, intended_cylinder_signed_D=0)
             for name in ('OD', 'OS')}
    result = _evaluate(
        extracted=_case(_eye('OD', I_S=0.61), _eye('OS', I_S=1.03)), plans=plans)
    assert [eye['status'] for eye in result['eyes']] == ['PASS', 'PASS WITH CAUTION']
    assert [eye['score']['total'] for eye in result['eyes']] == [1, 3]
    for eye in result['eyes']:
        assert eye['values']['PRK_RST_um'] == 545 - 50 - 22.5
        assert eye['report_payload']['randleman']['total'] == eye['score']['total']
        assert not eye['missing']


def test_prk_preserves_entered_ablation_and_requires_missing_erss_input():
    plans = {name: _plan('PRK', ablation_um=60, optical_zone_mm=6.5)
             for name in ('OD', 'OS')}
    result = _evaluate(plans=plans)
    assert all(eye['values']['PRK_RST_um'] == 435 for eye in result['eyes'])
    result = evaluate_case(_case(), None, plans, _modifiers())
    assert all(eye['score']['total'] is None for eye in result['eyes'])
    assert result['status'] == 'ASSESSMENT INCOMPLETE'


def test_surgeon_confirmed_negative_srax_completes_both_erss_and_ps3():
    od = _eye('OD', I_S=-0.92, srax_deg=None, srax='NO',
              field_provenance={'srax': [{'source': 'SURGEON_CONFIRMED'}]})
    result = _evaluate(extracted=_case(od), plans={'OD': _plan('PRK'), 'OS': _plan('PRK')})
    eye = result['eyes'][0]
    assert eye['score']['total'] == 1
    assert eye['ps3']['complete']
    assert eye['status'] == 'PASS'
    od['field_provenance'] = {}
    eye = _evaluate(extracted=_case(od))['eyes'][0]
    assert eye['score']['total'] is None
    assert not eye['ps3']['complete']


def test_ps3_compares_bad_flat_axis_only_and_never_substitutes_steep_axis():
    od = _eye('OD', topographic_astig_D=3.3, topographic_steep_axis_deg=92.8,
              bad_flat_axis_deg=2.8)
    plans = {name: _plan(manifest_cylinder_signed_D=-3, manifest_axis_deg=180)
             for name in ('OD', 'OS')}
    eye = _evaluate(extracted=_case(od), plans=plans)['eyes'][0]
    factor = next(f for f in eye['ps3']['findings'] if f['key'] == 'astigmatic_study')
    assert factor['status'] == 'NORMAL'
    assert '2.8°' in factor['detail']
    assert eye['report_payload']['source_values']['topographic_steep_axis_deg'] == 92.8
    od['bad_flat_axis_deg'] = None
    eye = _evaluate(extracted=_case(od), plans=plans)['eyes'][0]
    assert not eye['ps3']['complete']


def test_failed_lasik_automatically_evaluates_prk_and_retains_failed_assessment():
    result = _evaluate(extracted=_case(_eye('OD', PPI_avg=1.3)))
    od, os = result['eyes']
    assert od['lasik_assessment']['status'] == 'STOP-DEFER'
    assert od['lasik_assessment']['report_payload']['procedure'] == 'LASIK'
    assert od['report_payload']['procedure'] == 'PRK'
    assert od['status'] == 'PASS'
    assert od['values']['PRK_RST_um'] == 445
    assert result['effective_eye_plans']['OD']['flap_um'] is None
    assert result['procedure_transitions'][0]['message'] == 'OD: LASIK failed. Now evaluating PRK.'
    assert os['report_payload']['procedure'] == 'LASIK'
    assert 'lasik_assessment' not in os


def test_prk_fallback_keeps_shared_stops_and_missing_data():
    result = _evaluate(extracted=_case(_eye('OD', pachy_thinnest_um=498, PPI_avg=1.3,
                                           srax=None, srax_deg=None)))
    od = result['eyes'][0]
    assert od['report_payload']['procedure'] == 'PRK'
    assert od['status'] == 'STOP-DEFER'
    assert not od['ps3']['complete']
    assert 'Randleman: SRAX' in od['missing']
    assert od['ps3']['moderate_count'] == 2


def test_incomplete_lasik_does_not_trigger_prk_fallback():
    result = _evaluate(extracted=_case(_eye('OD', srax=None, srax_deg=None)))
    assert result['eyes'][0]['status'] == 'ASSESSMENT INCOMPLETE'
    assert not result['procedure_transitions']
    assert result['effective_eye_plans']['OD']['procedure'] == 'LASIK'


@pytest.mark.parametrize('ablation,expected_pta,expected_status', [
    (166, 36.0, 'PASS'),
    (189.94, 39.99, 'PASS'),
    (190, 40.0, 'STOP-DEFER'),
    (190.06, 40.01, 'STOP-DEFER'),
])
@pytest.mark.parametrize('requested_procedure', ['PRK', 'LASIK'])
def test_shared_pta_gate_in_direct_prk_and_automatic_transition(
    ablation, expected_pta, expected_status, requested_procedure,
):
    extracted = _case(
        _eye('OD', pachy_thinnest_um=600, central_pachy_um=605,
             PPI_avg=1.3 if requested_procedure == 'LASIK' else 1.0),
        _eye('OS', pachy_thinnest_um=600, central_pachy_um=605),
    )
    result = _evaluate(extracted=extracted, plans={
        'OD': _plan(requested_procedure, ablation_um=ablation,
                    optical_zone_mm=6.5, transition_zone_mm=9.0),
        'OS': _plan(),
    })
    od, os = result['eyes']
    safety = od['report_payload']['tissue_safety']
    assert od['report_payload']['procedure'] == 'PRK'
    assert od['status'] == od['report_payload']['status'] == expected_status
    assert safety['PRK_PTA_percent'] == pytest.approx(expected_pta)
    assert od['values']['PRK_PTA_percent'] == safety['PRK_PTA_percent']
    assert safety['LASIK_PTA_percent'] is None
    assert safety['hard_stops']['prk_pta'] is (expected_status == 'STOP-DEFER')
    assert not safety['hard_stops']['prk_rst']
    assert not od['missing']
    assert os['status'] == 'PASS'
    assert 'lasik_assessment' not in os
    if requested_procedure == 'LASIK':
        assert od['lasik_assessment']['status'] == 'STOP-DEFER'
        assert result['effective_eye_plans']['OD']['flap_um'] is None
        assert result['effective_eye_plans']['OD']['ablation_um'] == ablation
        assert result['effective_eye_plans']['OD']['optical_zone_mm'] == 6.5
        assert len(result['procedure_transitions']) == 1


def test_prk_rst_stop_remains_independent_of_passing_pta():
    result = _evaluate(
        extracted=_case(*[_eye(name, pachy_thinnest_um=480, central_pachy_um=485)
                          for name in ('OD', 'OS')]),
        plans={name: _plan('PRK', ablation_um=125) for name in ('OD', 'OS')},
    )
    for eye in result['eyes']:
        safety = eye['report_payload']['tissue_safety']
        assert safety['PRK_RST_um'] == 305
        assert safety['PRK_PTA_percent'] < 40
        assert safety['hard_stops']['prk_rst']
        assert not safety['hard_stops']['prk_pta']
        assert eye['status'] == 'STOP-DEFER'


def test_prk_missing_actual_hyperopic_ablation_cannot_clear_pta():
    plans = {name: _plan('PRK', ablation_um=None,
                        intended_entered_sphere_D=2, intended_cylinder_signed_D=0)
             for name in ('OD', 'OS')}
    result = _evaluate(plans=plans)
    for eye in result['eyes']:
        assert eye['values']['PRK_PTA_percent'] is None
        assert eye['status'] == 'ASSESSMENT INCOMPLETE'
        assert any('ablation' in field for field in eye['missing'])
