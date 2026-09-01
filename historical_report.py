"""Regenerate historical CER-AI reports from archived canonical assessment snapshots.

The immutable original PDF/DOCX remains the source record. Regeneration is a separate on-demand render
using the current report template and never overwrites or stores over an archived artifact.
"""

from __future__ import annotations

from io import BytesIO
import json
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import case_catalog


def load_archived_assessment(archive: Any, case_id: str, revision_id: str) -> Optional[Dict[str, Any]]:
    prefix = f"cases/{case_id}/revisions/{revision_id}/assessment-json-"
    keys = archive.store.list(prefix)
    if len(keys) != 1:
        return None
    try:
        payload = json.loads(archive.get_bytes(keys[0]))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def regenerate_bytes(
    archive: Any,
    case_id: str,
    revision_id: str,
    *,
    kind: str,
    locale: str,
    pdf_builder: Callable[[Dict[str, Any]], bytes],
    docx_builder: Callable[[Dict[str, Any]], bytes],
) -> bytes:
    assessment = load_archived_assessment(archive, case_id, revision_id)
    if assessment is None:
        raise HTTPException(404, "Archived CER-AI canonical assessment not found.")
    localized = dict(assessment)
    localized["locale"] = "tr" if str(locale).lower().startswith("tr") else "en"
    if kind == "pdf":
        return pdf_builder(localized)
    if kind == "docx":
        return docx_builder(localized)
    raise HTTPException(404, "Unsupported regenerated report type.")


def install(core: Any, archive_runtime: Any) -> None:
    if getattr(core, "_cerai_historical_report_installed", False):
        return

    if bool(getattr(core, "_cerai_named_users_enabled", False)):
        import user_access
        from reports import build_docx, build_pdf

        @core.app.get("/archive/cases/{case_id}/revisions/{revision_id}/regenerate/{kind}")
        def regenerate_report(case_id: str, revision_id: str, kind: str, locale: str = "en"):
            principal = user_access.require_current_principal()
            if not archive_runtime.enabled:
                raise HTTPException(503, "CER-AI secure archive is not enabled.")
            entry = case_catalog.get_entry(archive_runtime.archive, case_id, revision_id)
            if entry is None:
                raise HTTPException(404, "Archived CER-AI case revision not found.")
            if not case_catalog._principal_can_access(principal, entry):
                raise HTTPException(403, "You do not have access to this archived case.")
            normalized_locale = "tr" if str(locale).lower().startswith("tr") else "en"
            content = regenerate_bytes(
                archive_runtime.archive,
                case_id,
                revision_id,
                kind=kind,
                locale=normalized_locale,
                pdf_builder=build_pdf,
                docx_builder=build_docx,
            )
            callback = getattr(core, "_cerai_audit_event", None)
            if callback is not None:
                callback(
                    "REPORT_REGENERATE",
                    actor=principal,
                    case_id=case_id,
                    revision_id=revision_id,
                    details={"kind": kind, "locale": normalized_locale, "template": "CURRENT"},
                )
            if kind == "pdf":
                media_type = "application/pdf"
                filename = "CER-AI_Report_Regenerated.pdf"
            else:
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                filename = "CER-AI_Report_Regenerated.docx"
            return StreamingResponse(
                BytesIO(content),
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-store",
                    "X-CER-AI-Report-Source": "archived-canonical-current-template",
                },
            )

    core._cerai_historical_report_installed = True
