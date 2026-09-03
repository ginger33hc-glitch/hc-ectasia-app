import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-for-import-only")

from fastapi.testclient import TestClient

import canonical_engine


def test_public_homepage_is_the_root_and_home_alias():
    with TestClient(canonical_engine.app) as client:
        for path in ("/", "/home"):
            response = client.get(path)
            assert response.status_code == 200
            assert "Corneal Ectasia Risk Assessment Intelligence" in response.text
            assert "HC Ectasia App" in response.text
            assert "Hüseyin Cengiz, M.D." in response.text


def test_clinical_app_has_stable_app_entry():
    with TestClient(canonical_engine.app) as client:
        response = client.get("/app")
        assert response.status_code == 200
        assert "CER-AI — Cornea Ectasia Risk Assessment Intelligence v0.7.71" in response.text
        assert "public-home" not in response.text


def test_robots_allows_public_discovery_but_blocks_clinical_surfaces():
    with TestClient(canonical_engine.app) as client:
        response = client.get("/robots.txt")
        assert response.status_code == 200
        text = response.text
        for agent in (
            "GPTBot", "OAI-SearchBot", "PerplexityBot", "ClaudeBot",
            "Applebot-Extended", "Google-Extended", "Googlebot", "Bingbot", "DuckDuckBot",
        ):
            assert f"User-agent: {agent}" in text
        for path in (
            "/app", "/api/", "/analyze", "/assessment/", "/report/",
            "/archive", "/admin", "/auth", "/portal", "/dashboard", "/login", "/account",
        ):
            assert f"Disallow: {path}" in text
        assert "Allow: /" in text
        assert "Sitemap:" in text
        assert "/sitemap.xml" in text


def test_sitemap_contains_only_public_discovery_pages():
    with TestClient(canonical_engine.app) as client:
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        text = response.text
        for path in ("/corneal-ectasia-risk-assessment", "/clinical-evidence", "/references"):
            assert path in text
        for private_path in ("/app", "/analyze", "/assessment/", "/archive"):
            assert f"<loc>http://testserver{private_path}" not in text
