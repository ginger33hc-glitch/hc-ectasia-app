"""Encrypted immutable audit events for CER-AI archive and access activity.

Audit payloads may contain PHI (for example a search query) and are therefore encrypted with the same
client-side archive envelope before storage. Object keys contain only case/random identifiers, event
type, month, and content hash; search terms, patient identity and usernames are never placed in keys
or S3 metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Body, HTTPException

from case_archive import EncryptedArchive


AUDIT_FORMAT = "CER-AI-AUDIT-v1"
GLOBAL_AUDIT_CASE_ID = "0" * 32
_AUDIT_KEY_RE = re.compile(
    r"^cases/(?P<case_id>[0-9a-f]{32})/audit/(?P<month>\d{4}-\d{2})/"
    r"event-[a-z0-9_-]+-[0-9a-f]{64}\.enc$"
)


def _actor_payload(actor: Any) -> Optional[Dict[str, str]]:
    if actor is None:
        return None
    return {
        "user_id": str(actor.user_id),
        "username": str(actor.username),
        "display_name": str(actor.display_name),
        "role": str(actor.role),
    }


def write_event(
    archive: EncryptedArchive,
    event_type: str,
    *,
    actor: Any = None,
    case_id: Optional[str] = None,
    revision_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    now = datetime.now(timezone.utc)
    target_case_id = str(case_id or GLOBAL_AUDIT_CASE_ID)
    if not re.fullmatch(r"[0-9a-f]{32}", target_case_id):
        raise ValueError("Audit case_id must be a 32-character hexadecimal identifier.")
    clean_type = "".join(ch for ch in str(event_type).upper() if ch.isalnum() or ch == "_")[:48]
    if not clean_type:
        raise ValueError("Audit event type is required.")
    payload = {
        "audit_format": AUDIT_FORMAT,
        "event_id": uuid4().hex,
        "event_type": clean_type,
        "occurred_at_utc": now.isoformat(),
        "actor": _actor_payload(actor),
        "case_id": case_id,
        "revision_id": revision_id,
        "details": dict(details or {}),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return archive.put_bytes(
        target_case_id,
        f"audit/{now:%Y-%m}",
        f"event-{clean_type.lower()}-{payload['event_id']}",
        encoded,
        media_type="application/json",
    )


def list_events(
    archive: EncryptedArchive,
    *,
    case_id: Optional[str] = None,
    event_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    limit: int = 500,
) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit), 2000))
    if case_id is not None and not re.fullmatch(r"[0-9a-f]{32}", str(case_id)):
        raise ValueError("Audit case_id filter must be a 32-character hexadecimal identifier.")
    prefix = f"cases/{case_id}/audit/" if case_id else "cases/"
    requested_type = str(event_type or "").strip().upper()
    requested_actor = str(actor_user_id or "").strip()
    events: list[Dict[str, Any]] = []
    for key in archive.store.list(prefix):
        if not _AUDIT_KEY_RE.match(key):
            continue
        payload = json.loads(archive.get_bytes(key))
        if payload.get("audit_format") != AUDIT_FORMAT:
            continue
        if requested_type and payload.get("event_type") != requested_type:
            continue
        actor = payload.get("actor") or {}
        if requested_actor and actor.get("user_id") != requested_actor:
            continue
        events.append(payload)
    events.sort(
        key=lambda item: (
            str(item.get("occurred_at_utc") or ""),
            str(item.get("event_id") or ""),
        ),
        reverse=True,
    )
    return events[:limit]


def install(core: Any, archive_runtime: Any) -> None:
    """Expose fail-aware audit writes and an OWNER-only audit review API."""
    if getattr(core, "_cerai_audit_log_installed", False):
        return

    def audit_event(event_type: str, **kwargs):
        if not archive_runtime.enabled:
            return None
        try:
            return write_event(archive_runtime.archive, event_type, **kwargs)
        except Exception as exc:
            archive_runtime.fail_or_continue(exc)
            return None

    core._cerai_audit_event = audit_event
    core._cerai_audit_log_runtime = archive_runtime

    if bool(getattr(core, "_cerai_named_users_enabled", False)):
        import user_access

        @core.app.post("/archive/audit/search")
        def search_audit(payload: Dict[str, Any] = Body(default={})):
            principal = user_access.require_current_principal()
            if principal.role != "OWNER":
                raise HTTPException(403, "Only the CER-AI OWNER role may review audit records.")
            if not archive_runtime.enabled:
                raise HTTPException(503, "CER-AI secure archive is not enabled.")
            allowed = {"case_id", "event_type", "actor_user_id", "limit"}
            unknown = set(payload) - allowed
            if unknown:
                raise HTTPException(422, "Unsupported audit search field(s): " + ", ".join(sorted(unknown)))
            try:
                events = list_events(
                    archive_runtime.archive,
                    case_id=payload.get("case_id"),
                    event_type=payload.get("event_type"),
                    actor_user_id=payload.get("actor_user_id"),
                    limit=payload.get("limit", 500),
                )
            except (TypeError, ValueError) as exc:
                raise HTTPException(422, str(exc)) from exc
            audit_event(
                "AUDIT_VIEW",
                actor=principal,
                details={
                    "filters": {key: payload.get(key) for key in allowed if key in payload},
                    "result_count": len(events),
                },
            )
            return {"events": events, "count": len(events)}

    core._cerai_audit_log_installed = True
