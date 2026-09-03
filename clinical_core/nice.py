"""Pure CER-AI NICE scoring and disposition rules.

This module mirrors the launch-frozen NICE behavior without importing the
application runtime. It is intentionally side-effect-free so it can be tested
against production before any wiring change.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def score_nice(k2_d, central_pachy_um, b_ele_th_um, i_s_d) -> dict[str, Any]:
    values = {
        "K2_D": k2_d,
        "central_pachy_um": central_pachy_um,
        "B_Ele_Th_um": b_ele_th_um,
        "I_S_D": i_s_d,
    }
    missing = [key for key, value in values.items() if not _finite(value)]

    if _finite(k2_d) and not 20 <= float(k2_d) <= 80:
        missing.append("K2_D")
    if _finite(central_pachy_um) and not 300 <= float(central_pachy_um) <= 800:
        missing.append("central_pachy_um")
    if _finite(b_ele_th_um) and not -300 <= float(b_ele_th_um) <= 300:
        missing.append("B_Ele_Th_um")

    if missing:
        return {
            "total": None,
            "category": "INCOMPLETE",
            "rows": {},
            "values": values,
            "missing": sorted(set(missing)),
        }

    rows = {
        "K2": 1 if k2_d < 45 else 2 if k2_d <= 47 else 3,
        "central_pachymetry": 1 if central_pachy_um > 520 else 2 if central_pachy_um >= 500 else 3,
        "B_Ele_Th": 1 if b_ele_th_um <= 15.5 else 2 if b_ele_th_um < 18 else 3,
        "I_S": 1 if i_s_d < 1 else 2 if i_s_d <= 1.4 else 3,
    }
    total = sum(rows.values())
    category = "NO_NICE_ESCALATION" if total == 4 else "CAUTION" if total <= 8 else "HARD_STOP"
    return {
        "total": total,
        "category": category,
        "rows": rows,
        "values": values,
        "missing": [],
    }


def nice_disposition(total) -> str:
    """Return the launch-frozen NICE-specific escalation only."""
    if not isinstance(total, int) or isinstance(total, bool):
        return "DATA INSUFFICIENT"
    if total >= 9:
        return "STOP-DEFER"
    if total >= 5:
        return "CAUTION"
    if total == 4:
        return "PASS"
    return "DATA INSUFFICIENT"
