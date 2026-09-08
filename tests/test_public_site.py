import json
import os
import re

os.environ.setdefault("OPENAI_API_KEY", "test-key-for-import-only")

from fastapi.testclient import TestClient

import canonical_engine


def test_public_homepage_is_the_root_and_home_alias():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "CER-AI — Cornea Ectasia Risk Assessment Intelligence" in response.text
        assert "HC Ectasia App" not in response.text
        assert "Risk Analysis Intelligence" not in response.text
        assert "Hüseyin Cengiz, M.D." in response.text
        assert 'href="/corneal-ectasia-risk-assessment"' in response.text
        duplicate = client.get("/home", follow_redirects=False)
        assert duplicate.status_code == 308
        assert duplicate.headers["location"] == "/"


def test_public_homepage_uses_bad_d_for_both_pathway_labels():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.text.count('class="pill">BAD-D</span>') == 1
        assert response.text.count('class="risk-label">BAD-D</span>') == 1
        assert 'class="pill">Final BAD-D</span>' not in response.text
        assert 'class="risk-label">Final BAD-D</span>' not in response.text


def test_public_homepage_identifies_software_and_clinical_author():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/")
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            response.text,
            flags=re.DOTALL,
        )
        assert match is not None
        graph = json.loads(match.group(1))["@graph"]
        by_type = {item["@type"]: item for item in graph}
        assert by_type["SoftwareApplication"]["softwareVersion"] == "0.7.71"
        assert by_type["Person"]["name"] == "Hüseyin Cengiz, M.D."
        assert by_type["MedicalWebPage"]["dateModified"] == "2026-09-08"


def test_clinical_app_has_stable_app_entry():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/app")
        assert response.status_code == 200
        assert "CER-AI — Cornea Ectasia Risk Assessment Intelligence v0.7.71" in response.text
        assert "public-home" not in response.text


def test_robots_allows_public_discovery_but_blocks_clinical_surfaces():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
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
        assert "Sitemap: https://cer-ai.com/sitemap.xml" in text


def test_sitemap_contains_only_public_discovery_pages():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        text = response.text
        for path in ("/corneal-ectasia-risk-assessment", "/clinical-evidence", "/references"):
            assert f"<loc>https://cer-ai.com{path}</loc>" in text
        assert "<loc>https://cer-ai.com/</loc>" in text
        assert "https://cer-ai.com/home" not in text
        assert "http://cer-ai.com" not in text
        assert "<lastmod>2026-09-08</lastmod>" in text
        for private_path in ("/app", "/analyze", "/assessment/", "/archive"):
            assert f"<loc>https://cer-ai.com{private_path}" not in text


def test_all_public_pages_have_absolute_https_canonicals():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        expected = {
            "/": "https://cer-ai.com/",
            "/corneal-ectasia-risk-assessment": (
                "https://cer-ai.com/corneal-ectasia-risk-assessment"
            ),
            "/clinical-evidence": "https://cer-ai.com/clinical-evidence",
            "/references": "https://cer-ai.com/references",
        }
        for path, canonical in expected.items():
            response = client.get(path)
            assert response.status_code == 200
            assert response.text.count(
                f'<link rel="canonical" href="{canonical}">'
            ) == 1
            assert response.headers["x-robots-tag"].startswith("index,follow")


def test_public_landing_page_answers_surgeon_discovery_questions():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/corneal-ectasia-risk-assessment")
        assert response.status_code == 200
        for phrase in (
            "Corneal ectasia risk assessment software for refractive surgeons",
            "Frequently asked questions about CER-AI",
            "Which Pentacam images does a CER-AI assessment require?",
            "Who is CER-AI designed for?",
            "Has the complete CER-AI software been externally validated?",
            "Clinical author and reviewer:",
            "Hüseyin Cengiz, M.D.",
        ):
            assert phrase in response.text
        assert "do not constitute external validation" in response.text


def test_nonproduction_hosts_are_not_indexable():
    with TestClient(
        canonical_engine.app,
        base_url="https://cer-ai-staging-staging.up.railway.app",
    ) as client:
        homepage = client.get("/")
        assert '<meta name="robots" content="noindex,nofollow">' in homepage.text
        assert homepage.headers["x-robots-tag"] == "noindex,nofollow"
        robots = client.get("/robots.txt")
        assert robots.text == "User-agent: *\nDisallow: /\n"
        sitemap = client.get("/sitemap.xml")
        assert "<urlset" in sitemap.text
        assert "<url>" not in sitemap.text
