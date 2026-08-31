"""Provider-neutral, ciphertext-preserving CER-AI archive migration.

This module copies already encrypted archive objects between two S3-compatible providers without
opening clinical plaintext. Destination writes are create-once: an existing matching object is verified
and retained; an existing conflicting object aborts migration rather than being overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from typing import Any, Dict, Optional


class MigrationConfigurationError(RuntimeError):
    pass


class MigrationIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class EndpointConfig:
    bucket: str
    endpoint: str
    access_key: str
    secret_key: str
    region: str = "auto"
    url_style: str = "virtual"

    @classmethod
    def from_environment(cls, prefix: str) -> "EndpointConfig":
        normalized = str(prefix).strip().upper()
        values = {
            "bucket": os.getenv(f"CERAI_MIGRATION_{normalized}_BUCKET", "").strip(),
            "endpoint": os.getenv(f"CERAI_MIGRATION_{normalized}_ENDPOINT", "").strip(),
            "access_key": os.getenv(f"CERAI_MIGRATION_{normalized}_ACCESS_KEY_ID", "").strip(),
            "secret_key": os.getenv(f"CERAI_MIGRATION_{normalized}_SECRET_ACCESS_KEY", "").strip(),
        }
        missing = sorted(key for key, value in values.items() if not value)
        if missing:
            raise MigrationConfigurationError(
                f"Missing {normalized} archive migration configuration: " + ", ".join(missing)
            )
        region = os.getenv(f"CERAI_MIGRATION_{normalized}_REGION", "auto").strip() or "auto"
        style = os.getenv(f"CERAI_MIGRATION_{normalized}_URL_STYLE", "virtual").strip().lower()
        if style not in {"virtual", "path"}:
            raise MigrationConfigurationError(
                f"CERAI_MIGRATION_{normalized}_URL_STYLE must be 'virtual' or 'path'."
            )
        return cls(region=region, url_style=style, **values)

    def client(self):
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(s3={"addressing_style": self.url_style}),
        )


@dataclass(frozen=True)
class ObjectFingerprint:
    ciphertext_sha256: str
    ciphertext_bytes: int
    content_type: str
    metadata: Dict[str, str]


@dataclass(frozen=True)
class MigrationResult:
    discovered: int
    copied: int
    already_verified: int
    dry_run_pending: int
    ciphertext_bytes: int


def _metadata(value: Any) -> Dict[str, str]:
    return {str(key): str(item) for key, item in (value or {}).items()}


def _fingerprint(data: bytes, *, content_type: str, metadata: Dict[str, str]) -> ObjectFingerprint:
    return ObjectFingerprint(
        ciphertext_sha256=hashlib.sha256(data).hexdigest(),
        ciphertext_bytes=len(data),
        content_type=str(content_type or "application/octet-stream"),
        metadata=_metadata(metadata),
    )


def _read_object(client: Any, bucket: str, key: str) -> tuple[bytes, ObjectFingerprint]:
    response = client.get_object(Bucket=bucket, Key=key)
    data = response["Body"].read()
    fingerprint = _fingerprint(
        data,
        content_type=str(response.get("ContentType") or "application/octet-stream"),
        metadata=_metadata(response.get("Metadata")),
    )
    return data, fingerprint


def _destination_fingerprint(client: Any, bucket: str, key: str) -> Optional[ObjectFingerprint]:
    from botocore.exceptions import ClientError

    try:
        data, fingerprint = _read_object(client, bucket, key)
    except ClientError as exc:
        code = str((exc.response.get("Error") or {}).get("Code") or "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    del data
    return fingerprint


def list_keys(client: Any, bucket: str, prefix: str = "cases/") -> list[str]:
    keys: list[str] = []
    token: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        keys.extend(str(item["Key"]) for item in response.get("Contents") or [])
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
        if not token:
            raise MigrationIntegrityError("Source listing was truncated without a continuation token.")
    return sorted(keys)


def migrate_prefix(
    source_client: Any,
    source_bucket: str,
    destination_client: Any,
    destination_bucket: str,
    *,
    prefix: str = "cases/",
    apply: bool = False,
) -> MigrationResult:
    """Copy encrypted objects and verify ciphertext, size, content type, and metadata.

    `apply=False` is a read-only dry run. `apply=True` writes only missing destination objects and
    refuses to overwrite any conflicting object.
    """
    if not prefix or prefix.startswith("/") or ".." in prefix:
        raise ValueError("Migration prefix must be a safe relative object prefix.")

    keys = list_keys(source_client, source_bucket, prefix)
    copied = 0
    verified = 0
    pending = 0
    total_bytes = 0

    for key in keys:
        source_data, source_fp = _read_object(source_client, source_bucket, key)
        total_bytes += source_fp.ciphertext_bytes
        destination_fp = _destination_fingerprint(destination_client, destination_bucket, key)

        if destination_fp is not None:
            if destination_fp != source_fp:
                raise MigrationIntegrityError(
                    f"Destination contains a conflicting CER-AI archive object: {key}"
                )
            verified += 1
            continue

        if not apply:
            pending += 1
            continue

        destination_client.put_object(
            Bucket=destination_bucket,
            Key=key,
            Body=source_data,
            ContentType=source_fp.content_type,
            Metadata=source_fp.metadata,
        )
        after = _destination_fingerprint(destination_client, destination_bucket, key)
        if after != source_fp:
            raise MigrationIntegrityError(
                f"Destination verification failed after copying CER-AI archive object: {key}"
            )
        copied += 1

    return MigrationResult(
        discovered=len(keys),
        copied=copied,
        already_verified=verified,
        dry_run_pending=pending,
        ciphertext_bytes=total_bytes,
    )


def migrate_from_environment() -> MigrationResult:
    source = EndpointConfig.from_environment("SOURCE")
    destination = EndpointConfig.from_environment("DESTINATION")
    if source.endpoint == destination.endpoint and source.bucket == destination.bucket:
        raise MigrationConfigurationError("Source and destination archive locations are identical.")
    apply = os.getenv("CERAI_MIGRATION_APPLY", "0").strip() == "1"
    return migrate_prefix(
        source.client(),
        source.bucket,
        destination.client(),
        destination.bucket,
        prefix="cases/",
        apply=apply,
    )
