"""Public CER-AI website routes.

This module is presentation-only. It does not alter clinical decision logic,
authentication, assessment endpoints, report generation, or archive behavior.
"""
from fastapi.responses import FileResponse


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
    def public_root() -> FileResponse:
        return FileResponse("static/public-home.html")

    @core.app.get("/home", include_in_schema=False)
    def public_home() -> FileResponse:
        return FileResponse("static/public-home.html")

    @core.app.get("/app", include_in_schema=False)
    def clinical_app_entry() -> FileResponse:
        return FileResponse("static/index.html")

    core._cerai_public_site_installed = True
