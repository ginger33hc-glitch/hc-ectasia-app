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
        assert "CER-AI — Corneal Ectasia Risk Assessment Intelligence" in response.text
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


def test_public_homepage_mobile_navigation_exposes_learning_resources():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/")
        assert response.status_code == 200
        assert '/static/public-tr-home-overrides.js?v=2' in response.text
    helper = open("static/public-tr-home-overrides.js", encoding="utf-8").read()
    expected = (
        '["Learning Center", "/learning-center"]',
        '["Ectasia Assessment", "/corneal-ectasia-risk-assessment"]',
        '["Clinical Evidence", "/clinical-evidence"]',
    )
    for link in expected:
        assert link in helper
    assert 'href.startsWith("#") && !document.querySelector(href)' in helper


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
        assert by_type["MedicalWebPage"]["dateModified"] == "2026-09-09"


def test_clinical_app_has_stable_app_entry():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/app")
        assert response.status_code == 200
        assert "CER-AI — Corneal Ectasia Risk Assessment Intelligence v0.7.71" in response.text
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
        for path in (
            "/learning-center", "/learning/corneal-ectasia-basics",
            "/learning/pentacam-education", "/learning/bad-d-component-indices",
            "/learning/topometric-indices", "/learning/randleman-erss",
            "/learning/nice-risk-assessment", "/learning/ps3-risk-assessment",
            "/learning/topography-tomography-patterns",
            "/learning/surgical-safety-concepts", "/learning/clinical-cases",
            "/learning/cer-ai-methodology", "/learning/surgeon-learning-modules",
            "/learning/faq", "/corneal-ectasia-risk-assessment",
            "/clinical-evidence", "/references",
            "/tr/learning-center", "/tr/learning/randleman-erss",
            "/tr/learning/ps3-risk-assessment", "/tr/learning/faq",
            "/learning/cases/two-caution-pathways",
            "/tr/learning/cases/two-caution-pathways",
        ):
            assert f"<loc>https://cer-ai.com{path}</loc>" in text
        assert "<loc>https://cer-ai.com/</loc>" in text
        assert "https://cer-ai.com/home" not in text
        assert "http://cer-ai.com" not in text
        assert "<lastmod>2026-09-09</lastmod>" in text
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


def test_learning_center_exposes_the_full_public_education_architecture():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/learning-center")
        assert response.status_code == 200
        assert response.headers["x-robots-tag"].startswith("index,follow")
        assert '<link rel="canonical" href="https://cer-ai.com/learning-center">' in response.text
        assert '<link rel="stylesheet" href="/static/technical-public.css?v=3">' in response.text
        assert "Education explains the science; the CER-AI application performs the structured assessment." in response.text
        for phrase in (
            "Corneal ectasia: clinical foundations",
            "Pentacam education for ectasia screening",
            "BAD-D and component indices",
            "Pentacam topometric indices",
            "Randleman Ectasia Risk Score System (ERSS)",
            "NICE ectasia-risk assessment",
            "PS3 practical subjective scoring",
            "Corneal topography and tomography patterns",
            "Surgical tissue-safety concepts",
            "Clinical reasoning cases",
            "CER-AI methodology and evidence boundaries",
            "Surgeon learning pathway",
            "FAQ and educational assistant boundary",
        ):
            assert phrase in response.text
        schema = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            response.text,
            flags=re.DOTALL,
        )
        assert schema is not None
        assert json.loads(schema.group(1))["@type"] == "CollectionPage"


def test_learning_topics_are_crawlable_evidence_linked_and_nonclinical():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        paths = (
            "corneal-ectasia-basics", "pentacam-education",
            "bad-d-component-indices", "topometric-indices", "randleman-erss",
            "nice-risk-assessment", "ps3-risk-assessment",
            "topography-tomography-patterns",
            "surgical-safety-concepts", "clinical-cases", "cer-ai-methodology",
            "surgeon-learning-modules",
        )
        for slug in paths:
            response = client.get(f"/learning/{slug}")
            assert response.status_code == 200
            assert response.text.count(
                f'<link rel="canonical" href="https://cer-ai.com/learning/{slug}">'
            ) == 1
            assert "This module explains concepts. It does not perform or change a CER-AI clinical assessment." in response.text
            assert "Selected sources" in response.text
            schema = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                response.text,
                flags=re.DOTALL,
            )
            assert schema is not None
            assert json.loads(schema.group(1))["@type"] == "MedicalWebPage"


def test_learning_center_has_first_class_turkish_routes_and_hreflang():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        hub = client.get("/tr/learning-center")
        assert hub.status_code == 200
        assert '<html lang="tr">' in hub.text
        assert "CER-AI Öğrenme Merkezi" in hub.text
        assert "Klinik soruya göre öğrenin" in hub.text
        assert '<link rel="canonical" href="https://cer-ai.com/tr/learning-center">' in hub.text
        assert '<link rel="alternate" hreflang="en" href="https://cer-ai.com/learning-center">' in hub.text
        assert '<link rel="alternate" hreflang="tr" href="https://cer-ai.com/tr/learning-center">' in hub.text
        assert 'href="/learning-center">English</a>' in hub.text

        for slug in (
            "corneal-ectasia-basics", "pentacam-education",
            "bad-d-component-indices", "topometric-indices", "randleman-erss",
            "nice-risk-assessment", "ps3-risk-assessment",
            "topography-tomography-patterns", "surgical-safety-concepts",
            "clinical-cases", "cer-ai-methodology", "surgeon-learning-modules",
        ):
            response = client.get(f"/tr/learning/{slug}")
            assert response.status_code == 200
            assert '<html lang="tr">' in response.text
            assert f'href="/learning/{slug}">English</a>' in response.text
            assert "Bu modül" in response.text


def test_learning_center_documents_current_scoring_and_report_pipeline():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        expectations = {
            "/learning/randleman-erss": (
                "CER-AI ERSS component scoring", "0–2", "STOP-DEFER",
                "Manifest MRSE", "LASIK RSB or PRK RST",
            ),
            "/learning/bad-d-component-indices": (
                "Final BAD-D disposition", "&lt;=1.60", "&gt;=2.60",
                "CER-AI never reconstructs it from Df, Db, Dp, Dt, or Da",
            ),
            "/learning/nice-risk-assessment": (
                "CER-AI-adapted NICE component scoring", "B.Ele.Th", "5–8",
                "NICE remains independent",
            ),
            "/learning/ps3-risk-assessment": (
                "Automated PS3 factors in CER-AI", "Anterior Km", "PPI Average",
                "Inter-eye asymmetry", "PS3 procedure disposition",
            ),
            "/learning/cer-ai-methodology": (
                "How independent pathways become the final result",
                "Four systems complete; 2 CAUTION", "PASS WITH CAUTION",
                "PDF and Word reports consume the same already-computed canonical report payload",
            ),
        }
        for path, phrases in expectations.items():
            response = client.get(path)
            assert response.status_code == 200
            for phrase in phrases:
                assert phrase in response.text


def test_worked_cases_are_bilingual_indexable_and_clearly_synthetic():
    slugs = (
        "concordant-low-risk-lasik", "two-caution-pathways",
        "srax-ps3-stop", "incomplete-source",
    )
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        for slug in slugs:
            english = client.get(f"/learning/cases/{slug}")
            turkish = client.get(f"/tr/learning/cases/{slug}")
            assert english.status_code == turkish.status_code == 200
            assert "Not real patient data" in english.text
            assert "Synthetic teaching case" in english.text
            assert "Gerçek hasta verisi değildir" in turkish.text
            assert "Sentetik eğitim olgusu" in turkish.text
            assert "Pathway evaluation" in english.text
            assert "Yol değerlendirmesi" in turkish.text
            assert "Hüseyin Cengiz, M.D." in english.text
            assert "Tüm hakları saklıdır" in turkish.text


def test_every_learning_page_has_explicit_owner_and_rights_notice():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        for path in (
            "/learning-center", "/learning/randleman-erss", "/learning/faq",
            "/tr/learning-center", "/tr/learning/randleman-erss", "/tr/learning/faq",
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert '<meta name="author" content="Hüseyin Cengiz, M.D.">' in response.text
            assert "All rights reserved" in response.text or "Tüm hakları saklıdır" in response.text


def test_learning_faq_has_faq_schema_and_explicit_assistant_boundary():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/learning/faq")
        assert response.status_code == 200
        assert "No patient data" in response.text
        assert "No clinical scoring" in response.text
        assert "No modification of the CER-AI engine" in response.text
        schema = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            response.text,
            flags=re.DOTALL,
        )
        assert schema is not None
        payload = json.loads(schema.group(1))
        assert payload["@type"] == "FAQPage"
        assert len(payload["mainEntity"]) == 6


def test_learning_pages_remain_noindex_outside_canonical_production_host():
    with TestClient(
        canonical_engine.app,
        base_url="https://cer-ai-staging-staging.up.railway.app",
    ) as client:
        for path in ("/learning-center", "/learning/pentacam-education", "/learning/faq"):
            response = client.get(path)
            assert response.status_code == 200
            assert '<meta name="robots" content="noindex,nofollow">' in response.text
            assert response.headers["x-robots-tag"] == "noindex,nofollow"
            assert 'href="/static/technical-public.css?v=3"' in response.text
            assert 'href="https://cer-ai.com/static/technical-public.css?v=3"' not in response.text


def test_unknown_learning_topic_is_not_found():
    with TestClient(canonical_engine.app, base_url="https://cer-ai.com") as client:
        response = client.get("/learning/not-a-real-module")
        assert response.status_code == 404
