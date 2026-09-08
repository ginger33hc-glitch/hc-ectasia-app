"""Stage 12 acceptance for canonical archive persistence, reopening, and access."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import assessment_workflow
import analysis_job_service
import case_archive
import case_catalog
import historical_report
import operational_security
import reports
import user_access


KEY = bytes(range(32))
CASE_ID = "a" * 32
ROOT = Path(__file__).resolve().parents[1]


def _archive():
    return case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), KEY)


def _principal(user_id="doctor-1", display_name="Dr. Canonical", role="DOCTOR"):
    return user_access.Principal(user_id, user_id, display_name, role)


def _ready(reviewer="Dr. Canonical"):
    return {
        "report_token": "not-archived",
        "patient": {
            "name": "Archive Patient",
            "id": "P-12",
            "age": 44,
            "reviewer": reviewer,
            "report_date": "2026-09-07",
        },
        "decision": {
            "status": "PASS",
            "action": "Proceed with surgeon review.",
            "eyes": [{"eye": "OD", "status": "PASS"}, {"eye": "OS", "status": "PASS"}],
        },
        "extracted": {"eyes": []},
    }


def test_archive_and_catalog_installers_do_not_replace_workflow_upload_or_report_functions():
    original = (
        assessment_workflow.begin,
        assessment_workflow.complete,
        assessment_workflow.export_payload,
        operational_security.read_uploads,
    )
    core = SimpleNamespace(
        build_pdf=lambda payload: b"pdf",
        build_docx=lambda payload: b"docx",
        _cerai_named_users_enabled=False,
    )
    runtime = case_archive.CaseArchiveRuntime(_archive(), required=False)
    case_archive.install(core, runtime=runtime)
    case_catalog.install(core, runtime)
    assert original == (
        assessment_workflow.begin,
        assessment_workflow.complete,
        assessment_workflow.export_payload,
        operational_security.read_uploads,
    )
    assert core.build_pdf({}) == b"pdf"
    assert core.build_docx({}) == b"docx"


def test_one_archive_runtime_persists_sources_snapshot_reports_catalog_and_attribution(monkeypatch):
    archive = _archive()
    actor = _principal()
    audit_events = []
    core = SimpleNamespace(
        APP_VERSION="stage12-test",
        build_pdf=lambda payload: f"PDF:{payload.get('locale')}".encode(),
        build_docx=lambda payload: f"DOCX:{payload.get('locale')}".encode(),
        _cerai_current_principal=lambda: actor,
        _cerai_audit_event=lambda event_type, **kwargs: audit_events.append((event_type, kwargs)),
    )
    runtime = case_archive.CaseArchiveRuntime(archive, required=False)
    case_archive.install(core, runtime=runtime)

    def ready_response(core_arg, token, session, age, plans, modifiers, metadata, overrides):
        ready = _ready(metadata["reviewer"])
        ready["patient"].update(deepcopy(metadata))
        ready["report_token"] = "report-token"
        session["ready"] = ready
        return {
            "assessment_token": token,
            "report_token": "report-token",
            "workflow_status": "READY",
            "decision": ready["decision"],
        }

    monkeypatch.setattr(assessment_workflow, "_respond", ready_response)
    response = assessment_workflow.begin(
        core,
        {"eyes": []},
        44,
        {},
        {},
        {"name": "Archive Patient", "reviewer": "Untrusted typed name", "report_date": "2026-09-07"},
        source_images=[(b"od", "OD.png"), (b"os", "OS.png")],
    )

    state = response["archive"]
    assert state["status"] == "ARCHIVED"
    assert state["catalog_status"] == "INDEXED"
    assert archive.get_bytes(archive.find_report(state["case_id"], state["revision_id"], "en", "pdf")) == b"PDF:en"
    assert [item.original_filename for item in archive.list_sources(state["case_id"])] == ["OD.png", "OS.png"]
    saved = archive.load_assessment(state["case_id"], state["revision_id"])
    assert saved["patient"]["reviewer"] == "Dr. Canonical"
    entry = case_catalog.get_entry(archive, state["case_id"], state["revision_id"])
    assert entry["reviewer"] == "Dr. Canonical"
    assert entry["created_by"]["user_id"] == "doctor-1"
    assert [name for name, _details in audit_events] == ["CASE_ARCHIVED"]

    changed = deepcopy(saved)
    changed["report_token"] = "changed-report-token"
    changed["decision"]["status"] = "CAUTION"
    changed_response = runtime.finalize_ready(
        core,
        {
            "assessment_token": response["assessment_token"],
            "report_token": "changed-report-token",
            "workflow_status": "READY",
        },
        changed,
    )
    assert changed_response["archive"]["revision_id"] != state["revision_id"]
    assert len(case_catalog.list_entries(archive)) == 2
    assert [name for name, _details in audit_events] == ["CASE_ARCHIVED", "CASE_ARCHIVED"]


def _route_client(monkeypatch):
    archive = _archive()
    actor = _principal()
    current = {"principal": actor}
    monkeypatch.setattr(user_access, "require_current_principal", lambda: current["principal"])
    revision = archive.archive_ready(
        CASE_ID,
        _ready(),
        pdf_builder=lambda payload: f"ORIGINAL-PDF:{payload['locale']}".encode(),
        docx_builder=lambda payload: f"ORIGINAL-DOCX:{payload['locale']}".encode(),
    )
    case_catalog.write_entry(archive, revision, _ready(), actor=actor)
    events = []
    core = SimpleNamespace(
        app=FastAPI(),
        _cerai_named_users_enabled=True,
        _cerai_audit_event=lambda event_type, **kwargs: events.append((event_type, kwargs)),
    )
    runtime = case_archive.CaseArchiveRuntime(archive, required=False)
    case_catalog.install(core, runtime)
    monkeypatch.setattr(reports, "build_pdf", lambda payload: f"REGENERATED-PDF:{payload['locale']}".encode())
    monkeypatch.setattr(reports, "build_docx", lambda payload: f"REGENERATED-DOCX:{payload['locale']}".encode())
    historical_report.install(core, runtime)
    return TestClient(core.app), current, revision, events


def test_listed_case_reopens_and_original_pdf_opens_with_integrity_checked_bytes(monkeypatch):
    client, _current, revision, events = _route_client(monkeypatch)
    base = f"/archive/cases/{CASE_ID}/revisions/{revision.revision_id}"

    search = client.post("/archive/search", json={})
    assert search.status_code == 200
    assert search.json()["results"][0]["patient"]["name"] == "Archive Patient"

    reopened = client.get(base)
    assert reopened.status_code == 200
    assert reopened.json()["assessment"]["patient"]["reviewer"] == "Dr. Canonical"
    assert "report_token" not in reopened.json()["assessment"]
    assert reopened.json()["catalog"]["created_by"]["user_id"] == "doctor-1"

    report = client.get(f"{base}/report/pdf?locale=en")
    assert report.status_code == 200
    assert report.content == b"ORIGINAL-PDF:en"
    assert report.headers["content-disposition"] == 'inline; filename="CER-AI_Report.pdf"'
    assert report.headers["x-cer-ai-report-source"] == "archived-original"
    assert report.headers["cache-control"] == "no-store"
    assert {name for name, _details in events} >= {"ARCHIVE_SEARCH", "CASE_OPEN", "REPORT_DOWNLOAD"}


def test_regenerated_report_uses_saved_snapshot_and_does_not_replace_original(monkeypatch):
    client, _current, revision, _events = _route_client(monkeypatch)
    base = f"/archive/cases/{CASE_ID}/revisions/{revision.revision_id}"
    original_before = client.get(f"{base}/report/pdf?locale=tr").content
    regenerated = client.get(f"{base}/regenerate/pdf?locale=tr")
    original_after = client.get(f"{base}/report/pdf?locale=tr").content

    assert regenerated.status_code == 200
    assert regenerated.content == b"REGENERATED-PDF:tr"
    assert regenerated.headers["content-disposition"] == 'inline; filename="CER-AI_Report_Regenerated.pdf"'
    assert regenerated.headers["x-cer-ai-report-source"] == "archived-canonical-current-template"
    assert original_before == original_after == b"ORIGINAL-PDF:tr"


def test_other_doctor_is_denied_while_owner_receives_only_deidentified_case(monkeypatch):
    client, current, revision, _events = _route_client(monkeypatch)
    current["principal"] = _principal("doctor-2", "Dr. Other")
    base = f"/archive/cases/{CASE_ID}/revisions/{revision.revision_id}"
    assert client.get(base).status_code == 403
    assert client.get(f"{base}/report/pdf").status_code == 403
    assert client.get(f"{base}/regenerate/pdf").status_code == 403
    current["principal"] = _principal("owner-1", "Owner", "OWNER")
    search = client.post("/archive/search", json={})
    assert search.status_code == 200
    assert search.json()["results"][0]["patient"] == {
        "name": "Masked for owner", "id": "Masked for owner", "age": 44,
    }
    assert client.post("/archive/search", json={"patient_name": "Archive Patient"}).status_code == 422
    reopened = client.get(base)
    assert reopened.status_code == 200
    assert reopened.json()["assessment"]["patient"]["name"] == "Masked for owner"
    assert reopened.json()["assessment"]["patient"]["id"] == "Masked for owner"
    monkeypatch.setattr(
        reports,
        "build_pdf",
        lambda payload: (
            f"OWNER-PDF:{payload['patient']['name']}:{payload['patient']['id']}"
        ).encode(),
    )
    report = client.get(f"{base}/report/pdf")
    assert report.status_code == 200
    assert report.content == b"OWNER-PDF:Masked for owner:Masked for owner"
    assert report.headers["x-cer-ai-report-source"] == "owner-deidentified-canonical"
    regenerated = client.get(f"{base}/regenerate/pdf")
    assert regenerated.status_code == 200
    assert regenerated.headers["x-cer-ai-report-source"] == (
        "owner-deidentified-canonical-current-template"
    )


def test_archive_ui_has_authenticated_case_reopen_and_inline_pdf_actions():
    text = (ROOT / "static" / "archive.html").read_text(encoding="utf-8")
    assert 'class="case-button"' in text
    assert "showCase(caseButton.dataset.caseId" in text
    assert "Archived canonical assessment reopened" in text
    assert "target=\"_blank\"" in text
    assert "no clinical score was recalculated" in text


def test_background_assessment_job_is_protected_and_bound_to_its_doctor(monkeypatch):
    doctor_one = _principal("doctor-1", "Dr. One")
    doctor_two = _principal("doctor-2", "Dr. Two")
    principals = {"one": doctor_one, "two": doctor_two}
    app = FastAPI()

    async def analyze(**_kwargs):
        principal = user_access.current_principal()
        return {"workflow_status": "READY", "actor_user_id": principal.user_id}

    core = SimpleNamespace(
        app=app,
        analyze=analyze,
        _cerai_named_users_enabled=True,
        _cerai_authenticate_request=lambda request: principals.get(request.cookies.get("session")),
        _cerai_bind_principal=user_access.bind_current_principal,
        _cerai_reset_principal=user_access.reset_current_principal,
        _cerai_current_principal=user_access.current_principal,
    )
    monkeypatch.setattr(analysis_job_service, "_jobs", {})
    operational_security.install(core)
    analysis_job_service.install(core)

    with TestClient(app) as client:
        client.cookies.set("session", "one")
        started = client.post(
            "/analysis/jobs",
            files=[("images", ("OD.png", b"image", "image/png"))],
            data={"age": "40"},
        )
        assert started.status_code == 202
        job_id = started.json()["job_id"]

        client.cookies.set("session", "two")
        assert client.get(f"/analysis/jobs/{job_id}").status_code == 403

        client.cookies.set("session", "one")
        deadline = time.time() + 2
        while True:
            response = client.get(f"/analysis/jobs/{job_id}")
            if response.status_code != 202:
                break
            assert time.time() < deadline
            time.sleep(0.01)
        assert response.status_code == 200
        assert response.json()["result"]["workflow_status"] == "READY"
        assert response.json()["result"]["actor_user_id"] == "doctor-1"
