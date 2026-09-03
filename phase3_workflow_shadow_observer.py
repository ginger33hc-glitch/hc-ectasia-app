"""Temporary Phase 3 observer for completed CER-AI assessments.

This module runs non-authoritative linear-pipeline diagnostics only after the
legacy readiness workflow has produced a READY response.  It returns the exact
legacy response object and never writes shadow data into the response, report
snapshot, archive, audit record, or patient metadata.

The observer is intentionally isolated and removable.  It exists only during
the guarded Phase 3 cutover period.
"""
from __future__ import annotations

from typing import Any

import assessment_workflow
from phase3_normalized_adapter import build_clinical_core_input
from phase3_shadow_diagnostics import observe_shadow_parity


_previous_respond = None


def _observe_ready_response(response: Any, *, age, plans) -> None:
    if not isinstance(response, dict) or response.get("workflow_status") != "READY":
        return

    decision = response.get("decision")
    extracted = response.get("extracted")
    effective = response.get("effective_eye_plans")
    if not isinstance(decision, dict) or not isinstance(extracted, dict) or not isinstance(effective, dict):
        return

    source = {
        item.get("eye"): item
        for item in extracted.get("eyes", [])
        if isinstance(item, dict) and item.get("eye") in {"OD", "OS"}
    }
    production_results = {
        item.get("eye"): item
        for item in decision.get("eyes", [])
        if isinstance(item, dict) and item.get("eye") in {"OD", "OS"}
    }

    for eye_name in ("OD", "OS"):
        eye = source.get(eye_name)
        production_eye = production_results.get(eye_name)
        plan = effective.get(eye_name) or plans.get(eye_name) or {}
        if not isinstance(eye, dict) or not isinstance(production_eye, dict) or not isinstance(plan, dict):
            continue
        if production_eye.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED" or plan.get("prior") != "no":
            continue
        procedure = str(plan.get("procedure") or "").strip().upper()
        if procedure not in {"LASIK", "PRK", "SMILE"}:
            continue

        normalized = build_clinical_core_input(
            eye,
            plan,
            age_years=age,
            extracted=extracted,
        )
        observe_shadow_parity(
            production_eye,
            normalized,
            procedure=procedure,
        )


def respond_with_phase3_shadow_observer(core, token, session, age, plans, modifiers, metadata, overrides):
    """Return the legacy workflow response unchanged, then observe parity."""
    if _previous_respond is None:
        raise RuntimeError("Phase 3 workflow shadow observer was not initialized")

    response = _previous_respond(core, token, session, age, plans, modifiers, metadata, overrides)
    try:
        _observe_ready_response(response, age=age, plans=plans)
    except Exception:
        # Shadow diagnostics are explicitly non-authoritative.  No observer
        # failure may alter or block a clinical response during Phase 3.
        pass
    return response


def install(core: Any) -> None:
    global _previous_respond
    if getattr(core, "_cerai_phase3_workflow_shadow_observer_installed", False):
        return

    _previous_respond = assessment_workflow._respond
    assessment_workflow._respond = respond_with_phase3_shadow_observer
    core._cerai_phase3_workflow_shadow_observer_installed = True
