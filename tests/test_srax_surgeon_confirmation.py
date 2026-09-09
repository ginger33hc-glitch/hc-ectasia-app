"""Surgeon confirmation must gate both scoring and report issuance."""
import pytest

from assessment_workflow import _overrides
from srax_policy import srax_positive
from tests.test_step11_analyze_completion_workflow import _eye, _respond
from tests.test_step6_ps3_runtime_acceptance import _evaluate


@pytest.mark.parametrize('degrees,answer,expected', [
    (19.9, None, False), (20.0, None, False), (20.1, None, None),
    (90.0, None, None), (None, None, None),
    (20.5, True, True), (20.5, False, False),
])
def test_shared_confirmation_decision(degrees, answer, expected):
    assert srax_positive(degrees, answer) is expected


@pytest.mark.parametrize('i_s', [0.0, 0.8, 1.2, 1.4])
def test_positive_geometry_requires_one_question_and_no_final_report(i_s):
    response = _respond(od=_eye('OD', I_S=i_s, srax_deg=20.5, srax='YES'))
    requests = [r for r in response['input_requests'] if r.get('eye') == 'OD' and r.get('key') == 'srax']
    assert len(requests) == 1
    assert requests[0]['options'] == ['YES', 'NO']
    assert response['report_token'] is None


@pytest.mark.parametrize('answer,points,ps3_status', [('YES', 3, 'HIGH'), ('NO', 1, 'NORMAL')])
def test_surgeon_answer_controls_both_scores_and_releases_report(answer, points, ps3_status):
    extracted = {'eyes': [_eye('OD', I_S=0.8, srax_deg=20.5, srax='YES')]}
    corrected = _overrides(extracted, {'OD': {'srax': answer}})['eyes'][0]
    assert corrected['srax_deg'] == 20.5
    assert corrected['surgeon_corrections'][-1]['value'] == answer
    _, eyes = _evaluate(od=corrected)
    assert eyes['OD']['score']['rows']['topography'] == points
    factor = next(f for f in eyes['OD']['ps3']['findings'] if f['key'] == 'srax')
    assert factor['status'] == ps3_status
    assert '20.5°' in factor['detail']
    response = _respond(od=corrected)
    assert response['report_token']
    assert not any(r.get('key') == 'srax' for r in response.get('input_requests', []))


@pytest.mark.parametrize('i_s', [-0.01, -0.5, -0.51, -1.04, -3.0])
@pytest.mark.parametrize('degrees', [None, 20.5, 90.0])
def test_negative_signed_i_s_never_asks_for_srax(i_s, degrees):
    response = _respond(od=_eye('OD', I_S=i_s, srax_deg=degrees, srax='YES'))
    assert not any(r.get('key') == 'srax' for r in response.get('input_requests', []))
    assert response['report_token']


def test_unverified_machine_yes_is_not_a_surgeon_confirmation():
    _, eyes = _evaluate(od=_eye('OD', I_S=0.8, srax_deg=20.5, srax='YES',
        field_provenance={'srax': [{'source': 'GEOMETRIC_FRONT_MAP'}]}))
    assert eyes['OD']['score']['total'] is None
    assert not eyes['OD']['ps3']['complete']


def test_ps3_can_be_imported_before_clinical_core():
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, '-c', 'import ps3_policy; import clinical_core.rules'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
