"""Canonical non-scored inter-eye tomography concern layer.

This layer neutralizes the superseded manual inter-eye modifier and appends an
automated bilateral tomography concern after the established CER-AI engine finishes.
It must not change score, status, hard stops, BAD-D, or Randleman/ERSS decisions.
"""
import bootstrap
from inter_eye_tomography import assess_inter_eye_tomography

core = bootstrap.core
_previous_hc_engine = core.hc_engine


def hc_engine_with_inter_eye_tomography(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
    modifiers = dict(patient_modifiers or {})
    # Manual surgeon-entered inter-eye asymmetry is retired. Automated bilateral
    # comparison is contextual only and therefore cannot change clearance.
    modifiers["inter_eye_asymmetry"] = "no"

    result = _previous_hc_engine(extracted, age, eye_plans, modifiers, patient_metadata)
    finding = assess_inter_eye_tomography(extracted.get("eyes", []))
    result["inter_eye_tomography_concern"] = finding

    summary = f"Inter-eye tomography concern: {finding['status']}. {finding['note']}"
    details = list(finding.get("major_discordances") or [])
    if finding.get("unavailable_domains"):
        details.append("Unavailable bilateral domains: " + ", ".join(finding["unavailable_domains"]) + ".")

    for eye_result in result.get("eyes", []) or []:
        review = dict(eye_result.get("tomography_review") or {})
        review["inter_eye_tomography_concern"] = finding
        flags = list(review.get("cross_sectional_flags") or [])
        if summary not in flags:
            flags.append(summary)
        for detail in details:
            if detail not in flags:
                flags.append(detail)
        review["cross_sectional_flags"] = flags
        eye_result["tomography_review"] = review

    return result


core.hc_engine = hc_engine_with_inter_eye_tomography
bootstrap.hc_engine = hc_engine_with_inter_eye_tomography
core._hc_inter_eye_tomography_policy_installed = True
app = bootstrap.app
