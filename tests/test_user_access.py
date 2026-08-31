import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import operational_security
import user_access


def account_payload(*, role="OWNER", username="owner", user_id="owner-1", password="long-owner-password"):
    return {
        "user_id": user_id,
        "username": username,
        "display_name": "Test User",
        "role": role,
        "password_hash": user_access.hash_password(password, salt=bytes(range(16))),
        "enabled": True,
    }


def test_password_hash_round_trip_and_wrong_password_rejected():
    encoded = user_access.hash_password("a-strong-test-password", salt=bytes(range(16)))
    assert "a-strong-test-password" not in encoded
    assert user_access.verify_password("a-strong-test-password", encoded)
    assert not user_access.verify_password("wrong-password-value", encoded)


def test_registry_requires_an_enabled_owner():
    doctor = account_payload(
        role="DOCTOR",
        username="doctor",
        user_id="doctor-1",
        password="long-doctor-password",
    )
    with pytest.raises(user_access.UserConfigurationError):
        user_access.parse_registry(json.dumps([doctor]))


def test_registry_rejects_duplicate_usernames_and_ids():
    owner = account_payload()
    duplicate_username = account_payload(
        role="DOCTOR",
        username="OWNER",
        user_id="doctor-2",
        password="long-doctor-password",
    )
    with pytest.raises(user_access.UserConfigurationError):
        user_access.parse_registry(json.dumps([owner, duplicate_username]))

    duplicate_id = account_payload(
        role="DOCTOR",
        username="doctor",
        user_id="owner-1",
        password="long-doctor-password",
    )
    with pytest.raises(user_access.UserConfigurationError):
        user_access.parse_registry(json.dumps([owner, duplicate_id]))


def test_authentication_and_session_preserve_named_role():
    owner_payload = account_payload()
    doctor_payload = account_payload(
        role="DOCTOR",
        username="doctor",
        user_id="doctor-1",
        password="long-doctor-password",
    )
    registry = user_access.parse_registry(json.dumps([owner_payload, doctor_payload]))
    user_access._configure_for_tests(registry)
    try:
        principal = user_access.authenticate_credentials("Doctor", "long-doctor-password")
        assert principal.user_id == "doctor-1"
        assert principal.role == "DOCTOR"
        token = user_access.create_session(principal)
        restored = user_access.principal_for_token(token)
        assert restored == principal
    finally:
        user_access._reset_for_tests()


def test_disabled_account_cannot_authenticate():
    owner = account_payload()
    disabled = account_payload(
        role="DOCTOR",
        username="doctor",
        user_id="doctor-1",
        password="long-doctor-password",
    )
    disabled["enabled"] = False
    registry = user_access.parse_registry(json.dumps([owner, disabled]))
    user_access._configure_for_tests(registry)
    try:
        with pytest.raises(Exception) as exc:
            user_access.authenticate_credentials("doctor", "long-doctor-password")
        assert getattr(exc.value, "status_code", None) == 401
    finally:
        user_access._reset_for_tests()


def test_failed_login_rate_limit(monkeypatch):
    registry = user_access.parse_registry(json.dumps([account_payload()]))
    user_access._configure_for_tests(registry)
    monkeypatch.setattr(user_access, "LOGIN_FAILURE_LIMIT", 3)
    try:
        for _ in range(3):
            with pytest.raises(Exception) as exc:
                user_access.authenticate_credentials("owner", "definitely-wrong-password")
            assert getattr(exc.value, "status_code", None) == 401
        with pytest.raises(Exception) as exc:
            user_access.authenticate_credentials("owner", "long-owner-password")
        assert getattr(exc.value, "status_code", None) == 429
    finally:
        user_access._reset_for_tests()


def test_current_principal_context_is_explicitly_reset():
    principal = user_access.Principal("doctor-1", "doctor", "Doctor One", "DOCTOR")
    token = user_access.bind_current_principal(principal)
    assert user_access.current_principal() == principal
    user_access.reset_current_principal(token)
    assert user_access.current_principal() is None


def test_named_session_can_replace_shared_access_key_and_login_logout_are_audited(monkeypatch):
    owner = account_payload()
    registry_json = json.dumps([owner])
    monkeypatch.setenv("CERAI_USERS_JSON", registry_json)
    user_access._reset_for_tests()
    monkeypatch.setattr(user_access, "NAMED_USERS_ENABLED", True)

    app = FastAPI()
    events = []
    core = SimpleNamespace(
        app=app,
        _cerai_audit_event=lambda event_type, **kwargs: events.append((event_type, kwargs)),
    )
    try:
        user_access.install(core)
        operational_security.install(core)

        @app.post("/assessment/complete")
        def protected_route():
            principal = user_access.current_principal()
            return {"user_id": principal.user_id if principal else None}

        client = TestClient(app, base_url="https://testserver")
        denied = client.post("/assessment/complete", json={})
        assert denied.status_code == 401
        assert denied.headers["www-authenticate"] == "CER-AI-Session"

        login = client.post(
            "/auth/login",
            json={"username": "owner", "password": "long-owner-password"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "OWNER"
        cookie = login.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie
        assert "Secure" in cookie
        assert "SameSite=strict" in cookie
        assert events[0][0] == "LOGIN_SUCCESS"
        assert events[0][1]["actor"].user_id == "owner-1"

        admitted = client.post("/assessment/complete", json={})
        assert admitted.status_code == 200
        assert admitted.json()["user_id"] == "owner-1"
        assert user_access.current_principal() is None

        logout = client.post("/auth/logout")
        assert logout.status_code == 200
        assert events[-1][0] == "LOGOUT"
        assert events[-1][1]["actor"].user_id == "owner-1"
        assert client.post("/assessment/complete", json={}).status_code == 401
    finally:
        user_access._reset_for_tests()
