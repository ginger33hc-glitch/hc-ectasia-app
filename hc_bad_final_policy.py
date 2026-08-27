"""HC policy: Final BAD-D is the decision-making BAD gate.

Individual Df/Db/Dp/Dt/Da values remain displayed for clinical context, but an
isolated suspicious/abnormal component does not determine the HC BAD status.
Final BAD-D:
- <=1.6: NORMAL
- >1.6 and <3.0: SUSPICIOUS -> REVIEW / NOT CLEARED
- >=3.0: ABNORMAL CORNEA -> DO NOT PROCEED hard stop
"""
import bootstrap

core = bootstrap.core
_original_assess_eye = core.assess_eye


def final_bad_status(eye):
    return core.bad_classification(eye.get("BAD_D"), final=True)


def hc_tomography_review(eye):
    bad = {"BAD_D": final_bad_status(eye)}
    for key in ("Df", "Db", "Dp", "Dt", "Da"):
        bad[key] = core.bad_classification(eye.get(key))

    flags = []
    if core.is_number(eye.get("ARTmax_um")) and eye["ARTmax_um"] <= 424:
        flags.append("ARTmax <=424 µm: cross-sectional subclinical-KC concern flag.")
    if core.is_number(eye.get("pachy_thinnest_um")) and eye["pachy_thinnest_um"] <= 544:
        flags.append("Thinnest pachymetry <=544 µm: cross-sectional phenotype flag, not an exclusion cutoff.")
    if core.is_number(eye.get("Dt")) and eye["Dt"] >= -0.165:
        flags.append("BAD-Dt >=-0.165: cross-sectional subclinical-KC concern flag.")
    if core.is_number(eye.get("Da")) and eye["Da"] >= 0.585:
        flags.append("BAD-Da >=0.585: cross-sectional subclinical-KC concern flag.")

    final_status = bad["BAD_D"]
    map_patterns = (eye.get("anterior_pattern"), eye.get("posterior_pattern"))
    if final_status == "ABNORMAL" or "ABNORMAL" in map_patterns:
        status = "ABNORMAL"
    elif final_status == "SUSPICIOUS" or "BORDERLINE" in map_patterns:
        status = "SUSPICIOUS"
    elif final_status == "UNAVAILABLE" or "UNREADABLE" in map_patterns:
        status = "INCOMPLETE"
    elif flags:
        status = "CONCERN FLAGS"
    else:
        status = "REASSURING"

    return {
        "status": status,
        "BAD_display": bad,
        "cross_sectional_flags": flags,
        "evidence_note": (
            "HC BAD policy: Final BAD-D determines the BAD decision gate. Individual Df/Db/Dp/Dt/Da "
            "remain contextual findings and do not independently determine BAD clearance."
        ),
    }


core.tomography_review = hc_tomography_review


def assess_eye_with_final_bad_cutoff(eye, plan, age, patient_modifiers):
    result = _original_assess_eye(eye, plan, age, patient_modifiers)
    bad_d_status = final_bad_status(eye)
    result["final_bad_d_interpretation"] = bad_d_status
    if bad_d_status == "ABNORMAL":
        hard_stop = "HC operational hard stop: Final BAD-D abnormal (>=3.0); cornea classified ABNORMAL by the HC BAD-D gate."
        hard_stops = result.setdefault("hard_stops", [])
        reasons = result.setdefault("reasons", [])
        if hard_stop not in hard_stops:
            hard_stops.append(hard_stop)
        if hard_stop not in reasons:
            reasons.append(hard_stop)
        result["status"] = "DO NOT PROCEED"
        result["action"] = "DO NOT PROCEED — ABNORMAL CORNEA. Final BAD-D is >=3.0 and meets the HC abnormal cutoff."
    elif bad_d_status == "SUSPICIOUS" and result.get("status") == "PASS":
        result["status"] = "REVIEW — NOT CLEARED"
        result["action"] = "NOT CLEARED. Final BAD-D is suspicious; confirm/review tomography before any surgical decision."
        reason = "HC BAD gate: Final BAD-D suspicious (>1.6 and <3.0)."
        if reason not in result.setdefault("reasons", []):
            result["reasons"].append(reason)
    return result


core.assess_eye = assess_eye_with_final_bad_cutoff
bootstrap.assess_eye = assess_eye_with_final_bad_cutoff
app = bootstrap.app
