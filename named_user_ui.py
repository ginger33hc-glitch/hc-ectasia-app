"""Minimal named-user web UI routing without changing the clinical frontend source file.

When named-user authentication is enabled, unauthenticated visits to the main application or archive
page are redirected to a dedicated login page. The existing clinical HTML is served unchanged except
for a small authenticated navigation/session script injected at response time, keeping the clinical UI
source and clinical engine isolated from authentication concerns.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import quote
from typing import Any

from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse


ROOT_HTML = Path("static/index.html")
LOGIN_HTML = Path("static/login.html")
ARCHIVE_HTML = Path("static/archive.html")


def _authenticated_root_html(display_name: str) -> str:
    html = ROOT_HTML.read_text(encoding="utf-8")
    label = escape(display_name or "CER-AI user")
    injection = f"""
<div id="cerAiAccountBar" style="position:fixed;right:12px;bottom:12px;z-index:9999;background:#fff;border:1px solid #bcc8d1;border-radius:9px;padding:8px 10px;box-shadow:0 4px 18px rgba(0,0,0,.14);font:12px Arial,sans-serif;color:#173b57">
  <span style="margin-right:8px">{label}</span>
  <a href="/archive-ui" style="font-weight:bold;color:#1f5e8c">Case Archive</a>
</div>
<script>
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
        @core.app.get("/auth/login-page", include_in_schema=False)
        def login_page():
            return FileResponse(LOGIN_HTML, media_type="text/html")

        @core.app.get("/archive-ui", include_in_schema=False)
        def archive_page():
            return FileResponse(ARCHIVE_HTML, media_type="text/html")

        @core.app.middleware("http")
        async def named_user_page_gate(request, call_next):
            path = request.url.path
            if request.method == "GET" and path in {"/", "/archive-ui"}:
                principal = core._cerai_authenticate_request(request)
                if principal is None:
                    destination = "/auth/login-page?next=" + quote(path, safe="/")
                    return RedirectResponse(destination, status_code=303)
                if path == "/":
                    return HTMLResponse(
                        _authenticated_root_html(principal.display_name),
                        headers={"Cache-Control": "no-store"},
                    )
            return await call_next(request)

    core._cerai_named_user_ui_installed = True
