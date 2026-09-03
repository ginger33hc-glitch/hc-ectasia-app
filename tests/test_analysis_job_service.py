import os
import time

os.environ.setdefault("OPENAI_API_KEY", "test-key-for-import-only")

from fastapi.testclient import TestClient

import canonical_engine


def test_app_loads_analysis_job_transport_client():
    with TestClient(canonical_engine.app) as client:
        response = client.get("/app")
        assert response.status_code == 200
        assert "/static/analysis-jobs-client.js?v=1" in response.text


def test_upload_returns_job_then_background_calls_canonical_analyze(monkeypatch):
    expected = {"workflow_status": "READY", "sentinel": "canonical-result"}
    calls = []

    async def fake_analyze(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(canonical_engine.core, "analyze", fake_analyze)

    with TestClient(canonical_engine.app) as client:
        response = client.post(
            "/analysis/jobs",
            files=[("images", ("od-four-maps.jpg", b"fake-image", "image/jpeg"))],
            data={
                "age": "30",
                "eye_plans": "{}",
                "patient_modifiers": "{}",
                "patient_metadata": "{}",
                "assessment_request_id": "browser-request-id",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "UPLOADED"
        assert payload["job_id"]

        deadline = time.time() + 2
        while True:
            status = client.get(f"/analysis/jobs/{payload['job_id']}")
            if status.status_code != 202:
                break
            assert time.time() < deadline
            time.sleep(.01)

        assert status.status_code == 200
        assert status.json()["status"] == "COMPLETED"
        assert status.json()["result"] == expected
        assert len(calls) == 1
        assert calls[0]["age"] == 30
        assert calls[0]["assessment_request_id"] == payload["job_id"]
        assert calls[0]["images"][0].filename == "od-four-maps.jpg"
