import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-for-import-only")

from fastapi.testclient import TestClient

import canonical_engine


def test_public_homepage_is_the_root_and_home_alias():
    with TestClient(canonical_engine.app) as client:
        for path in ("/", "/home"):
            response = client.get(path)
            assert response.status_code == 200
            assert "Cornea Ectasia Risk Assessment Intelligence" in response.text
            assert "HC Ectasia App" in response.text
            assert "Hüseyin Cengiz, M.D." in response.text


def test_clinical_app_has_stable_app_entry():
    with TestClient(canonical_engine.app) as client:
        response = client.get("/app")
        assert response.status_code == 200
        assert "CER-AI — Cornea Ectasia Risk Assessment Intelligence v0.7.71" in response.text
        assert "public-home" not in response.text
