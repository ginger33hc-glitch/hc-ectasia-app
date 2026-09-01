import json

import pytest
from fastapi import HTTPException

import case_archive
import historical_report


KEY = bytes(range(32))


def make_archive():
    return case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), KEY)


def store_assessment(archive, case_id, revision_id):
    payload = {
        "patient": {"name": "Archived Patient", "id": "P-1"},
        "decision": {"status": "PASS", "eyes": []},
        "extracted": {},
    }
    archive.put_bytes(
        case_id,
        f"revisions/{revision_id}",
        "assessment-json",
        json.dumps(payload).encode("utf-8"),
        media_type="application/json",
    )
    return payload


def test_regenerate_pdf_uses_archived_canonical_snapshot_and_requested_locale():
    archive = make_archive()
    case_id, revision_id = "1" * 32, "2" * 24
    store_assessment(archive, case_id, revision_id)

    def pdf_builder(payload):
        return f"PDF:{payload['locale']}:{payload['decision']['status']}".encode()

    content = historical_report.regenerate_bytes(
        archive,
        case_id,
        revision_id,
        kind="pdf",
        locale="tr-TR",
        pdf_builder=pdf_builder,
        docx_builder=lambda payload: b"unused",
    )
    assert content == b"PDF:tr:PASS"


def test_regenerate_docx_does_not_modify_archive():
    archive = make_archive()
    case_id, revision_id = "3" * 32, "4" * 24
    store_assessment(archive, case_id, revision_id)
    before = list(archive.store.list(f"cases/{case_id}/"))
    content = historical_report.regenerate_bytes(
        archive,
        case_id,
        revision_id,
        kind="docx",
        locale="en",
        pdf_builder=lambda payload: b"unused",
        docx_builder=lambda payload: b"DOCX-current-template",
    )
    after = list(archive.store.list(f"cases/{case_id}/"))
    assert content == b"DOCX-current-template"
    assert after == before


def test_regeneration_requires_existing_canonical_assessment():
    archive = make_archive()
    with pytest.raises(HTTPException) as exc:
        historical_report.regenerate_bytes(
            archive,
            "5" * 32,
            "6" * 24,
            kind="pdf",
            locale="en",
            pdf_builder=lambda payload: b"pdf",
            docx_builder=lambda payload: b"docx",
        )
    assert exc.value.status_code == 404


def test_regeneration_rejects_unsupported_kind():
    archive = make_archive()
    case_id, revision_id = "7" * 32, "8" * 24
    store_assessment(archive, case_id, revision_id)
    with pytest.raises(HTTPException) as exc:
        historical_report.regenerate_bytes(
            archive,
            case_id,
            revision_id,
            kind="txt",
            locale="en",
            pdf_builder=lambda payload: b"pdf",
            docx_builder=lambda payload: b"docx",
        )
    assert exc.value.status_code == 404
