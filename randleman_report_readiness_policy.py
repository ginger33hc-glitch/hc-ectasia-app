"""Fail-closed Randleman/ERSS readiness for LASIK reports.

A LASIK assessment must not receive a report token unless the patient-specific
Randleman/ERSS five-row score is complete for every assessed virgin eye.
Missing ERSS components are converted into explicit completion requests so the
surgeon can supply/confirm the underlying data before report generation.
"""
from copy import deepcopy

from fastapi import HTTPException

_REQUIRED_ROWS = ("topography", "RSB", "age", "pachymetry", "MRSE")
_previous_missing_items = None
_previous_request = None
_previous_export_payload = None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_lasik_virgin_eye(eye):
    values = eye.get("values") or {}
    if str(values.get("procedure") or "").upper() != "LASIK":
        return False
    prior = str(values.get("prior_refractive_surgery") or "").strip().lower()
    return prior not in {"yes", "true", "1"}


def _erss_complete(eye):
    if not _is_lasik_virgin_eye(eye):
        return True
    erss = eye.get("randleman_erss")
    if not isinstance(erss, dict):
        return False
    rows = erss.get("rows") or {}
    if not all(_number(rows.get(name)) for name in _REQUIRED_ROWS):
        return False
    return _number(erss.get("total"))


def _component_requests(eye):
    """Return actionable missing-data messages for an incomplete LASIK ERSS."""
    if not _is_lasik_virgin_eye(eye) or _erss_complete(eye):
        return []

    erss = eye.get("randleman_erss") or {}
    rows = erss.get("rows") or {}
    missing_rows = set(erss.get("missing_erss_inputs") or [])
    missing_rows.update(name for name in _REQUIRED_ROWS if not _number(rows.get(name)))
    evidence = eye.get("erss_topography_evidence") or {}
    messages = []

    if "topography" in missing_rows:
        if evidence.get("needs_surgeon_I_S"):
            messages.append("Randleman/ERSS requires a usable signed I-S value for numeric topography scoring.")
        if evidence.get("needs_surgeon_SRAX"):
            messages.append(
                "Randleman/ERSS requires SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map."
            )
        if not evidence.get("needs_surgeon_I_S") and not evidence.get("needs_surgeon_SRAX"):
            messages.append(
                "Randleman/ERSS topography is unresolved; confirm signed I-S and Front-map SRAX evidence."
            )
    if "RSB" in missing_rows:
        messages.append("Randleman/ERSS RSB is unavailable; complete the LASIK flap thickness and ablation inputs.")
    if "age" in missing_rows:
        messages.append("Randleman/ERSS age is unavailable; enter the patient age.")
    if "pachymetry" in missing_rows:
        messages.append("Randleman/ERSS requires preoperative pachy_thinnest_um.")
    if "MRSE" in missing_rows:
        messages.extend((
            "Randleman/ERSS requires the preoperative manifest sphere.",
            "Randleman/ERSS requires the preoperative manifest cylinder magnitude.",
        ))

    if not messages:
        messages.append(
            "Randleman/ERSS score is unavailable; all five LASIK ERSS components must be documented before report generation."
        )
    return list(dict.fromkeys(messages))


def missing_items_with_complete_erss(decision):
    items = list(_previous_missing_items(decision))
    for eye in decision.get("eyes") or []:
        eye_id = eye.get("eye", "GLOBAL")
        for message in _component_requests(eye):
            items.append((eye_id, message))
    return list(dict.fromkeys(items))


def request_with_randleman(eye, message, extracted):
    text = str(message).lower()
    prefix = str(eye).lower()
    if "randleman/erss age is unavailable" in text:
        return {
            "eye": "PATIENT",
            "label": "Patient age (years) — required for Randleman/ERSS",
            "kind": "form",
            "key": "age",
            "destination": "source",
            "form_id": "age",
            "help": "Randleman/ERSS cannot be completed without age.",
        }
    if "randleman/erss rsb is unavailable" in text:
        return {
            "eye": eye,
            "label": "LASIK flap thickness — required to calculate RSB for Randleman/ERSS",
            "kind": "form",
            "key": "flap_um",
            "destination": "source",
            "form_id": f"{prefix}_flap",
            "help": "Complete the LASIK flap/ablation plan so residual stromal bed can be calculated.",
        }
    return _previous_request(eye, message, extracted)


def _validate_export_erss(payload):
    decision = payload.get("decision") or {}
    incomplete = [
        eye.get("eye", "UNKNOWN")
        for eye in decision.get("eyes") or []
        if _is_lasik_virgin_eye(eye) and not _erss_complete(eye)
    ]
    if incomplete:
        raise HTTPException(
            409,
            "Randleman/ERSS is incomplete for " + ", ".join(incomplete)
            + "; complete the missing ERSS inputs before generating a report.",
        )


def export_payload_with_complete_erss(payload):
    exported = _previous_export_payload(payload)
    _validate_export_erss(exported)
    return exported


def install(assessment_workflow):
    global _previous_missing_items, _previous_request, _previous_export_payload
    if getattr(assessment_workflow, "_cerai_randleman_report_readiness_installed", False):
        return
    _previous_missing_items = assessment_workflow.missing_items
    _previous_request = assessment_workflow._request
    _previous_export_payload = assessment_workflow.export_payload
    assessment_workflow.missing_items = missing_items_with_complete_erss
    assessment_workflow._request = request_with_randleman
    assessment_workflow.export_payload = export_payload_with_complete_erss
    assessment_workflow._cerai_randleman_report_readiness_installed = True
