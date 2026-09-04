"""Canonical CER-AI final hierarchy using PASS / CAUTION / STOP-DEFER."""
import bootstrap
from clinical_disposition import CAUTION, PASS, STATUS_RANK, STOP_DEFER

core = bootstrap.core
_previous_assess_eye = core.assess_eye

def _decision_critical_incomplete(result):
    if result.get("missing"): return True
    status=str(result.get("status") or "").upper()
    return "DATA INSUFFICIENT" in status or "NOT ASSESSED" in status

def _apply_locked_i_s_normal_band(eye):
    working=dict(eye);i_s=working.get("I_S");verified="I_S" in set(working.get("table_verified_numeric_fields") or []);surgeon_confirmed=working.get("I_S_status")=="SURGEON_CONFIRMED"
    if core.is_number(i_s) and (verified or surgeon_confirmed) and -.50<=float(i_s)<=.50:
        working["morphology"]="NORMAL_SYMMETRIC";working["asymmetric_bow_tie"]="NO";working["srax"]="NO";working["srax_deg"]=None;working["inferior_opposite_steepening_D"]=None
        evidence=list(working.get("morphology_evidence") or []);evidence.append(f"CER-AI signed I-S rule: labeled/confirmed I-S {float(i_s):+.2f} D is within -0.50 to +0.50 D; topography scoring category NORMAL_SYMMETRIC.");working["morphology_evidence"]=list(dict.fromkeys(evidence))
    return working

def _prk_caution_was_auto_deferred(result):
    values=result.get("values") or {};score=result.get("score") or {}
    return str(values.get("procedure") or "").upper()=="PRK" and score.get("category")=="CAUTION" and not result.get("hard_stops")

def assess_eye_with_hc_final_hierarchy(eye,plan,age,patient_modifiers):
    eye=_apply_locked_i_s_normal_band(eye);result=_previous_assess_eye(eye,plan,age,patient_modifiers)
    # This is a routing disposition, not a virgin-cornea risk category. It must escape
    # untouched before BAD-D/ERSS/PRK final-hierarchy logic can convert it to PASS/CAUTION.
    if result.get("status")=="POST-REFRACTIVE PATHWAY REQUIRED":
        return result
    if result.get("status") not in STATUS_RANK:raise ValueError(f"Non-canonical CER-AI disposition escaped the clinical engine: {result.get('status')!r}")
    if _prk_caution_was_auto_deferred(result):
        result["status"]=CAUTION;result["action"]="CAUTION — surgeon review is required; this category does not automatically defer surgery.";result["reasons"]=[r for r in result.get("reasons",[]) if "PRK-EWSS v1.0 provisional caution category" not in str(r)];reason="CER-AI final hierarchy: PRK-EWSS provisional CAUTION does not automatically defer surgery."
        if reason not in result.setdefault("reasons",[]):result["reasons"].append(reason)
    if result.get("hard_stops") or result.get("status")==STOP_DEFER:
        result["status"]=STOP_DEFER;result["action"]="STOP-DEFER; do not proceed unless the stated stop/defer condition is resolved.";return result
    if _decision_critical_incomplete(result):return result
    bad_status=core.bad_classification(eye.get("BAD_D"),final=True);erss=result.get("randleman_erss") or {};erss_total=erss.get("total")
    if str((result.get("values") or {}).get("procedure") or "").upper()=="PRK":
        result["status"]=CAUTION if result.get("status")==CAUTION else PASS;return result
    if bad_status in {"UNAVAILABLE","UNREADABLE",None} or not core.is_number(erss_total):return result
    if bad_status=="ABNORMAL":
        stop="CER-AI operational hard stop: Final BAD-D abnormal (>=2.60); cornea classified ABNORMAL by the CER-AI BAD-D gate."
        if stop not in result.setdefault("hard_stops",[]):result["hard_stops"].append(stop)
        if stop not in result.setdefault("reasons",[]):result["reasons"].append(stop)
        result["status"]=STOP_DEFER;result["action"]="STOP-DEFER — ABNORMAL CORNEA. Final BAD-D is >=2.60 and meets the CER-AI abnormal cutoff.";return result
    if float(erss_total)>=4:
        result["status"]=STOP_DEFER;result["action"]="STOP-DEFER. Randleman/ERSS score is 4 or greater.";reason=f"CER-AI final hierarchy: Randleman/ERSS total {float(erss_total):g} is >=4."
        if reason not in result.setdefault("reasons",[]):result["reasons"].append(reason)
        if reason not in result.setdefault("hard_stops",[]):result["hard_stops"].append(reason)
        return result
    if float(erss_total)==3:
        result["status"]=core.combine_status(result["status"],CAUTION);result["action"]="CAUTION — surgeon review is required; Randleman/ERSS score is 3.";return result
    result["status"]=core.combine_status(result["status"],PASS);return result

core.assess_eye=assess_eye_with_hc_final_hierarchy
core._hc_final_decision_hierarchy_installed=True
