"""Public CER-AI website routes.

This module is presentation-only. It does not alter clinical decision logic,
authentication, assessment endpoints, report generation, or archive behavior.
"""
import json
import os
import re
from html import escape
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response


_PUBLIC_HOME = Path("static/public-home.html")
_AI_LANDING = Path("static/corneal-ectasia-risk-assessment.html")
_EVIDENCE_PAGE = Path("static/clinical-evidence.html")
_REFERENCES_PAGE = Path("static/references.html")
_TESTING_NOTICE = Path("static/testing-notice.html")
_PUBLIC_CANONICAL_BASE = os.getenv(
    "CERAI_PUBLIC_CANONICAL_BASE", "https://cer-ai.com"
).rstrip("/")
_PUBLIC_CONTENT_LASTMOD = "2026-09-08"
_MOBILE_INSTALL_SECTION = """
<div id="mobile-install" style="margin-top:34px;padding:26px;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 6px 18px rgba(23,59,87,.045)">
  <div class="section-kicker">Mobile access</div>
  <h2 style="font-size:clamp(25px,3vw,34px);margin-bottom:10px">Install CER-AI on your phone</h2>
  <p class="lead" style="font-size:16px">CER-AI can be added to your phone's Home Screen and opened like an app. No App Store or Google Play download is required.</p>
  <div class="guide-grid" style="margin-top:22px">
    <div class="guide-step"><div class="step-no">iOS</div><h3>iPhone or iPad</h3><p><strong>1.</strong> Open <strong>cer-ai.com</strong> in Safari.<br><strong>2.</strong> Tap <strong>Share</strong>.<br><strong>3.</strong> Choose <strong>Add to Home Screen</strong>.<br><strong>4.</strong> Tap <strong>Add</strong>.</p></div>
    <div class="guide-step"><div class="step-no">AND</div><h3>Android</h3><p><strong>1.</strong> Open <strong>cer-ai.com</strong> in Chrome.<br><strong>2.</strong> Tap the browser menu <strong>⋮</strong>.<br><strong>3.</strong> Choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.<br><strong>4.</strong> Confirm.</p></div>
  </div>
  <div class="guide-alert"><strong>After installation:</strong> CER-AI appears on the Home Screen and opens the secure clinical application. An internet connection is required for clinical use.</div>
</div>
"""
_PRIVATE_CRAWL_PATHS = (
    "/app",
    "/testing-app",
    "/api/",
    "/analyze",
    "/assessment/",
    "/report/",
    "/reports",
    "/archive",
    "/admin",
    "/auth",
    "/portal",
    "/dashboard",
    "/login",
    "/account",
)
_AI_CRAWLERS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "Applebot-Extended",
    "Google-Extended",
)
_SEARCH_CRAWLERS = (
    "Googlebot",
    "Bingbot",
    "DuckDuckBot",
)


def _site_base(request: Request) -> str:
    del request
    return _PUBLIC_CANONICAL_BASE


def _is_indexable_host(request: Request) -> bool:
    """Only the canonical production host may enter public search indexes."""
    hostname = (request.url.hostname or "").lower().rstrip(".")
    return hostname in {"cer-ai.com", "www.cer-ai.com"}


def _robots_directive(request: Request) -> str:
    if _is_indexable_host(request):
        return "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
    return "noindex,nofollow"


def _webmaster_verification_meta() -> str:
    """Render optional public ownership tokens configured by the site owner."""
    tags = []
    google = os.getenv("CERAI_GOOGLE_SITE_VERIFICATION", "").strip()
    bing = os.getenv("CERAI_BING_SITE_VERIFICATION", "").strip()
    if google:
        tags.append(
            f'<meta name="google-site-verification" content="{escape(google, quote=True)}">'
        )
    if bing:
        tags.append(
            f'<meta name="msvalidate.01" content="{escape(bing, quote=True)}">'
        )
    return "\n  ".join(tags)


def _discovery_head(base: str, *, robots_directive: str) -> str:
    """Machine-readable discovery metadata for public CER-AI pages."""
    citations = [
        {
            "@type": "ScholarlyArticle",
            "name": "Risk assessment for ectasia after corneal refractive surgery",
            "identifier": "https://doi.org/10.1016/j.ophtha.2007.03.073",
        },
        {
            "@type": "ScholarlyArticle",
            "name": "Validation of the Ectasia Risk Score System for Preoperative Laser In Situ Keratomileusis Screening",
            "identifier": "https://doi.org/10.1016/j.ajo.2007.12.033",
        },
        {
            "@type": "ScholarlyArticle",
            "name": "Risk Assessment for Corneal Ectasia following Photorefractive Keratectomy",
            "identifier": "https://doi.org/10.1155/2017/2434830",
        },
        {
            "@type": "ScholarlyArticle",
            "name": "Enhanced Tomographic Assessment to Detect Corneal Ectasia Based on Artificial Intelligence",
            "identifier": "https://doi.org/10.1016/j.ajo.2018.08.005",
        },
        {
            "@type": "ScholarlyArticle",
            "name": "Association Between the Percent Tissue Altered and Post-LASIK Ectasia in Eyes With Normal Preoperative Topography",
            "identifier": "https://doi.org/10.1016/j.ajo.2014.04.002",
        },
    ]
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{base}/#website",
                "url": f"{base}/",
                "name": "CER-AI",
                "description": (
                    "Clinical decision-support software for structured preoperative "
                    "corneal ectasia risk assessment in refractive surgery."
                ),
                "inLanguage": "en",
            },
            {
                "@type": "SoftwareApplication",
                "@id": f"{base}/#software",
                "name": "CER-AI",
                "url": f"{base}/",
                "softwareVersion": "0.7.71",
                "creator": {"@id": f"{base}/#clinical-author"},
                "applicationCategory": "MedicalApplication",
                "applicationSubCategory": (
                    "Corneal ectasia risk assessment and refractive-surgery screening"
                ),
                "operatingSystem": "Web",
                "description": (
                    "CER-AI is clinical decision-support software for preoperative "
                    "corneal ectasia risk assessment. It organizes independent risk "
                    "pathways including Randleman/ERSS, Pentacam Final BAD-D, NICE, "
                    "PS3, corneal topography and tomography findings, pachymetry, "
                    "residual stromal bed and procedure-specific tissue-safety checks."
                ),
                "featureList": [
                    "Corneal ectasia risk assessment",
                    "Keratoconus and ectasia susceptibility screening support",
                    "Pentacam-derived tomography and topography review",
                    "Randleman Ectasia Risk Score System (ERSS)",
                    "Belin/Ambrosio Final BAD-D review",
                    "NICE pathway assessment",
                    "PS3 pathway assessment",
                    "Pachymetry and residual stromal bed safety checks",
                    "LASIK and PRK procedure-specific screening",
                    "Auditable clinical decision-support reporting",
                ],
                "isAccessibleForFree": False,
            },
            {
                "@type": "Person",
                "@id": f"{base}/#clinical-author",
                "name": "Hüseyin Cengiz, M.D.",
                "jobTitle": "Ophthalmic Surgeon and Developer of CER-AI",
                "url": f"{base}/#developer",
            },
            {
                "@type": "MedicalWebPage",
                "@id": f"{base}/#medical-page",
                "url": f"{base}/",
                "name": "CER-AI corneal ectasia risk assessment",
                "description": (
                    "Professional information about structured screening for corneal "
                    "ectasia risk before corneal refractive surgery."
                ),
                "about": {"@type": "MedicalCondition", "name": "Corneal ectasia"},
                "medicalAudience": {
                    "@type": "MedicalAudience",
                    "audienceType": "Ophthalmologists and refractive surgeons",
                },
                "keywords": [
                    "corneal ectasia",
                    "post-LASIK ectasia",
                    "refractive surgery ectasia risk",
                    "keratoconus screening",
                    "Pentacam ectasia screening",
                    "Belin Ambrosio BAD-D",
                    "Final BAD-D",
                    "Randleman Ectasia Risk Score System",
                    "ERSS",
                    "NICE ectasia risk",
                    "PS3 ectasia risk",
                    "corneal topography",
                    "corneal tomography",
                    "pachymetry",
                    "residual stromal bed",
                    "LASIK screening",
                    "PRK screening",
                ],
                "citation": citations,
                "author": {"@id": f"{base}/#clinical-author"},
                "dateModified": _PUBLIC_CONTENT_LASTMOD,
                "mainEntity": {"@id": f"{base}/#software"},
                "isPartOf": {"@id": f"{base}/#website"},
                "inLanguage": "en",
            },
        ],
    }
    schema = json.dumps(structured_data, ensure_ascii=False, separators=(",", ":"))
    verification = _webmaster_verification_meta()
    if verification:
        verification = f"  {verification}\n"
    return f"""
  <meta name="robots" content="{robots_directive}">
{verification}  <meta name="keywords" content="corneal ectasia, ectasia risk assessment, refractive surgery screening, keratoconus screening, Pentacam, Final BAD-D, Belin Ambrosio, Randleman ERSS, NICE, PS3, LASIK ectasia, PRK ectasia, residual stromal bed">
  <link rel="canonical" href="{base}/">
  <link rel="describedby" type="text/markdown" href="{base}/llms.txt">
  <link rel="alternate" type="text/html" href="{base}/corneal-ectasia-risk-assessment">
  <link rel="related" type="text/html" href="{base}/clinical-evidence">
  <link rel="related" type="text/html" href="{base}/references">
  <link rel="stylesheet" href="{base}/static/technical-public.css?v=1">
  <script type="application/ld+json">{schema}</script>
"""


def _render_public_home(request: Request) -> HTMLResponse:
    html = _PUBLIC_HOME.read_text(encoding="utf-8")
    directive = _robots_directive(request)
    discovery = _discovery_head(_site_base(request), robots_directive=directive)
    if "</head>" in html:
        html = html.replace("</head>", f"{discovery}</head>", 1)
    marker = '<a href="#about">About</a>'
    if marker in html and 'href="/clinical-evidence"' not in html:
        html = html.replace(marker, '<a href="/clinical-evidence">Clinical Evidence</a>' + marker, 1)
    if 'id="references"' not in html and "</main>" in html:
        references_section = """
<section id="references" class="alt"><div class="wrap">
  <div class="section-kicker">Scientific foundation</div>
  <h2>Medical References</h2>
  <p class="lead">Review the consolidated medical literature discussed and used across CER-AI development, including ERSS, NICE, PS3, BAD-D, Pentacam tomography, PRFI, PTA, RTA, SCORE, biomechanical safety and postoperative ectasia literature.</p>
  <div class="cta-panel"><div><h3>View the CER-AI reference registry</h3><p>The registry is searchable by author, title, journal, DOI and clinical topic.</p></div><a class="btn" href="/references">Open References</a></div>
</div></section>
"""
        html = html.replace("</main>", f"{references_section}</main>", 1)
    if 'id="mobile-install"' not in html:
        marker = '<div class="guide-alert"><strong>Clinical use:'
        if marker in html:
            html = html.replace(marker, _MOBILE_INSTALL_SECTION + marker, 1)
    return HTMLResponse(html, headers={"X-Robots-Tag": directive})


def _render_public_page(path: Path, request: Request, canonical_path: str) -> HTMLResponse:
    """Serve a static public page with one environment-safe canonical contract."""
    html = path.read_text(encoding="utf-8")
    directive = _robots_directive(request)
    canonical = f'{_site_base(request)}{canonical_path}'
    canonical_tag = '<link rel="canonical" href="{}">'.format(canonical)
    if re.search(r'<link\s+rel="canonical"[^>]*>', html, flags=re.IGNORECASE):
        html = re.sub(
            r'<link\s+rel="canonical"[^>]*>', canonical_tag, html,
            count=1, flags=re.IGNORECASE,
        )
    else:
        html = html.replace("</head>", f"  {canonical_tag}\n</head>", 1)
    if re.search(r'<meta\s+name="robots"[^>]*>', html, flags=re.IGNORECASE):
        html = re.sub(
            r'<meta\s+name="robots"[^>]*>',
            f'<meta name="robots" content="{directive}">',
            html, count=1, flags=re.IGNORECASE,
        )
    else:
        html = html.replace(
            "</head>", f'  <meta name="robots" content="{directive}">\n</head>', 1,
        )
    return HTMLResponse(html, headers={"X-Robots-Tag": directive})


def _robot_group(agents: tuple[str, ...], *, explicit_allow: bool) -> str:
    lines = [*(f"User-agent: {agent}" for agent in agents)]
    if explicit_allow:
        lines.extend(("Allow: /", "Allow: /public/", "Allow: /about/", "Allow: /documentation/"))
    lines.extend(f"Disallow: {path}" for path in _PRIVATE_CRAWL_PATHS)
    return "\n".join(lines)


def _robots_txt(base: str) -> str:
    ai_group = _robot_group(_AI_CRAWLERS, explicit_allow=True)
    search_group = _robot_group(_SEARCH_CRAWLERS, explicit_allow=True)
    fallback_group = _robot_group(("*",), explicit_allow=False)
    return f"""# CER-AI public discovery policy
# Public medical-information pages may be indexed; clinical/private surfaces may not.
# robots.txt is crawler guidance only and is not an access-control boundary.

# AI/search-assistant crawlers
{ai_group}

# Traditional search engines
{search_group}

# Global fallback: unknown crawlers may access public pages but not clinical/private paths
{fallback_group}

Sitemap: {base}/sitemap.xml
"""


def _llms_txt(base: str) -> str:
    """Concise, public, LLM-oriented description. This is not clinical output."""
    return f"""# CER-AI

> CER-AI is web-based clinical decision-support software for structured preoperative corneal ectasia risk assessment in refractive surgery. It is intended for qualified ophthalmic professionals and does not replace surgeon judgment.

CER-AI is relevant to searches about corneal ectasia, post-LASIK ectasia, keratoconus susceptibility screening, refractive-surgery ectasia risk, Pentacam tomography/topography, Belin/Ambrosio Final BAD-D, the Randleman Ectasia Risk Score System (ERSS), NICE, PS3, pachymetry, residual stromal bed, LASIK screening, PRK screening, and procedure-specific corneal tissue safety.

The software keeps major risk pathways independently interpretable rather than hiding them inside a single opaque score. Public pages describe the concepts and workflow; patient-specific clinical assessment occurs only inside the protected application.

## Primary public pages
- [CER-AI home]({base}/): Overview of the clinical decision-support platform and its independent ectasia-risk pathways.
- [Corneal ectasia risk assessment]({base}/corneal-ectasia-risk-assessment): Search-oriented clinical overview of the problem CER-AI addresses and the terminology used by the platform.
- [Clinical evidence and references]({base}/clinical-evidence): Verified literature mapped to the CER-AI pathways and concepts it supports, with explicit evidence boundaries.
- [Full medical reference registry]({base}/references): Searchable consolidated CER-AI bibliography grouped by clinical topic.

## Evidence anchors
- Randleman et al. Risk assessment for ectasia after corneal refractive surgery. Ophthalmology. 2008. DOI 10.1016/j.ophtha.2007.03.073.
- Randleman et al. Validation of the Ectasia Risk Score System for Preoperative LASIK Screening. Am J Ophthalmol. 2008. DOI 10.1016/j.ajo.2007.12.033.
- Sorkin et al. Risk Assessment for Corneal Ectasia following Photorefractive Keratectomy. J Ophthalmol. 2017. DOI 10.1155/2017/2434830.
- Navarro-Naranjo et al. Assessment of Preoperative Risk Factors for Post-LASIK Ectasia Development. Clin Ophthalmol. 2024. DOI 10.2147/OPTH.S464217.
- Lopes et al. Enhanced Tomographic Assessment to Detect Corneal Ectasia Based on Artificial Intelligence. Am J Ophthalmol. 2018. DOI 10.1016/j.ajo.2018.08.005.
- Santhiago et al. Association Between the Percent Tissue Altered and Post-LASIK Ectasia in Eyes With Normal Preoperative Topography. Am J Ophthalmol. 2014. DOI 10.1016/j.ajo.2014.04.002.

## Core concepts
- Corneal ectasia and postoperative corneal ectasia risk
- Keratoconus and ectasia susceptibility screening before refractive surgery
- Pentacam corneal tomography and topography
- Belin/Ambrosio Enhanced Ectasia Display and Final BAD-D
- Randleman Ectasia Risk Score System (ERSS)
- NICE ectasia-risk pathway
- PS3 ectasia-risk pathway
- Pachymetry and thinnest corneal thickness
- Residual stromal bed and procedure-specific tissue-safety calculations
- LASIK and PRK preoperative screening

## Interpretation guidance
CER-AI is a clinical decision-support system, not an autonomous diagnostic system. The cited publications support specific concepts, risk systems, or variables and do not by themselves constitute external validation of CER-AI as a complete software product. Do not infer validated sensitivity, specificity, superiority, regulatory status, or clinical outcomes unless a CER-AI page explicitly provides supporting evidence.
"""


def _sitemap_xml(base: str) -> str:
    urls = (
        (f"{base}/", "1.0"),
        (f"{base}/corneal-ectasia-risk-assessment", "0.9"),
        (f"{base}/clinical-evidence", "0.9"),
        (f"{base}/references", "0.9"),
    )
    body = "".join(
        f"<url><loc>{url}</loc><lastmod>{_PUBLIC_CONTENT_LASTMOD}</lastmod>"
        f"<changefreq>weekly</changefreq><priority>{priority}</priority></url>"
        for url, priority in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</urlset>"
    )


def install(core) -> None:
    if getattr(core, "_cerai_public_site_installed", False):
        return

    core.app.router.routes[:] = [
        route
        for route in core.app.router.routes
        if not (
            getattr(route, "path", None) == "/"
            and "GET" in (getattr(route, "methods", None) or set())
        )
    ]

    @core.app.get("/", include_in_schema=False)
    def public_root(request: Request) -> HTMLResponse:
        return _render_public_home(request)

    @core.app.get("/home", include_in_schema=False)
    def public_home() -> RedirectResponse:
        return RedirectResponse(url="/", status_code=308)

    @core.app.get("/corneal-ectasia-risk-assessment", include_in_schema=False)
    def corneal_ectasia_risk_assessment(request: Request) -> HTMLResponse:
        return _render_public_page(
            _AI_LANDING, request, "/corneal-ectasia-risk-assessment"
        )

    @core.app.get("/clinical-evidence", include_in_schema=False)
    def clinical_evidence(request: Request) -> HTMLResponse:
        return _render_public_page(_EVIDENCE_PAGE, request, "/clinical-evidence")

    @core.app.get("/references", include_in_schema=False)
    def references(request: Request) -> HTMLResponse:
        return _render_public_page(_REFERENCES_PAGE, request, "/references")

    @core.app.get("/robots.txt", include_in_schema=False)
    def robots(request: Request) -> PlainTextResponse:
        if not _is_indexable_host(request):
            return PlainTextResponse(
                "User-agent: *\nDisallow: /\n",
                headers={"X-Robots-Tag": "noindex, nofollow"},
            )
        return PlainTextResponse(_robots_txt(_site_base(request)))

    @core.app.get("/llms.txt", include_in_schema=False)
    def llms(request: Request) -> PlainTextResponse:
        return PlainTextResponse(_llms_txt(_site_base(request)), media_type="text/plain")

    @core.app.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request) -> Response:
        if not _is_indexable_host(request):
            return Response(
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>',
                media_type="application/xml",
                headers={"X-Robots-Tag": "noindex, nofollow"},
            )
        return Response(_sitemap_xml(_site_base(request)), media_type="application/xml")

    # Public website application links intentionally land on the testing notice.
    @core.app.get("/app", include_in_schema=False)
    def public_application_notice() -> FileResponse:
        return FileResponse(_TESTING_NOTICE)

    # Separate non-public entry point retained for the current authorized testing phase.
    @core.app.get("/testing-app", include_in_schema=False)
    def clinical_testing_entry() -> FileResponse:
        return FileResponse("static/index.html")

    core._cerai_public_site_installed = True
