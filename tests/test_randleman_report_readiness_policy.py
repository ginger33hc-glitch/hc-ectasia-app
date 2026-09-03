"""Fail-closed report readiness contract for incomplete LASIK Randleman/ERSS."""
from copy import deepcopy

import pytest
from fastapi import HTTPException

import randleman_report_readiness_policy as policy


_COMPLETE_ROWS = {"topography": 0, "RSB": 0, "age": 0, "pachymetry": 0, "MRSE": 0}


def _eye(*, complete=True, needs_srax=False, needs_i_s=False):
    rows = dict(_COMPLETE_ROWS)
    missing = []
    total = 0
    if not complete:
        rows["topography"] = None
        missing = ["topography"]
        total = None
    return {
        "eye": "OD",
        "values": {"procedure": "LASIK", "prior_refractive_surgery": "no"},
        "randleman_erss": {
            "rows": rows,
            "total": total,
            "category": "LOW" if total is not None else None,
            "missing_erss_inputs": missing,
        },
        "erss_topography_evidence": {
            "needs_surgeon_SRAX": needs_srax,
            "needs_surgeon_I_S": needs_i_s,
        },
    }


def test_missing_front_map_srax_makes_patient_erss_incomplete_and_actionable():
    od = _eye(complete=False, needs_srax=True)

    assert not policy._erss_complete(od)
    messages = policy._component_requests(od)
    assert any("SRAX >20° confirmation" in message for message in messages)


def test_complete_patient_erss_passes_readiness_gate():
    od = _eye(complete=True)

    assert policy._erss_complete(od)
    assert policy._component_requests(od) == []


def test_export_validation_rejects_incomplete_patient_erss():
    decision = {"eyes": [_eye(complete=True)]}
    forged = deepcopy(decision)
    forged["eyes"][0]["randleman_erss"]["total"] = None
    forged["eyes"][0]["randleman_erss"]["rows"]["topography"] = None
    forged["eyes"][0]["randleman_erss"]["missing_erss_inputs"] = ["topography"]

    with pytest.raises(HTTPException) as exc:
        policy._validate_export_erss({"decision": forged})
    assert exc.value.status_code == 409
    assert "Randleman/ERSS is incomplete" in str(exc.value.detail)


def test_prk_is_not_forced_through_lasik_erss_gate():
    prk_eye = _eye(complete=False)
    prk_eye["values"]["procedure"] = "PRK"
    assert policy._erss_complete(prk_eye)
    assert policy._component_requests(prk_eye) == []
