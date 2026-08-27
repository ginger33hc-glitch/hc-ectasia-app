"""HC LASIK automatic planning fallback.

Plan A (default): flap 100 µm, optical zone 6.5 mm, transition zone 9.0 mm.
If Plan A fails OR LASIK PTA is >=40%, and there is no independent HC hard-stop, re-evaluate with
Plan B: flap 100 µm, optical zone 6.0 mm, transition zone 8.5 mm.
If Plan B also fails or has PTA >=40%, re-evaluate with Plan C: flap 90 µm, optical zone
6.0 mm, transition zone 8.5 mm. If Plan C PTA remains >=40%, the final disposition is
DO NOT PROCEED.

Earlier failed plans remain visible in the final result. A favorable fallback plan never erases
or hides the fact that a preceding plan failed. Independent hard-stops are never bypassed by
changing flap/zone parameters.
"""
from copy import deepcopy
from typing import Any, Dict, List

LASIK_PTA_CUTOFF_PERCENT = 40.0
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
    return any(any(marker in str(stop) for marker in _INDEPENDENT_HARD_STOP_MARKERS) for stop in hard_stops)


def _pta_cutoff(result: Dict[str, Any]) -> bool:
    pta = (result.get("values") or {}).get("LASIK_PTA_percent")
    return isinstance(pta, (int, float)) and not isinstance(pta, bool) and float(pta) >= LASIK_PTA_CUTOFF_PERCENT


def _plan_payload(base_plan: Dict[str, Any], plan_spec: Dict[str, Any], first: bool) -> Dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["flap_um"] = plan_spec["flap_um"]
    plan["optical_zone_mm"] = plan_spec["optical_zone_mm"]
    plan["transition_zone_mm"] = plan_spec["transition_zone_mm"]
    plan["transition_zone_not_applicable"] = "no"
    if not first and plan.get("ablation_um") is not None:
        plan["ablation_um"] = None
    return plan


def _summary(plan_spec: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    values = result.get("values") or {}
    return {
        "plan": plan_spec["name"], "flap_um": plan_spec["flap_um"],
        "optical_zone_mm": plan_spec["optical_zone_mm"], "transition_zone_mm": plan_spec["transition_zone_mm"],
        "status": result.get("status"), "ablation_um": values.get("max_ablation_um", values.get("ablation_um")),
        "LASIK_RSB_um": values.get("LASIK_RSB_um"), "LASIK_PTA_percent": values.get("LASIK_PTA_percent"),
        "score_total": (result.get("score") or {}).get("total"), "score_category": (result.get("score") or {}).get("category"),
    }


def _sequence_lines(sequence: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for item in sequence:
        rsb, pta, ablation = item.get("LASIK_RSB_um"), item.get("LASIK_PTA_percent"), item.get("ablation_um")
        details = [f"flap {item['flap_um']:g} µm", f"optical zone {item['optical_zone_mm']:.1f} mm", f"transition zone {item['transition_zone_mm']:.1f} mm"]
        if isinstance(ablation, (int, float)): details.append(f"max ablation {ablation:.1f} µm")
        if isinstance(rsb, (int, float)): details.append(f"RSB {rsb:.1f} µm")
        if isinstance(pta, (int, float)): details.append(f"PTA {pta:.1f}%")
        lines.append(f"LASIK {item['plan']}: {item.get('status') or 'UNKNOWN'} — " + ", ".join(details) + ".")
    return lines


def install(core: Any) -> None:
    if getattr(core, "_hc_lasik_fallback_installed", False): return
    original_assess_eye = core.assess_eye

    def assess_eye_with_fallback(eye: Dict[str, Any], plan: Dict[str, Any], age: Any, patient_modifiers: Dict[str, Any]) -> Dict[str, Any]:
        if str(plan.get("procedure") or "").upper() != "LASIK": return original_assess_eye(eye, plan, age, patient_modifiers)
        sequence, evaluated = [], []
        for idx, spec in enumerate(LASIK_PLANS):
            planned = _plan_payload(plan, spec, first=(idx == 0))
            result = original_assess_eye(eye, planned, age, patient_modifiers)
            evaluated.append(result); sequence.append(_summary(spec, result))
            pta_fail = _pta_cutoff(result)
            ordinary_fail = result.get("status") == "DO NOT PROCEED"
            if not ordinary_fail and not pta_fail: break
            if _independent_hard_stop(result): break
            if idx == len(LASIK_PLANS) - 1: break

        final_result = deepcopy(evaluated[-1])
        final_pta_fail = _pta_cutoff(final_result)
        if final_pta_fail:
            final_result["status"] = "DO NOT PROCEED"
            final_result["action"] = "DO NOT PROCEED with elective corneal refractive surgery."
            hard_stops = list(final_result.get("hard_stops") or [])
            hard_stops.append("HC operational LASIK PTA hard stop: PTA >=40.0%.")
            final_result["hard_stops"] = list(dict.fromkeys(hard_stops))
            reasons = list(final_result.get("reasons") or [])
            reasons.append("LASIK PTA is >=40.0%; tissue-load cutoff reached. If this persists through Plan C, operation is cancelled.")
            final_result["reasons"] = list(dict.fromkeys(reasons))

        final_result["lasik_planning_sequence"] = sequence
        final_result["lasik_selected_plan"] = sequence[-1]["plan"]
        flags = list(final_result.get("surgical_load_flags") or []) + _sequence_lines(sequence)
        if len(sequence) > 1:
            flags.append(f"Final LASIK disposition is based on {sequence[-1]['plan']}, an automatic fallback/reduced-tissue plan; preceding failed plan(s) remain documented above.")
        if final_pta_fail:
            flags.append("LASIK PTA cutoff reached: PTA >=40.0%. Plan C did not reduce PTA below 40%; operation cancelled.")
        final_result["surgical_load_flags"] = list(dict.fromkeys(flags))
        values = dict(final_result.get("values") or {})
        values.update({"LASIK_selected_plan": sequence[-1]["plan"], "LASIK_flap_um": sequence[-1]["flap_um"], "optical_zone_mm": sequence[-1]["optical_zone_mm"], "transition_zone_mm": sequence[-1]["transition_zone_mm"]})
        final_result["values"] = values
        warnings = list(final_result.get("warnings") or [])
        if len(sequence) > 1: warnings.append("Automatic LASIK fallback planning was activated because the preceding plan failed or reached the HC PTA cutoff (>=40.0%). A fallback result does not erase the earlier configuration.")
        final_result["warnings"] = list(dict.fromkeys(warnings))
        return final_result

    core.assess_eye = assess_eye_with_fallback
    core._hc_lasik_fallback_installed = True
