"""Phase 3 parity service for guarded CER-AI cutover.

The service compares a completed production eye result with the linear clinical
core result. It never mutates either result and never selects the linear path;
it only reports whether the compared clinical channels are equivalent.
"""
from __future__ import annotations

from typing import Any, Mapping


def _get(mapping: Mapping[str, Any] | None, *path: str):
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _selected_ps3(disposition: Mapping[str, Any] | None, procedure: str):
    if not isinstance(disposition, Mapping):
        return None
    return disposition.get(str(procedure or "").strip().lower())


def compare_eye_results(
    production: Mapping[str, Any],
    linear: Mapping[str, Any],
    *,
    procedure: str,
    compare_final_status: bool = True,
) -> dict[str, Any]:
    """Return an explicit channel-by-channel parity record."""
    procedure = str(procedure or "").strip().upper()
    production_values = production.get("values") or {}
    linear_safety = linear.get("procedural_safety") or {}

    checks = {
        "erss_total": (
            _get(production, "score", "total"),
            _get(linear, "erss", "total"),
        ),
        "bad_d_classification": (
            _get(production, "bad_summary", "category"),
            _get(linear, "bad_d", "classification"),
        ),
        "nice_total": (
            _get(production, "nice", "total"),
            _get(linear, "nice", "total"),
        ),
        "ps3_selected_disposition": (
            _selected_ps3(_get(production, "ps3", "disposition"), procedure),
            {
                "PASS": "ALLOWED",
                "STOP-DEFER": "DEFER",
            }.get(linear.get("ps3_status")),
        ),
    }

    if procedure == "LASIK":
        checks["LASIK_RSB_um"] = (
            production_values.get("LASIK_RSB_um"),
            linear_safety.get("LASIK_RSB_um"),
        )
        checks["LASIK_PTA_percent"] = (
            production_values.get("LASIK_PTA_percent"),
            linear_safety.get("LASIK_PTA_percent"),
        )
    elif procedure == "PRK":
        checks["PRK_RST_um"] = (
            production_values.get("PRK_RST_um"),
            linear_safety.get("PRK_RST_um"),
        )

    checks["estimated_final_Kmean_D"] = (
        production_values.get("estimated_final_Kmean_D", production_values.get("postop_Kmean_D")),
        linear_safety.get("estimated_final_Kmean_D"),
    )

    if compare_final_status:
        checks["final_status"] = (production.get("status"), linear.get("status"))

    details = {
        name: {
            "production": pair[0],
            "linear": pair[1],
            "match": pair[0] == pair[1],
        }
        for name, pair in checks.items()
    }
    mismatches = [name for name, detail in details.items() if not detail["match"]]
    return {
        "procedure": procedure,
        "checks": details,
        "mismatches": mismatches,
        "cutover_allowed": not mismatches,
    }
