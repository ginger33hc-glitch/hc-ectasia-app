"""Public CER-AI website routes.

This module is presentation-only. It does not alter clinical decision logic,
authentication, assessment endpoints, report generation, or archive behavior.
"""
import json
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response


_PUBLIC_HOME = Path("static/public-home.html")
_AI_LANDING = Path("static/corneal-ectasia-risk-assessment.html")
_PRIVATE_CRAWL_PATHS = (
    "/app",
    "/api/",
    "/archive",
    "/admin",
    "/auth",
    "/reports",
)


def _site_base(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _discovery_head(base: str) -> str:
    """Machine-readable discovery metadata for public CER-AI pages."""
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
                "@type": "MedicalWebPage",
                "@id": f"{base}/#medical-page",
                "url": f"{base}/",
                "name": "CER-AI corneal ectasia risk assessment",
                "description": (
                    "Professional information about structured screening for corneal "
                    "ectasia risk before corneal refractive surgery."
                ),
                "about": {
                    "@type": "MedicalCondition",
                    "name": "Corneal ectasia",
                },
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
                "mainEntity": {"@id": f"{base}/#software"},
                "isPartOf": {"@id": f"{base}/#website"},
                "inLanguage": "en",
            },
        ],
    }
    schema = json.dumps(structured_data, ensure_ascii=False, separators=(",", ":"))
    return f"""
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
  <meta name="keywords" content="corneal ectasia, ectasia risk assessment, refractive surgery screening, keratoconus screening, Pentacam, Final BAD-D, Belin Ambrosio, Randleman ERSS, NICE, PS3, LASIK ectasia, PRK ectasia, residual stromal bed">
  <link rel="canonical" href="{base}/">
  <link rel="describedby" type="text/markdown" href="{base}/llms.txt">
  <link rel="alternate" type="text/html" href="{base}/corneal-ectasia-risk-assessment">
  <script type="application/ld+json">{schema}</script>
"""


def _render_public_home(request: Request) -> HTMLResponse:
    html = _PUBLIC_HOME.read_text(encoding="utf-8")
    discovery = _discovery_head(_site_base(request))
    if "</head>" in html:
        html = html.replace("</head>", f"{discovery}</head>", 1)
    return HTMLResponse(html)


def _robots_txt(base: str) -> str:
    disallow = "\n".join(f"Disallow: {path}" for path in _PRIVATE_CRAWL_PATHS)
    return f"""# CER-AI public discovery policy
# Public medical-information pages may be indexed; clinical/private surfaces may not.

User-agent: *
Allow: /
{disallow}

User-agent: OAI-SearchBot
Allow: /
{disallow}

User-agent: ChatGPT-User
Allow: /
{disallow}

User-agent: GPTBot
Allow: /
{disallow}

User-agent: Claude-SearchBot
Allow: /
{disallow}

User-agent: Claude-User
Allow: /
{disallow}

User-agent: ClaudeBot
Allow: /
{disallow}

User-agent: Googlebot
Allow: /
{disallow}

User-agent: Google-Extended
Allow: /
{disallow}

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
CER-AI is a clinical decision-support system, not an autonomous diagnostic system. Public information should be interpreted as professional educational/product information and not as patient-specific medical advice. Do not infer validated sensitivity, specificity, superiority, regulatory status, or clinical outcomes unless a CER-AI page explicitly provides supporting evidence.
"""


def _sitemap_xml(base: str) -> str:
    urls = (
        (f"{base}/", "1.0"),
        (f"{base}/home", "0.9"),
        (f"{base}/corneal-ectasia-risk-assessment", "0.9"),
    )
    body = "".join(
        f"<url><loc>{url}</loc><changefreq>weekly</changefreq><priority>{priority}</priority></url>"
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

    # The legacy core registers the clinical UI at /. During the public-site
    # cutover, remove only that GET route; the clinical UI remains available at
    # /app and all clinical/API endpoints keep their existing paths.
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
    def public_home(request: Request) -> HTMLResponse:
        return _render_public_home(request)

    @core.app.get("/corneal-ectasia-risk-assessment", include_in_schema=False)
    def corneal_ectasia_risk_assessment() -> FileResponse:
        return FileResponse(_AI_LANDING)

    @core.app.get("/robots.txt", include_in_schema=False)
    def robots(request: Request) -> PlainTextResponse:
        return PlainTextResponse(_robots_txt(_site_base(request)))

    @core.app.get("/llms.txt", include_in_schema=False)
    def llms(request: Request) -> PlainTextResponse:
        return PlainTextResponse(_llms_txt(_site_base(request)), media_type="text/plain")

    @core.app.get("/sitemap.xml", include_in_schema=False)
    def sitemap(request: Request) -> Response:
        return Response(_sitemap_xml(_site_base(request)), media_type="application/xml")

    @core.app.get("/app", include_in_schema=False)
    def clinical_app_entry() -> FileResponse:
        return FileResponse("static/index.html")

    core._cerai_public_site_installed = True