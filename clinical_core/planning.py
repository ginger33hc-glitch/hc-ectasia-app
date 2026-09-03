"""Pure CER-AI LASIK fallback-planning primitives.

This module contains no runtime installation, FastAPI access, reporting, or
persistence. It mirrors the frozen launch behavior of lasik_planning.py so the
future orchestrator can call explicit functions instead of wrapper layers.
"""
from copy import deepcopy
from typing import Any, Dict

LASIK_PTA_CUTOFF_PERCENT = 40.0
LASIK_PLANS = (
    {"name": "Plan A", "flap_um": 100.0, "optical_zone_mm": 6.5, "transition_zone_mm": 9.0},
    {"name": "Plan B", "flap_um": 100.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
    {"name": "Plan C", "flap_um": 90.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
)

INDEPENDENT_HARD_STOP_MARKERS = (
    "thinnest preoperative cornea <480",
    "Definite KC/FFKC/PMD",
    "intended sphere <−10.00",
    "intended sphere >+6.00",
    "postoperative Kmean <36.00",
    "postoperative Kmean >48.00",
)


def pta_cutoff(result: Dict[str, Any]) -> bool:
    pta = (result.get("values") or {}).get("LASIK_PTA_percent")
    return isinstance(pta, (int, float)) and not isinstance(pta, bool) and float(pta) >= LASIK_PTA_CUTOFF_PERCENT


def independent_hard_stop(result: Dict[str, Any]) -> bool:
    hard_stops = result.get("hard_stops") or []
    return any(
        any(marker in str(stop) for marker in INDEPENDENT_HARD_STOP_MARKERS)
        for stop in hard_stops
    )


def plan_responsive_failure(result: Dict[str, Any]) -> bool:
    """Return only failures that flap/zone fallback may plausibly resolve."""
    if result.get("hard_stops"):
        return True
    return (result.get("score") or {}).get("category") == "HIGH"


def plan_payload(base_plan: Dict[str, Any], plan_spec: Dict[str, Any], first: bool) -> Dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["flap_um"] = plan_spec["flap_um"]
    plan["optical_zone_mm"] = plan_spec["optical_zone_mm"]
    plan["transition_zone_mm"] = plan_spec["transition_zone_mm"]
    plan["transition_zone_not_applicable"] = "no"
    if not first and plan.get("ablation_um") is not None:
        plan["ablation_um"] = None
    return plan


def planning_summary(plan_spec: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    values = result.get("values") or {}
    return {
        "plan": plan_spec["name"],
        "flap_um": plan_spec["flap_um"],
        "optical_zone_mm": plan_spec["optical_zone_mm"],
        "transition_zone_mm": plan_spec["transition_zone_mm"],
        "status": result.get("status"),
        "ablation_um": values.get("max_ablation_um", values.get("ablation_um")),
        "LASIK_RSB_um": values.get("LASIK_RSB_um"),
        "LASIK_PTA_percent": values.get("LASIK_PTA_percent"),
        "score_total": (result.get("score") or {}).get("total"),
        "score_category": (result.get("score") or {}).get("category"),
    }
