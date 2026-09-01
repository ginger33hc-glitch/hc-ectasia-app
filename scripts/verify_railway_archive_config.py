"""Validate CER-AI Railway archive configuration without printing secrets.

This is a configuration-only preflight. It does not contact the bucket and does not upload data.
Run scripts/verify_case_archive.py separately for the non-PHI encrypted canary after this passes.
"""

from __future__ import annotations

import base64
import json
import os
from urllib.parse import urlparse


REQUIRED_BUCKET_VARS = ("BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "ENDPOINT")
ALLOWED_URL_STYLES = {"virtual", "path"}
RAILWAY_STORAGE_HOSTS = {"storage.railway.app"}
RAILWAY_STORAGE_HOST_SUFFIXES = (".storageapi.dev",)


class PreflightError(RuntimeError):
    pass


def _value(env: dict[str, str], name: str) -> str:
    return str(env.get(name) or "").strip()


def _decode_32_byte_secret(value: str, name: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise PreflightError(f"{name} must be valid base64.") from exc
    if len(decoded) != 32:
        raise PreflightError(f"{name} must decode to exactly 32 bytes.")
    return decoded


def validate_environment(env: dict[str, str] | None = None) -> dict[str, object]:
    env = dict(os.environ if env is None else env)
    missing = [name for name in REQUIRED_BUCKET_VARS if not _value(env, name)]
    if missing:
        raise PreflightError("Missing Railway bucket variable(s): " + ", ".join(missing))

    bucket = _value(env, "BUCKET")
    display_name = _value(env, "RAILWAY_BUCKET_NAME")
    if display_name and bucket == display_name:
        raise PreflightError(
            "BUCKET must be the globally unique S3 bucket name, not RAILWAY_BUCKET_NAME."
        )

    endpoint = _value(env, "ENDPOINT")
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise PreflightError("ENDPOINT must be a valid https URL.")
    hostname = (parsed.hostname or "").lower()
    if hostname not in RAILWAY_STORAGE_HOSTS and not any(
        hostname.endswith(suffix) for suffix in RAILWAY_STORAGE_HOST_SUFFIXES
    ):
        raise PreflightError(
            "ENDPOINT must use the HTTPS Railway Storage hostname shown in the "
            "Bucket Credentials tab."
        )

    style = (_value(env, "AWS_S3_URL_STYLE") or "virtual").lower()
    if style not in ALLOWED_URL_STYLES:
        raise PreflightError("AWS_S3_URL_STYLE must be virtual or path.")

    region = _value(env, "REGION") or "auto"
    archive_key = _decode_32_byte_secret(
        _value(env, "CERAI_ARCHIVE_MASTER_KEY_B64"),
        "CERAI_ARCHIVE_MASTER_KEY_B64",
    )

    research_enabled = _value(env, "CERAI_RESEARCH_EXPORT_ENABLED") == "1"
    research_key_value = _value(env, "CERAI_RESEARCH_PSEUDONYM_KEY_B64")
    if research_enabled and not research_key_value:
        raise PreflightError(
            "CERAI_RESEARCH_EXPORT_ENABLED=1 requires CERAI_RESEARCH_PSEUDONYM_KEY_B64."
        )
    if research_key_value:
        research_key = _decode_32_byte_secret(
            research_key_value,
            "CERAI_RESEARCH_PSEUDONYM_KEY_B64",
        )
        if research_key == archive_key:
            raise PreflightError(
                "Research pseudonym key must be different from the archive encryption key."
            )

    named_users_enabled = _value(env, "CERAI_NAMED_USERS_ENABLED") == "1"
    if named_users_enabled:
        users_raw = _value(env, "CERAI_USERS_JSON")
        if not users_raw:
            raise PreflightError("CERAI_NAMED_USERS_ENABLED=1 requires CERAI_USERS_JSON.")
        try:
            users = json.loads(users_raw)
        except json.JSONDecodeError as exc:
            raise PreflightError("CERAI_USERS_JSON must be valid JSON.") from exc
        if not isinstance(users, list) or not users:
            raise PreflightError("CERAI_USERS_JSON must contain at least one account.")
        if not any(
            isinstance(item, dict)
            and item.get("enabled", True) is not False
            and str(item.get("role") or "").upper() == "OWNER"
            for item in users
        ):
            raise PreflightError("CERAI_USERS_JSON must contain at least one enabled OWNER.")
        if any("password" in item for item in users if isinstance(item, dict)):
            raise PreflightError("Raw password fields are not allowed in CERAI_USERS_JSON.")

    archive_enabled = _value(env, "CERAI_ARCHIVE_ENABLED") == "1"
    archive_required = _value(env, "CERAI_ARCHIVE_REQUIRED") == "1"
    return {
        "bucket_configured": True,
        "endpoint": endpoint,
        "region": region,
        "url_style": style,
        "archive_enabled": archive_enabled or archive_required,
        "archive_required": archive_required,
        "named_users_enabled": named_users_enabled,
        "research_export_enabled": research_enabled,
    }


def main() -> None:
    result = validate_environment()
    print("CER-AI Railway archive configuration preflight passed.")
    print(json.dumps(result, sort_keys=True))
    print("Next: run python scripts/verify_case_archive.py for the non-PHI encrypted canary.")


if __name__ == "__main__":
    main()
