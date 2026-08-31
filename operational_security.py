"""Operational safeguards for the CER-AI web boundary.

This module intentionally contains no clinical rules.  It limits untrusted input,
upstream extraction load, and browser exposure around the canonical engine.
"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
import hashlib
import os
import secrets
from threading import RLock
from time import monotonic

from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse


MIB = 1024 * 1024
MAX_UPLOAD_FILES = max(1, min(int(os.getenv("CERAI_MAX_UPLOAD_FILES", "16")), 64))
MAX_FILE_BYTES = max(MIB, min(int(os.getenv("CERAI_MAX_FILE_BYTES", str(12 * MIB))), 40 * MIB))
MAX_TOTAL_UPLOAD_BYTES = max(
    MAX_FILE_BYTES,
    min(int(os.getenv("CERAI_MAX_TOTAL_UPLOAD_BYTES", str(80 * MIB))), 256 * MIB),
)
MAX_REQUEST_BYTES = MAX_TOTAL_UPLOAD_BYTES + (2 * MIB)
MAX_JSON_REQUEST_BYTES = max(
    64 * 1024,
    min(int(os.getenv("CERAI_MAX_JSON_REQUEST_BYTES", str(2 * MIB))), 10 * MIB),
)
ANALYSIS_RATE_LIMIT = max(1, min(int(os.getenv("CERAI_ANALYSIS_RATE_LIMIT", "24")), 500))
ANALYSIS_RATE_WINDOW_SECONDS = max(
    60,
    min(int(os.getenv("CERAI_ANALYSIS_RATE_WINDOW_SECONDS", "900")), 86400),
)
GLOBAL_ANALYSIS_CONCURRENCY = max(
    1,
    min(int(os.getenv("CERAI_GLOBAL_ANALYSIS_CONCURRENCY", "2")), 8),
)
ANALYSIS_QUEUE_TIMEOUT_SECONDS = max(
    0.1,
    min(float(os.getenv("CERAI_ANALYSIS_QUEUE_TIMEOUT_SECONDS", "5")), 60.0),
)

ACCESS_KEY = os.getenv("CERAI_ACCESS_KEY", "").strip()
# Railway does not expose a usable password-entry workflow for this project.  The
# fallback stores only a salted PBKDF2 verifier; the access key itself is never
# committed.  A deployment secret still takes precedence when one is available.
EMBEDDED_ACCESS_KEY_HASH = (
    "pbkdf2_sha256$600000$45af5e97bcbf0cb878b3ac0ceccc7258$"
    "16dad2560cb1deef49e5c916e6da9953bdf382ac14fe2d991912eedf09748d57"
)
ACCESS_KEY_HASH = os.getenv("CERAI_ACCESS_KEY_HASH", EMBEDDED_ACCESS_KEY_HASH).strip()
REQUIRE_ACCESS_KEY = os.getenv(
    "CERAI_REQUIRE_ACCESS_KEY", "1" if (ACCESS_KEY or ACCESS_KEY_HASH) else "0"
).strip() == "1"
EXPOSE_API_DOCS = os.getenv("CERAI_EXPOSE_API_DOCS", "0").strip() == "1"
PROTECTED_PATHS = frozenset({
    "/analyze",
    "/assessment/complete",
    "/report/pdf",
    "/report/word",
})

_rate_lock = RLock()
_analysis_starts: deque[float] = deque()
_analysis_slots = asyncio.Semaphore(GLOBAL_ANALYSIS_CONCURRENCY)


def _prune_rate_window(now: float) -> None:
    cutoff = now - ANALYSIS_RATE_WINDOW_SECONDS
    while _analysis_starts and _analysis_starts[0] <= cutoff:
        _analysis_starts.popleft()


def admit_analysis() -> None:
    """Apply a process-wide cost guard before any upstream model request."""
    now = monotonic()
    with _rate_lock:
        _prune_rate_window(now)
        if len(_analysis_starts) >= ANALYSIS_RATE_LIMIT:
            raise HTTPException(
                429,
                "Analysis capacity limit reached. Wait before retrying; repeated retries increase the delay.",
                headers={"Retry-After": str(ANALYSIS_RATE_WINDOW_SECONDS)},
            )
        _analysis_starts.append(now)


@asynccontextmanager
async def analysis_slot():
    """Bound simultaneous whole-case extraction work across all requests."""
    try:
        await asyncio.wait_for(
            _analysis_slots.acquire(), timeout=ANALYSIS_QUEUE_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        raise HTTPException(
            429,
            "The analysis service is busy. Wait briefly before retrying.",
            headers={"Retry-After": "10"},
        ) from exc
    try:
        yield
    finally:
        _analysis_slots.release()


def _is_image(upload: UploadFile) -> bool:
    content_type = str(upload.content_type or "").lower()
    return content_type.startswith("image/")


async def read_uploads(images: list[UploadFile]) -> list[tuple[bytes, str]]:
    """Read image uploads incrementally with per-file and aggregate hard limits."""
    if not images:
        raise HTTPException(400, "No images supplied.")
    if len(images) > MAX_UPLOAD_FILES:
        raise HTTPException(
            413,
            f"Too many images. A maximum of {MAX_UPLOAD_FILES} images is accepted per assessment.",
        )

    payloads: list[tuple[bytes, str]] = []
    total = 0
    for upload in images:
        filename = upload.filename or "image.jpg"
        if not _is_image(upload):
            raise HTTPException(415, f"{filename}: only image uploads are accepted.")
        data = bytearray()
        while chunk := await upload.read(MIB):
            data.extend(chunk)
            total += len(chunk)
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(
                    413,
                    f"{filename}: image exceeds the {MAX_FILE_BYTES // MIB} MB per-file limit.",
                )
            if total > MAX_TOTAL_UPLOAD_BYTES:
                raise HTTPException(
                    413,
                    f"Total image upload exceeds the {MAX_TOTAL_UPLOAD_BYTES // MIB} MB limit.",
                )
        if data:
            payloads.append((bytes(data), filename))
    if not payloads:
        raise HTTPException(400, "No readable images supplied.")
    return payloads


def _verify_access_key_hash(supplied: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, expected_hex = encoded.split("$", 3)
        iterations = int(iterations_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
        if len(salt) < 16 or len(expected) != 32:
            return False
    except (TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", supplied.encode("utf-8"), salt, iterations, dklen=len(expected)
    )
    return secrets.compare_digest(actual, expected)


def _access_key_hash_well_formed(encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, expected_hex = encoded.split("$", 3)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (TypeError, ValueError):
        return False
    return (
        algorithm == "pbkdf2_sha256"
        and 100_000 <= iterations <= 2_000_000
        and len(salt) >= 16
        and len(expected) == 32
    )


def _access_key_valid(request: Request) -> bool:
    supplied = request.headers.get("X-CERAI-Access-Key", "")
    if not supplied:
        return False
    if ACCESS_KEY:
        return secrets.compare_digest(supplied, ACCESS_KEY)
    return bool(ACCESS_KEY_HASH) and _verify_access_key_hash(supplied, ACCESS_KEY_HASH)


def _request_limit(path: str) -> int:
    return MAX_REQUEST_BYTES if path == "/analyze" else MAX_JSON_REQUEST_BYTES


def _secure_response(response, path: str):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'; img-src 'self' data: blob:; connect-src 'self'; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path in PROTECTED_PATHS:
        response.headers["Cache-Control"] = "no-store"
    return response


def _remove_public_documentation_routes(app) -> None:
    if EXPOSE_API_DOCS:
        return
    hidden = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
    app.router.routes[:] = [
        route for route in app.router.routes if getattr(route, "path", None) not in hidden
    ]


def install(core) -> None:
    """Install once around the fully assembled FastAPI application."""
    if getattr(core, "_cerai_operational_security_installed", False):
        return
    if REQUIRE_ACCESS_KEY and not (ACCESS_KEY or ACCESS_KEY_HASH):
        raise RuntimeError(
            "CERAI_REQUIRE_ACCESS_KEY=1 but no access-key verifier is configured."
        )
    if ACCESS_KEY and len(ACCESS_KEY) < 20:
        raise RuntimeError("CERAI_ACCESS_KEY must contain at least 20 characters.")
    if ACCESS_KEY_HASH and not _access_key_hash_well_formed(ACCESS_KEY_HASH):
        raise RuntimeError("CERAI_ACCESS_KEY_HASH has an invalid or unsupported format.")

    _remove_public_documentation_routes(core.app)

    @core.app.middleware("http")
    async def cerai_web_boundary(request: Request, call_next):
        path = request.url.path
        if path in PROTECTED_PATHS:
            request_limit = _request_limit(path)
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > request_limit:
                        return _secure_response(JSONResponse(
                            status_code=413,
                            content={"detail": "Request body exceeds the configured CER-AI limit."},
                        ), path)
                except ValueError:
                    return _secure_response(JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header."},
                    ), path)
            if REQUIRE_ACCESS_KEY and not _access_key_valid(request):
                return _secure_response(JSONResponse(
                    status_code=401,
                    content={"detail": "CER-AI access key required."},
                    headers={"WWW-Authenticate": "CER-AI-Key"},
                ), path)

        response = await call_next(request)
        return _secure_response(response, path)

    core._cerai_operational_security_installed = True


def _reset_rate_limit_for_tests() -> None:
    with _rate_lock:
        _analysis_starts.clear()
