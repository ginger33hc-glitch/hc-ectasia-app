from tests.test_nice_workflow import scenario, core, MODIFIERS


def test_debug_lasik_baseline_missing_state():
    extracted, plans = scenario("LASIK")
    result = core.hc_engine(extracted, 35, plans, MODIFIERS)["eyes"][0]
    assert result.get("status") != "DATA INSUFFICIENT", {
        "status": result.get("status"),
        "missing": result.get("missing"),
        "reasons": result.get("reasons"),
        "erss": result.get("randleman_erss"),
        "erss_topography_evidence": result.get("erss_topography_evidence"),
    }
