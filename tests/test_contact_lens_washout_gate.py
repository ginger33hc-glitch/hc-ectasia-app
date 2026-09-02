from copy import deepcopy
from types import SimpleNamespace

import assessment_workflow as workflow


def _core(call_counter, decision=None):
    def apply_extracted_corrections(extracted, plans):
        return deepcopy(plans)

    def hc_engine(extracted, age, effective, modifiers, metadata):
        call_counter["count"] += 1
        return deepcopy(decision or {"eyes": [], "critical_input_issues": []})

    return SimpleNamespace(
        MORPHOLOGY={
            "NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA",
            "ABNORMAL_ECTATIC", "UNCERTAIN",
        },
        apply_extracted_corrections=apply_extracted_corrections,
        hc_engine=hc_engine,
    )


def _session():
    return {
        "extracted": {"eyes": []},
        "ready": None,
        "expires": 0,
        "source_images": [],
    }


def _respond(modifiers, decision=None):
    calls = {"count": 0}
    result = workflow._respond(
        _core(calls, decision),
        "token",
        _session(),
        30,
        {},
        modifiers,
        {},
        {},
    )
    return result, calls["count"]


def test_soft_lens_nine_days_blocks_before_engine():
    result, calls = _respond({
        "contact_lens_type": "SOFT",
        "contact_lens_discontinuation_days": 9,
    })
    assert calls == 0
    assert result["workflow_status"] == "CONTACT_LENS_WASHOUT_REQUIRED"
    assert result["contact_lens_washout"]["required_days"] == 10
    assert result["contact_lens_washout"]["remaining_days"] == 1
    assert result["report_token"] is None
    assert "repeat Pentacam" in result["message"]


def test_soft_lens_ten_full_days_allows_engine_and_supersedes_legacy_fourteen_day_missing():
    legacy = {
        "eyes": [{
            "eye": "OD",
            "missing": [workflow._LEGACY_SOFT_CONTACT_LENS_MESSAGE],
        }],
        "critical_input_issues": [],
    }
    result, calls = _respond({
        "contact_lens_type": "SOFT",
        "contact_lens_discontinuation_days": 10,
    }, legacy)
    assert calls == 1
    assert result["workflow_status"] == "READY"
    assert result["decision"]["eyes"][0]["missing"] == []
    assert result["report_token"]


def test_rigid_lens_twenty_days_blocks_before_engine():
    result, calls = _respond({
        "contact_lens_type": "RIGID",
        "contact_lens_discontinuation_days": 20,
    })
    assert calls == 0
    assert result["workflow_status"] == "CONTACT_LENS_WASHOUT_REQUIRED"
    assert result["contact_lens_washout"]["required_days"] == 21
    assert result["contact_lens_washout"]["remaining_days"] == 1


def test_rigid_lens_twenty_one_full_days_allows_engine():
    result, calls = _respond({
        "contact_lens_type": "RIGID",
        "contact_lens_discontinuation_days": 21,
    })
    assert calls == 1
    assert result["workflow_status"] != "CONTACT_LENS_WASHOUT_REQUIRED"


def test_contact_lens_days_must_be_documented_when_lens_is_used():
    result, calls = _respond({"contact_lens_type": "SOFT"})
    assert calls == 0
    assert result["workflow_status"] == "CONTACT_LENS_WASHOUT_REQUIRED"
    assert result["input_requests"][0]["form_id"] == "contact_lens_days"


def test_none_lens_type_allows_engine_without_days():
    result, calls = _respond({"contact_lens_type": "NONE"})
    assert calls == 1
    assert result["workflow_status"] != "CONTACT_LENS_WASHOUT_REQUIRED"
