"""Guarded Phase 3 runtime seam for the CER-AI linear clinical pipeline.

This module introduces routing infrastructure only. It deliberately does not
replace assess_eye, hc_engine, merge_extractions, readiness, reporting, or
archive behavior. The production default remains the frozen legacy-composed
runtime until an explicit later Phase 3 cutover is approved and equivalence
proven at the normalized-case adapter boundary.
"""
from __future__ import annotations

import os
from typing import Any, Callable

from clinical_core.pipeline import evaluate_normalized_case
from phase3_shadow_diagnostics import (
    ENV_FLAG as SHADOW_DIAGNOSTICS_ENV_FLAG,
    diagnostics_snapshot,
    observe_shadow_parity,
    shadow_diagnostics_enabled,
)
from phase3_shadow_service import evaluate_shadow


ENV_FLAG = "CERAI_LINEAR_PIPELINE_ENABLED"


def linear_pipeline_enabled(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return str(source.get(ENV_FLAG, "0")).strip().lower() in {"1", "true", "yes", "on"}


def route_normalized_case(
    normalized_input: Any,
    *,
    legacy_evaluator: Callable[[Any], Any],
    enabled: bool | None = None,
):
    """Route one already-normalized case at the future cutover seam.

    No extraction/readiness/report/archive work belongs here. When disabled,
    the caller-supplied legacy evaluator remains authoritative. When enabled,
    the pure linear clinical pipeline evaluates the normalized input.
    """
    use_linear = linear_pipeline_enabled() if enabled is None else bool(enabled)
    if not use_linear:
        return legacy_evaluator(normalized_input)
    return evaluate_normalized_case(normalized_input)


def shadow_compare_eye(production_eye_result: Any, normalized_input: Any, *, procedure: str):
    """Run the linear core as a non-authoritative shadow comparison."""
    return evaluate_shadow(
        production_eye_result,
        normalized_input,
        procedure=procedure,
    )


def install(core: Any) -> None:
    """Expose Phase 3 seam metadata without altering production clinical calls."""
    if getattr(core, "_cerai_phase3_runtime_seam_installed", False):
        return

    core._cerai_linear_pipeline_enabled = linear_pipeline_enabled()
    core._cerai_linear_pipeline_env_flag = ENV_FLAG
    core._cerai_route_normalized_case = route_normalized_case
    core._cerai_shadow_compare_eye = shadow_compare_eye
    core._cerai_shadow_diagnostics_enabled = shadow_diagnostics_enabled()
    core._cerai_shadow_diagnostics_env_flag = SHADOW_DIAGNOSTICS_ENV_FLAG
    core._cerai_observe_shadow_parity = observe_shadow_parity
    core._cerai_shadow_diagnostics_snapshot = diagnostics_snapshot
    core._cerai_phase3_runtime_seam_installed = True
