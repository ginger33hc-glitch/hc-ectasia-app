"""Encrypted case catalog and role-scoped archive retrieval for CER-AI.

Catalog entries live inside the same encrypted S3-compatible case archive. Searchable PHI is never
placed in object keys or S3 metadata. OWNER may search the complete archive; DOCTOR is restricted to
cases created under that authenticated user identity. Legacy/unattributed cases remain OWNER-only.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
import json
import re
import unicodedata
from typing import Any, Dict, Optional

from fastapi import Body, HTTPException
from fastapi.responses import StreamingResponse

from case_archive import EncryptedArchive, RevisionRef


CATALOG_FORMAT = "CER-AI-CASE-CATALOG-v1"
_CATALOG_KEY_RE = re.compile(
    r"^cases/(?P<case_id>[0-9a-f]{32})/catalog/(?P<revision_id>[0-9a-f]{24})/case-index-[0-9a-f]{64}\.enc$"
)
_CASE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_REVISION_ID_RE = re.compile(r"^[0-9a-f]{24}$")


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _search_text(value: Any) -> str:
    text = _clean_text(value) or ""
    # Turkish/Latin diacritics, punctuation and spacing are presentation details rather than
    # identifiers. Removing them makes common searches such as "Şule Işık"/"sule isik",
    # "Dr. Example"/"dr example" and "P-123"/"p123" equivalent without exposing PHI in keys.
    text = text.replace("ı", "i").replace("İ", "I")
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_like = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "".join(ch for ch in ascii_like.casefold() if ch.isalnum())


def _date_text(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return text


def _creator_payload(actor: Any) -> Optional[Dict[str, str]]:
    if actor is None:
        return None
    return {
        "user_id": str(actor.user_id),
        "username": str(actor.username),
        "display_name": str(actor.display_name),
        "role": str(actor.role),
    }


def build_entry(
    ready: Dict[str, Any],
    *,
    case_id: str,
    revision_id: str,
    actor: Any = None,
) -> Dict[str, Any]:
    patient = deepcopy(ready.get("patient") or {})
    decision = deepcopy(ready.get("decision") or {})
    eyes = []
    for eye in decision.get("eyes") or []:
        eyes.append({
            "eye": _clean_text(eye.get("eye")),
            "status": _clean_text(eye.get("status")),
        })
    eyes.sort(key=lambda item: {"OD": 0, "OS": 1}.get(item.get("eye"), 2))
    return {
        "catalog_format": CATALOG_FORMAT,
        "case_id": case_id,
        "revision_id": revision_id,
        "created_by": _creator_payload(actor),
        "patient": {
            "name": _clean_text(patient.get("name")),
            "id": _clean_text(patient.get("id")),
            "age": patient.get("age"),
        },
        "reviewer": _clean_text(patient.get("reviewer")),
        "report_date": _date_text(patient.get("report_date")),
        "decision": {
            "status": _clean_text(decision.get("status")),
            "action": _clean_text(decision.get("action")),
            "eyes": eyes,
        },
    }


def write_entry(
    archive: EncryptedArchive,
    revision: RevisionRef,
    ready: Dict[str, Any],
    *,
    actor: Any = None,
):
    entry = build_entry(
        ready,
        case_id=revision.case_id,
        revision_id=revision.revision_id,
        actor=actor,
    )
    payload = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return archive.put_bytes(
        revision.case_id,
        f"catalog/{revision.revision_id}",
        "case-index",
        payload,
        media_type="application/json",
    )


def _catalog_keys(archive: EncryptedArchive) -> list[str]:
    return [key for key in archive.store.list("cases/") if _CATALOG_KEY_RE.match(key)]


def list_entries(archive: EncryptedArchive) -> list[Dict[str, Any]]:
    entries: list[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for key in _catalog_keys(archive):
        match = _CATALOG_KEY_RE.match(key)
        if not match:
            continue
        identity = (match.group("case_id"), match.group("revision_id"))
        if identity in seen:
            continue
        payload = json.loads(archive.get_bytes(key))
        if payload.get("catalog_format") != CATALOG_FORMAT:
            continue
        if payload.get("case_id") != identity[0] or payload.get("revision_id") != identity[1]:
            continue
        seen.add(identity)
        entries.append(payload)
    entries.sort(
        key=lambda item: (
            _clean_text(item.get("report_date")) or "",
            _clean_text(item.get("case_id")) or "",
            _clean_text(item.get("revision_id")) or "",
        ),
        reverse=True,
    )
    return entries


def get_entry(archive: EncryptedArchive, case_id: str, revision_id: str) -> Optional[Dict[str, Any]]:
    if not _CASE_ID_RE.fullmatch(str(case_id)) or not _REVISION_ID_RE.fullmatch(str(revision_id)):
        return None
    for entry in list_entries(archive):
        if entry.get("case_id") == case_id and entry.get("revision_id") == revision_id:
            return entry
    return None


def search_entries(
    archive: EncryptedArchive,
    *,
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    report_date: Optional[str] = None,
    decision: Optional[str] = None,
    reviewer: Optional[str] = None,
    created_by_user_id: Optional[str] = None,
    limit: int = 100,
) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    name_q = _search_text(patient_name)
    id_q = _search_text(patient_id)
    date_q = _search_text(report_date)
    decision_q = _search_text(decision)
    reviewer_q = _search_text(reviewer)
    creator_q = str(created_by_user_id or "").strip()

    matches: list[Dict[str, Any]] = []
    for entry in list_entries(archive):
        patient = entry.get("patient") or {}
        disposition = entry.get("decision") or {}
        creator = entry.get("created_by") or {}
        if creator_q and str(creator.get("user_id") or "") != creator_q:
            continue
        if name_q and name_q not in _search_text(patient.get("name")):
            continue
        if id_q and id_q not in _search_text(patient.get("id")):
            continue
        if date_q and date_q not in _search_text(entry.get("report_date")):
            continue
        if decision_q and decision_q not in _search_text(disposition.get("status")):
            continue
        if reviewer_q and reviewer_q not in _search_text(entry.get("reviewer")):
            continue
        matches.append(entry)
        if len(matches) >= limit:
            break
    return matches


def _principal_can_access(principal: Any, entry: Dict[str, Any]) -> bool:
    if principal.role == "OWNER":
        return True
    creator = entry.get("created_by") or {}
    return principal.role == "DOCTOR" and creator.get("user_id") == principal.user_id


def install(core: Any, archive_runtime: Any) -> None:
    """Persist encrypted catalog entries and add role-scoped archive routes when named auth is on."""
    if getattr(core, "_cerai_case_catalog_installed", False):
        return

    import assessment_workflow
    import user_access

    previous_begin = assessment_workflow.begin
    previous_complete = assessment_workflow.complete
    export_payload = assessment_workflow.export_payload

    def audit(event_type: str, **kwargs) -> None:
        callback = getattr(core, "_cerai_audit_event", None)
        if callback is not None:
            callback(event_type, **kwargs)

    def catalog_if_ready(response: Dict[str, Any]) -> Dict[str, Any]:
        if not archive_runtime.enabled or response.get("workflow_status") != "READY":
            return response
        archive_state = response.get("archive") or {}
        if archive_state.get("status") != "ARCHIVED":
            return response
        token = str(response.get("assessment_token") or "")
        report_token = str(response.get("report_token") or "")
        case_id = str(archive_state.get("case_id") or "")
        revision_id = str(archive_state.get("revision_id") or "")
        if not all((token, report_token, case_id, revision_id)):
            return response
        try:
            ready = export_payload({
                "assessment_token": token,
                "report_token": report_token,
                "locale": "en",
            })
            revision = RevisionRef(case_id=case_id, revision_id=revision_id, artifacts=tuple())
            actor = user_access.current_principal()
            ref = write_entry(
                archive_runtime.archive,
                revision,
                ready,
                actor=actor,
            )
            response["archive"]["catalog_status"] = "INDEXED"
            response["archive"]["catalog_sha256"] = ref.sha256
            audit(
                "CASE_ARCHIVED",
                actor=actor,
                case_id=case_id,
                revision_id=revision_id,
                details={
                    "decision": (ready.get("decision") or {}).get("status"),
                    "report_date": (ready.get("patient") or {}).get("report_date"),
                },
            )
        except Exception as exc:
            archive_runtime.fail_or_continue(exc)
            response["archive"]["catalog_status"] = "UNAVAILABLE"
        return response

    def begin_cataloged(core_arg, extracted, age, plans, modifiers, metadata):
        return catalog_if_ready(previous_begin(core_arg, extracted, age, plans, modifiers, metadata))

    def complete_cataloged(core_arg, payload):
        return catalog_if_ready(previous_complete(core_arg, payload))

    assessment_workflow.begin = begin_cataloged
    assessment_workflow.complete = complete_cataloged
    core._cerai_case_catalog_runtime = archive_runtime
    core._cerai_case_catalog_search = (
        (lambda **filters: search_entries(archive_runtime.archive, **filters))
        if archive_runtime.enabled
        else (lambda **filters: [])
    )

    if bool(getattr(core, "_cerai_named_users_enabled", False)):
        @core.app.post("/archive/search")
        def search_archive(payload: Dict[str, Any] = Body(default={})):
            principal = user_access.require_current_principal()
            if not archive_runtime.enabled:
                raise HTTPException(503, "CER-AI secure archive is not enabled.")
            allowed = {"patient_name", "patient_id", "report_date", "decision", "reviewer", "limit"}
            unknown = set(payload) - allowed
            if unknown:
                raise HTTPException(422, "Unsupported archive search field(s): " + ", ".join(sorted(unknown)))
            filters = {key: payload.get(key) for key in allowed if key in payload}
            if principal.role == "DOCTOR":
                filters["created_by_user_id"] = principal.user_id
            results = search_entries(archive_runtime.archive, **filters)
            audit(
                "ARCHIVE_SEARCH",
                actor=principal,
                details={
                    "filters": {key: payload.get(key) for key in allowed if key in payload},
                    "result_count": len(results),
                    "scope": "ALL_CASES" if principal.role == "OWNER" else "OWN_CASES",
                },
            )
            return {"results": results, "count": len(results)}

        @core.app.get("/archive/cases/{case_id}/revisions/{revision_id}/report/{kind}")
        def archived_report(case_id: str, revision_id: str, kind: str, locale: str = "en"):
            principal = user_access.require_current_principal()
            if not archive_runtime.enabled:
                raise HTTPException(503, "CER-AI secure archive is not enabled.")
            entry = get_entry(archive_runtime.archive, case_id, revision_id)
            if entry is None:
                raise HTTPException(404, "Archived CER-AI case revision not found.")
            if not _principal_can_access(principal, entry):
                raise HTTPException(403, "You do not have access to this archived case.")
            if kind not in {"pdf", "docx"}:
                raise HTTPException(404, "Unsupported archived report type.")
            locale = "tr" if str(locale).lower().startswith("tr") else "en"
            ref = archive_runtime.archive.find_report(case_id, revision_id, locale, kind)
            if ref is None:
                raise HTTPException(404, "Archived CER-AI report not found.")
            content = archive_runtime.archive.get_bytes(ref)
            audit(
                "REPORT_DOWNLOAD",
                actor=principal,
                case_id=case_id,
                revision_id=revision_id,
                details={"kind": kind, "locale": locale},
            )
            if kind == "pdf":
                media_type = "application/pdf"
                filename = "CER-AI_Report.pdf"
            else:
                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                filename = "CER-AI_Report.docx"
            return StreamingResponse(
                BytesIO(content),
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

    core._cerai_case_catalog_installed = True
