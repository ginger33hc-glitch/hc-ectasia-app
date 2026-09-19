"""Verify the configured CER-AI archive with a non-PHI encrypted canary object.

Run only after Railway Storage Bucket credentials and CERAI_ARCHIVE_MASTER_KEY_B64 are configured.
The canary is intentionally retained as an immutable audit artifact; it contains no patient data.
"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from case_archive import EncryptedArchive, verify_storage_canary


def main() -> None:
    archive = EncryptedArchive.from_environment()
    result = verify_storage_canary(archive)

    print("CER-AI archive verification passed.")
    print(f"verified_at_utc={result['verified_at_utc']}")
    print(f"sha256={result['sha256']}")
    print(f"plaintext_bytes={result['plaintext_bytes']}")


if __name__ == "__main__":
    main()
