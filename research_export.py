"""Owner-only pseudonymized scientific CSV export for CER-AI.

Direct identifiers, reviewer/user names, original filenames, free-text notes, and exact calendar dates
are never exported. Stable study identifiers are HMAC pseudonyms created with a dedicated research
secret that is independent from the archive-encryption key. The CSV is generated on demand and is not
stored back into the clinical archive.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
from io import BytesIO, StringIO
import json
import os
from typing import Any, Dict, Iterable, Optional

from fastapi import Body, HTTPException
from fastapi.responses import StreamingResponse

import case_catalog


RESEARCH_EXPORT_ENABLED = os.getenv("CERAI_RESEARCH_EXPORT_ENABLED", "0").strip() == "1"
RESEARCH_FIELDS = (
    "study_subject_id",
    "study_case_id",
    "study_revision_id",
    "report_year_month",
    "exam_year_month",
    "age_years",
    "eye",
    "overall_status",
    "eye_status",
    "procedure",
    "laser_platform",
    "prior_refractive_surgery",
    "pachy_thinnest_um",
    "K1_D",
    "K2_D",
    "Kmax_D",
    "Kmean_D",
    "BAD_D",
    "BAD_category",
    "randleman_total",
    "randleman_category",
    "nice_total",
    "nice_category",
    "score_total",
    "score_category",
    "morphology_category",
    "I_S_D",
    "Rmin_mm",
    "ARTmax_um",
    "PPI_min",
    "PPI_avg",
    "PPI_max",
    "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um",
    "manifest_MRSE_D",
    "intended_MRSE_D",
    "max_ablation_um",
    "LASIK_RSB_um",
    "LASIK_PTA_percent",
    "PRK_RST_um",
    "PRK_PTA_percent",
    "optical_zone_mm",
    "transition_zone_mm",
    "flap_thickness_um",
    "preoperative_Kmean_D",
    "estimated_final_Kmean_D",
    "pentacam_qs",
)


class ResearchConfigurationError(RuntimeError):
    """Research export is enabled without an acceptable pseudonym key."""


def decode_pseudonym_key(value: str) -> bytes:
    try:
        key = base64.b64decode(str(value).strip(), validate=True)
    except Exception as exc:
        raise ResearchConfigurationError(
            "CERAI_RESEARCH_PSEUDONYM_KEY_B64 must be valid base64."
        ) from exc
    if len(key) != 32:
        raise ResearchConfigurationError(
            "CERAI_RESEARCH_PSEUDONYM_KEY_B64 must decode to exactly 32 bytes."
        )
    return key


def key_from_environment() -> bytes:
    value = os.getenv("CERAI_RESEARCH_PSEUDONYM_KEY_B64", "").strip()
    if not value:
        raise ResearchConfigurationError(
            "CERAI_RESEARCH_EXPORT_ENABLED=1 requires CERAI_RESEARCH_PSEUDONYM_KEY_B64."
        )
    return decode_pseudonym_key(value)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _identity_text(patient: Dict[str, Any]) -> Optional[str]:
    patient_id = _clean(patient.get("id"))
    if patient_id:
        return "patient-id|" + patient_id.casefold()
    name = _clean(patient.get("name"))
    if name:
        return "patient-name|" + case_catalog._search_text(name)
    return None


def pseudonym(key: bytes, namespace: str, value: str, *, length: int = 24) -> str:
    digest = hmac.new(
        key,
        f"CER-AI-RESEARCH-v1|{namespace}|{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:length]


def _year_month(value: Any) -> str:
    text = _clean(value)
    if len(text) >= 7 and text[4] in {"-", "/", "."}:
        year = text[:4]
        month = text[5:7]
        if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
            return f"{year}-{month}"
    return ""


def _assessment_key(archive: Any, case_id: str, revision_id: str) -> Optional[str]:
    prefix = f"cases/{case_id}/revisions/{revision_id}/assessment-json-"
    keys = archive.store.list(prefix)
    return keys[0] if len(keys) == 1 else None


def _manifest_timestamp(archive: Any, case_id: str, revision_id: str) -> str:
    prefix = f"cases/{case_id}/revisions/{revision_id}/manifest-json-"
    keys = archive.store.list(prefix)
    if len(keys) != 1:
        return ""
    try:
        payload = json.loads(archive.get_bytes(keys[0]))
    except Exception:
        return ""
    return str(payload.get("archived_at_utc") or "")


def load_assessment(archive: Any, case_id: str, revision_id: str) -> Optional[Dict[str, Any]]:
    key = _assessment_key(archive, case_id, revision_id)
    if not key:
        return None
    try:
        payload = json.loads(archive.get_bytes(key))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _latest_entries(archive: Any, entries: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    latest: Dict[str, tuple[str, Dict[str, Any]]] = {}
    for entry in entries:
        case_id = str(entry.get("case_id") or "")
        revision_id = str(entry.get("revision_id") or "")
        stamp = _manifest_timestamp(archive, case_id, revision_id)
        order_key = stamp + "|" + revision_id
        previous = latest.get(case_id)
        if previous is None or order_key > previous[0]:
            latest[case_id] = (order_key, entry)
    return [item[1] for item in latest.values()]


def _extracted_eye(extracted: Dict[str, Any], eye_id: str) -> Dict[str, Any]:
    for eye in extracted.get("eyes") or []:
        if isinstance(eye, dict) and eye.get("eye") == eye_id:
            return eye
    return {}


def _exam_year_month(extracted: Dict[str, Any]) -> str:
    dates = sorted({
        _year_month(context.get("exam_date"))
        for context in extracted.get("document_contexts") or []
        if isinstance(context, dict) and _year_month(context.get("exam_date"))
    })
    return dates[0] if len(dates) == 1 else ""


def _row_for_eye(
    key: bytes,
    entry: Dict[str, Any],
    assessment: Dict[str, Any],
    eye: Dict[str, Any],
) -> Dict[str, Any]:
    patient = assessment.get("patient") or {}
    decision = assessment.get("decision") or {}
    extracted = assessment.get("extracted") or {}
    eye_id = str(eye.get("eye") or "")
    raw_eye = _extracted_eye(extracted, eye_id)
    values = eye.get("values") or {}
    score = eye.get("score") or {}
    randleman = eye.get("randleman_erss") or {}
    nice = eye.get("nice") or {}
    bad = eye.get("bad_summary") or {}
    morphology = eye.get("topography_classification") or {}
    identity = _identity_text(patient)
    subject_id = pseudonym(key, "subject", identity) if identity else ""
    case_id = str(entry.get("case_id") or "")
    revision_id = str(entry.get("revision_id") or "")
    return {
        "study_subject_id": subject_id,
        "study_case_id": pseudonym(key, "case", case_id),
        "study_revision_id": pseudonym(key, "revision", case_id + "|" + revision_id),
        "report_year_month": _year_month(patient.get("report_date")),
        "exam_year_month": _exam_year_month(extracted),
        "age_years": patient.get("age"),
        "eye": eye_id,
        "overall_status": decision.get("status"),
        "eye_status": eye.get("status"),
        "procedure": values.get("procedure"),
        "laser_platform": values.get("laser_platform"),
        "prior_refractive_surgery": values.get("prior_refractive_surgery"),
        "pachy_thinnest_um": values.get("pachy_thinnest_um", raw_eye.get("pachy_thinnest_um")),
        "K1_D": raw_eye.get("K1_D"),
        "K2_D": raw_eye.get("K2_D"),
        "Kmax_D": raw_eye.get("Kmax_D"),
        "Kmean_D": raw_eye.get("Kmean_D"),
        "BAD_D": bad.get("value", raw_eye.get("BAD_D")),
        "BAD_category": bad.get("category"),
        "randleman_total": randleman.get("total"),
        "randleman_category": randleman.get("category"),
        "nice_total": nice.get("total"),
        "nice_category": nice.get("category"),
        "score_total": score.get("total"),
        "score_category": score.get("category"),
        "morphology_category": morphology.get("scoring_category"),
        "I_S_D": raw_eye.get("I_S"),
        "Rmin_mm": raw_eye.get("Rmin_mm"),
        "ARTmax_um": raw_eye.get("ARTmax_um"),
        "PPI_min": raw_eye.get("PPI_min"),
        "PPI_avg": raw_eye.get("PPI_avg"),
        "PPI_max": raw_eye.get("PPI_max"),
        "anterior_elevation_thinnest_um": raw_eye.get("anterior_elevation_thinnest_um"),
        "posterior_elevation_thinnest_um": raw_eye.get("posterior_elevation_thinnest_um"),
        "manifest_MRSE_D": values.get("MRSE_D"),
        "intended_MRSE_D": values.get("intended_MRSE_D"),
        "max_ablation_um": values.get("max_ablation_um"),
        "LASIK_RSB_um": values.get("LASIK_RSB_um"),
        "LASIK_PTA_percent": values.get("LASIK_PTA_percent"),
        "PRK_RST_um": values.get("PRK_RST_um"),
        "PRK_PTA_percent": values.get("PRK_PTA_percent"),
        "optical_zone_mm": values.get("optical_zone_mm"),
        "transition_zone_mm": values.get("transition_zone_mm"),
        "flap_thickness_um": values.get("flap_thickness_um"),
        "preoperative_Kmean_D": values.get("preoperative_Kmean_D"),
        "estimated_final_Kmean_D": values.get("estimated_final_Kmean_D"),
        "pentacam_qs": values.get("pentacam_qs"),
    }


def build_rows(archive: Any, key: bytes, *, latest_only: bool = True) -> list[Dict[str, Any]]:
    entries = case_catalog.list_entries(archive)
    if latest_only:
        entries = _latest_entries(archive, entries)
    rows: list[Dict[str, Any]] = []
    for entry in entries:
        assessment = load_assessment(
            archive,
            str(entry.get("case_id") or ""),
            str(entry.get("revision_id") or ""),
        )
        if not assessment:
            continue
        for eye in (assessment.get("decision") or {}).get("eyes") or []:
            if isinstance(eye, dict) and eye.get("eye") in {"OD", "OS"}:
                rows.append(_row_for_eye(key, entry, assessment, eye))
    rows.sort(key=lambda item: (item["study_case_id"], {"OD": 0, "OS": 1}.get(item["eye"], 2)))
    return rows


def render_csv(rows: Iterable[Dict[str, Any]]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(RESEARCH_FIELDS), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in RESEARCH_FIELDS})
    return stream.getvalue().encode("utf-8-sig")


def install(core: Any, archive_runtime: Any) -> None:
    if getattr(core, "_cerai_research_export_installed", False):
        return
    core._cerai_research_export_enabled = RESEARCH_EXPORT_ENABLED

    if RESEARCH_EXPORT_ENABLED:
        if not bool(getattr(core, "_cerai_named_users_enabled", False)):
            raise ResearchConfigurationError(
                "CER-AI research export requires named-user authentication."
            )
        key = key_from_environment()
        import user_access

        @core.app.post("/archive/research/export.csv")
        def export_research_csv(payload: Dict[str, Any] = Body(default={})):
            principal = user_access.require_current_principal()
            if principal.role != "OWNER":
                raise HTTPException(403, "Only the CER-AI OWNER role may export research data.")
            if not archive_runtime.enabled:
                raise HTTPException(503, "CER-AI secure archive is not enabled.")
            unknown = set(payload) - {"latest_only"}
            if unknown:
                raise HTTPException(422, "Unsupported research export option(s).")
            latest_only = payload.get("latest_only", True)
            if not isinstance(latest_only, bool):
                raise HTTPException(422, "latest_only must be true or false.")
            rows = build_rows(archive_runtime.archive, key, latest_only=latest_only)
            callback = getattr(core, "_cerai_audit_event", None)
            if callback is not None:
                callback(
                    "RESEARCH_EXPORT",
                    actor=principal,
                    details={"row_count": len(rows), "latest_only": latest_only},
                )
            content = render_csv(rows)
            return StreamingResponse(
                BytesIO(content),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="CER-AI_research_export.csv"',
                    "Cache-Control": "no-store",
                },
            )

    core._cerai_research_export_installed = True
