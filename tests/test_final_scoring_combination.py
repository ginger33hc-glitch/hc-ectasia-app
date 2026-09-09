"""Final aggregation counts scoring systems, never findings or fellow eyes."""
from itertools import product

import pytest

from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE, CAUTION, PASS, PASS_WITH_CAUTION, STOP_DEFER,
    DecisionFinding, finalize_disposition, presentation_class,
)
from canonical_runtime_service import _overall_status
from test_step10_canonical_reports import _payload, _section
import reports

KEYS = ("randleman_erss", "nice", "ps3", "bad_d")


@pytest.mark.parametrize("statuses", list(product((PASS, CAUTION), repeat=4)))
def test_every_completed_scoring_combination(statuses):
    findings = tuple(DecisionFinding(k, s) for k, s in zip(KEYS, statuses))
    count = statuses.count(CAUTION)
    expected = PASS if count <= 1 else PASS_WITH_CAUTION if count == 2 else CAUTION
    result = finalize_disposition(findings)
    assert result.status == expected
    assert len(result.caution_drivers) == count
    assert tuple(f.status for f in findings) == statuses


@pytest.mark.parametrize("gate", (STOP_DEFER, ASSESSMENT_INCOMPLETE))
def test_independent_gate_overrides_single_scoring_caution(gate):
    findings = [DecisionFinding(k, CAUTION if k == "nice" else PASS) for k in KEYS]
    findings.append(DecisionFinding("safety_or_missing", gate))
    assert finalize_disposition(findings).status == gate


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("gate", (STOP_DEFER, ASSESSMENT_INCOMPLETE))
def test_each_system_stop_or_missing_blocks_pass(key, gate):
    findings = [DecisionFinding(k, gate if k == key else PASS) for k in KEYS]
    assert finalize_disposition(findings).status == gate


def test_stop_dominates_missing_and_cautions():
    findings = [DecisionFinding(k, CAUTION) for k in KEYS]
    findings += [DecisionFinding("missing", ASSESSMENT_INCOMPLETE), DecisionFinding("bad_d", STOP_DEFER)]
    assert finalize_disposition(findings).status == STOP_DEFER


def test_duplicate_findings_are_not_counted_as_extra_scoring_systems():
    findings = [DecisionFinding(k, CAUTION if k == "nice" else PASS) for k in KEYS]
    findings.append(DecisionFinding("nice", CAUTION, "second detail"))
    assert finalize_disposition(findings).status == PASS


def test_independent_caution_is_not_downgraded():
    findings = [DecisionFinding(k, CAUTION if k == "nice" else PASS) for k in KEYS]
    findings.append(DecisionFinding("clinical_eligibility", CAUTION))
    assert finalize_disposition(findings).status == CAUTION


@pytest.mark.parametrize("statuses,expected", [
    ((PASS, PASS_WITH_CAUTION), PASS_WITH_CAUTION),
    ((PASS_WITH_CAUTION, PASS_WITH_CAUTION), PASS_WITH_CAUTION),
    ((PASS_WITH_CAUTION, CAUTION), CAUTION),
    ((PASS_WITH_CAUTION, STOP_DEFER), STOP_DEFER),
    ((PASS_WITH_CAUTION, ASSESSMENT_INCOMPLETE), ASSESSMENT_INCOMPLETE),
])
def test_bilateral_result_preserves_worse_eye_without_counting_eyes(statuses, expected):
    assert _overall_status([{"eye": eye, "status": status} for eye, status in zip(("OD", "OS"), statuses)]) == expected


def test_actual_runtime_one_vs_two_scoring_cautions_and_report():
    one = _payload(K2_D=45.0)
    eye = one["decision"]["eyes"][0]
    assert eye["status"] == PASS
    assert one["decision"]["status"] == PASS
    assert eye["planning"]["selected_plan"] == "Plan A"
    assert eye["report_payload"]["status"] == PASS
    assert presentation_class(eye["status"]) == "pass"
    assert reports._status_palette(eye["status"])[0] == reports.GREEN
    model = reports.canonical_report_model(one)
    assert ["Disposition", "PASS", ""] in _section(model, "OD", "Randleman / ERSS")
    assert ["Classification", "CAUTION", "CAUTION"] in _section(model, "OD", "NICE")
    two = _payload(I_S=1.03)
    assert two["decision"]["eyes"][0]["status"] == PASS_WITH_CAUTION
    assert two["decision"]["status"] == PASS_WITH_CAUTION


def test_bad_is_a_fourth_system_and_component_flags_are_not_counted():
    bad_only = _payload(BAD_D=2.0, Df=3.0, Db=3.0, ARTmax_um=300)
    assert bad_only["decision"]["eyes"][0]["status"] == PASS
    three = _payload(I_S=1.03, BAD_D=2.0)
    assert three["decision"]["eyes"][0]["status"] == CAUTION
