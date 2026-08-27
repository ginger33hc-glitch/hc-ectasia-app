"""HC LASIK automatic planning fallback.

Plan A (default): flap 100 µm, optical zone 6.5 mm, transition zone 9.0 mm.
If Plan A is DO NOT PROCEED and there is no independent HC hard-stop, re-evaluate with
Plan B: flap 100 µm, optical zone 6.0 mm, transition zone 8.5 mm.
If Plan B is also DO NOT PROCEED, re-evaluate with Plan C: flap 90 µm, optical zone
6.0 mm, transition zone 8.5 mm.

Earlier failed plans remain visible in the final result. A favorable fallback plan never erases
or hides the fact that a preceding plan failed. Independent hard-stops are never bypassed by
changing flap/zone parameters.
"""
from copy import deepcopy
from typing import Any, Dict, List

LASIK_PLANS = (
    {"name": "Plan A", "flap_um": 100.0, "optical_zone_mm": 6.5, "transition_zone_mm": 9.0},
    {"name": "Plan B", "flap_um": 100.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
    {"name": "Plan C", "flap_um": 90.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
)

_INDEPENDENT_HARD_STOP_MARKERS = (
    "thinnest preoperative cornea <480",
    "Definite KC/FFKC/PMD",
    "intended sphere <−10.00",
    "intended sphere >+6.00",
    "postoperative Kmean <36.00",
    "postoperative Kmean >48.00",
)


def _independent_hard_stop(result: Dict[str, Any]) -> bool:
    hard_stops = result.get("hard_stops") or []
    return any(
        any(marker in str(stop) for marker in _INDEPENDENT_HARD_STOP_MARKERS)
        for stop in hard_stops
    )


def _plan_payload(base_plan: Dict[str, Any], plan_spec: Dict[str, Any], first: bool) -> Dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["flap_um"] = plan_spec["flap_um"]
    plan["optical_zone_mm"] = plan_spec["optical_zone_mm"]
    plan["transition_zone_mm"] = plan_spec["transition_zone_mm"]
    plan["transition_zone_not_applicable"] = "no"

    # An actual laser-plan ablation entered for Plan A belongs to that exact optical-zone plan.
    # It must not be silently reused for a different optical zone. For fallback plans the core
    # engine may calculate its documented EX500 estimate; if it cannot, the result remains
    # DATA INSUFFICIENT rather than inventing an ablation depth.
    if not first and plan.get("ablation_um") is not None:
        plan["ablation_um"] = None
    return plan


def _summary(plan_spec: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    values = result.get("values") or {}
    return {
        "plan": plan_spec["name"],
        "flap_um": plan_spec["flap_um"],
        "optical_zone_mm": plan_spec["optical_zone_mm"],
        "transition_zone_mm": plan_spec["transition_zone_mm"],
        "status": result.get("status"),
        "ablation_um": values.get("ablation_um"),
        "LASIK_RSB_um": values.get("LASIK_RSB_um"),
        "LASIK_PTA_percent": values.get("LASIK_PTA_percent"),
        "score_total": (result.get("score") or {}).get("total"),
        "score_category": (result.get("score") or {}).get("category"),
    }


def _sequence_lines(sequence: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for item in sequence:
        rsb = item.get("LASIK_RSB_um")
        ablation = item.get("ablation_um")
        details = [
            f"flap {item['flap_um']:g} µm",
            f"optical zone {item['optical_zone_mm']:.1f} mm",
            f"transition zone {item['transition_zone_mm']:.1f} mm",
        ]
        if isinstance(ablation, (int, float)):
            details.append(f"max ablation {ablation:.1f} µm")
        if isinstance(rsb, (int, float)):
            details.append(f"RSB {rsb:.1f} µm")
        lines.append(f"LASIK {item['plan']}: {item.get('status') or 'UNKNOWN'} — " + ", ".join(details) + ".")
    return lines


def install(core: Any) -> None:
    """Patch the app's eye assessor once, preserving all existing HC engine behavior."""
    if getattr(core, "_hc_lasik_fallback_installed", False):
        return

    original_assess_eye = core.assess_eye

    def assess_eye_with_fallback(
        eye: Dict[str, Any],
        plan: Dict[str, Any],
        age: Any,
        patient_modifiers: Dict[str, Any],
    ) -> Dict[str, Any]:
        if str(plan.get("procedure") or "").upper() != "LASIK":
            return original_assess_eye(eye, plan, age, patient_modifiers)

        sequence: List[Dict[str, Any]] = []
        evaluated: List[Dict[str, Any]] = []

        for idx, spec in enumerate(LASIK_PLANS):
            planned = _plan_payload(plan, spec, first=(idx == 0))
            result = original_assess_eye(eye, planned, age, patient_modifiers)
            evaluated.append(result)
            sequence.append(_summary(spec, result))

            # Only a FAIL/DO NOT PROCEED triggers the next fallback plan.
            if result.get("status") != "DO NOT PROCEED":
                break

            # A flap/zone change must never bypass an independent HC hard-stop.
            if _independent_hard_stop(result):
                break

        final_result = deepcopy(evaluated[-1])
        final_result["lasik_planning_sequence"] = sequence
        final_result["lasik_selected_plan"] = sequence[-1]["plan"]

        sequence_lines = _sequence_lines(sequence)
        flags = list(final_result.get("surgical_load_flags") or [])
        flags.extend(sequence_lines)
        if len(sequence) > 1:
            flags.append(
                f"Final LASIK disposition is based on {sequence[-1]['plan']}, an automatic fallback/reduced-tissue plan; "
                "preceding failed plan(s) remain documented above."
            )
        final_result["surgical_load_flags"] = list(dict.fromkeys(flags))

        values = dict(final_result.get("values") or {})
        values.update({
            "LASIK_selected_plan": sequence[-1]["plan"],
            "LASIK_flap_um": sequence[-1]["flap_um"],
            "optical_zone_mm": sequence[-1]["optical_zone_mm"],
            "transition_zone_mm": sequence[-1]["transition_zone_mm"],
        })
        final_result["values"] = values

        warnings = list(final_result.get("warnings") or [])
        if len(sequence) > 1:
            warnings.append(
                "Automatic LASIK fallback planning was activated because the preceding plan was DO NOT PROCEED. "
                "A fallback result does not erase the earlier failed configuration."
            )
        final_result["warnings"] = list(dict.fromkeys(warnings))
        return final_result

    core.assess_eye = assess_eye_with_fallback
    core._hc_lasik_fallback_installed = True
