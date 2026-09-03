from copy import deepcopy

from tests.test_nice_workflow import scenario, core, MODIFIERS


def _snapshot(result):
    return {
        "status": result.get("status"),
        "missing": result.get("missing"),
        "reasons": result.get("reasons"),
        "erss": result.get("randleman_erss"),
        "erss_topography_evidence": result.get("erss_topography_evidence"),
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
