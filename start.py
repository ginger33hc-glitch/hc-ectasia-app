import os
import uvicorn

# Single supported production composition point.
import canonical_engine  # noqa: F401
from case_archive import verify_storage_canary


def verify_required_archive(core):
    """Fail deployment before serving traffic when mandatory archive I/O is unavailable."""
    runtime = getattr(core, "_cerai_case_archive_runtime", None)
    if runtime is None or not runtime.required:
        return None
    if not runtime.enabled:
        raise RuntimeError("Required CER-AI archive is not enabled.")
    result = verify_storage_canary(runtime.archive)
    print(
        "CER-AI required archive verification passed "
        f"verified_at_utc={result['verified_at_utc']} "
        f"sha256={result['sha256']} plaintext_bytes={result['plaintext_bytes']}"
    )
    return result

if __name__ == "__main__":
    verify_required_archive(canonical_engine.core)
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("canonical_engine:app", host="0.0.0.0", port=port, server_header=False)
