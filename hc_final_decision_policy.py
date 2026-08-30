"""Canonical CER-AI final decision hierarchy.

CER-AI policy:
- Independent hard stops always prevail.
- Missing/unresolved decision-critical data can never be promoted to clearance.
- Final BAD-D ABNORMAL (>=3.0) remains a hard stop.
- Randleman/ERSS total >=3 remains an adverse/defer pathway.
- Otherwise, when Final BAD-D is available and not ABNORMAL and Randleman is complete
  with total <3, secondary/contextual findings may generate warnings but the final
  classification is PASS WITH CAUTION.

This policy intentionally prevents isolated secondary tomography/topometric concern
flags from escalating an otherwise non-abnormal Final BAD-D + ERSS<3 case to defer.
"""
import bootstrap
import randleman_bad_independence  # ensure BAD-independent ERSS is installed first

core = bootstrap.core
_previous_assess_eye = core.assess_eye

_ADVERSE_STATUSES = {"DO NOT PROCEED", "FAIL"}


def _decision_critical_incomplete(result):
    if result.get("missing"):
        return True
    # Preserve explicit data-insufficiency states produced by upstream safety logic.
    status = str(result.get("status") or "").upper()
    return "DATA INSUFFICIENT" in status or "NOT ASSESSED" in status


def assess_eye_with_hc_final_hierarchy(eye, plan, age, patient_modifiers):
    result = _previous_assess_eye(eye, plan, age, patient_modifiers)

    # Never override any independent hard stop or explicit upstream FAIL.
    if result.get("hard_stops") or str(result.get("status") or "").upper() in _ADVERSE_STATUSES:
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
        stop = "CER-AI operational hard stop: Final BAD-D abnormal (>=3.0); cornea classified ABNORMAL by the CER-AI BAD-D gate."
        if stop not in result.setdefault("hard_stops", []):
            result["hard_stops"].append(stop)
        if stop not in result.setdefault("reasons", []):
            result["reasons"].append(stop)
        result["status"] = "DO NOT PROCEED"
        result["action"] = "DO NOT PROCEED — ABNORMAL CORNEA. Final BAD-D is >=3.0 and meets the CER-AI abnormal cutoff."
        return result

    if float(erss_total) >= 3:
        # Do not weaken the existing ERSS adverse pathway. If an upstream layer happened
        # to leave PASS, enforce the CER-AI threshold explicitly.
        if str(result.get("status") or "").upper() in {"PASS", "PASS WITH CAUTION"}:
            result["status"] = "CAUTION — DEFER"
            result["action"] = "DEFER / NOT CLEARED. Randleman/ERSS score is 3 or greater."
        reason = f"CER-AI final hierarchy: Randleman/ERSS total {float(erss_total):g} is >=3."
        if reason not in result.setdefault("reasons", []):
            result["reasons"].append(reason)
        return result

    # New governing rule: Final BAD-D not abnormal + complete ERSS <3 = PASS WITH CAUTION.
    # Secondary findings remain visible as warnings/reasons but cannot independently
    # escalate the final classification to defer.
    result["status"] = "PASS WITH CAUTION"
    result["action"] = (
        "PASS WITH CAUTION — Final BAD-D is not abnormal and Randleman/ERSS is <3. "
        "Review all displayed secondary/contextual findings and apply surgeon judgment."
    )
    result["hc_final_decision_hierarchy"] = {
        "final_BAD_D_status": bad_status,
        "randleman_erss_total": float(erss_total),
        "rule": "FINAL_BAD_D_NOT_ABNORMAL_AND_ERSS_LT_3_PASS_WITH_CAUTION",
    }
    return result


core.assess_eye = assess_eye_with_hc_final_hierarchy
core._hc_final_decision_hierarchy_installed = True
