"""Canonical post-assessment integration for ML7 microkeratome planning.

This wrapper runs after the complete HC ectasia decision and only appends a
surgeon-review planning record.  It never changes status, score, hard stops,
missing data, or the ectasia action.
"""
from typing import Any, Dict, Optional, Tuple

import bootstrap
from planning.microkeratome import MicrokeratomePlanningInput, plan_microkeratome


core = bootstrap.core
_previous_hc_engine = core.hc_engine


def _number(value: Any) -> Optional[float]:
    return float(value) if core.is_number(value) else None


def _keratometry(eye: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    k1, k2 = _number(eye.get("K1_D")), _number(eye.get("K2_D"))
    if k1 is None or k2 is None:
        return None, None, None
    if k2 > k1:
        return k2, k1, _number(eye.get("K2_axis_deg"))
    if k1 > k2:
        return k1, k2, _number(eye.get("K1_axis_deg"))
    return k1, k2, None


def _planning_record(result: Dict[str, Any], eye: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    values = result.get("values") or {}
    steep, flat, steep_axis = _keratometry(eye)
    pattern = str(values.get("intended_refractive_pattern") or "")
    hyperopic = pattern in {"HYPEROPIC", "SIMPLE_HYPEROPIC_ASTIGMATISM"}
    mixed = pattern == "MIXED_ASTIGMATISM"
    selected_flap = values.get("LASIK_flap_um")
    if not core.is_number(selected_flap):
        selected_flap = plan.get("flap_um")

    out = plan_microkeratome(MicrokeratomePlanningInput(
        assessment_status=result.get("status") or "",
        procedure=values.get("procedure") or plan.get("procedure") or "",
        steepest_k_d=steep,
        flattest_k_d=flat,
        steep_axis_deg=steep_axis,
        w2w_mm=_number(eye.get("corneal_diameter_mm")),
        pachy_um=_number(values.get("pachy_thinnest_um")),
        t_zone_mm=_number(values.get("transition_zone_mm")),
        hyperopic=hyperopic,
        mixed_cylinder=mixed,
        # Anatomical feasibility cannot be inferred from the uploaded maps.
        perpendicular_hinge_anatomically_possible=None,
        planned_flap_um=_number(selected_flap),
        max_ablation_um=_number(values.get("max_ablation_um")),
    )).as_dict()
    issues = list(eye.get("planning_data_issues") or [])
    if issues:
        out["warnings"] = list(dict.fromkeys(list(out.get("warnings") or []) + issues))
    out["status_independent"] = True
    return out


def hc_engine_with_microkeratome_planning(
    extracted: Dict[str, Any],
    age: Any,
    eye_plans: Dict[str, Any],
    patient_modifiers: Dict[str, Any],
    patient_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    decision = _previous_hc_engine(extracted, age, eye_plans, patient_modifiers, patient_metadata)
    source_by_eye = {
        eye.get("eye"): eye for eye in extracted.get("eyes", [])
        if isinstance(eye, dict) and eye.get("eye") in core.EYES
    }
    for result in decision.get("eyes", []):
        eye_id = result.get("eye")
        source = source_by_eye.get(eye_id, {})
        plan = eye_plans.get(eye_id, {}) if isinstance(eye_plans, dict) else {}
        planning = _planning_record(result, source, plan)
        if planning.get("applicable"):
            result["microkeratome_planning"] = planning
    return decision


core.hc_engine = hc_engine_with_microkeratome_planning
core._hc_microkeratome_planning_installed = True

