"""Canonical CER-AI final hierarchy using PASS / CAUTION / STOP-DEFER."""
import bootstrap
from clinical_disposition import CAUTION, PASS, STATUS_RANK, STOP_DEFER

core = bootstrap.core
_previous_assess_eye = core.assess_eye


def _decision_critical_incomplete(result):
    if result.get("missing"):
        return True
    status = str(result.get("status") or "").upper()
    return "DATA INSUFFICIENT" in status or "NOT ASSESSED" in status


def _remove_visual_morphology_authority(eye):
    """Prevent visual morphology from affecting CER-AI scoring or hard stops.

    Visual anterior-map interpretation is error-prone and is no longer a
    decision authority. The original observation/evidence may remain in the
    extraction record for audit context, but the assessor receives neutralized
    morphology fields. Numeric signed I-S and derived SRAX remain available and
    are scored by the dedicated ERSS evidence policy.
    """
    working = dict(eye)
    visual = working.get("morphology")
    if visual not in (None, "UNCERTAIN"):
        evidence = list(working.get("morphology_evidence") or [])
        evidence.append(
            f"Visual morphology {visual} retained as non-scoring context only; CER-AI decision logic uses numeric I-S/SRAX instead."
        )
        working["morphology_evidence"] = list(dict.fromkeys(evidence))
    working["morphology"] = "UNCERTAIN"
    working["morphology_confidence"] = "UNREADABLE"
    working["asymmetric_bow_tie"] = "UNCERTAIN"
    working["srax"] = "UNCERTAIN"
    working["srax_deg"] = None
    working["inferior_opposite_steepening_D"] = None
    return working


def _remove_prk_ewss_pathway(result):
    """Remove the legacy provisional PRK-EWSS as a clinical decision pathway.

    PRK remains governed by the independent CER-AI risk/safety layers applied
    elsewhere (Final BAD-D, NICE, PS3, tissue/procedure hard stops, readiness,
    and other explicit clinical cautions). The legacy PRK-EWSS was explicitly
    unvalidated and must neither create STOP-DEFER nor appear as a fifth score.
    """
    values = result.get("values") or {}
    if str(values.get("procedure") or "").upper() != "PRK":
        return result

    original_reasons = list(result.get("reasons") or [])
    prk_ewss_reasons = [reason for reason in original_reasons if "PRK-EWSS" in str(reason)]
    remaining_reasons = [reason for reason in original_reasons if "PRK-EWSS" not in str(reason)]
    result["reasons"] = remaining_reasons

    result["warnings"] = [
        warning for warning in (result.get("warnings") or [])
        if "PRK-EWSS" not in str(warning)
    ]

    if "score" in result:
        result["score"] = {
            "rows": {},
            "total": None,
            "category": "NOT_APPLICABLE",
            "source": "PRK-EWSS removed from CER-AI decision architecture",
            "breakdown": [],
        }
    result["instrument"] = (
        "PRK: no provisional PRK-EWSS score. CER-AI uses independent risk and "
        "procedure-safety pathways."
    )
    result["prk_ewss_removed"] = True

    # Never cancel an independently recorded hard stop.
    if result.get("hard_stops"):
        return result

    # If upstream STOP-DEFER came from the removed provisional PRK-EWSS only,
    # release that restriction. Preserve any other upstream concern as CAUTION.
    if result.get("status") == STOP_DEFER and prk_ewss_reasons:
        result["status"] = CAUTION if remaining_reasons else PASS
        result["action"] = (
            "CAUTION — surgeon review is required. The legacy provisional PRK-EWSS "
            "does not participate in CER-AI decision-making."
            if result["status"] == CAUTION
            else "PRK assessment continues through the remaining independent CER-AI pathways."
        )
    return result


def assess_eye_with_hc_final_hierarchy(eye, plan, age, patient_modifiers):
    eye = _remove_visual_morphology_authority(eye)
    result = _previous_assess_eye(eye, plan, age, patient_modifiers)
    result = _remove_prk_ewss_pathway(result)

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

    if str((result.get("values") or {}).get("procedure") or "").upper() == "PRK":
        result["status"] = CAUTION if result.get("status") == CAUTION else PASS
        return result

    if bad_status in {"UNAVAILABLE", "UNREADABLE", None} or not core.is_number(erss_total):
        return result

    if bad_status == "ABNORMAL":
        stop = "CER-AI operational hard stop: Final BAD-D abnormal (>=2.60); cornea classified ABNORMAL by the CER-AI BAD-D gate."
        if stop not in result.setdefault("hard_stops", []):
            result["hard_stops"].append(stop)
        if stop not in result.setdefault("reasons", []):
            result["reasons"].append(stop)
        result["status"] = STOP_DEFER
        result["action"] = "STOP-DEFER — ABNORMAL CORNEA. Final BAD-D is >=2.60 and meets the CER-AI abnormal cutoff."
        return result

    if float(erss_total) >= 4:
        result["status"] = STOP_DEFER
        result["action"] = "STOP-DEFER. Randleman/ERSS score is 4 or greater."
        reason = f"CER-AI final hierarchy: Randleman/ERSS total {float(erss_total):g} is >=4."
        if reason not in result.setdefault("reasons", []):
            result["reasons"].append(reason)
        return result

    if float(erss_total) == 3:
        result["status"] = CAUTION
        result["action"] = (
            "CAUTION — Randleman/ERSS score 3 is moderate risk; explicit surgeon review "
            "is required without automatic defer."
        )
        reason = "CER-AI final hierarchy: Randleman/ERSS total 3 is moderate risk (CAUTION)."
        if reason not in result.setdefault("reasons", []):
            result["reasons"].append(reason)
        return result

    result["status"] = CAUTION if result.get("status") == CAUTION else PASS
    result["action"] = (
        "CAUTION — surgeon review is required; this category does not automatically defer surgery."
        if result["status"] == CAUTION
        else "CER-AI assessment PASS; this is not a guarantee of zero ectasia risk."
    )
    result["hc_final_decision_hierarchy"] = {
        "final_BAD_D_status": bad_status,
        "randleman_erss_total": float(erss_total),
        "rule": "FINAL_BAD_D_NOT_ABNORMAL_AND_ERSS_0_TO_2_PRESERVE_PASS_OR_CAUTION",
    }
    return result


core.assess_eye = assess_eye_with_hc_final_hierarchy
core._hc_final_decision_hierarchy_installed = True
