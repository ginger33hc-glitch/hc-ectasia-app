"""Verify the configured CER-AI archive with a non-PHI encrypted canary object.

Run only after Railway Storage Bucket credentials and CERAI_ARCHIVE_MASTER_KEY_B64 are configured.
The canary is intentionally retained as an immutable audit artifact; it contains no patient data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from case_archive import EncryptedArchive


def main() -> None:
    archive = EncryptedArchive.from_environment()
    case_id = archive.new_case_id()
    payload = json.dumps(
        {
            "type": "CER-AI archive verification canary",
            "contains_phi": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    ref = archive.put_bytes(
        case_id,
        "verification",
        "non-phi-canary",
        payload,
        media_type="application/json",
    )
    recovered = archive.get_bytes(ref)
    if recovered != payload:
        raise SystemExit("CER-AI archive verification failed: read-back mismatch.")
    listed = archive.store.list(f"cases/{case_id}/verification/")
    if ref.key not in listed:
        raise SystemExit("CER-AI archive verification failed: object not visible in prefix listing.")

    print("CER-AI archive verification passed.")
    print(f"case_id={case_id}")
    print(f"key={ref.key}")
    print(f"sha256={ref.sha256}")
    print(f"plaintext_bytes={ref.plaintext_bytes}")


if __name__ == "__main__":
    main()
