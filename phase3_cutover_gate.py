"""Fail-closed Phase 3 cutover eligibility policy for CER-AI.

This module does not switch runtime authority. It only decides whether one
completed virgin-cornea case is eligible for a future linear-authority route.
Any uncertainty keeps the legacy composed runtime authoritative.
"""
from __future__ import annotations

from typing import Any, Mapping


ALLOWED_PROCEDURES = {"LASIK", "PRK", "SMILE"}


def evaluate_cutover_eligibility(
    *,
    linear_flag_enabled: bool,
    workflow_status: str,
    production_eye_result: Mapping[str, Any] | None,
    plan: Mapping[str, Any] | None,
    shadow_observation: Mapping[str, Any] | None,
    observer_error: bool = False,
) -> dict[str, Any]:
    """Return a deterministic fail-closed cutover eligibility record."""
    production_eye_result = production_eye_result or {}
    plan = plan or {}
    shadow_observation = shadow_observation or {}

    reasons: list[str] = []
    procedure = str(plan.get("procedure") or "").strip().upper()

    if not bool(linear_flag_enabled):
        reasons.append("LINEAR_FEATURE_FLAG_DISABLED")
    if str(workflow_status or "").strip().upper() != "READY":
        reasons.append("ASSESSMENT_NOT_READY")
    if production_eye_result.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED" or plan.get("prior") != "no":
        reasons.append("POST_REFRACTIVE_OR_NON_VIRGIN_PATHWAY")
    if procedure not in ALLOWED_PROCEDURES:
        reasons.append("UNSUPPORTED_OR_MISSING_PROCEDURE")
    if observer_error:
        reasons.append("SHADOW_OBSERVER_ERROR")
    if not shadow_observation.get("observed"):
        reasons.append("NO_SHADOW_OBSERVATION")
    elif not shadow_observation.get("cutover_allowed"):
        reasons.append("PARITY_MISMATCH")

    return {
        "eligible": not reasons,
        "authoritative_engine_if_ineligible": "LEGACY_COMPOSED_RUNTIME",
        "candidate_engine_if_eligible": "LINEAR_CLINICAL_CORE",
        "procedure": procedure or None,
        "reasons": reasons,
    }
