import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

import canonical_engine
import assessment_workflow
import operational_security as security


client = TestClient(canonical_engine.app)


def test_security_headers_and_production_docs_are_closed():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_configured_access_key_protects_clinical_endpoints(monkeypatch):
    monkeypatch.setattr(security, "ACCESS_KEY", "correct-horse-battery-staple")
    monkeypatch.setattr(security, "REQUIRE_ACCESS_KEY", True)
    denied = client.post("/assessment/complete", json={})
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "CER-AI-Key"
    assert denied.headers["x-frame-options"] == "DENY"
    assert denied.headers["cache-control"] == "no-store"

    admitted = client.post(
        "/assessment/complete",
        json={},
        headers={"X-CERAI-Access-Key": "correct-horse-battery-staple"},
    )
    assert admitted.status_code == 410


def test_non_image_upload_is_rejected_before_extraction():
    response = client.post(
        "/analyze",
        files={"images": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_json_endpoint_has_a_separate_small_body_limit(monkeypatch):
    monkeypatch.setattr(security, "MAX_JSON_REQUEST_BYTES", 10)
    response = client.post(
        "/assessment/complete",
        content=b"12345678901",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_upload_count_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(security, "MAX_UPLOAD_FILES", 1)
    response = client.post(
        "/analyze",
        files=[
            ("images", ("one.png", b"one", "image/png")),
            ("images", ("two.png", b"two", "image/png")),
        ],
    )
    assert response.status_code == 413


def test_per_file_and_total_upload_limits_are_incremental(monkeypatch):
    monkeypatch.setattr(security, "MAX_FILE_BYTES", 3)
    monkeypatch.setattr(security, "MAX_TOTAL_UPLOAD_BYTES", 5)
    too_large = UploadFile(filename="large.png", file=BytesIO(b"1234"), headers={"content-type": "image/png"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.read_uploads([too_large]))
    assert exc.value.status_code == 413

    first = UploadFile(filename="one.png", file=BytesIO(b"123"), headers={"content-type": "image/png"})
    second = UploadFile(filename="two.png", file=BytesIO(b"123"), headers={"content-type": "image/png"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.read_uploads([first, second]))
    assert exc.value.status_code == 413


def test_global_analysis_rate_limit(monkeypatch):
    security._reset_rate_limit_for_tests()
    monkeypatch.setattr(security, "ANALYSIS_RATE_LIMIT", 1)
    security.admit_analysis()
    with pytest.raises(HTTPException) as exc:
        security.admit_analysis()
    assert exc.value.status_code == 429
    security._reset_rate_limit_for_tests()


def test_full_session_store_preserves_existing_assessments(monkeypatch):
    existing = {"extracted": {}, "expires": float("inf"), "ready": None}
    with assessment_workflow._lock:
        assessment_workflow._sessions.clear()
        assessment_workflow._sessions["existing-token"] = existing
    monkeypatch.setattr(assessment_workflow, "MAX_SESSIONS", 1)
    with pytest.raises(HTTPException) as exc:
        assessment_workflow.begin(canonical_engine.core, {}, None, {}, {}, {})
    assert exc.value.status_code == 503
    assert assessment_workflow._sessions == {"existing-token": existing}
    with assessment_workflow._lock:
        assessment_workflow._sessions.clear()
