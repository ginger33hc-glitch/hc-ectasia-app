from copy import deepcopy
import json

import case_archive
import case_catalog
import user_access


KEY = bytes(range(32))


def make_archive():
    return case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), KEY)


def ready_payload(
    *,
    name="Şule Işık",
    patient_id="P-123",
    reviewer="Dr. Example",
    report_date="2026-08-31",
    status="PASS WITH CAUTION",
):
    return {
        "report_token": "never-index-this-token",
        "patient": {
            "name": name,
            "id": patient_id,
            "age": 42,
            "reviewer": reviewer,
            "report_date": report_date,
        },
        "decision": {
            "status": status,
            "action": "Surgeon review",
            "eyes": [
                {"eye": "OS", "status": "PASS WITH CAUTION"},
                {"eye": "OD", "status": "PASS"},
            ],
        },
        "extracted": {"eyes": []},
    }


def revision(case_id, revision_id="a" * 24):
    return case_archive.RevisionRef(case_id, revision_id, tuple())


def doctor(user_id="doctor-1"):
    return user_access.Principal(user_id, user_id, "Doctor One", "DOCTOR")


def owner():
    return user_access.Principal("owner-1", "owner", "Owner", "OWNER")


def test_catalog_entry_contains_search_fields_and_orders_eyes_od_first():
    entry = case_catalog.build_entry(
        ready_payload(),
        case_id="1" * 32,
        revision_id="2" * 24,
    )
    assert entry["patient"] == {"name": "Şule Işık", "id": "P-123", "age": 42}
    assert entry["reviewer"] == "Dr. Example"
    assert entry["report_date"] == "2026-08-31"
    assert entry["decision"]["status"] == "PASS WITH CAUTION"
    assert [eye["eye"] for eye in entry["decision"]["eyes"]] == ["OD", "OS"]


def test_catalog_object_key_and_storage_metadata_do_not_contain_phi():
    archive = make_archive()
    case_id = "1" * 32
    ref = case_catalog.write_entry(archive, revision(case_id), ready_payload())
    assert "Şule" not in ref.key
    assert "P-123" not in ref.key
    stored = archive.store.get(ref.key)
    rendered_metadata = " ".join(f"{k}={v}" for k, v in stored.metadata.items())
    assert "Şule" not in rendered_metadata
    assert "P-123" not in rendered_metadata
    assert stored.data != archive.get_bytes(ref)


def test_catalog_round_trip_is_encrypted_and_integrity_checked():
    archive = make_archive()
    case_id = "3" * 32
    ref = case_catalog.write_entry(archive, revision(case_id, "4" * 24), ready_payload())
    decoded = json.loads(archive.get_bytes(ref))
    assert decoded["patient"]["name"] == "Şule Işık"
    assert decoded["case_id"] == case_id


def test_search_is_turkish_diacritic_and_punctuation_insensitive():
    archive = make_archive()
    case_catalog.write_entry(archive, revision("5" * 32), ready_payload())
    by_name = case_catalog.search_entries(archive, patient_name="sule isik")
    by_reviewer = case_catalog.search_entries(archive, reviewer="dr example")
    assert len(by_name) == 1
    assert len(by_reviewer) == 1


def test_search_supports_patient_id_date_and_decision_filters_together():
    archive = make_archive()
    case_catalog.write_entry(archive, revision("6" * 32), ready_payload())
    matches = case_catalog.search_entries(
        archive,
        patient_id="p123",
        report_date="2026/08/31",
        decision="caution",
    )
    assert len(matches) == 1
    assert matches[0]["patient"]["id"] == "P-123"


def test_search_does_not_return_nonmatching_patient():
    archive = make_archive()
    case_catalog.write_entry(archive, revision("7" * 32), ready_payload())
    assert case_catalog.search_entries(archive, patient_name="different patient") == []
    assert case_catalog.search_entries(archive, patient_id="ZZZ") == []


def test_multiple_revisions_remain_distinct_for_auditable_history():
    archive = make_archive()
    case_id = "8" * 32
    first = ready_payload(report_date="2026-08-30", status="PASS")
    second = ready_payload(report_date="2026-08-31", status="DO NOT PROCEED")
    case_catalog.write_entry(archive, revision(case_id, "9" * 24), first)
    case_catalog.write_entry(archive, revision(case_id, "a" * 24), second)
    entries = case_catalog.list_entries(archive)
    assert len(entries) == 2
    assert entries[0]["report_date"] == "2026-08-31"
    assert entries[0]["decision"]["status"] == "DO NOT PROCEED"


def test_search_limit_is_bounded():
    archive = make_archive()
    for index in range(3):
        case_id = f"{index + 1:032x}"
        revision_id = f"{index + 1:024x}"
        payload = deepcopy(ready_payload(patient_id=f"P-{index}"))
        case_catalog.write_entry(archive, revision(case_id, revision_id), payload)
    assert len(case_catalog.search_entries(archive, limit=2)) == 2


def test_authenticated_creator_is_encrypted_in_catalog_and_filterable_by_user_id():
    archive = make_archive()
    actor = doctor("doctor-7")
    ref = case_catalog.write_entry(
        archive,
        revision("b" * 32, "c" * 24),
        ready_payload(),
        actor=actor,
    )
    assert "doctor-7" not in ref.key
    stored = archive.store.get(ref.key)
    assert "doctor-7" not in " ".join(stored.metadata.values())
    matches = case_catalog.search_entries(archive, created_by_user_id="doctor-7")
    assert len(matches) == 1
    assert matches[0]["created_by"]["user_id"] == "doctor-7"


def test_owner_sees_all_doctor_only_own_and_legacy_is_owner_only():
    own_entry = case_catalog.build_entry(
        ready_payload(),
        case_id="d" * 32,
        revision_id="e" * 24,
        actor=doctor("doctor-1"),
    )
    other_entry = case_catalog.build_entry(
        ready_payload(),
        case_id="f" * 32,
        revision_id="1" * 24,
        actor=doctor("doctor-2"),
    )
    legacy_entry = case_catalog.build_entry(
        ready_payload(),
        case_id="2" * 32,
        revision_id="3" * 24,
    )
    assert case_catalog._principal_can_access(owner(), own_entry)
    assert case_catalog._principal_can_access(owner(), other_entry)
    assert case_catalog._principal_can_access(owner(), legacy_entry)
    assert case_catalog._principal_can_access(doctor("doctor-1"), own_entry)
    assert not case_catalog._principal_can_access(doctor("doctor-1"), other_entry)
    assert not case_catalog._principal_can_access(doctor("doctor-1"), legacy_entry)
