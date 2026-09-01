"""Encrypted, provider-neutral case archive for CER-AI.

The clinical engine never depends on this module. It wraps the web/workflow boundary and stores
source images, canonical assessment snapshots, and generated reports in private S3-compatible object
storage. Object keys contain only random case identifiers and content hashes; patient names and IDs
are never used in storage paths.

Railway Storage Buckets currently do not provide server-side encryption, object versioning, or object
locks. CER-AI therefore encrypts every archived payload before upload, verifies plaintext SHA-256 on
read, and refuses application-level overwrites of an existing logical artifact.
"""

from __future__ import annotations

import base64
from collections import OrderedDict
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import PurePosixPath
from threading import RLock
from typing import Any, Callable, Dict, Iterable, Optional, Protocol
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException


ARCHIVE_FORMAT = "CER-AI-ARCHIVE-v1"
ENVELOPE_MAGIC = b"CER-AI1"
MAX_TOKEN_CASE_MAPPINGS = 256


class ArchiveConfigurationError(RuntimeError):
    """Archive configuration is missing, malformed, or internally inconsistent."""


class ArchiveIntegrityError(RuntimeError):
    """Archived ciphertext cannot be authenticated or does not match its recorded digest."""


@dataclass(frozen=True)
class StoredObject:
    data: bytes
    metadata: Dict[str, str]
    content_type: str = "application/octet-stream"


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str, metadata: Dict[str, str]) -> None: ...
    def get(self, key: str) -> StoredObject: ...
    def list(self, prefix: str) -> list[str]: ...


class MemoryObjectStore:
    """Deterministic in-memory store used by archive tests; not a production backend."""

    def __init__(self) -> None:
        self.objects: Dict[str, StoredObject] = {}

    def put(self, key: str, data: bytes, *, content_type: str, metadata: Dict[str, str]) -> None:
        existing = self.objects.get(key)
        candidate = StoredObject(bytes(data), dict(metadata), content_type)
        if existing is not None:
            # AES-GCM uses a random nonce, so a retry can produce different ciphertext for the same
            # plaintext. Matching authenticated plaintext metadata means the logical object already
            # exists and must be preserved byte-for-byte rather than overwritten.
            if existing.metadata == candidate.metadata and existing.content_type == candidate.content_type:
                return
            raise ArchiveIntegrityError(f"Attempted overwrite of immutable archive key: {key}")
        self.objects[key] = candidate

    def get(self, key: str) -> StoredObject:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]

    def list(self, prefix: str) -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))


class S3ObjectStore:
    """Small S3 adapter compatible with Railway Storage Buckets and later S3 providers."""

    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    @classmethod
    def from_environment(cls) -> "S3ObjectStore":
        bucket = (
            os.getenv("CERAI_ARCHIVE_BUCKET")
            or os.getenv("BUCKET")
            or os.getenv("AWS_S3_BUCKET_NAME")
            or ""
        ).strip()
        endpoint = (
            os.getenv("CERAI_ARCHIVE_ENDPOINT")
            or os.getenv("ENDPOINT")
            or os.getenv("AWS_ENDPOINT_URL")
            or ""
        ).strip()
        access_key = (
            os.getenv("CERAI_ARCHIVE_ACCESS_KEY_ID")
            or os.getenv("ACCESS_KEY_ID")
            or os.getenv("AWS_ACCESS_KEY_ID")
            or ""
        ).strip()
        secret_key = (
            os.getenv("CERAI_ARCHIVE_SECRET_ACCESS_KEY")
            or os.getenv("SECRET_ACCESS_KEY")
            or os.getenv("AWS_SECRET_ACCESS_KEY")
            or ""
        ).strip()
        region = (
            os.getenv("CERAI_ARCHIVE_REGION")
            or os.getenv("REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "auto"
        ).strip()
        style = (
            os.getenv("CERAI_ARCHIVE_URL_STYLE")
            or os.getenv("AWS_S3_URL_STYLE")
            or "virtual"
        ).strip().lower()
        required = {
            "bucket": bucket,
            "endpoint": endpoint,
            "access_key": access_key,
            "secret_key": secret_key,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ArchiveConfigurationError("Missing S3 archive configuration: " + ", ".join(missing))
        if style not in {"virtual", "path"}:
            raise ArchiveConfigurationError("CERAI_ARCHIVE_URL_STYLE must be 'virtual' or 'path'.")

        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(s3={"addressing_style": style}),
        )
        return cls(client, bucket)

    def put(self, key: str, data: bytes, *, content_type: str, metadata: Dict[str, str]) -> None:
        """Create once; an existing logical object is never replaced by the application."""
        from botocore.exceptions import ClientError

        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            code = str((exc.response.get("Error") or {}).get("Code") or "")
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            existing_metadata = {str(k): str(v) for k, v in (existing.get("Metadata") or {}).items()}
            expected_metadata = {str(k): str(v) for k, v in metadata.items()}
            existing_type = str(existing.get("ContentType") or "application/octet-stream")
            if existing_metadata == expected_metadata and existing_type == content_type:
                return
            raise ArchiveIntegrityError(f"Attempted overwrite of immutable archive key: {key}")

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={str(k): str(v) for k, v in metadata.items()},
        )

    def get(self, key: str) -> StoredObject:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"].read()
        return StoredObject(
            data=body,
            metadata={str(k): str(v) for k, v in (response.get("Metadata") or {}).items()},
            content_type=str(response.get("ContentType") or "application/octet-stream"),
        )

    def list(self, prefix: str) -> list[str]:
        keys: list[str] = []
        token: Optional[str] = None
        while True:
            kwargs: Dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self.client.list_objects_v2(**kwargs)
            keys.extend(str(item["Key"]) for item in response.get("Contents") or [])
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
            if not token:
                break
        return sorted(keys)


@dataclass(frozen=True)
class ArtifactRef:
    key: str
    sha256: str
    plaintext_bytes: int
    media_type: str
    kind: str
    locale: Optional[str] = None


@dataclass(frozen=True)
class RevisionRef:
    case_id: str
    revision_id: str
    artifacts: tuple[ArtifactRef, ...]


@dataclass(frozen=True)
class SourceFileRef:
    ordinal: int
    original_filename: str
    artifact: ArtifactRef


class EncryptedArchive:
    """Encrypt and integrity-protect every object before it reaches the storage provider."""

    def __init__(self, store: ObjectStore, master_key: bytes) -> None:
        if len(master_key) != 32:
            raise ArchiveConfigurationError("CER-AI archive master key must decode to exactly 32 bytes.")
        self.store = store
        self._aead = AESGCM(master_key)

    @staticmethod
    def decode_master_key(value: str) -> bytes:
        try:
            key = base64.b64decode(value.strip(), validate=True)
        except Exception as exc:
            raise ArchiveConfigurationError("CERAI_ARCHIVE_MASTER_KEY_B64 must be valid base64.") from exc
        if len(key) != 32:
            raise ArchiveConfigurationError("CERAI_ARCHIVE_MASTER_KEY_B64 must decode to exactly 32 bytes.")
        return key

    @classmethod
    def from_environment(cls) -> "EncryptedArchive":
        key_value = os.getenv("CERAI_ARCHIVE_MASTER_KEY_B64", "").strip()
        if not key_value:
            raise ArchiveConfigurationError(
                "CERAI_ARCHIVE_MASTER_KEY_B64 is required when archive storage is enabled."
            )
        return cls(S3ObjectStore.from_environment(), cls.decode_master_key(key_value))

    @staticmethod
    def new_case_id() -> str:
        return uuid4().hex

    @staticmethod
    def _safe_component(value: str) -> str:
        cleaned = "".join(ch for ch in str(value).lower() if ch.isalnum() or ch in {"-", "_"})
        return cleaned[:48] or "artifact"

    @classmethod
    def _safe_group_parts(cls, group: str) -> list[str]:
        raw_parts = [part for part in str(group).split("/") if part]
        if not raw_parts:
            return ["artifact"]
        return [cls._safe_component(part) for part in raw_parts]

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _encrypt(self, plaintext: bytes, *, aad: bytes) -> bytes:
        nonce = os.urandom(12)
        ciphertext = self._aead.encrypt(nonce, plaintext, aad)
        return ENVELOPE_MAGIC + nonce + ciphertext

    def _decrypt(self, envelope: bytes, *, aad: bytes) -> bytes:
        if not envelope.startswith(ENVELOPE_MAGIC) or len(envelope) <= len(ENVELOPE_MAGIC) + 12:
            raise ArchiveIntegrityError("Unrecognized or truncated CER-AI archive envelope.")
        nonce_start = len(ENVELOPE_MAGIC)
        nonce = envelope[nonce_start:nonce_start + 12]
        ciphertext = envelope[nonce_start + 12:]
        try:
            return self._aead.decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise ArchiveIntegrityError("Archived object authentication failed.") from exc

    def put_bytes(
        self,
        case_id: str,
        group: str,
        kind: str,
        plaintext: bytes,
        *,
        media_type: str,
        locale: Optional[str] = None,
        ordinal: Optional[int] = None,
    ) -> ArtifactRef:
        if not case_id or any(ch not in "0123456789abcdef" for ch in case_id.lower()) or len(case_id) != 32:
            raise ValueError("case_id must be a 32-character hexadecimal identifier.")
        digest = self._digest(plaintext)
        components = ["cases", case_id, *self._safe_group_parts(group)]
        if ordinal is not None:
            components.append(f"{int(ordinal):03d}")
        label = self._safe_component(kind)
        if locale:
            label += "-" + self._safe_component(locale)
        key = str(PurePosixPath(*components, f"{label}-{digest}.enc"))
        aad = f"{ARCHIVE_FORMAT}|{case_id}|{key}|{digest}".encode("utf-8")
        envelope = self._encrypt(plaintext, aad=aad)
        metadata = {
            "cer-ai-format": ARCHIVE_FORMAT,
            "plaintext-sha256": digest,
            "plaintext-bytes": str(len(plaintext)),
            "media-type": media_type,
        }
        self.store.put(key, envelope, content_type="application/octet-stream", metadata=metadata)
        return ArtifactRef(key, digest, len(plaintext), media_type, kind, locale)

    def get_bytes(self, ref_or_key: ArtifactRef | str) -> bytes:
        ref = ref_or_key if isinstance(ref_or_key, ArtifactRef) else None
        key = ref.key if ref else str(ref_or_key)
        stored = self.store.get(key)
        digest = (ref.sha256 if ref else stored.metadata.get("plaintext-sha256") or "").lower()
        if len(digest) != 64:
            raise ArchiveIntegrityError("Archived object is missing its plaintext digest.")
        parts = PurePosixPath(key).parts
        if len(parts) < 3 or parts[0] != "cases":
            raise ArchiveIntegrityError("Archived object key is outside the CER-AI case namespace.")
        case_id = parts[1]
        aad = f"{ARCHIVE_FORMAT}|{case_id}|{key}|{digest}".encode("utf-8")
        plaintext = self._decrypt(stored.data, aad=aad)
        if self._digest(plaintext) != digest:
            raise ArchiveIntegrityError("Archived plaintext SHA-256 verification failed.")
        if ref and len(plaintext) != ref.plaintext_bytes:
            raise ArchiveIntegrityError("Archived plaintext size verification failed.")
        return plaintext

    def archive_sources(
        self,
        case_id: str,
        image_payloads: Iterable[tuple[bytes, str]],
        *,
        patient_metadata: Dict[str, Any],
        extracted: Dict[str, Any],
    ) -> tuple[ArtifactRef, ...]:
        refs: list[ArtifactRef] = []
        source_index: list[Dict[str, Any]] = []
        for index, (raw, filename) in enumerate(image_payloads, 1):
            media_type = mimetypes.guess_type(str(filename))[0] or "application/octet-stream"
            ref = self.put_bytes(
                case_id,
                "source",
                "pentacam-source",
                raw,
                media_type=media_type,
                ordinal=index,
            )
            refs.append(ref)
            source_index.append({
                "ordinal": index,
                "original_filename": filename,
                "artifact": asdict(ref),
            })
        intake = {
            "archive_format": ARCHIVE_FORMAT,
            "case_id": case_id,
            "archived_at_utc": datetime.now(timezone.utc).isoformat(),
            "patient_metadata": deepcopy(patient_metadata),
            "source_files": source_index,
            "extracted": deepcopy(extracted),
        }
        payload = json.dumps(
            intake,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        refs.append(
            self.put_bytes(case_id, "intake", "intake-json", payload, media_type="application/json")
        )
        return tuple(refs)

    def list_sources(self, case_id: str) -> tuple[SourceFileRef, ...]:
        """Return the authenticated source inventory without exposing storage object keys."""
        if not case_id or any(ch not in "0123456789abcdef" for ch in case_id.lower()) or len(case_id) != 32:
            return tuple()
        intake_keys = self.store.list(f"cases/{case_id}/intake/")
        if not intake_keys:
            return tuple()
        if len(intake_keys) != 1:
            raise ArchiveIntegrityError("Archived case has an ambiguous source intake manifest.")
        try:
            intake = json.loads(self.get_bytes(intake_keys[0]))
        except ArchiveIntegrityError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ArchiveIntegrityError("Archived source intake manifest is unreadable.") from exc
        if intake.get("archive_format") != ARCHIVE_FORMAT or intake.get("case_id") != case_id:
            raise ArchiveIntegrityError("Archived source intake manifest identity is invalid.")

        sources: list[SourceFileRef] = []
        seen_ordinals: set[int] = set()
        for item in intake.get("source_files") or []:
            if not isinstance(item, dict) or not isinstance(item.get("artifact"), dict):
                raise ArchiveIntegrityError("Archived source intake entry is invalid.")
            artifact = item["artifact"]
            try:
                ordinal = int(item.get("ordinal"))
                plaintext_bytes = int(artifact.get("plaintext_bytes"))
            except (TypeError, ValueError):
                raise ArchiveIntegrityError("Archived source intake ordinal or size is invalid.")
            original_filename = str(item.get("original_filename") or "").strip()
            key = str(artifact.get("key") or "")
            sha256 = str(artifact.get("sha256") or "").lower()
            media_type = str(artifact.get("media_type") or "application/octet-stream")
            expected_prefix = f"cases/{case_id}/source/{ordinal:03d}/pentacam-source-"
            if (
                ordinal < 1
                or ordinal in seen_ordinals
                or not original_filename
                or not key.startswith(expected_prefix)
                or not key.endswith(".enc")
                or len(sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in sha256)
                or plaintext_bytes < 0
                or artifact.get("kind") != "pentacam-source"
                or artifact.get("locale") is not None
            ):
                raise ArchiveIntegrityError("Archived source intake artifact reference is invalid.")
            seen_ordinals.add(ordinal)
            sources.append(
                SourceFileRef(
                    ordinal=ordinal,
                    original_filename=original_filename,
                    artifact=ArtifactRef(
                        key=key,
                        sha256=sha256,
                        plaintext_bytes=plaintext_bytes,
                        media_type=media_type,
                        kind="pentacam-source",
                        locale=None,
                    ),
                )
            )
        return tuple(sorted(sources, key=lambda source: source.ordinal))

    def find_source(self, case_id: str, ordinal: int) -> Optional[SourceFileRef]:
        for source in self.list_sources(case_id):
            if source.ordinal == int(ordinal):
                return source
        return None

    @staticmethod
    def _canonical_ready(ready: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = deepcopy(ready)
        cleaned.pop("report_token", None)
        cleaned.pop("locale", None)
        for key in list(cleaned):
            if str(key).startswith("_archive_"):
                cleaned.pop(key, None)
        return cleaned

    def archive_ready(
        self,
        case_id: str,
        ready: Dict[str, Any],
        *,
        pdf_builder: Callable[[Dict[str, Any]], bytes],
        docx_builder: Callable[[Dict[str, Any]], bytes],
    ) -> RevisionRef:
        canonical = self._canonical_ready(ready)
        canonical_bytes = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        revision_id = self._digest(canonical_bytes)[:24]
        group = f"revisions/{revision_id}"
        refs: list[ArtifactRef] = [
            self.put_bytes(
                case_id,
                group,
                "assessment-json",
                canonical_bytes,
                media_type="application/json",
            )
        ]
        for locale in ("en", "tr"):
            localized = deepcopy(canonical)
            localized["locale"] = locale
            pdf = pdf_builder(localized)
            docx = docx_builder(localized)
            refs.append(
                self.put_bytes(
                    case_id,
                    group,
                    "report-pdf",
                    pdf,
                    media_type="application/pdf",
                    locale=locale,
                )
            )
            refs.append(
                self.put_bytes(
                    case_id,
                    group,
                    "report-docx",
                    docx,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    locale=locale,
                )
            )
        manifest = {
            "archive_format": ARCHIVE_FORMAT,
            "case_id": case_id,
            "revision_id": revision_id,
            "archived_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifacts": [asdict(ref) for ref in refs],
        }
        manifest_bytes = json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        refs.append(
            self.put_bytes(
                case_id,
                group,
                "manifest-json",
                manifest_bytes,
                media_type="application/json",
            )
        )
        return RevisionRef(case_id, revision_id, tuple(refs))

    def find_report(
        self,
        case_id: str,
        revision_id: str,
        locale: str,
        kind: str,
    ) -> Optional[ArtifactRef]:
        locale = "tr" if str(locale).lower().startswith("tr") else "en"
        kind = "report-pdf" if kind == "pdf" else "report-docx"
        prefix = f"cases/{case_id}/revisions/{revision_id}/{kind}-{locale}-"
        keys = self.store.list(prefix)
        if len(keys) != 1:
            return None
        stored = self.store.get(keys[0])
        digest = stored.metadata.get("plaintext-sha256") or ""
        size_text = stored.metadata.get("plaintext-bytes") or "0"
        try:
            size = int(size_text)
        except ValueError:
            return None
        media_type = stored.metadata.get("media-type") or "application/octet-stream"
        return ArtifactRef(keys[0], digest, size, media_type, kind, locale)


class CaseArchiveRuntime:
    """Optional runtime integration; REQUIRED mode blocks release if secure archive fails."""

    def __init__(self, archive: Optional[EncryptedArchive], *, required: bool) -> None:
        self.archive = archive
        self.required = required
        self._lock = RLock()
        self._token_case: "OrderedDict[str, str]" = OrderedDict()
        self._token_revision: "OrderedDict[str, str]" = OrderedDict()
        self._pending: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
            "cer_ai_archive_pending",
            default=None,
        )

    @property
    def enabled(self) -> bool:
        return self.archive is not None

    def _remember(self, mapping: "OrderedDict[str, str]", token: str, value: str) -> None:
        with self._lock:
            mapping[token] = value
            mapping.move_to_end(token)
            while len(mapping) > MAX_TOKEN_CASE_MAPPINGS:
                mapping.popitem(last=False)

    def case_for_token(self, token: str) -> Optional[str]:
        with self._lock:
            return self._token_case.get(token)

    def revision_for_token(self, token: str) -> Optional[str]:
        with self._lock:
            return self._token_revision.get(token)

    def fail_or_continue(self, exc: Exception) -> None:
        if self.required:
            raise HTTPException(
                503,
                "Secure CER-AI case archive is unavailable. The clinical result was not released; "
                "retry after archive service recovery.",
            ) from exc


def runtime_from_environment() -> CaseArchiveRuntime:
    required = os.getenv("CERAI_ARCHIVE_REQUIRED", "0").strip() == "1"
    bucket_markers = any(
        (os.getenv(name) or "").strip()
        for name in (
            "CERAI_ARCHIVE_BUCKET",
            "BUCKET",
            "AWS_S3_BUCKET_NAME",
            "CERAI_ARCHIVE_ENDPOINT",
            "ENDPOINT",
            "AWS_ENDPOINT_URL",
            "CERAI_ARCHIVE_MASTER_KEY_B64",
        )
    )
    if not bucket_markers:
        if required:
            raise ArchiveConfigurationError(
                "CERAI_ARCHIVE_REQUIRED=1 but no archive storage configuration is present."
            )
        return CaseArchiveRuntime(None, required=False)
    return CaseArchiveRuntime(EncryptedArchive.from_environment(), required=required)


def install(core: Any, *, runtime: Optional[CaseArchiveRuntime] = None) -> CaseArchiveRuntime:
    """Install archive hooks without changing any clinical scoring or decision function."""
    if getattr(core, "_cerai_case_archive_installed", False):
        return getattr(core, "_cerai_case_archive_runtime")

    runtime = runtime or runtime_from_environment()
    import assessment_workflow
    import operational_security

    original_read_uploads = operational_security.read_uploads
    original_begin = assessment_workflow.begin
    original_complete = assessment_workflow.complete
    original_export_payload = assessment_workflow.export_payload
    original_build_pdf = core.build_pdf
    original_build_docx = core.build_docx

    async def read_uploads_archived(images):
        payloads = await original_read_uploads(images)
        runtime._pending.set({
            "case_id": EncryptedArchive.new_case_id(),
            "payloads": payloads,
        })
        return payloads

    def finalize_if_ready(response: Dict[str, Any]) -> Dict[str, Any]:
        if not runtime.enabled or response.get("workflow_status") != "READY":
            return response
        token = str(response.get("assessment_token") or "")
        report_token = str(response.get("report_token") or "")
        case_id = runtime.case_for_token(token)
        if not (token and report_token and case_id):
            return response
        try:
            ready = original_export_payload({
                "assessment_token": token,
                "report_token": report_token,
                "locale": "en",
            })
            revision = runtime.archive.archive_ready(
                case_id,
                ready,
                pdf_builder=original_build_pdf,
                docx_builder=original_build_docx,
            )
            runtime._remember(runtime._token_revision, token, revision.revision_id)
            response["archive"] = {
                "status": "ARCHIVED",
                "case_id": case_id,
                "revision_id": revision.revision_id,
            }
        except Exception as exc:
            runtime.fail_or_continue(exc)
            response["archive"] = {"status": "UNAVAILABLE"}
        return response

    def begin_archived(core_arg, extracted, age, plans, modifiers, metadata):
        pending = runtime._pending.get()
        runtime._pending.set(None)
        response = original_begin(core_arg, extracted, age, plans, modifiers, metadata)
        token = str(response.get("assessment_token") or "")
        if pending and token:
            case_id = str(pending["case_id"])
            runtime._remember(runtime._token_case, token, case_id)
            if runtime.enabled:
                try:
                    runtime.archive.archive_sources(
                        case_id,
                        pending["payloads"],
                        patient_metadata=metadata,
                        extracted=extracted,
                    )
                except Exception as exc:
                    runtime.fail_or_continue(exc)
                    response["archive"] = {"status": "UNAVAILABLE"}
        return finalize_if_ready(response)

    def complete_archived(core_arg, payload):
        response = original_complete(core_arg, payload)
        return finalize_if_ready(response)

    def export_payload_archived(payload):
        exported = original_export_payload(payload)
        token = str(payload.get("assessment_token") or "")
        case_id = runtime.case_for_token(token)
        revision_id = runtime.revision_for_token(token)
        if case_id:
            exported["_archive_case_id"] = case_id
        if revision_id:
            exported["_archive_revision_id"] = revision_id
        return exported

    def _clean_for_report(payload: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = deepcopy(payload)
        for key in list(cleaned):
            if str(key).startswith("_archive_"):
                cleaned.pop(key, None)
        return cleaned

    def build_pdf_archived(payload: Dict[str, Any]) -> bytes:
        case_id = payload.get("_archive_case_id")
        revision_id = payload.get("_archive_revision_id")
        locale = payload.get("locale", "en")
        if runtime.enabled and case_id and revision_id:
            try:
                ref = runtime.archive.find_report(
                    str(case_id),
                    str(revision_id),
                    str(locale),
                    "pdf",
                )
                if ref:
                    return runtime.archive.get_bytes(ref)
            except Exception as exc:
                runtime.fail_or_continue(exc)
        return original_build_pdf(_clean_for_report(payload))

    def build_docx_archived(payload: Dict[str, Any]) -> bytes:
        case_id = payload.get("_archive_case_id")
        revision_id = payload.get("_archive_revision_id")
        locale = payload.get("locale", "en")
        if runtime.enabled and case_id and revision_id:
            try:
                ref = runtime.archive.find_report(
                    str(case_id),
                    str(revision_id),
                    str(locale),
                    "docx",
                )
                if ref:
                    return runtime.archive.get_bytes(ref)
            except Exception as exc:
                runtime.fail_or_continue(exc)
        return original_build_docx(_clean_for_report(payload))

    operational_security.read_uploads = read_uploads_archived
    assessment_workflow.begin = begin_archived
    assessment_workflow.complete = complete_archived
    assessment_workflow.export_payload = export_payload_archived
    core.build_pdf = build_pdf_archived
    core.build_docx = build_docx_archived
    core._cerai_case_archive_runtime = runtime
    core._cerai_case_archive_installed = True
    return runtime
