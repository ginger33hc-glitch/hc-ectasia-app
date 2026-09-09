"""Canonical report projection for CER-AI.

This module is presentation-only. It consumes an already-computed clinical-core
result and copies structured values into a report payload. It performs no
clinical calculation, scoring, threshold comparison, or disposition logic.
PDF and DOCX renderers must consume this same payload.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping


# Presentation-only copy list. These are canonical extraction field names, not
# alternate sources or report-side calculations. Keeping the list here lets both
# renderers consume the exact same source values and provenance.
REPORT_EXTRACTION_FIELDS = (
    "ml7_k1_d", "ml7_k2_d", "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D",
    "topographic_astig_D", "topographic_steep_axis_deg", "bad_flat_axis_deg",
    "Rmin_mm", "ISV", "IVA", "KI", "CKI", "IHA", "IHD",
    "topometric_RMin", "TKC", "KISA", "I_S",
    "central_pachy_um", "pachy_thinnest_um", "Kmax_D",
    "corneal_diameter_mm", "F_Ele_Th_um", "B_Ele_Th_um",
    "PPI_min", "PPI_avg", "PPI_max", "ARTmax_um",
    "Df", "Db", "Dp", "Dt", "Da", "BAD_D", "srax_deg",
)


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _driver_payload(final_disposition: Any) -> dict[str, Any]:
    if final_disposition is None:
        return {"stop": [], "caution": [], "incomplete": []}
    return {
        "stop": _plain(getattr(final_disposition, "stop_drivers", ())),
        "caution": _plain(getattr(final_disposition, "caution_drivers", ())),
        "incomplete": _plain(getattr(final_disposition, "incomplete_drivers", ())),
    }


def build_report_payload(
    assessment: Mapping[str, Any],
    *,
    eye: str,
    software_version: str,
    clinical_policy_version: str,
    source_registry_version: str,
    srax_algorithm_version: str,
    source_eye: Mapping[str, Any] | None = None,
    planning: Any = None,
    microkeratome_planning: Any = None,
    astigmatic_disparity: Any = None,
    manual_corrections: Iterable[Any] = (),
) -> dict[str, Any]:
    """Project one completed canonical assessment into a renderer-neutral payload."""
    erss = assessment.get("erss")
    nice = assessment.get("nice") or {}
    bad_block = assessment.get("bad_d") or {}
    bad_result = bad_block.get("result")
    ps3 = assessment.get("ps3")
    procedure = str(assessment.get("procedure") or "").upper()

    randleman = None
    if erss is not None:
        randleman = {
            "rows": _plain(erss.get("rows") or {}),
            "total": erss.get("total"),
            "category": erss.get("category"),
            "status": assessment.get("erss_status"),
        }

    ps3_payload = None
    if ps3 is not None:
        ps3_payload = {
            "complete": bool(getattr(ps3, "complete", False)),
            "missing_keys": _plain(getattr(ps3, "missing_keys", ())),
            "moderate_count": getattr(ps3, "moderate_count", None),
            "high_count": getattr(ps3, "high_count", None),
            "findings": _plain(getattr(ps3, "findings", ())),
            "disposition": _plain(getattr(ps3, "disposition", None)),
            "review_notes": _plain(getattr(ps3, "review_notes", ())),
            "status": assessment.get("ps3_status"),
            "decision": _plain(assessment.get("ps3_decision")),
        }

    bad_payload = {
        "final_d": getattr(bad_result, "final_d", None),
        "classification": bad_block.get("classification"),
        "status": bad_block.get("status"),
        "context": _plain(getattr(bad_result, "context", {})),
        "component_interpretations": _plain(getattr(bad_result, "component_interpretations", {})),
    }

    corrections = []
    for item in manual_corrections:
        plain = _plain(item)
        if isinstance(plain, dict):
            plain = {**plain, "label": "SURGEON_CONFIRMED"}
        corrections.append(plain)

    source_eye = source_eye or {}
    source_values = {
        field: _plain(source_eye_value)
        for field in REPORT_EXTRACTION_FIELDS
        if (source_eye_value := source_eye.get(field)) is not None
    }
    source_provenance = {
        field: _plain(entries)
        for field, entries in (source_eye.get("field_provenance") or {}).items()
        if field in REPORT_EXTRACTION_FIELDS
    }

    return {
        "eye": eye,
        "procedure": procedure,
        "status": assessment.get("status"),
        "randleman": randleman,
        "nice": {
            "rows": _plain(nice.get("rows") or {}),
            "total": nice.get("total"),
            "category": nice.get("category"),
            "status": assessment.get("nice_status"),
            "values": _plain(nice.get("values") or {}),
            "missing": _plain(nice.get("missing") or []),
        },
        "bad": bad_payload,
        "ps3": ps3_payload,
        "astigmatic_disparity": _plain(astigmatic_disparity),
        "tissue_safety": _plain(assessment.get("procedural_safety") or {}),
        "planning": _plain(planning),
        "microkeratome_planning": _plain(microkeratome_planning),
        "source_values": source_values,
        "source_provenance": source_provenance,
        "procedure_display": {
            "flap": "N/A" if procedure == "PRK" else None,
        },
        "manual_corrections": corrections,
        "decision_drivers": _driver_payload(assessment.get("final_disposition")),
        "versions": {
            "software": software_version,
            "clinical_policy": clinical_policy_version,
            "source_registry": source_registry_version,
            "srax_algorithm": srax_algorithm_version,
        },
    }
