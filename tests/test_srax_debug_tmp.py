from copy import deepcopy

from fastapi.testclient import TestClient

from tests.test_nice_workflow import scenario, core, MODIFIERS
import assessment_workflow as workflow


def _snapshot(result):
    return {
        "status": result.get("status"),
        "missing": result.get("missing"),
        "reasons": result.get("reasons"),
        "erss": result.get("randleman_erss"),
        "erss_topography_evidence": result.get("erss_topography_evidence"),
        "microkeratome": result.get("microkeratome_planning"),
    }


def test_debug_lasik_baseline_missing_state():
    extracted, plans = scenario("LASIK")
    result = core.hc_engine(extracted, 35, plans, MODIFIERS)["eyes"][0]
    assert result.get("status") != "DATA INSUFFICIENT", _snapshot(result)


def test_debug_after_direct_microkeratome_wrapper_call():
    extracted, plans = scenario("LASIK")
    from microkeratome_planning_policy import hc_engine_with_microkeratome_planning
    before = hc_engine_with_microkeratome_planning(deepcopy(extracted), 35, deepcopy(plans), MODIFIERS)["eyes"][0]
    after = core.hc_engine(extracted, 35, plans, MODIFIERS)["eyes"][0]
    assert after.get("status") != "DATA INSUFFICIENT", {"before": _snapshot(before), "after": _snapshot(after)}


def test_debug_after_malformed_completion_then_exact_nice_case():
    first_extracted, first_plans = scenario("LASIK")
    ready = workflow.begin(core, first_extracted, 35, first_plans, MODIFIERS, {})
    first_plans["OD"]["surgeon_I_S_D"] = .5
    response = TestClient(core.app).post("/assessment/complete", json={
        "assessment_token": ready["assessment_token"], "age": 35,
        "eye_plans": first_plans, "patient_modifiers": MODIFIERS,
        "clinical_overrides": {"OD": None},
    })
    assert response.status_code == 422

    extracted, plans = scenario("LASIK")
    eye = extracted["eyes"][0]
    eye["K2_D"] = 43
    eye["nice_candidates"][0].update(B_Ele_Th_um=8, central_pachy_um=565)
    from microkeratome_planning_policy import hc_engine_with_microkeratome_planning
    before = hc_engine_with_microkeratome_planning(deepcopy(extracted), 35, deepcopy(plans), MODIFIERS)["eyes"][0]
    after = core.hc_engine(extracted, 35, plans, MODIFIERS)["eyes"][0]
    assert after.get("status") != "DATA INSUFFICIENT", {"before": _snapshot(before), "after": _snapshot(after)}
