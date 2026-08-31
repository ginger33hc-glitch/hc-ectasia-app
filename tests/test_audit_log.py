import json

import pytest
from fastapi import HTTPException

import audit_log
import case_archive
import user_access


KEY = bytes(range(32))


def make_archive(store=None):
    return case_archive.EncryptedArchive(store or case_archive.MemoryObjectStore(), KEY)


def actor(user_id="doctor-1", role="DOCTOR"):
    return user_access.Principal(user_id, user_id, "Doctor Example", role)


def test_audit_payload_is_encrypted_and_phi_never_enters_key_or_metadata():
    archive = make_archive()
    ref = audit_log.write_event(
        archive,
        "ARCHIVE_SEARCH",
        actor=actor(),
        details={"patient_name": "Şule Işık", "patient_id": "P-123"},
    )
    assert "Şule" not in ref.key
    assert "P-123" not in ref.key
    assert "doctor-1" not in ref.key
    stored = archive.store.get(ref.key)
    metadata_text = " ".join(f"{key}={value}" for key, value in stored.metadata.items())
    assert "Şule" not in metadata_text
    assert "P-123" not in metadata_text
    assert "doctor-1" not in metadata_text
    assert stored.data != archive.get_bytes(ref)
    payload = json.loads(archive.get_bytes(ref))
    assert payload["event_type"] == "ARCHIVE_SEARCH"
    assert payload["actor"]["user_id"] == "doctor-1"
    assert payload["details"]["patient_name"] == "Şule Işık"


def test_global_and_case_audit_events_remain_distinct_and_filterable():
    archive = make_archive()
    case_id = "a" * 32
    audit_log.write_event(archive, "LOGIN_SUCCESS", actor=actor())
    audit_log.write_event(
        archive,
        "REPORT_DOWNLOAD",
        actor=actor(),
        case_id=case_id,
        revision_id="b" * 24,
        details={"kind": "pdf", "locale": "tr"},
    )
    all_events = audit_log.list_events(archive)
    case_events = audit_log.list_events(archive, case_id=case_id)
    download_events = audit_log.list_events(archive, event_type="REPORT_DOWNLOAD")
    assert len(all_events) == 2
    assert len(case_events) == 1
    assert case_events[0]["case_id"] == case_id
    assert len(download_events) == 1
    assert download_events[0]["details"]["kind"] == "pdf"


def test_audit_can_filter_by_authenticated_actor_user_id():
    archive = make_archive()
    audit_log.write_event(archive, "ARCHIVE_SEARCH", actor=actor("doctor-1"))
    audit_log.write_event(archive, "ARCHIVE_SEARCH", actor=actor("doctor-2"))
    events = audit_log.list_events(archive, actor_user_id="doctor-1")
    assert len(events) == 1
    assert events[0]["actor"]["user_id"] == "doctor-1"


def test_audit_event_type_is_sanitized_without_phi():
    archive = make_archive()
    ref = audit_log.write_event(archive, "report download!!!", actor=actor())
    payload = json.loads(archive.get_bytes(ref))
    assert payload["event_type"] == "REPORTDOWNLOAD"


class FailingStore:
    def put(self, key, data, *, content_type, metadata):
        raise RuntimeError("storage down")

    def get(self, key):
        raise KeyError(key)

    def list(self, prefix):
        return []


def test_non_required_audit_failure_does_not_break_operation():
    archive = make_archive(FailingStore())
    runtime = case_archive.CaseArchiveRuntime(archive, required=False)
    core = type("Core", (), {})()
    audit_log.install(core, runtime)
    assert core._cerai_audit_event("ARCHIVE_SEARCH", actor=actor()) is None


def test_required_audit_failure_is_fail_closed():
    archive = make_archive(FailingStore())
    runtime = case_archive.CaseArchiveRuntime(archive, required=True)
    core = type("Core", (), {})()
    audit_log.install(core, runtime)
    with pytest.raises(HTTPException) as exc:
        core._cerai_audit_event("REPORT_DOWNLOAD", actor=actor())
    assert exc.value.status_code == 503
