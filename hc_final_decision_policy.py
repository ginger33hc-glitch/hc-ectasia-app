"""Canonical CER-AI final hierarchy using PASS / CAUTION / STOP-DEFER."""
import bootstrap
from clinical_disposition import CAUTION, PASS, STATUS_RANK, STOP_DEFER

core = bootstrap.core
_previous_assess_eye = core.assess_eye

def _decision_critical_incomplete(result):
    if result.get("missing"):
        return True
    # Preserve explicit data-insufficiency states produced by upstream safety logic.
    status = str(result.get("status") or "").upper()
    return "DATA INSUFFICIENT" in status or "NOT ASSESSED" in status


def assess_eye_with_hc_final_hierarchy(eye, plan, age, patient_modifiers):
    result = _previous_assess_eye(eye, plan, age, patient_modifiers)

    if result.get("status") not in STATUS_RANK:
        raise ValueError(f"Non-canonical CER-AI disposition escaped the clinical engine: {result.get('status')!r}")

    if result.get("hard_stops") or result.get("status") == STOP_DEFER:
        result["status"] = STOP_DEFER
        result["action"] = "STOP-DEFER; do not proceed unless the stated stop/defer condition is resolved."
        return result
    if _decision_critical_incomplete(result):
        return result

    bad_status = core.bad_classification(eye.get("BAD_D"), final=True)
    erss = result.get("randleman_erss") or {}
    erss_total = erss.get("total")

    # The hierarchy requires both principal pathways to be actually available.
    if bad_status in {"UNAVAILABLE", "UNREADABLE", None} or not core.is_number(erss_total):
        return result

    if bad_status == "ABNORMAL":
        # Normally enforced upstream; retain a defensive guard here.
        stop = "CER-AI operational hard stop: Final BAD-D abnormal (>=2.60); cornea classified ABNORMAL by the CER-AI BAD-D gate."
        if stop not in result.setdefault("hard_stops", []):
            result["hard_stops"].append(stop)
        if stop not in result.setdefault("reasons", []):
            result["reasons"].append(stop)
        result["status"] = STOP_DEFER
        result["action"] = "STOP-DEFER — ABNORMAL CORNEA. Final BAD-D is >=2.60 and meets the CER-AI abnormal cutoff."
        return result

    if float(erss_total) >= 3:
        # Do not weaken the existing ERSS adverse pathway. If an upstream layer happened
        # to leave PASS, enforce the CER-AI threshold explicitly.
        result["status"] = STOP_DEFER
        result["action"] = "STOP-DEFER. Randleman/ERSS score is 3 or greater."
        reason = f"CER-AI final hierarchy: Randleman/ERSS total {float(erss_total):g} is >=3."
        if reason not in result.setdefault("reasons", []):
            result["reasons"].append(reason)
        return result

    # Preserve a truly reassuring upstream PASS. Contextual review findings become
    # CAUTION without an automatic defer instruction.
    result["status"] = CAUTION if result.get("status") == CAUTION else PASS
    result["action"] = (
        "CAUTION — surgeon review is required; this category does not automatically defer surgery."
        if result["status"] == CAUTION
        else "CER-AI assessment PASS; this is not a guarantee of zero ectasia risk."
    )
    result["hc_final_decision_hierarchy"] = {
        "final_BAD_D_status": bad_status,
        "randleman_erss_total": float(erss_total),
        "rule": "FINAL_BAD_D_NOT_ABNORMAL_AND_ERSS_LT_3_PRESERVE_PASS_OR_CAUTION",
    }
    return result


core.assess_eye = assess_eye_with_hc_final_hierarchy
core._hc_final_decision_hierarchy_installed = True
