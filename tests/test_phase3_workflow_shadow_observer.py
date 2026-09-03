"""Safety locks for the completed-assessment Phase 3 shadow observer."""
from copy import deepcopy

import phase3_workflow_shadow_observer as observer


class DummyCore:
    pass


def _install_previous(response):
    calls = []

    def previous(core, token, session, age, plans, modifiers, metadata, overrides):
        calls.append((core, token, session, age, plans, modifiers, metadata, overrides))
        return response

    observer._previous_respond = previous
    return calls


def test_observer_returns_exact_legacy_response_object(monkeypatch):
    response = {"workflow_status": "READY", "decision": {"eyes": []}, "extracted": {"eyes": []}, "effective_eye_plans": {}}
    calls = _install_previous(response)
    seen = []
    monkeypatch.setattr(observer, "_observe_ready_response", lambda *args, **kwargs: seen.append((args, kwargs)))

    returned = observer.respond_with_phase3_shadow_observer(
        DummyCore(), "token", {}, 30, {}, {}, {}, {}
    )

    assert returned is response
    assert len(calls) == 1
    assert len(seen) == 1


def test_observer_failure_never_blocks_or_mutates_response(monkeypatch):
    response = {"workflow_status": "READY", "decision": {"eyes": [{"eye": "OD", "status": "PASS"}]}}
    before = deepcopy(response)
    _install_previous(response)

    def explode(*args, **kwargs):
        raise RuntimeError("shadow-only failure")

    monkeypatch.setattr(observer, "_observe_ready_response", explode)
    returned = observer.respond_with_phase3_shadow_observer(
        DummyCore(), "token", {}, 30, {}, {}, {}, {}
    )

    assert returned is response
    assert response == before
    assert "shadow" not in response
    assert "parity" not in response


def test_non_ready_response_is_never_observed(monkeypatch):
    response = {"workflow_status": "NEEDS_INPUT", "missing": [{"eye": "OD", "message": "age"}]}
    _install_previous(response)
    called = []
    monkeypatch.setattr(observer, "build_clinical_core_input", lambda *args, **kwargs: called.append(True))

    returned = observer.respond_with_phase3_shadow_observer(
        DummyCore(), "token", {}, None, {}, {}, {}, {}
    )

    assert returned is response
    assert called == []


def test_ready_observer_does_not_modify_decision_or_extracted(monkeypatch):
    response = {
        "workflow_status": "READY",
        "decision": {"eyes": [{"eye": "OD", "status": "PASS"}]},
        "extracted": {"eyes": [{"eye": "OD", "I_S": 0.5}]},
        "effective_eye_plans": {"OD": {"prior": "no", "procedure": "LASIK"}},
    }
    before = deepcopy(response)
    _install_previous(response)

    monkeypatch.setattr(observer, "build_clinical_core_input", lambda *args, **kwargs: object())
    monkeypatch.setattr(observer, "observe_shadow_parity", lambda *args, **kwargs: {"observed": False})

    returned = observer.respond_with_phase3_shadow_observer(
        DummyCore(), "token", {}, 30,
        {"OD": {"prior": "no", "procedure": "LASIK"}}, {}, {}, {}
    )

    assert returned is response
    assert response == before


def test_post_refractive_eye_is_skipped(monkeypatch):
    response = {
        "workflow_status": "READY",
        "decision": {"eyes": [{"eye": "OD", "status": "POST-REFRACTIVE PATHWAY REQUIRED"}]},
        "extracted": {"eyes": [{"eye": "OD", "I_S": 0.5}]},
        "effective_eye_plans": {"OD": {"prior": "PRK", "procedure": "PRK"}},
    }
    _install_previous(response)
    called = []
    monkeypatch.setattr(observer, "build_clinical_core_input", lambda *args, **kwargs: called.append(True))

    returned = observer.respond_with_phase3_shadow_observer(
        DummyCore(), "token", {}, 30,
        {"OD": {"prior": "PRK", "procedure": "PRK"}}, {}, {}, {}
    )

    assert returned is response
    assert called == []
