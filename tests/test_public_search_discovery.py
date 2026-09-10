"""Public presentation contracts; no clinical scoring or patient data."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import public_site


class PageStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attributes(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


@pytest.fixture
def public_app():
    # Install the actual public route owner, not a copied route or scorer.
    core = SimpleNamespace(app=FastAPI())
    public_site.install(core)
    return core.app


def test_product_page_explains_category_ai_boundaries_and_examples(public_app):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get("/corneal-ectasia-risk-assessment")
    assert response.status_code == 200
    html = response.text
    for phrase in (
        "corneal ectasia screening and risk assessment software",
        "How does CER-AI use artificial intelligence?",
        "Extracted measurements can be incorrect, incomplete or conflicting",
        "canonical rule-based assessment engine",
        "does not acquire the corneal scan",
        "not a claim that CER-AI is an externally validated autonomous",
        "From Pentacam images to an assessment report",
        "synthetic educational cases, not live analyses or actual patient reports",
        "do not constitute external validation",
    ):
        assert phrase in html
    assert "Relevant search concepts include" not in html
    assert "Search terminology associated with CER-AI" not in html
    structure = PageStructure(html)
    assert len(structure.attributes("h1")) == 1
    assert len(structure.attributes("title")) == 1
    assert not [m for m in structure.attributes("meta") if m.get("name") == "keywords"]
    assert not structure.attributes("form")
    assert not structure.attributes("input")
    assert len([m for m in structure.attributes("meta") if m.get("name") == "description"]) == 1


def test_new_editorial_sections_have_both_languages_with_one_existing_controller():
    html = Path("static/corneal-ectasia-risk-assessment.html").read_text(encoding="utf-8")
    structure = PageStructure(html)
    variants = [a for _, a in structure.tags if "data-language-variant" in a]
    assert len(variants) == 8
    assert sum(a["data-language-variant"] == "en" for a in variants) == 4
    assert sum(a["data-language-variant"] == "tr" for a in variants) == 4
    assert all(a["lang"] == a["data-language-variant"] for a in variants)
    assert 'html:not([lang="tr"]) [data-language-variant="tr"]' in html
    assert 'html[lang="tr"] [data-language-variant="en"]' in html
    scripts = structure.attributes("script")
    assert len(scripts) == 1
    assert scripts[0]["src"] == "/static/public-i18n.js?v=3"
    assert "CER-AI yapay zekâyı nasıl kullanır?" in html
    assert "Bunlar sentetik eğitim olgularıdır" in html


def test_product_public_links_resolve_without_patient_submission(public_app):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get("/corneal-ectasia-risk-assessment")
        structure = PageStructure(response.text)
        links = {a.get("href", "") for a in structure.attributes("a")}
        assert "/learning/clinical-cases" in links
        assert "/tr/learning/clinical-cases" in links
        for path in sorted(links):
            if path.startswith("/") and not path.startswith("//"):
                result = client.get(path)
                assert result.status_code == 200, path
        # Real Pentacam demo assets have not yet been approved for publication.
        assert "/demo" not in links


@pytest.mark.parametrize("agent", [
    "OAI-SearchBot", "Googlebot", "Bingbot", "PerplexityBot",
    "Claude-SearchBot", "ChatGPT-User", "Claude-User", "UnknownCrawler",
])
def test_existing_public_crawl_permissions_do_not_expose_private_paths(public_app, agent):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get("/robots.txt")
    assert response.status_code == 200
    groups = []
    for block in response.text.split("\n\n"):
        directives = [line.split(":", 1) for line in block.splitlines()
                      if ":" in line and not line.startswith("#")]
        names = [value.strip() for key, value in directives if key == "User-agent"]
        rules = [(key, value.strip()) for key, value in directives if key in ("Allow", "Disallow")]
        if names:
            groups.append((names, rules))
    matches = [rules for names, rules in groups if agent in names]
    if not matches:
        matches = [rules for names, rules in groups if "*" in names]
    assert len(matches) == 1
    rules = matches[0]
    # This site's rules are literal prefixes. Check longest-match precedence,
    # not urllib.robotparser's first-matching-rule behavior.
    assert all("*" not in prefix and "$" not in prefix for _, prefix in rules)

    def public_path_allowed(path):
        allow = max([len(prefix) for kind, prefix in rules
                     if kind == "Allow" and path.startswith(prefix)] or [0])
        block = max([len(prefix) for kind, prefix in rules
                     if kind == "Disallow" and prefix and path.startswith(prefix)] or [0])
        return allow >= block

    for path in ("/", "/corneal-ectasia-risk-assessment", "/learning/clinical-cases"):
        assert public_path_allowed(path), (agent, path)
    for path in ("/app", "/testing-app", "/api/example", "/analyze", "/archive", "/report/example"):
        assert not public_path_allowed(path), (agent, path)


@pytest.mark.parametrize("path", ["/", "/corneal-ectasia-risk-assessment", "/learning/clinical-cases"])
def test_staging_pages_remain_noindex(public_app, path):
    with TestClient(public_app, base_url="https://cer-ai-staging-staging.up.railway.app") as client:
        response = client.get(path)
    assert response.status_code == 200
    assert response.headers["x-robots-tag"] == "noindex,nofollow"
    assert '<meta name="robots" content="noindex,nofollow">' in response.text


def test_production_canonical_and_real_software_identity_remain_intact(public_app):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get("/corneal-ectasia-risk-assessment")
        structure = PageStructure(response.text)
        canonicals = [a["href"] for a in structure.attributes("link") if a.get("rel") == "canonical"]
        assert canonicals == ["https://cer-ai.com/corneal-ectasia-risk-assessment"]
        assert response.headers["x-robots-tag"].startswith("index,follow")
        home = client.get("/")
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', home.text, re.S)
    assert match
    graph = json.loads(match.group(1))["@graph"]
    software = next(item for item in graph if item["@type"] == "SoftwareApplication")
    assert software["name"] == "CER-AI"
    assert software["url"] == "https://cer-ai.com/"
    home_structure = PageStructure(home.text)
    assert [
        meta["content"]
        for meta in home_structure.attributes("meta")
        if meta.get("property") == "og:url"
    ] == ["https://cer-ai.com/"]
    assert [
        meta["content"]
        for meta in home_structure.attributes("meta")
        if meta.get("name") == "twitter:card"
    ] == ["summary"]


@pytest.mark.parametrize(
    ("path", "schema_type", "title"),
    (
        (
            "/corneal-ectasia-risk-assessment",
            "MedicalWebPage",
            "Corneal Ectasia Risk Assessment Software for Refractive Surgeons | CER-AI",
        ),
        (
            "/clinical-evidence",
            "MedicalWebPage",
            "Clinical Evidence for Corneal Ectasia Risk Assessment | CER-AI",
        ),
        (
            "/references",
            "CollectionPage",
            "Corneal Ectasia and Refractive Surgery References | CER-AI",
        ),
    ),
)
def test_static_public_pages_have_page_specific_discovery_identity(
    public_app, path, schema_type, title
):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get(path)
    assert response.status_code == 200
    structure = PageStructure(response.text)
    assert [m["content"] for m in structure.attributes("meta") if m.get("property") == "og:title"] == [title]
    assert [m["content"] for m in structure.attributes("meta") if m.get("property") == "og:url"] == [f"https://cer-ai.com{path}"]
    assert [m["content"] for m in structure.attributes("meta") if m.get("name") == "twitter:card"] == ["summary"]
    schema_match = re.search(
        r'<script id="cerai-page-discovery" type="application/ld\+json">(.*?)</script>',
        response.text,
        re.S,
    )
    assert schema_match is not None
    schema = json.loads(schema_match.group(1))
    assert schema["@type"] == schema_type
    assert schema["url"] == f"https://cer-ai.com{path}"
    assert schema["name"] == title
    assert schema["dateModified"] == "2026-09-10"
    assert schema["author"] == {"@id": "https://cer-ai.com/#clinical-author"}


def test_product_page_discovery_schema_points_to_canonical_software(public_app):
    with TestClient(public_app, base_url="https://cer-ai.com") as client:
        response = client.get("/corneal-ectasia-risk-assessment")
    schema_match = re.search(
        r'<script id="cerai-page-discovery" type="application/ld\+json">(.*?)</script>',
        response.text,
        re.S,
    )
    assert schema_match is not None
    schema = json.loads(schema_match.group(1))
    assert schema["mainEntity"] == {"@id": "https://cer-ai.com/#software"}
