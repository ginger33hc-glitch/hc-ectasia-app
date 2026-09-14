"""Idempotently ensure CERAI_USERS_JSON contains a staging user account for "idil".

STAGING-ONLY. Do not run this against production CER-AI environments. It is intended to
unblock testing of the named-user authentication system (see user_access.py) without manual
secret management, and without duplicating the account if a prior invocation timed out.

The scrypt parameters used here (n=16384, r=8, p=1, salt=16 random bytes, dklen=32) and the
resulting `scrypt$N$r$p$salt_hex$digest_hex` encoding intentionally match hash_password() in
user_access.py exactly, so the generated hash can be verified by verify_password() unchanged.

Usage:
    python scripts/ensure_staging_idil_user.py

Reads CERAI_USERS_JSON from the environment (or an empty-list default if unset), and prints a
JSON status report to stdout. If the "idil" account does not already exist, the report includes
the full, updated CERAI_USERS_JSON value to apply. No secrets other than the newly generated
hash (which is a one-way password verifier, not the plaintext) are printed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from user_access import ROLE_OWNER, normalize_username  # noqa: E402

TARGET_USERNAME = "idil"
TARGET_USER_ID = "idil-doctor"
TARGET_DISPLAY_NAME = "Idil"
TARGET_ROLE = "DOCTOR"
TARGET_PASSWORD = "idil"

# Must match hash_password() in user_access.py exactly.
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_SALT_BYTES = 16
SCRYPT_DKLEN = 32


class EnsureUserError(RuntimeError):
    """The staging users registry could not be safely updated."""


def _hash_target_password(password: str) -> str:
    """Generate a scrypt verifier using the same parameters/encoding as hash_password().

    Reimplemented here (rather than importing hash_password directly) only because
    hash_password() enforces a >=12 character minimum intended for real account passwords;
    the requested staging password "idil" is intentionally short for test purposes. The
    scrypt parameters, salt length, and encoding format below are otherwise identical.
    """
    salt = os.urandom(SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def _load_users(raw: str) -> list:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EnsureUserError("CERAI_USERS_JSON must be valid JSON.") from exc
    if not isinstance(payload, list):
        raise EnsureUserError("CERAI_USERS_JSON must be a JSON array of user objects.")
    return payload


def _find_existing(users: list, normalized_username: str) -> dict | None:
    for item in users:
        if not isinstance(item, dict):
            continue
        if normalize_username(item.get("username")) == normalized_username:
            return item
    return None


def _has_enabled_owner(users: list) -> bool:
    return any(
        isinstance(item, dict)
        and item.get("enabled", True) is not False
        and str(item.get("role") or "").strip().upper() == ROLE_OWNER
        for item in users
    )


def ensure_idil_user(raw_users_json: str) -> dict:
    users = _load_users(raw_users_json)
    before_count = len(users)
    normalized_target = normalize_username(TARGET_USERNAME)

    existing = _find_existing(users, normalized_target)
    if existing is not None:
        return {
            "status": "already_present",
            "username": TARGET_USERNAME,
            "user_count_before": before_count,
            "user_count_after": before_count,
        }

    if not _has_enabled_owner(users):
        raise EnsureUserError(
            "Refusing to add 'idil': the existing CERAI_USERS_JSON has no enabled OWNER "
            "account, so the registry is already invalid and must be fixed first."
        )

    new_user = {
        "user_id": TARGET_USER_ID,
        "username": TARGET_USERNAME,
        "display_name": TARGET_DISPLAY_NAME,
        "role": TARGET_ROLE,
        "password_hash": _hash_target_password(TARGET_PASSWORD),
        "enabled": True,
    }
    updated_users = [*users, new_user]

    if not _has_enabled_owner(updated_users):
        raise EnsureUserError(
            "Post-update validation failed: no enabled OWNER account would exist."
        )

    updated_json = json.dumps(updated_users)

    return {
        "status": "changed",
        "username": TARGET_USERNAME,
        "user_count_before": before_count,
        "user_count_after": len(updated_users),
        "cerai_users_json": updated_json,
    }


def main() -> None:
    raw = os.environ.get("CERAI_USERS_JSON", "")
    try:
        report = ensure_idil_user(raw)
    except EnsureUserError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, sort_keys=True))
        raise SystemExit(1)

    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
