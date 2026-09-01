from io import BytesIO

import pytest
from botocore.exceptions import ClientError

import archive_migration


class FakeS3:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.put_calls = 0

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        return {
            "Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(Prefix)],
            "IsTruncated": False,
        }

    def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        item = self.objects[Key]
        return {
            "Body": BytesIO(item["data"]),
            "ContentType": item.get("content_type", "application/octet-stream"),
            "Metadata": dict(item.get("metadata", {})),
        }

    def put_object(self, *, Bucket, Key, Body, ContentType, Metadata):
        self.put_calls += 1
        self.objects[Key] = {
            "data": bytes(Body),
            "content_type": ContentType,
            "metadata": dict(Metadata),
        }


def encrypted_object(data=b"ciphertext", digest="a" * 64):
    return {
        "data": data,
        "content_type": "application/octet-stream",
        "metadata": {
            "cer-ai-format": "CER-AI-ARCHIVE-v1",
            "plaintext-sha256": digest,
            "plaintext-bytes": "7",
            "media-type": "application/pdf",
        },
    }


def test_dry_run_never_writes_destination():
    source = FakeS3({"cases/a/object.enc": encrypted_object()})
    destination = FakeS3()
    result = archive_migration.migrate_prefix(
        source, "source", destination, "destination", apply=False
    )
    assert result.discovered == 1
    assert result.copied == 0
    assert result.already_verified == 0
    assert result.dry_run_pending == 1
    assert result.ciphertext_bytes == len(b"ciphertext")
    assert destination.put_calls == 0
    assert destination.objects == {}


def test_apply_copies_ciphertext_and_metadata_then_verifies():
    original = encrypted_object(data=b"encrypted-patient-object")
    source = FakeS3({"cases/abc/object.enc": original})
    destination = FakeS3()
    result = archive_migration.migrate_prefix(
        source, "source", destination, "destination", apply=True
    )
    assert result.copied == 1
    assert result.dry_run_pending == 0
    assert destination.put_calls == 1
    copied = destination.objects["cases/abc/object.enc"]
    assert copied["data"] == original["data"]
    assert copied["metadata"] == original["metadata"]
    assert copied["content_type"] == original["content_type"]


def test_existing_matching_destination_is_verified_without_overwrite():
    original = encrypted_object()
    source = FakeS3({"cases/abc/object.enc": original})
    destination = FakeS3({"cases/abc/object.enc": encrypted_object()})
    result = archive_migration.migrate_prefix(
        source, "source", destination, "destination", apply=True
    )
    assert result.copied == 0
    assert result.already_verified == 1
    assert destination.put_calls == 0


def test_conflicting_destination_aborts_instead_of_overwriting():
    source = FakeS3({"cases/abc/object.enc": encrypted_object(data=b"source")})
    destination = FakeS3({"cases/abc/object.enc": encrypted_object(data=b"different")})
    with pytest.raises(archive_migration.MigrationIntegrityError):
        archive_migration.migrate_prefix(
            source, "source", destination, "destination", apply=True
        )
    assert destination.put_calls == 0


def test_migration_only_reads_requested_case_namespace():
    source = FakeS3({
        "cases/abc/object.enc": encrypted_object(),
        "unrelated/plain.txt": {"data": b"do-not-copy", "metadata": {}, "content_type": "text/plain"},
    })
    destination = FakeS3()
    result = archive_migration.migrate_prefix(
        source, "source", destination, "destination", prefix="cases/", apply=True
    )
    assert result.discovered == 1
    assert "cases/abc/object.enc" in destination.objects
    assert "unrelated/plain.txt" not in destination.objects


def test_unsafe_prefix_is_rejected():
    source = FakeS3()
    destination = FakeS3()
    for prefix in ("", "/cases/", "../cases/"):
        with pytest.raises(ValueError):
            archive_migration.migrate_prefix(
                source, "source", destination, "destination", prefix=prefix
            )


def test_environment_config_rejects_missing_or_invalid_values(monkeypatch):
    names = (
        "BUCKET", "ENDPOINT", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "REGION", "URL_STYLE"
    )
    for suffix in names:
        monkeypatch.delenv(f"CERAI_MIGRATION_SOURCE_{suffix}", raising=False)
    with pytest.raises(archive_migration.MigrationConfigurationError):
        archive_migration.EndpointConfig.from_environment("SOURCE")

    monkeypatch.setenv("CERAI_MIGRATION_SOURCE_BUCKET", "bucket")
    monkeypatch.setenv("CERAI_MIGRATION_SOURCE_ENDPOINT", "https://example.invalid")
    monkeypatch.setenv("CERAI_MIGRATION_SOURCE_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("CERAI_MIGRATION_SOURCE_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("CERAI_MIGRATION_SOURCE_URL_STYLE", "bad")
    with pytest.raises(archive_migration.MigrationConfigurationError):
        archive_migration.EndpointConfig.from_environment("SOURCE")
