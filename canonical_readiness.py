"""Pure pre-core readiness for the CER-AI assessment workflow.

This module decides only whether a case may enter the canonical clinical core.
It does not inspect tomography values, calculate scores, classify risk, or alter
a clinical disposition. Decision-critical measurement completeness remains owned
by the canonical clinical core, which returns ASSESSMENT INCOMPLETE with explicit
missing dependencies when necessary.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from clinical_core.readiness import contact_lens_washout
from clinical_core.safety import ablation_um_is_valid

SUPPORTED_PROCEDURES = frozenset({"LASIK", "PRK", "SMILE"})
KNOWN_PRIOR_STATES = frozenset({"no", "prk", "lasik", "smile"})
POST_REFRACTIVE = "POST-REFRACTIVE PATHWAY REQUIRED"
VIRGIN = "VIRGIN_CORNEA"


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _age_issue(age_years: Any) -> str | None:
    if not _finite(age_years) or int(age_years) != float(age_years):
        return "Patient age must be documented as a whole number."
    age = int(age_years)
    if age < 18 or age > 120:
        return "Patient age must be within the supported adult range of 18-120 years."
    return None


def evaluate_precore_readiness(
    *,
    age_years: Any,
    eye_plans: Mapping[str, Mapping[str, Any]] | None,
    patient_modifiers: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return transport/workflow readiness without running clinical scoring."""
    blockers: list[dict[str, Any]] = []
    pathways: dict[str, str] = {}

    age_issue = _age_issue(age_years)
    if age_issue:
        blockers.append({"eye": "PATIENT", "key": "age", "message": age_issue})

    lens_block = contact_lens_washout(dict(patient_modifiers or {}))
    if lens_block:
        blockers.append({
            "eye": "PATIENT",
            "key": "contact_lens_discontinuation_days" if lens_block.get("form_id") == "contact_lens_days" else "contact_lens_type",
            "message": lens_block.get("message"),
        })

    plans = eye_plans if isinstance(eye_plans, Mapping) else {}
    for eye in ("OD", "OS"):
        plan = plans.get(eye)
        if plan is None:
            continue
        if not isinstance(plan, Mapping):
            blockers.append({"eye": eye, "key": "plan", "message": "Eye plan must be a structured object."})
            continue

        prior = str(plan.get("prior") or "").strip().lower()
        if prior not in KNOWN_PRIOR_STATES:
            blockers.append({
                "eye": eye,
                "key": "prior",
                "message": "Prior corneal refractive-surgery status must be documented.",
            })
            continue
        if prior != "no":
            pathways[eye] = POST_REFRACTIVE
            continue

        pathways[eye] = VIRGIN
        procedure = str(plan.get("procedure") or "").strip().upper()
        if procedure not in SUPPORTED_PROCEDURES:
            blockers.append({
                "eye": eye,
                "key": "procedure",
                "message": "Select LASIK, PRK, or SMILE before canonical assessment.",
            })

        ablation = plan.get("max_ablation_um", plan.get("ablation_um"))
        if _finite(ablation) and not ablation_um_is_valid(ablation):
            blockers.append({
                "eye": eye,
                "key": "ablation_um",
                "message": "Actual maximum ablation must be zero or greater.",
            })

    if not pathways and not any(item.get("key") == "plan" for item in blockers):
        blockers.append({
            "eye": "GLOBAL",
            "key": "eye_plan",
            "message": "At least one OD or OS treatment plan is required.",
        })

    return {
        "ready": not blockers,
        "blockers": blockers,
        "pathways": pathways,
        "contact_lens_washout": lens_block,
    }
