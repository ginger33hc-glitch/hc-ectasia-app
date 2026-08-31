from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import named_user_ui
import operational_security


class Principal:
    def __init__(self, display_name="Doctor <One>"):
        self.display_name = display_name


def make_client():
    app = FastAPI()

    def authenticate(request):
        if request.cookies.get("cer_ai_session") == "valid":
            return Principal()
        return None

    core = SimpleNamespace(
        app=app,
        _cerai_named_users_enabled=True,
        _cerai_authenticate_request=authenticate,
    )
    operational_security.install(core)
    named_user_ui.install(core)
    return TestClient(app, base_url="https://testserver", follow_redirects=False), core


def test_unauthenticated_root_redirects_to_login_page():
    client, _core = make_client()
    response = client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login-page?next=/"
    assert response.headers["x-frame-options"] == "DENY"


def test_login_page_exists_and_does_not_store_password_in_browser_storage():
    client, _core = make_client()
    response = client.get("/auth/login-page")
    assert response.status_code == 200
    text = response.text
    assert "/auth/login" in text
    assert "sessionStorage" not in text
    assert "localStorage" not in text
    assert 'type="password"' in text
    assert response.headers["cache-control"] == "no-store"


def test_authenticated_root_injects_archive_navigation_and_escapes_display_name():
    client, _core = make_client()
    client.cookies.set("cer_ai_session", "valid")
    response = client.get("/")
    assert response.status_code == 200
    assert "Case Archive" in response.text
    assert "Doctor &lt;One&gt;" in response.text
    assert "Doctor <One>" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"]


def test_archive_page_requires_session_and_contains_role_aware_tools():
    client, _core = make_client()
    denied = client.get("/archive-ui")
    assert denied.status_code == 303
    client.cookies.set("cer_ai_session", "valid")
    allowed = client.get("/archive-ui")
    assert allowed.status_code == 200
    assert "/archive/search" in allowed.text
    assert "/archive/research/export.csv" in allowed.text
    assert "/archive/audit/search" in allowed.text
    assert "Original PDF EN" in allowed.text
    assert "Regenerate PDF EN" in allowed.text
    assert allowed.headers["cache-control"] == "no-store"
