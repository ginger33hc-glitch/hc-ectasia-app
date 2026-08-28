"""HC final-decision hierarchy.

Secondary non-hard-stop findings must not over-escalate an otherwise acceptable case.
PASS WITH CAUTION is permitted only when Final BAD-D is not ABNORMAL and the
Randleman/ERSS total is <3, with no independent hard stop and no decision-critical
missing/unresolved data. Existing hard stops and data-insufficiency gates always win.
"""
import bootstrap

core = bootstrap.core
_previous_assess_eye = core.assess_eye


def _has_decision_blocker(result):
    if result.get("hard_stops"):
        return True
    if result.get("missing"):
        return True
    if result.get("data_conflicts"):
        return True
    status = str(result.get("status") or "").upper()
    return status in {"DO NOT PROCEED", "FAIL", "NOT ASSESSED", "DATA INSUFFICIENT"}


def assess_eye_with_hc_final_hierarchy(eye, plan, age, patient_modifiers):
    result = _previous_assess_eye(eye, plan, age, patient_modifiers)
    if _has_decision_blocker(result):
        return result

    bad_d = eye.get("BAD_D")
    if not core.is_number(bad_d):
        return result
    bad_class = core.bad_classification(float(bad_d), final=True)

    erss = result.get("randleman_erss") or {}
    erss_total = erss.get("total")
    if not core.is_number(erss_total):
        score = result.get("score") or {}
        erss_total = score.get("total")
    if not core.is_number(erss_total):
        return result

    if bad_class != "ABNORMAL" and float(erss_total) < 3.0:
        result["status"] = "PASS WITH CAUTION"
        result["action"] = (
            "PASS WITH CAUTION: Final BAD-D is not abnormal and Randleman/ERSS is <3. "
            "Review the listed secondary findings clinically; they do not independently convert this case to CAUTION/DEFER."
        )
        result["hc_final_decision_basis"] = {
            "rule": "FINAL_BAD_D_NOT_ABNORMAL_AND_RANDLEMAN_LT_3",
            "final_BAD_D": float(bad_d),
            "final_BAD_D_class": bad_class,
            "randleman_erss_total": float(erss_total),
        }
    return result


core.assess_eye = assess_eye_with_hc_final_hierarchy
core._hc_final_decision_policy_installed = True
