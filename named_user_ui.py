"""Named-user web UI routing kept outside the clinical frontend and decision engine.

When named-user authentication is enabled, unauthenticated visits to the clinical application or archive
page are redirected to a dedicated login page. The existing clinical HTML is served unchanged except
for a small authenticated navigation/session script injected at response time.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote
from typing import Any

from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse


ROOT_HTML = Path("static/index.html")
LOGIN_HTML = Path("static/login.html")
TRIAL_LOGIN_HTML = Path("static/trial-login.html")
ARCHIVE_HTML = Path("static/archive.html")
_SHARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9-]{1,128}$")
_SHARE_ERRORS = frozenset({"no_images", "too_many_images", "image_too_large", "images_too_large"})


def _authenticated_destination(request) -> str:
    path = request.url.path
    if path != "/app":
        return path
    token = str(request.query_params.get("share_token") or "")
    if _SHARE_TOKEN_RE.fullmatch(token):
        return f"/app?share_token={token}"
    error = str(request.query_params.get("share_error") or "")
    if error in _SHARE_ERRORS:
        return f"/app?share_error={error}"
    return path


def _authenticated_root_html(display_name: str) -> str:
    html = ROOT_HTML.read_text(encoding="utf-8")
    # Make the visual CER-AI logo itself a native link back to the public website.
    # A real anchor is used instead of JavaScript so the navigation works reliably
    # across browsers, touch devices, cached pages, and CSP/security wrappers.
    logo_frame = '<div class="brand-logo-frame" aria-label="CER-AI"><span class="brand-wordmark">CER-AI</span></div>'
    linked_logo_frame = '<a href="/" class="brand-logo-frame" aria-label="Return to CER-AI website" title="Return to CER-AI website"><span class="brand-wordmark">CER-AI</span></a>'
    html = html.replace(logo_frame, linked_logo_frame, 1)

    label = escape(display_name or "CER-AI user")
    reviewer_json = (
        json.dumps(display_name or "CER-AI user", ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    injection = f"""
<div id="cerAiAccountBar" style="position:fixed;right:12px;bottom:12px;z-index:9999;background:#fff;border:1px solid #bcc8d1;border-radius:9px;padding:8px 10px;box-shadow:0 4px 18px rgba(0,0,0,.14);font:12px Arial,sans-serif;color:#173b57">
  <span style="margin-right:8px">{label}</span>
  <a href="/archive-ui" style="font-weight:bold;color:#1f5e8c">Case Archive</a>
</div>
<script>
const cerAiAuthenticatedReviewer = {reviewer_json};
const cerAiReviewerField = document.getElementById("reviewer");
if (cerAiReviewerField) {{
  cerAiReviewerField.value = cerAiAuthenticatedReviewer;
  cerAiReviewerField.readOnly = true;
  cerAiReviewerField.title = "Report attribution is bound to the authenticated CER-AI user.";
}}
if (typeof ceraiFetch === "function") {{
  ceraiFetch = async function(url, options={{}}) {{
    const response = await fetch(url, options);
    if (response.status === 401 && (response.headers.get("www-authenticate") || "").includes("CER-AI-Session")) {{
      window.location.assign("/auth/login-page?next=" + encodeURIComponent(window.location.pathname));
      throw new Error("CER-AI session expired. Sign in again.");
    }}
    return response;
  }};
}}
</script>
"""
    return html.replace("</body>", injection + "\n</body>")


def install(core: Any) -> None:
    if getattr(core, "_cerai_named_user_ui_installed", False):
        return
    enabled = bool(getattr(core, "_cerai_named_users_enabled", False))

    if enabled:
        import operational_security
        import user_access

        @core.app.get("/auth/login-page", include_in_schema=False)
        def login_page():
            return FileResponse(
                TRIAL_LOGIN_HTML
                if bool(getattr(core, "_cerai_trial_name_login_enabled", False))
                else LOGIN_HTML,
                media_type="text/html",
                headers={"Cache-Control": "no-store"},
            )

        @core.app.get("/archive-ui", include_in_schema=False)
        def archive_page():
            return FileResponse(
                ARCHIVE_HTML,
                media_type="text/html",
                headers={"Cache-Control": "no-store"},
            )

        @core.app.get("/archive/capabilities", include_in_schema=False)
        def archive_capabilities():
            principal = user_access.require_current_principal()
            archive_runtime = getattr(core, "_cerai_case_archive_runtime", None)
            return {
                "role": principal.role,
                "archive_enabled": bool(archive_runtime and archive_runtime.enabled),
                "identifiable_archive_access": bool(
                    archive_runtime and archive_runtime.enabled and principal.role == "DOCTOR"
                ),
                "retrospective_archive_access": bool(
                    archive_runtime
                    and archive_runtime.enabled
                    and principal.role in {"DOCTOR", "OWNER"}
                ),
                "owner_deidentified_access": bool(
                    archive_runtime and archive_runtime.enabled and principal.role == "OWNER"
                ),
                "audit_enabled": bool(getattr(core, "_cerai_audit_log_installed", False)),
                "historical_report_enabled": bool(
                    getattr(core, "_cerai_historical_report_installed", False)
                ),
                "research_export_enabled": bool(
                    getattr(core, "_cerai_research_export_enabled", False)
                ),
            }

        @core.app.middleware("http")
        async def named_user_page_gate(request, call_next):
            path = request.url.path
            if request.method == "GET" and path in {"/app", "/archive-ui"}:
                principal = core._cerai_authenticate_request(request)
                if principal is None:
                    destination = "/auth/login-page?next=" + quote(
                        _authenticated_destination(request), safe="/"
                    )
                    return operational_security._secure_response(
                        RedirectResponse(destination, status_code=303),
                        path,
                    )
                if path == "/app":
                    response = HTMLResponse(
                        _authenticated_root_html(principal.display_name),
                        headers={"Cache-Control": "no-store"},
                    )
                    return operational_security._secure_response(response, path)
            return await call_next(request)

    core._cerai_named_user_ui_installed = True
