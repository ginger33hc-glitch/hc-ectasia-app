"""Dry-run or apply a ciphertext-preserving CER-AI archive migration between S3 providers."""

from archive_migration import migrate_from_environment


if __name__ == "__main__":
    result = migrate_from_environment()
    print("CER-AI encrypted archive migration verification completed.")
    print(f"discovered={result.discovered}")
    print(f"copied={result.copied}")
    print(f"already_verified={result.already_verified}")
    print(f"dry_run_pending={result.dry_run_pending}")
    print(f"ciphertext_bytes={result.ciphertext_bytes}")
