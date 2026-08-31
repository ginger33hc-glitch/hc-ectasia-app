"""Encrypted case-catalog foundation for CER-AI.

Catalog entries live inside the same encrypted S3-compatible case archive.  Searchable PHI is never
placed in object keys or S3 metadata.  This intentionally provides a durable storage/index seam only;
authenticated owner/doctor UI routes are added separately once named-user authentication is restored.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import json
import re
import unicodedata
from typing import Any, Dict, Iterable, Optional

from case_archive import EncryptedArchive, RevisionRef


CATALOG_FORMAT = "CER-AI-CASE-CATALOG-v1"
_CATALOG_KEY_RE = re.compile(
    r"^cases/(?P<case_id>[0-9a-f]{32})/catalog/(?P<revision_id>[0-9a-f]{24})/case-index-[0-9a-f]{64}\.enc$"
)


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _search_text(value: Any) -> str:
    text = _clean_text(value) or ""
    # Diacritic-insensitive matching is useful for Turkish names entered on different keyboards.
    text = text.replace("ı", "i").replace("İ", "I")
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_like = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_like.casefold()


def _date_text(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    # Preserve the displayed report date exactly, but normalize ISO date/datetime inputs.
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return text


def build_entry(ready: Dict[str, Any], *, case_id: str, revision_id: str) -> Dict[str, Any]:
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
):
    entry = build_entry(ready, case_id=revision.case_id, revision_id=revision.revision_id)
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


def search_entries(
    archive: EncryptedArchive,
    *,
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    report_date: Optional[str] = None,
    decision: Optional[str] = None,
    reviewer: Optional[str] = None,
    limit: int = 100,
) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    name_q = _search_text(patient_name)
    id_q = _search_text(patient_id)
    date_q = _search_text(report_date)
    decision_q = _search_text(decision)
    reviewer_q = _search_text(reviewer)

    matches: list[Dict[str, Any]] = []
    for entry in list_entries(archive):
        patient = entry.get("patient") or {}
        disposition = entry.get("decision") or {}
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


def install(core: Any, archive_runtime: Any) -> None:
    """Wrap readiness after the archive layer and persist a catalog entry for each archived revision."""
    if getattr(core, "_cerai_case_catalog_installed", False):
        return

    import assessment_workflow

    previous_begin = assessment_workflow.begin
    previous_complete = assessment_workflow.complete
    export_payload = assessment_workflow.export_payload

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
            ref = write_entry(archive_runtime.archive, revision, ready)
            response["archive"]["catalog_status"] = "INDEXED"
            response["archive"]["catalog_sha256"] = ref.sha256
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
    core._cerai_case_catalog_installed = True
