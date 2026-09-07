"""Canonical report projection for CER-AI.

This module is presentation-only. It consumes an already-computed clinical-core
result and copies structured values into a report payload. It performs no
clinical calculation, scoring, threshold comparison, or disposition logic.
PDF and DOCX renderers must consume this same payload.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping


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
    planning: Any = None,
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
        }

    bad_payload = {
        "final_d": getattr(bad_result, "final_d", None),
        "classification": bad_block.get("classification"),
        "status": bad_block.get("status"),
        "context": _plain(getattr(bad_result, "context", {})),
    }

    corrections = []
    for item in manual_corrections:
        plain = _plain(item)
        if isinstance(plain, dict):
            plain = {**plain, "label": "SURGEON_CONFIRMED"}
        corrections.append(plain)

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
        "tissue_safety": _plain(assessment.get("procedural_safety") or {}),
        "planning": _plain(planning),
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
