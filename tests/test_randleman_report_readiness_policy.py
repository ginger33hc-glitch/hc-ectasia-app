"""Report generation must fail closed when LASIK Randleman/ERSS is incomplete."""
from copy import deepcopy

import pytest
from fastapi import HTTPException

import canonical_engine as runtime
import assessment_workflow as workflow
from test_hc_engine import MODIFIERS, normal_eye, plan

core = runtime.core


def _scenario():
    extracted = {"eyes": [normal_eye("OD"), normal_eye("OS")], "critical_input_issues": []}
    for eye in extracted["eyes"]:
        eye["srax"] = "NO"
        eye["srax_deg"] = 0.0
        eye["morphology_confidence"] = "HIGH"
        eye["erss_source_read"] = "DEDICATED_CURVATURE_PASS"
    plans = {eye: plan("LASIK", flap=100) for eye in ("OD", "OS")}
    return extracted, plans


def test_missing_front_map_srax_blocks_report_and_asks_surgeon():
    extracted, plans = _scenario()
    extracted["eyes"][0]["srax"] = "UNCERTAIN"
    extracted["eyes"][0]["srax_deg"] = None

    result = workflow.begin(core, extracted, 35, plans, MODIFIERS, {})

    assert result["workflow_status"] == "NEEDS_INPUT"
    assert result["report_token"] is None
    requests = [item for item in result["input_requests"] if item.get("eye") == "OD"]
    assert any(item.get("key") == "srax" for item in requests)
    assert any("Randleman/ERSS" in item.get("label", "") for item in requests)


def test_surgeon_srax_confirmation_allows_randleman_completion():
    extracted, plans = _scenario()
    extracted["eyes"][0]["srax"] = "UNCERTAIN"
    extracted["eyes"][0]["srax_deg"] = None
    result = workflow.begin(core, extracted, 35, plans, MODIFIERS, {})

    ready = workflow.complete(core, {
        "assessment_token": result["assessment_token"],
        "age": 35,
        "eye_plans": plans,
        "patient_modifiers": MODIFIERS,
        "clinical_overrides": {"OD": {"srax": "NO"}},
    })

    assert ready["workflow_status"] == "READY", ready
    erss = ready["decision"]["eyes"][0]["randleman_erss"]
    assert erss["total"] is not None
    assert erss["missing_erss_inputs"] == []
    assert ready["report_token"]


def test_incomplete_randleman_cannot_be_exported_even_with_stale_ready_snapshot():
    extracted, plans = _scenario()
    ready = workflow.begin(core, extracted, 35, plans, MODIFIERS, {})
    assert ready["workflow_status"] == "READY", ready

    token = ready["assessment_token"]
    session = workflow._sessions[token]
    forged = deepcopy(session["ready"])
    forged["decision"]["eyes"][0]["randleman_erss"]["total"] = None
    forged["decision"]["eyes"][0]["randleman_erss"]["rows"]["topography"] = None
    forged["decision"]["eyes"][0]["randleman_erss"]["missing_erss_inputs"] = ["topography"]
    session["ready"] = forged

    with pytest.raises(HTTPException) as exc:
        workflow.export_payload({
            "assessment_token": token,
            "report_token": forged["report_token"],
        })
    assert exc.value.status_code == 409
    assert "Randleman/ERSS is incomplete" in str(exc.value.detail)
