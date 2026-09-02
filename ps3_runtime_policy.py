"""Production adapter for the independent PS3 policy.

PS3 remains a separate result channel. It never rewrites Randleman, BAD-D, or
NICE scores. It may only restrict the currently selected procedure according
to the PS3 decision matrix.
"""
from dataclasses import asdict

from ps3_policy import DEFER, PS3EyeInput, PS3InterEyeInput, evaluate_ps3


_previous_hc_engine = None
_installed_hc_engine = None
_runtime_core = None


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _first_number(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if _finite(value):
            return float(value)
    return None


def _manifest_axis(plan):
    return _first_number(
        plan,
        "manifest_axis_deg",
        "manifest_cylinder_axis_deg",
        "entered_axis_deg",
        "cylinder_axis_deg",
        "axis_deg",
    )


def _manifest_astig(plan):
    magnitude = _first_number(plan, "manifest_cylinder_magnitude_D")
    if magnitude is not None:
        return abs(magnitude)
    signed = _first_number(plan, "manifest_cylinder_signed_D")
    return abs(signed) if signed is not None else None


def _refractive_group(plan):
    explicit = str(plan.get("ps3_refractive_group") or "").upper()
    if explicit in {"MYOPIC_EMMETROPIC", "HYPEROPIC_MIXED"}:
        return explicit
    return None


def _inter_eye(source):
    if set(source) != {"OD", "OS"}:
        return None
    od, os = source["OD"], source["OS"]
    return PS3InterEyeInput(
        od_anterior_km_d=od.get("Kmean_D"),
        os_anterior_km_d=os.get("Kmean_D"),
        od_posterior_km_d=od.get("posterior_Kmean_D"),
        os_posterior_km_d=os.get("posterior_Kmean_D"),
        od_thinnest_um=od.get("pachy_thinnest_um"),
        os_thinnest_um=os.get("pachy_thinnest_um"),
        od_front_elevation_thinnest_um=od.get("F_Ele_Th_um"),
        os_front_elevation_thinnest_um=os.get("F_Ele_Th_um"),
        od_back_elevation_thinnest_um=od.get("B_Ele_Th_um"),
        os_back_elevation_thinnest_um=os.get("B_Ele_Th_um"),
    )


def _eye_input(eye, plan):
    return PS3EyeInput(
        anterior_km_d=eye.get("Kmean_D"),
        thinnest_um=eye.get("pachy_thinnest_um"),
        topographic_astig_d=eye.get("topographic_astig_D"),
        topographic_steep_axis_deg=eye.get("topographic_steep_axis_deg"),
        manifest_astig_d=_manifest_astig(plan),
        manifest_axis_deg=_manifest_axis(plan),
        ppi_avg=eye.get("PPI_avg"),
        kmax_d=eye.get("Kmax_D"),
        i_s_d=eye.get("I_S"),
        kisa_percent=eye.get("KISA"),
        # Main BFS/BFTE PS3 elevation inputs intentionally remain unbound until
        # their distinct labeled boxes are mapped unambiguously. F.Ele.Th and
        # B.Ele.Th are used for the agreed inter-eye comparison only.
        refractive_group=_refractive_group(plan),
    )


def _selected_procedure_disposition(result, procedure):
    procedure = str(procedure or "").upper()
    if procedure == "PRK":
        return result.disposition.prk
    if procedure == "SMILE":
        return result.disposition.smile
    if procedure == "LASIK":
        return result.disposition.lasik
    return None


def _procedure_summary(result):
    return (
        f"PRK {result.disposition.prk}; SMILE {result.disposition.smile}; "
        f"LASIK {result.disposition.lasik}"
    )


def hc_engine_with_ps3(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
    if _previous_hc_engine is None or _runtime_core is None:
        raise RuntimeError("PS3 runtime adapter was not initialized")

    decision = _previous_hc_engine(extracted, age, eye_plans, patient_modifiers, patient_metadata)
    source = {
        item.get("eye"): item
        for item in extracted.get("eyes", [])
        if item.get("eye") in {"OD", "OS"}
    }
    bilateral = _inter_eye(source)

    for eye_result in decision.get("eyes", []):
        eye_name = eye_result.get("eye")
        eye = source.get(eye_name)
        plan = eye_plans.get(eye_name, {})
        if not eye or eye_result.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED" or plan.get("prior") != "no":
            eye_result["ps3"] = {
                "applicable": False,
                "reason": "PS3 virgin-cornea pathway not applicable.",
            }
            continue

        ps3 = evaluate_ps3(_eye_input(eye, plan), bilateral)
        payload = asdict(ps3)
        payload["applicable"] = True
        payload["derived_srax_label"] = "DERIVED SRAX — not directly reported by Pentacam"
        eye_result["ps3"] = payload

        eye_result.setdefault("reasons", []).append(
            f"PS3: {ps3.moderate_count} moderate, {ps3.high_count} high risk factor(s); "
            f"{_procedure_summary(ps3)}."
        )
        eye_result.setdefault("warnings", []).extend(
            f"PS3 surgeon review required: {note}" for note in ps3.review_notes
        )

        selected = _selected_procedure_disposition(ps3, plan.get("procedure"))
        if selected == DEFER:
            reason = (
                f"PS3 DEFER for selected {str(plan.get('procedure') or '').upper()}: "
                f"{ps3.moderate_count} moderate, {ps3.high_count} high risk factor(s)."
            )
            eye_result.setdefault("hard_stops", []).append(reason)
            eye_result.setdefault("reasons", []).append(reason)
            eye_result["status"] = _runtime_core.combine_status(eye_result["status"], "STOP-DEFER")
            eye_result["action"] = "STOP-DEFER — selected procedure is not allowed by PS3."

        decision["status"] = _runtime_core.combine_status(decision["status"], eye_result["status"])

    decision["ps3_method_note"] = (
        "PS3 is reported independently. Corneal Thickness Map morphology, Relative Thickness Map, "
        "and PTI/CTSP profile morphology are not automatically evaluated and require surgeon review."
    )
    return decision


def install(core):
    global _previous_hc_engine
    global _installed_hc_engine
    global _runtime_core

    if getattr(core, "_cerai_ps3_runtime_installed", False):
        return

    _runtime_core = core
    _previous_hc_engine = core.hc_engine
    _installed_hc_engine = hc_engine_with_ps3
    core.hc_engine = hc_engine_with_ps3
    core._cerai_ps3_runtime_installed = True
