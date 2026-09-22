"""Shared non-clinical entry point for CER-AI clinical modules."""

from pathlib import Path
from typing import Any

from fastapi.responses import FileResponse


MODULE_SELECTOR_HTML = Path("static/module-select.html")


def install(core: Any) -> None:
    if getattr(core, "_cerai_clinical_entry_installed", False):
        return

    @core.app.get("/clinical-modules", include_in_schema=False)
    def clinical_modules():
        return FileResponse(
            MODULE_SELECTOR_HTML,
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    core._cerai_clinical_entry_installed = True
