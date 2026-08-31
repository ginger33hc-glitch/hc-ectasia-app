from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient

import assessment_workflow
import case_archive
import case_catalog
import user_access


KEY = bytes(range(32))
CASE_ID = "a" * 32
REVISION_ID = "b" * 24


def ready_payload():
    return {
        "patient": {
            "name": "Source Patient",
            "id": "SOURCE-1",
            "age": 40,
            "reviewer": "Doctor One",
            "report_date": "2026-08-31",
        },
        "decision": {"status": "PASS", "eyes": [{"eye": "OD", "status": "PASS"}]},
        "extracted": {"eyes": []},
    }


def principal(user_id, role="DOCTOR"):
    return user_access.Principal(user_id, user_id, user_id, role)


def test_source_routes_enforce_case_scope_and_return_integrity_checked_files(monkeypatch):
    archive = case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), KEY)
    archive.archive_sources(
        CASE_ID,
        [
            (b"od-image", "PATIENT_OD.jpg"),
            (b"os-image", "folder/PATIENT_OS.png"),
            (b"pdf-source", "Pentacam export.pdf"),
        ],
        patient_metadata={"patient_name": "Source Patient"},
        extracted={},
    )
    case_catalog.write_entry(
        archive,
        case_archive.RevisionRef(CASE_ID, REVISION_ID, tuple()),
        ready_payload(),
        actor=principal("doctor-1"),
    )

    current = {"principal": principal("owner-1", "OWNER")}
    monkeypatch.setattr(user_access, "require_current_principal", lambda: current["principal"])
    audit_events = []
    core = SimpleNamespace(
        app=FastAPI(),
        _cerai_named_users_enabled=True,
        _cerai_audit_event=lambda event_type, **kwargs: audit_events.append((event_type, kwargs)),
    )
    runtime = case_archive.CaseArchiveRuntime(archive, required=False)
    original_begin = assessment_workflow.begin
    original_complete = assessment_workflow.complete
    try:
        case_catalog.install(core, runtime)
        client = TestClient(core.app)
        base = f"/archive/cases/{CASE_ID}/revisions/{REVISION_ID}"

        inventory = client.get(f"{base}/sources")
        assert inventory.status_code == 200
        assert inventory.json()["count"] == 3
        assert [item["original_filename"] for item in inventory.json()["sources"]] == [
            "PATIENT_OD.jpg",
            "folder/PATIENT_OS.png",
            "Pentacam export.pdf",
        ]
        assert all("key" not in item for item in inventory.json()["sources"])

        preview = client.get(f"{base}/sources/1/preview")
        assert preview.status_code == 200
        assert preview.content == b"od-image"
        assert preview.headers["content-disposition"] == (
            'inline; filename="CER-AI_Pentacam_Source_001.jpg"'
        )
        assert "PATIENT" not in preview.headers["content-disposition"]

        download = client.get(f"{base}/sources/2/download")
        assert download.status_code == 200
        assert download.content == b"os-image"
        assert download.headers["content-disposition"] == (
            'attachment; filename="CER-AI_Pentacam_Source_002.png"'
        )
        assert client.get(f"{base}/sources/3/preview").status_code == 415
        pdf_download = client.get(f"{base}/sources/3/download")
        assert pdf_download.status_code == 200
        assert pdf_download.content == b"pdf-source"

        bundle = client.get(f"{base}/sources.zip")
        assert bundle.status_code == 200
        assert bundle.headers["content-disposition"] == (
            'attachment; filename="CER-AI_Pentacam_Sources.zip"'
        )
        with ZipFile(BytesIO(bundle.content)) as zipped:
            assert zipped.namelist() == [
                "001_PATIENT_OD.jpg",
                "002_PATIENT_OS.png",
                "003_Pentacam export.pdf",
            ]
            assert zipped.read("001_PATIENT_OD.jpg") == b"od-image"
            assert zipped.read("002_PATIENT_OS.png") == b"os-image"
            assert zipped.read("003_Pentacam export.pdf") == b"pdf-source"

        current["principal"] = principal("doctor-1")
        assert client.get(f"{base}/sources").status_code == 200
        current["principal"] = principal("doctor-2")
        assert client.get(f"{base}/sources").status_code == 403
        assert client.get(f"{base}/sources/1/preview").status_code == 403
        assert client.get(f"{base}/sources.zip").status_code == 403

        event_names = [name for name, _kwargs in audit_events]
        assert "SOURCE_LIST" in event_names
        assert "SOURCE_PREVIEW" in event_names
        assert "SOURCE_DOWNLOAD" in event_names
        assert "SOURCE_DOWNLOAD_ALL" in event_names
    finally:
        assessment_workflow.begin = original_begin
        assessment_workflow.complete = original_complete
