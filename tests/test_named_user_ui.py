import logging
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import named_user_ui
import operational_security
import user_access
import case_archive
import clinical_entry
from iol_module import web as iol_web


def make_client(role="DOCTOR"):
    app = FastAPI()
    principal = user_access.Principal(
        "owner-1" if role == "OWNER" else "doctor-1",
        "owner" if role == "OWNER" else "doctor",
        "Owner" if role == "OWNER" else "Doctor <One>",
        role,
    )

    def authenticate(request):
        if request.cookies.get("cer_ai_session") == "valid":
            return principal
        return None

    core = SimpleNamespace(
        app=app,
        _cerai_named_users_enabled=True,
        _cerai_authenticate_request=authenticate,
        _cerai_bind_principal=user_access.bind_current_principal,
        _cerai_reset_principal=user_access.reset_current_principal,
        _cerai_case_archive_runtime=SimpleNamespace(enabled=True),
        _cerai_audit_log_installed=True,
        _cerai_historical_report_installed=True,
        _cerai_research_export_enabled=False,
    )
    clinical_entry.install(core)
    iol_web.install(core)
    operational_security.install(core)
    named_user_ui.install(core)
    return TestClient(app, base_url="https://testserver", follow_redirects=False), core


def test_unauthenticated_clinical_app_redirects_to_login_page():
    client, _core = make_client()
    response = client.get("/app")
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login-page?next=/app"
    assert response.headers["x-frame-options"] == "DENY"


def test_public_root_is_not_intercepted_by_named_user_gate():
    client, _core = make_client()
    response = client.get("/")
    assert response.status_code == 404


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


def test_login_uses_module_selection_as_canonical_default_without_session_bypass():
    client, _core = make_client()
    response = client.get("/auth/login-page?next=/clinical-modules")
    assert response.status_code == 200
    assert 'const requested = params.get("next") || "/clinical-modules"' in response.text
    assert 'fetch("/auth/me"' not in response.text
    assert 'params.get("reauth")' not in response.text


def test_login_page_remains_username_and_password_when_legacy_trial_flag_is_set():
    client, core = make_client()
    core._cerai_trial_name_login_enabled = True

    response = client.get("/auth/login-page")
    text = response.text

    assert response.status_code == 200
    assert "Username" in text
    assert 'type="password"' in text
    assert "display_name" not in text
    assert "sessionStorage" not in text
    assert "localStorage" not in text


def test_module_selector_precedes_login_and_preserves_module_destination():
    client, _core = make_client()
    response = client.get("/clinical-modules")
    assert response.status_code == 200
    assert "Refractive Surgery" in response.text
    assert "IOL Calculation Surgery" in response.text
    assert 'href="/app"' in response.text
    assert 'href="/iol"' in response.text
    assert response.headers["cache-control"] == "no-store"


def test_unauthenticated_iol_redirects_to_login_and_authenticated_iol_is_separate():
    client, _core = make_client()
    denied = client.get("/iol")
    assert denied.status_code == 303
    assert denied.headers["location"] == "/auth/login-page?next=/iol"
    client.cookies.set("cer_ai_session", "valid")
    allowed = client.get("/iol")
    assert allowed.status_code == 200
    assert "IOL Decision Assistant" in allowed.text
    assert "IOL Calculation Surgery" in allowed.text
    assert "Doctor &lt;One&gt;" in allowed.text
    assert "/static/iol.js?v=12" in allowed.text
    assert 'href="/clinical-modules"' in allowed.text


def test_toric_test_outputs_are_owner_only_at_http_boundary():
    payload = {
        "patient_name":"Synthetic", "biological_sex":"Female", "eye":"OD",
        "selected_lens_id":"clareon-panoptix-toric-cnwtt3", "axial_length_mm":24.2,
        "acd_mm":2.21, "k1_d":42.0, "k1_axis_deg":20,
        "k2_d":43.0, "k2_axis_deg":110, "astigmatism_type":"REGULAR",
        "incision_axis_deg":110, "sia_d":0.25, "sia_axis_deg":110, "cct_um":573,
        "posterior_cornea":{
            "eye":"OD", "source":"PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
            "k1_d":-5.8, "k2_d":-6.1, "k1_axis_deg":20,
            "k2_axis_deg":110, "rh_mm":6.7, "rv_mm":6.5,
        },
    }
    with patch("iol_module.power._call_k6", return_value=[{"IOL":21.0, "Rx":0.01, "IsBestOption":True}]):
        for role in ("DOCTOR", "OWNER"):
            client, core = make_client(role)
            core._cerai_current_principal = user_access.current_principal
            client.cookies.set("cer_ai_session", "valid")
            response = client.post("/iol/power/plan", json=payload)
            assert response.status_code == 200
            result = response.json()
            assert result["toric_status"] == ("TEST_ONLY" if role == "OWNER" else "TEST_RESTRICTED")
            assert bool(result["toric_candidates"]) == (role == "OWNER")
            assert result["calculator_url"] == "https://www.myalcon-toriccalc.com/"


def test_authenticated_clinical_app_injects_archive_navigation_and_escapes_display_name():
    client, _core = make_client()
    client.cookies.set("cer_ai_session", "valid")
    response = client.get("/app")
    assert response.status_code == 200
    assert "Case Archive" in response.text
    assert 'href="/clinical-modules"' in response.text
    assert "Doctor &lt;One&gt;" in response.text
    assert "Doctor <One>" not in response.text
    assert 'cerAiReviewerField.readOnly = true' in response.text
    assert 'Report attribution is bound to the authenticated CER-AI user.' in response.text
    assert response.text.count('/static/analysis-jobs-client.js?v=2') == 1
    assert response.text.index('/static/analysis-jobs-client.js?v=2') < response.text.index(
        'async function ceraiFetch'
    )
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
    assert "/archive/capabilities" in allowed.text
    assert "/archive/research/export.csv" in allowed.text
    assert "/archive/audit/search" in allowed.text
    assert 'const reportLabel = entry.owner_deidentified ? "De-identified" : "Original"' in allowed.text
    assert "Regenerate PDF EN" in allowed.text
    assert 'class="archive-file"' in allowed.text
    assert "Retrieving authenticated archive file" in allowed.text
    assert "Pentacam sources" in allowed.text
    assert "View source images" in allowed.text
    assert "Restricted to case creator" in allowed.text
    assert allowed.headers["cache-control"] == "no-store"


def test_archive_capabilities_are_session_protected_and_role_aware():
    client, _core = make_client()
    denied = client.get("/archive/capabilities")
    assert denied.status_code == 401
    client.cookies.set("cer_ai_session", "valid")
    allowed = client.get("/archive/capabilities")
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload == {
        "role": "DOCTOR",
        "archive_enabled": True,
        "identifiable_archive_access": True,
        "retrospective_archive_access": True,
        "owner_deidentified_access": False,
        "original_source_access": True,
        "audit_enabled": True,
        "historical_report_enabled": True,
        "research_export_enabled": False,
    }
    assert user_access.current_principal() is None


def test_owner_capabilities_allow_own_identifiable_and_other_deidentified_archive():
    client, _core = make_client("OWNER")
    client.cookies.set("cer_ai_session", "valid")

    payload = client.get("/archive/capabilities").json()

    assert payload["identifiable_archive_access"] is True
    assert payload["retrospective_archive_access"] is True
    assert payload["owner_deidentified_access"] is True
    assert payload["original_source_access"] is True


def test_archive_operational_status_is_owner_only_and_contains_no_storage_credentials(monkeypatch):
    doctor_client, _doctor_core = make_client("DOCTOR")
    doctor_client.cookies.set("cer_ai_session", "valid")
    assert doctor_client.get("/archive/operational-status").status_code == 403

    owner_client, core = make_client("OWNER")
    owner_client.cookies.set("cer_ai_session", "valid")
    archive = case_archive.EncryptedArchive(
        case_archive.MemoryObjectStore(), bytes(range(32))
    )
    core._cerai_case_archive_runtime = case_archive.CaseArchiveRuntime(archive, required=True)
    core.APP_VERSION = "test-version"
    core.build_pdf = lambda payload: b"pdf"
    core.build_docx = lambda payload: b"docx"
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "a" * 40)

    before = owner_client.get("/archive/operational-status")
    assert before.status_code == 200
    assert before.json()["storage_canary"] == {"status": "NOT_FOUND"}

    verified = owner_client.post("/archive/operational-canary")
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED"

    status = owner_client.get("/archive/operational-status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["software_version"] == "test-version"
    assert payload["deployment_sha"] == "a" * 40
    assert payload["archive_enabled"] is True
    assert payload["archive_required"] is True
    assert payload["archive_mode"] == "REQUIRED"
    assert payload["storage_canary"] == verified.json()
    assert payload["report_endpoints"] == {
        "current_pdf": True,
        "current_docx": True,
        "historical": True,
    }
    serialized = status.text.lower()
    for forbidden in ("bucket", "access_key", "secret_access", "storage.railway"):
        assert forbidden not in serialized


def test_archive_operational_routes_require_authentication():
    client, _core = make_client("OWNER")
    assert client.get("/archive/operational-status").status_code == 401
    assert client.post("/archive/operational-canary").status_code == 401


def test_archive_canary_failure_logs_phi_free_storage_stage(monkeypatch, caplog):
    owner_client, core = make_client("OWNER")
    owner_client.cookies.set("cer_ai_session", "valid")
    archive = case_archive.EncryptedArchive(
        case_archive.MemoryObjectStore(), bytes(range(32))
    )
    core._cerai_case_archive_runtime = case_archive.CaseArchiveRuntime(archive, required=True)

    def fail_canary(_archive):
        raise RuntimeError("sensitive detail")

    monkeypatch.setattr(case_archive, "verify_storage_canary", fail_canary)
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        response = owner_client.post("/archive/operational-canary")

    assert response.status_code == 503
    message = caplog.messages[-1]
    assert "operation=operational_canary" in message
    assert "stage=write_read_list" in message
    assert "error_type=RuntimeError" in message
    assert "sensitive detail" not in message


def test_archive_page_hides_archive_until_retrospective_capability_is_confirmed():
    text = named_user_ui.ARCHIVE_HTML.read_text(encoding="utf-8")
    assert 'id="archiveSearch" class="card capability" hidden' in text
    assert 'id="archiveResults" class="card capability" hidden' in text
    assert "cases created under your account retain original identity" in text
    assert 'id="patient_id"' not in text
    assert "if(capabilities.retrospective_archive_access)" in text
    assert "Search your own identifiable cases" in text
    assert 'id="operationalControls" class="capability" hidden' in text
    assert 'id="archiveStatusButton"' in text
    assert 'id="archiveCanaryButton"' in text
    assert 'request("/archive/operational-status")' in text
    assert 'request("/archive/operational-canary",{method:"POST"})' in text
    assert '$("operationalControls").hidden=false' in text
    assert "No patient data was used." in text
