import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

import case_archive


KEY = bytes(range(32))


def make_archive():
    return case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), KEY)


def ready_payload():
    return {
        "report_token": "must-never-be-archived",
        "patient": {"name": "Test Patient", "patient_id": "P-123"},
        "decision": {"status": "PASS", "eyes": [{"eye": "OD", "status": "PASS"}]},
        "extracted": {"eyes": [{"eye": "OD", "BAD_D": 1.2}]},
        "locale": "tr",
    }


def pdf_builder(payload):
    return ("PDF:" + payload["locale"] + ":" + payload["decision"]["status"]).encode()


def docx_builder(payload):
    return ("DOCX:" + payload["locale"] + ":" + payload["decision"]["status"]).encode()


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.put_calls = 0

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        obj = self.objects[Key]
        return {"Metadata": dict(obj["Metadata"]), "ContentType": obj["ContentType"]}

    def put_object(self, *, Bucket, Key, Body, ContentType, Metadata):
        self.put_calls += 1
        self.objects[Key] = {
            "Body": bytes(Body),
            "ContentType": ContentType,
            "Metadata": dict(Metadata),
        }

    def get_object(self, *, Bucket, Key):
        obj = self.objects[Key]
        return {
            "Body": BytesIO(obj["Body"]),
            "ContentType": obj["ContentType"],
            "Metadata": dict(obj["Metadata"]),
        }

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        return {
            "Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(Prefix)],
            "IsTruncated": False,
        }


def test_case_ids_are_random_32_character_hex():
    first = case_archive.EncryptedArchive.new_case_id()
    second = case_archive.EncryptedArchive.new_case_id()
    assert first != second
    assert len(first) == len(second) == 32
    int(first, 16)
    int(second, 16)


@pytest.mark.parametrize("length", [0, 1, 16, 31, 33, 64])
def test_master_key_length_is_exactly_32_bytes(length):
    with pytest.raises(case_archive.ArchiveConfigurationError):
        case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), b"x" * length)


def test_base64_master_key_round_trip():
    encoded = base64.b64encode(KEY).decode()
    assert case_archive.EncryptedArchive.decode_master_key(encoded) == KEY


@pytest.mark.parametrize("value", ["not base64!!!", "", base64.b64encode(b"short").decode()])
def test_invalid_base64_master_key_is_rejected(value):
    with pytest.raises(case_archive.ArchiveConfigurationError):
        case_archive.EncryptedArchive.decode_master_key(value)


@pytest.mark.parametrize(
    "payload,media_type",
    [
        (b"abc", "application/octet-stream"),
        (b"{}", "application/json"),
        (b"%PDF-test", "application/pdf"),
        (bytes(range(256)), "image/jpeg"),
    ],
)
def test_encrypted_object_round_trip(payload, media_type):
    archive = make_archive()
    case_id = archive.new_case_id()
    ref = archive.put_bytes(case_id, "test", "artifact", payload, media_type=media_type)
    assert archive.get_bytes(ref) == payload
    stored = archive.store.get(ref.key)
    assert stored.data != payload
    assert stored.content_type == "application/octet-stream"


def test_plaintext_sha256_and_size_are_recorded():
    archive = make_archive()
    payload = b"clinical-report"
    ref = archive.put_bytes(
        archive.new_case_id(), "test", "artifact", payload, media_type="application/pdf"
    )
    stored = archive.store.get(ref.key)
    assert ref.sha256 == hashlib.sha256(payload).hexdigest()
    assert ref.plaintext_bytes == len(payload)
    assert stored.metadata["plaintext-sha256"] == ref.sha256
    assert stored.metadata["plaintext-bytes"] == str(len(payload))
    assert stored.metadata["media-type"] == "application/pdf"


def test_ciphertext_tampering_is_detected():
    archive = make_archive()
    ref = archive.put_bytes(
        archive.new_case_id(), "test", "artifact", b"secret", media_type="application/octet-stream"
    )
    stored = archive.store.objects[ref.key]
    altered = bytearray(stored.data)
    altered[-1] ^= 1
    archive.store.objects[ref.key] = case_archive.StoredObject(
        bytes(altered), stored.metadata, stored.content_type
    )
    with pytest.raises(case_archive.ArchiveIntegrityError):
        archive.get_bytes(ref)


def test_plaintext_digest_metadata_tampering_is_detected():
    archive = make_archive()
    ref = archive.put_bytes(
        archive.new_case_id(), "test", "artifact", b"secret", media_type="application/octet-stream"
    )
    stored = archive.store.objects[ref.key]
    metadata = dict(stored.metadata)
    metadata["plaintext-sha256"] = "0" * 64
    archive.store.objects[ref.key] = case_archive.StoredObject(
        stored.data, metadata, stored.content_type
    )
    with pytest.raises(case_archive.ArchiveIntegrityError):
        archive.get_bytes(ref.key)


def test_wrong_master_key_cannot_decrypt_archive():
    store = case_archive.MemoryObjectStore()
    first = case_archive.EncryptedArchive(store, KEY)
    ref = first.put_bytes(
        first.new_case_id(), "test", "artifact", b"secret", media_type="application/octet-stream"
    )
    second = case_archive.EncryptedArchive(store, b"z" * 32)
    with pytest.raises(case_archive.ArchiveIntegrityError):
        second.get_bytes(ref)


@pytest.mark.parametrize(
    "case_id",
    ["", "abc", "g" * 32, "0" * 31, "0" * 33, "patient-name-should-never-be-a-case-id"],
)
def test_invalid_case_identifiers_are_rejected(case_id):
    archive = make_archive()
    with pytest.raises(ValueError):
        archive.put_bytes(case_id, "test", "artifact", b"x", media_type="application/octet-stream")


def test_source_archive_uses_random_case_path_not_patient_or_filename():
    archive = make_archive()
    case_id = archive.new_case_id()
    refs = archive.archive_sources(
        case_id,
        [(b"image-a", "HASAN_CENGIZ_OD.jpg"), (b"image-b", "patient-123-OS.png")],
        patient_metadata={"patient_name": "Hasan Cengiz", "patient_id": "123"},
        extracted={"eyes": []},
    )
    assert len(refs) == 3
    for ref in refs:
        lowered = ref.key.lower()
        assert "hasan" not in lowered
        assert "cengiz" not in lowered
        assert "patient-123" not in lowered
        assert ref.key.startswith(f"cases/{case_id}/")


def test_source_manifest_preserves_original_filename_inside_encryption_only():
    archive = make_archive()
    case_id = archive.new_case_id()
    refs = archive.archive_sources(
        case_id,
        [(b"image-a", "original-name.jpg")],
        patient_metadata={"patient_name": "Patient Name"},
        extracted={"eyes": [{"eye": "OD"}]},
    )
    intake_ref = next(ref for ref in refs if ref.kind == "intake-json")
    intake = json.loads(archive.get_bytes(intake_ref))
    assert intake["source_files"][0]["original_filename"] == "original-name.jpg"
    assert intake["patient_metadata"]["patient_name"] == "Patient Name"
    assert "original-name" not in intake_ref.key
    assert "patient" not in intake_ref.key.lower()


def test_source_media_type_is_preserved_from_filename_extension():
    archive = make_archive()
    refs = archive.archive_sources(
        archive.new_case_id(),
        [(b"webp", "map.webp")],
        patient_metadata={},
        extracted={},
    )
    source = next(ref for ref in refs if ref.kind == "pentacam-source")
    assert source.media_type == "image/webp"


def test_source_inventory_round_trip_preserves_order_and_encrypted_filename():
    archive = make_archive()
    case_id = archive.new_case_id()
    archive.archive_sources(
        case_id,
        [(b"second", "Patient OS.png"), (b"first", "Patient OD.jpg")],
        patient_metadata={"patient_name": "Patient Name"},
        extracted={},
    )
    sources = archive.list_sources(case_id)
    assert [source.ordinal for source in sources] == [1, 2]
    assert [source.original_filename for source in sources] == ["Patient OS.png", "Patient OD.jpg"]
    assert archive.get_bytes(sources[0].artifact) == b"second"
    assert archive.find_source(case_id, 2) == sources[1]
    assert archive.find_source(case_id, 99) is None


def test_source_inventory_rejects_invalid_case_identifier_without_listing_storage():
    archive = make_archive()
    assert archive.list_sources("patient-name") == tuple()
    assert archive.find_source("patient-name", 1) is None


def test_source_inventory_fails_closed_when_encrypted_intake_is_tampered():
    archive = make_archive()
    case_id = archive.new_case_id()
    refs = archive.archive_sources(
        case_id,
        [(b"image", "map.jpg")],
        patient_metadata={},
        extracted={},
    )
    intake = next(ref for ref in refs if ref.kind == "intake-json")
    stored = archive.store.objects[intake.key]
    altered = bytearray(stored.data)
    altered[-1] ^= 1
    archive.store.objects[intake.key] = case_archive.StoredObject(
        bytes(altered), stored.metadata, stored.content_type
    )
    with pytest.raises(case_archive.ArchiveIntegrityError):
        archive.list_sources(case_id)


def test_ready_archive_generates_canonical_json_and_both_report_languages():
    archive = make_archive()
    revision = archive.archive_ready(
        archive.new_case_id(),
        ready_payload(),
        pdf_builder=pdf_builder,
        docx_builder=docx_builder,
    )
    assert len(revision.artifacts) == 6
    assert {ref.kind for ref in revision.artifacts} == {
        "assessment-json", "report-pdf", "report-docx", "manifest-json"
    }
    report_locales = sorted(
        ref.locale for ref in revision.artifacts if ref.kind.startswith("report-")
    )
    assert report_locales == ["en", "en", "tr", "tr"]


def test_revision_paths_keep_revision_namespace_components():
    archive = make_archive()
    case_id = archive.new_case_id()
    revision = archive.archive_ready(
        case_id, ready_payload(), pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    assert all(
        ref.key.startswith(f"cases/{case_id}/revisions/{revision.revision_id}/")
        for ref in revision.artifacts
    )


def test_report_token_and_presentation_locale_are_not_in_canonical_snapshot():
    archive = make_archive()
    revision = archive.archive_ready(
        archive.new_case_id(), ready_payload(), pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    assessment = next(ref for ref in revision.artifacts if ref.kind == "assessment-json")
    payload = json.loads(archive.get_bytes(assessment))
    assert "report_token" not in payload
    assert "locale" not in payload
    assert b"must-never-be-archived" not in archive.get_bytes(assessment)


@pytest.mark.parametrize(
    "locale,kind,expected",
    [
        ("en", "pdf", b"PDF:en:PASS"),
        ("tr", "pdf", b"PDF:tr:PASS"),
        ("en", "docx", b"DOCX:en:PASS"),
        ("tr", "docx", b"DOCX:tr:PASS"),
    ],
)
def test_archived_reports_can_be_retrieved_exactly(locale, kind, expected):
    archive = make_archive()
    case_id = archive.new_case_id()
    revision = archive.archive_ready(
        case_id, ready_payload(), pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    ref = archive.find_report(case_id, revision.revision_id, locale, kind)
    assert ref is not None
    assert archive.get_bytes(ref) == expected


def test_turkish_locale_prefix_selects_turkish_report():
    archive = make_archive()
    case_id = archive.new_case_id()
    revision = archive.archive_ready(
        case_id, ready_payload(), pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    ref = archive.find_report(case_id, revision.revision_id, "tr-TR", "pdf")
    assert ref is not None
    assert archive.get_bytes(ref) == b"PDF:tr:PASS"


def test_missing_report_returns_none():
    archive = make_archive()
    assert archive.find_report(archive.new_case_id(), "missing", "en", "pdf") is None


def test_internal_archive_fields_are_removed_from_canonical_snapshot():
    payload = ready_payload()
    payload["_archive_case_id"] = "x"
    payload["_archive_revision_id"] = "y"
    cleaned = case_archive.EncryptedArchive._canonical_ready(payload)
    assert not any(key.startswith("_archive_") for key in cleaned)


def test_revision_identity_is_locale_neutral():
    archive = make_archive()
    payload_en = ready_payload()
    payload_en["locale"] = "en"
    payload_tr = deepcopy(payload_en)
    payload_tr["locale"] = "tr"
    first = archive.archive_ready(
        archive.new_case_id(), payload_en, pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    second = archive.archive_ready(
        archive.new_case_id(), payload_tr, pdf_builder=pdf_builder, docx_builder=docx_builder
    )
    assert first.revision_id == second.revision_id


def test_repeated_identical_plaintext_keeps_first_ciphertext_immutable():
    archive = make_archive()
    case_id = archive.new_case_id()
    first = archive.put_bytes(case_id, "test", "artifact", b"same", media_type="application/pdf")
    first_ciphertext = archive.store.get(first.key).data
    second = archive.put_bytes(case_id, "test", "artifact", b"same", media_type="application/pdf")
    assert first.key == second.key
    assert archive.store.get(first.key).data == first_ciphertext
    assert archive.get_bytes(first) == b"same"


def test_memory_store_rejects_conflicting_metadata_for_existing_key():
    store = case_archive.MemoryObjectStore()
    store.put("k", b"a", content_type="x", metadata={"plaintext-sha256": "a"})
    with pytest.raises(case_archive.ArchiveIntegrityError):
        store.put("k", b"b", content_type="x", metadata={"plaintext-sha256": "b"})


def test_memory_store_lists_keys_in_sorted_order():
    store = case_archive.MemoryObjectStore()
    for key in ("p/z", "p/a", "other"):
        store.put(key, key.encode(), content_type="x", metadata={"k": key})
    assert store.list("p/") == ["p/a", "p/z"]


def test_s3_store_creates_missing_object_once():
    client = FakeS3Client()
    store = case_archive.S3ObjectStore(client, "bucket")
    metadata = {"plaintext-sha256": "a" * 64, "plaintext-bytes": "1", "media-type": "x"}
    store.put("key", b"ciphertext-1", content_type="application/octet-stream", metadata=metadata)
    assert client.put_calls == 1
    assert client.objects["key"]["Body"] == b"ciphertext-1"


def test_s3_store_retry_never_overwrites_matching_logical_object():
    client = FakeS3Client()
    store = case_archive.S3ObjectStore(client, "bucket")
    metadata = {"plaintext-sha256": "a" * 64, "plaintext-bytes": "1", "media-type": "x"}
    store.put("key", b"ciphertext-1", content_type="application/octet-stream", metadata=metadata)
    store.put("key", b"ciphertext-2", content_type="application/octet-stream", metadata=metadata)
    assert client.put_calls == 1
    assert client.objects["key"]["Body"] == b"ciphertext-1"


def test_s3_store_rejects_existing_key_with_conflicting_metadata():
    client = FakeS3Client()
    store = case_archive.S3ObjectStore(client, "bucket")
    first = {"plaintext-sha256": "a" * 64, "plaintext-bytes": "1", "media-type": "x"}
    second = {"plaintext-sha256": "b" * 64, "plaintext-bytes": "1", "media-type": "x"}
    store.put("key", b"ciphertext-1", content_type="application/octet-stream", metadata=first)
    with pytest.raises(case_archive.ArchiveIntegrityError):
        store.put("key", b"ciphertext-2", content_type="application/octet-stream", metadata=second)
    assert client.put_calls == 1


def test_required_runtime_converts_archive_failure_to_service_unavailable():
    runtime = case_archive.CaseArchiveRuntime(None, required=True)
    with pytest.raises(HTTPException) as exc:
        runtime.fail_or_continue(RuntimeError("storage down"))
    assert exc.value.status_code == 503
    assert "archive" in exc.value.detail.lower()


def test_optional_runtime_does_not_block_on_archive_failure():
    runtime = case_archive.CaseArchiveRuntime(None, required=False)
    assert runtime.fail_or_continue(RuntimeError("storage down")) is None


def test_runtime_token_mapping_is_bounded(monkeypatch):
    monkeypatch.setattr(case_archive, "MAX_TOKEN_CASE_MAPPINGS", 3)
    runtime = case_archive.CaseArchiveRuntime(None, required=False)
    for index in range(5):
        runtime._remember(runtime._token_case, f"token-{index}", f"case-{index}")
    assert list(runtime._token_case) == ["token-2", "token-3", "token-4"]


def test_runtime_without_configuration_is_disabled_by_default(monkeypatch):
    for name in (
        "CERAI_ARCHIVE_REQUIRED", "CERAI_ARCHIVE_BUCKET", "BUCKET", "AWS_S3_BUCKET_NAME",
        "CERAI_ARCHIVE_ENDPOINT", "ENDPOINT", "AWS_ENDPOINT_URL", "CERAI_ARCHIVE_MASTER_KEY_B64",
    ):
        monkeypatch.delenv(name, raising=False)
    runtime = case_archive.runtime_from_environment()
    assert runtime.enabled is False
    assert runtime.required is False


def test_required_runtime_without_configuration_fails_startup(monkeypatch):
    for name in (
        "CERAI_ARCHIVE_BUCKET", "BUCKET", "AWS_S3_BUCKET_NAME", "CERAI_ARCHIVE_ENDPOINT",
        "ENDPOINT", "AWS_ENDPOINT_URL", "CERAI_ARCHIVE_MASTER_KEY_B64",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CERAI_ARCHIVE_REQUIRED", "1")
    with pytest.raises(case_archive.ArchiveConfigurationError):
        case_archive.runtime_from_environment()


def test_canonical_runtime_has_archive_boundary_installed():
    import canonical_engine

    assert canonical_engine.core._cerai_case_archive_installed is True
    assert canonical_engine.core._cerai_case_archive_runtime is not None
