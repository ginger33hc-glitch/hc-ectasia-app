"""Public CER-AI website routes.

This module is presentation-only. It does not alter clinical decision logic,
authentication, assessment endpoints, report generation, or archive behavior.
"""
from fastapi.responses import FileResponse


def install(core) -> None:
    if getattr(core, "_cerai_public_site_installed", False):
        return

    @core.app.get("/home", include_in_schema=False)
    def public_home() -> FileResponse:
        return FileResponse("static/public-home.html")

    @core.app.get("/app", include_in_schema=False)
    def clinical_app_entry() -> FileResponse:
        return FileResponse("static/index.html")

    core._cerai_public_site_installed = True
