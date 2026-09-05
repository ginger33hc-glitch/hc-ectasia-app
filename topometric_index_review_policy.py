"""Report-only Pentacam topometric index review for CER-AI.

This module adds a non-scoring surgeon-alert layer for ten printed Pentacam
indices.  It must never add Randleman/NICE/BAD-D/PS3 points, change a clinical
disposition, or create an independent hard stop.

Reference ranges follow the OCULUS Pentacam Interpretation Guide for the
8-mm topometric indices and KISA/I-S. TKC is treated as the device's printed
summary classification: an explicit suspect comment is yellow; an explicit
keratoconus stage above 0 is red. Unknown/unreadable TKC text is not inferred.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, Iterable


# Report-only thresholds. Operators intentionally mirror the printed OCULUS
# reference table; do not reuse CER-AI Randleman I-S bands here.
INDEX_ORDER = ("ISV", "IVA", "KI", "CKI", "IHA", "IHD", "Rmin_mm", "KISA", "I_S", "TKC")


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _numeric_status(field: str, value: Any) -> str:
    x = _number(value)
    if x is None:
        return "UNAVAILABLE"
    if field == "ISV":
        return "RED" if x >= 41 else "YELLOW" if x >= 37 else "NORMAL"
    if field == "IVA":
        return "RED" if x >= 0.32 else "YELLOW" if x >= 0.28 else "NORMAL"
    if field == "KI":
        return "RED" if x > 1.07 else "NORMAL"
    if field == "CKI":
        return "RED" if x >= 1.03 else "NORMAL"
    if field == "IHA":
        return "RED" if x > 21 else "YELLOW" if x >= 19 else "NORMAL"
    if field == "IHD":
        return "RED" if x >= 0.016 else "YELLOW" if x >= 0.014 else "NORMAL"
    if field == "Rmin_mm":
        return "RED" if x < 6.71 else "NORMAL"
    if field == "KISA":
        # Printed Pentacam guide: <60 normal; 60-100 suspect; >100 red.
        return "RED" if x > 100 else "YELLOW" if x >= 60 else "NORMAL"
    if field == "I_S":
        # Pentacam guide supplies a keratoconus-indicative threshold (>1.2 D)
        # but no separate yellow interval. Do not invent one.
        return "RED" if x > 1.2 else "NORMAL"
    return "UNAVAILABLE"


def _tkc_status(value: Any) -> str:
    if value is None:
        return "UNAVAILABLE"
    text = str(value).strip()
    if not text:
        return "UNAVAILABLE"
    compact = re.sub(r"\s+", "", text).upper().replace("–", "-").replace("—", "-")
    if compact in {"0", "TKC0", "NORMAL", "NO", "NONE", "NO_KC", "NOKC"}:
        return "NORMAL"
    if any(token in compact for token in ("SUSPECT", "POSSIBLE", "BORDERLINE")):
        return "YELLOW"
    # Accepted printed stage forms: 1, 1-2, 2, 2-3, 3, 3-4, 4 and TKC-prefixed forms.
    stage = compact[3:] if compact.startswith("TKC") else compact
    if re.fullmatch(r"[1-4](?:-[1-4])?", stage):
        return "RED"
    return "UNINTERPRETED"


def _reference(field: str) -> str:
    return {
        "ISV": "yellow >=37; red >=41",
        "IVA": "yellow >=0.28; red >=0.32",
        "KI": "red >1.07",
        "CKI": "red >=1.03",
        "IHA": "yellow >=19 um; red >21 um",
        "IHD": "yellow >=0.014; red >=0.016",
        "Rmin_mm": "red <6.71 mm",
        "KISA": "yellow 60-100%; red >100%",
        "I_S": "red >1.2 D; no separate Pentacam yellow threshold",
        "TKC": "printed TKC suspect comment = yellow; explicit TKC stage >0 = red",
    }[field]


def _display_value(field: str, value: Any) -> str:
    if value is None:
        return "Not available"
    if field == "Rmin_mm":
        return f"{float(value):.2f} mm" if _number(value) is not None else str(value)
    if field == "KISA":
        return f"{float(value):.1f}%" if _number(value) is not None else str(value)
    if field == "I_S":
        return f"{float(value):.2f} D" if _number(value) is not None else str(value)
    if field in {"IVA", "KI", "CKI", "IHD"}:
        return f"{float(value):.3f}" if _number(value) is not None else str(value)
    if field == "IHA":
        return f"{float(value):.1f} um" if _number(value) is not None else str(value)
    if field == "ISV":
        return f"{float(value):.0f}" if _number(value) is not None else str(value)
    return str(value)


def build_review(eye: Dict[str, Any]) -> Dict[str, Any]:
    labels = {
        "ISV": "ISV", "IVA": "IVA", "KI": "KI", "CKI": "CKI", "IHA": "IHA",
        "IHD": "IHD", "Rmin_mm": "Rmin", "KISA": "KISA%", "I_S": "I-S", "TKC": "TKC",
    }
    rows = []
    for field in INDEX_ORDER:
        value = eye.get(field)
        status = _tkc_status(value) if field == "TKC" else _numeric_status(field, value)
        rows.append({
            "field": field,
            "label": labels[field],
            "value": value,
            "display_value": _display_value(field, value),
            "status": status,
            "reference": _reference(field),
        })
    statuses = {row["status"] for row in rows}
    overall = "RED" if "RED" in statuses else "YELLOW" if "YELLOW" in statuses else "NORMAL"
    return {
        "status": overall,
        "rows": rows,
        "report_only": True,
        "scoring_effect": "NONE",
        "note": (
            "Report-only adjunct. These index alerts do not add points and do not independently "
            "change Randleman, NICE, BAD-D, PS3, or CER-AI PASS/CAUTION/STOP disposition."
        ),
    }


def _strip_tkc_conflicts(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a report-only TKC transcription can never become decision-critical."""
    safe = deepcopy(extracted)
    for eye in safe.get("eyes") or []:
        if not isinstance(eye, dict):
            continue
        eye["data_conflicts"] = [
            item for item in eye.get("data_conflicts") or []
            if str(item).split(":", 1)[0].strip() != "TKC"
        ]
    return safe


def _install_tkc_extraction(core) -> None:
    eye_schema = (((core.SCHEMA.get("properties") or {}).get("eyes") or {}).get("items") or {})
    properties = eye_schema.setdefault("properties", {})
    properties.setdefault("TKC", {"type": ["string", "null"]})
    required = eye_schema.setdefault("required", [])
    if "TKC" not in required:
        required.append("TKC")
    marker = "TOPOMETRIC TKC REPORT-ONLY TRANSCRIPTION RULE"
    if marker not in core.PROMPT:
        core.PROMPT += f"""

{marker}:
TKC is a report-only field. Transcribe TKC only from an explicitly printed Pentacam TKC / Topographic
Keratoconus Classification result on the corresponding eye's Topometric/KC display. Preserve the
printed classification text (for example 0, 1, 1-2, 2, 2-3, 3, 3-4, 4, or an explicit device
comment). Never infer TKC from ISV, IVA, KI, CKI, IHA, IHD, Rmin, KISA, I-S, map colors, or morphology.
If the TKC field is absent or unreadable, return null. TKC is not a scoring input.
"""


def _colorize(text: str, status: str, report_module) -> str:
    if status == "RED":
        return f'<font color="#{report_module.RED}"><b>{text}</b></font>'
    if status == "YELLOW":
        return f'<font color="#{report_module.AMBER}"><b>{text}</b></font>'
    return text


def _install_report_adapter(report_module) -> None:
    if getattr(report_module, "_cerai_topometric_index_review_installed", False):
        return
    previous_findings = report_module._findings
    previous_tomography_rows = report_module._tomography_rows
    previous_add_bullet = report_module._add_bullet

    def findings(eye: Dict[str, Any], locale: str = "en") -> Iterable[tuple[str, list[str]]]:
        groups = list(previous_findings(eye, locale))
        review = eye.get("topometric_index_review") or {}
        if not review:
            return groups
        tr = lambda value: report_module.translate_text(value, locale)
        status = str(review.get("status") or "NORMAL")
        if status == "RED":
            summary = "RED ALERT — one or more topometric indices meet a pathological/highly suspicious reference threshold or an explicit TKC keratoconus stage."
        elif status == "YELLOW":
            summary = "YELLOW ALERT — one or more topometric indices meet an abnormal/suspect reference threshold."
        else:
            summary = "No yellow/red topometric index threshold was identified among available values."
        items = [_colorize(tr(summary), status, report_module)]
        for row in review.get("rows") or []:
            row_status = str(row.get("status") or "UNAVAILABLE")
            status_label = {
                "RED": "RED", "YELLOW": "YELLOW", "NORMAL": "Normal",
                "UNAVAILABLE": "Not available", "UNINTERPRETED": "Uninterpreted",
            }.get(row_status, row_status)
            text = (
                f"{row.get('label')}: {row.get('display_value')} — {status_label} "
                f"(reference: {row.get('reference')})"
            )
            items.append(_colorize(tr(text), row_status, report_module))
        items.append(tr(str(review.get("note") or "")))
        groups.append((tr("Topometric / Ectasia Indices Review"), items))
        return groups

    def tomography_rows(extracted: Dict[str, Any], eye_id: str, locale: str = "en"):
        rows = list(previous_tomography_rows(extracted, eye_id, locale))
        source_eye = next((item for item in extracted.get("eyes") or [] if item.get("eye") == eye_id), {})
        rows.append((report_module.translate_text("TKC", locale), report_module.translate_text(str(source_eye.get("TKC")) if source_eye.get("TKC") is not None else "Not available", locale)))
        return rows

    color_re = re.compile(r'^<font color="#([0-9A-Fa-f]{6})"><b>(.*)</b></font>$', re.DOTALL)

    def add_bullet(document, text: str) -> None:
        match = color_re.match(str(text))
        if not match:
            previous_add_bullet(document, text)
            return
        color_hex, clean_text = match.groups()
        p = document.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = report_module.Pt(3)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(clean_text)
        run.bold = True
        run.font.color.rgb = report_module.RGBColor.from_string(color_hex.upper())

    report_module._findings = findings
    report_module._tomography_rows = tomography_rows
    report_module._add_bullet = add_bullet
    report_module._cerai_topometric_index_review_installed = True


def install(core, report_module) -> None:
    if getattr(core, "_cerai_topometric_index_review_installed", False):
        return
    _install_tkc_extraction(core)
    _install_report_adapter(report_module)

    previous_hc_engine = core.hc_engine

    def hc_engine_with_topometric_review(
        extracted: Dict[str, Any], age, eye_plans, patient_modifiers, patient_metadata=None
    ) -> Dict[str, Any]:
        # TKC is report-only; remove TKC-only merge conflicts before the clinical
        # engine sees them so they can never change completeness/disposition.
        decision = previous_hc_engine(
            _strip_tkc_conflicts(extracted), age, eye_plans, patient_modifiers, patient_metadata
        )
        source_by_eye = {
            item.get("eye"): item for item in extracted.get("eyes") or []
            if isinstance(item, dict) and item.get("eye") in {"OD", "OS"}
        }
        for result_eye in decision.get("eyes") or []:
            source_eye = source_by_eye.get(result_eye.get("eye"))
            if source_eye is not None:
                result_eye["topometric_index_review"] = build_review(source_eye)
        return decision

    core.hc_engine = hc_engine_with_topometric_review
    core._cerai_topometric_index_review_previous_hc_engine = previous_hc_engine
    core._cerai_topometric_index_review_installed = True
