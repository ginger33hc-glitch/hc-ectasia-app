"""Fail-closed report readiness contract for incomplete LASIK Randleman/ERSS."""
from copy import deepcopy

import pytest
from fastapi import HTTPException

import canonical_engine as runtime
import randleman_report_readiness_policy as policy
from test_hc_engine import MODIFIERS, normal_eye, plan

core = runtime.core


def _decision(*, srax=None, srax_deg=0.0, surgeon_confirmed=False):
    extracted = {"eyes": [normal_eye("OD"), normal_eye("OS")], "critical_input_issues": []}
    for eye in extracted["eyes"]:
        eye["morphology_confidence"] = "HIGH"
        eye["erss_source_read"] = "DEDICATED_CURVATURE_PASS"
        eye["srax_deg"] = srax_deg
        if srax is not None:
            eye["srax"] = srax
        elif srax_deg is None:
            eye["srax"] = "UNCERTAIN"
        else:
            eye["srax"] = "YES" if float(srax_deg) > 20.0 else "NO"
        if surgeon_confirmed:
            eye["srax_deg"] = None
            eye.setdefault("field_provenance", {})["srax"] = [{"source": "SURGEON_CONFIRMED"}]
    plans = {eye: plan("LASIK", flap=100) for eye in ("OD", "OS")}
    return core.hc_engine(extracted, 35, plans, MODIFIERS)


def test_missing_front_map_srax_makes_patient_erss_incomplete_and_actionable():
    decision = _decision(srax="UNCERTAIN", srax_deg=None)
    od = decision["eyes"][0]

    assert not policy._erss_complete(od)
    messages = policy._component_requests(od)
    assert any("SRAX >20° confirmation" in message for message in messages)


def test_surgeon_confirmed_srax_can_complete_patient_erss():
    decision = _decision(srax="NO", srax_deg=None, surgeon_confirmed=True)
    od = decision["eyes"][0]

    assert policy._erss_complete(od), od
    erss = od["randleman_erss"]
    assert erss["total"] is not None
    assert erss["missing_erss_inputs"] == []
    assert od["erss_topography_evidence"]["SRAX_source"] == "SURGEON_CONFIRMED_FRONT_MAP_REVIEW"


def test_export_validation_rejects_incomplete_patient_erss():
    decision = _decision(srax_deg=0.0)
    forged = deepcopy(decision)
    od = forged["eyes"][0]
    od["randleman_erss"]["total"] = None
    od["randleman_erss"]["rows"]["topography"] = None
    od["randleman_erss"]["missing_erss_inputs"] = ["topography"]

    with pytest.raises(HTTPException) as exc:
        policy._validate_export_erss({"decision": forged})
    assert exc.value.status_code == 409
    assert "Randleman/ERSS is incomplete" in str(exc.value.detail)
