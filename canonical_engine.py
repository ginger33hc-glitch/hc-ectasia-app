"""Canonical production entrypoint for CER-AI.

Startup invariants validate the direct canonical architecture rather than runtime
wrapper order. Clinical truth lives in ``clinical_core`` and
``canonical_runtime_service``; operational composition may not replace it.
"""
from __future__ import annotations

import inspect

import assessment_workflow
import canonical_runtime_service
import geometric_srax_policy
import mandatory_source_set_policy
import pentacam_targeted_reread
import runtime_composition as composition
from clinical_core.bad import final_bad_d_classification
from clinical_core.erss import erss_disposition, erss_rsb_points
from clinical_core.rules import erss_age_points, erss_pachymetry_points
from clinical_core.safety import (
    FINAL_KMEAN_MAX_D,
    FINAL_KMEAN_MIN_D,
    PTA_LIMIT_PERCENT,
    LASIK_RSB_MIN_UM,
    PREOP_THINNEST_HARD_STOP_UM,
    PRK_EPITHELIUM_UM,
    PRK_RST_MIN_UM,
    pta_hard_stop,
)
from pentacam_canonical_source_lock import (
    CANONICAL_FIELD_SOURCES,
    SHOW_2_CORNEA_BACK,
)

core = composition.core
app = composition.app
CANONICAL_VERSION = "0.7.71"
_archive_runtime = composition.compose(CANONICAL_VERSION)


def runtime_invariants():
    """Fail startup if canonical clinical/runtime ownership is disconnected."""
    errors = []

    # Canonical clinical boundaries are validated directly at their owning modules.
    if [erss_age_points(x) for x in (18, 19, 20, 21, 30)] != [3, 2, 2, 0, 0]:
        errors.append("Canonical Randleman age policy is invalid")
    if [erss_pachymetry_points(x) for x in (479, 480, 499, 500, 509, 510)] != [None, 2, 2, 1, 1, 0]:
        errors.append("Canonical Randleman pachymetry policy is invalid")
    if [erss_rsb_points(x) for x in (239, 240, 259, 260, 279, 280, 299, 300)] != [4, 3, 3, 2, 2, 1, 1, 0]:
        errors.append("Canonical Randleman RSB policy is invalid")
    if [erss_disposition(x) for x in (0, 2, 3, 4)] != ["PASS", "PASS", "CAUTION", "STOP-DEFER"]:
        errors.append("Canonical Randleman disposition is invalid")
    if [final_bad_d_classification(x) for x in (1.60, 1.61, 2.59, 2.60)] != [
        "NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL"
    ]:
        errors.append("Canonical Final BAD-D policy is invalid")

    if PRK_EPITHELIUM_UM != 50.0:
        errors.append("Canonical PRK epithelial convention is not 50 µm")
    if LASIK_RSB_MIN_UM != 300.0 or PRK_RST_MIN_UM != 310.0:
        errors.append("Canonical stromal safety minima are invalid")
    if PTA_LIMIT_PERCENT != 40.0 or [
        pta_hard_stop(value) for value in (39.99, 40.0, 40.01)
    ] != [False, True, True]:
        errors.append("Canonical LASIK/PRK PTA boundary is invalid")
    if PREOP_THINNEST_HARD_STOP_UM != 480.0:
        errors.append("Canonical preoperative thickness hard stop is invalid")
    if FINAL_KMEAN_MIN_D != 36.0 or FINAL_KMEAN_MAX_D != 48.0:
        errors.append("Canonical final keratometry bounds are invalid")

    # Canonical source registry, not legacy module naming, owns source truth.
    if CANONICAL_FIELD_SOURCES.get("Rmin_mm", (None,))[0] != SHOW_2_CORNEA_BACK:
        errors.append("Rmin is not source-locked to Show 2 Exams Cornea Back")
    if CANONICAL_FIELD_SOURCES.get("posterior_Kmean_D", (None,))[0] != SHOW_2_CORNEA_BACK:
        errors.append("Posterior Km is not source-locked to Show 2 Exams Cornea Back")

    # Workflow must call the direct canonical runtime, never the legacy clinical engine.
    workflow_source = inspect.getsource(assessment_workflow._respond)
    if "evaluate_case(" not in workflow_source:
        errors.append("Assessment workflow is not connected to canonical_runtime_service")
    if "core.hc_engine" in workflow_source:
        errors.append("Assessment workflow still calls legacy core.hc_engine")
    if "apply_extracted_corrections" in workflow_source:
        errors.append("Assessment workflow still uses legacy plan correction pre-pass")
    if assessment_workflow._respond.__module__ != "assessment_workflow":
        errors.append("Assessment workflow has been monkey-patched")
    if callable(getattr(canonical_runtime_service, "install", None)):
        errors.append("Canonical runtime service must not expose an installer")

    # Retired Phase 3 shadow/cutover wrappers must not be in production composition.
    phase_names = {name for values in composition.COMPOSITION_PHASES.values() for name in values}
    if "phase3_runtime_seam" in phase_names or "phase3_workflow_shadow_observer" in phase_names:
        errors.append("Retired Phase 3 wrapper remains in production composition")
    if "srax_completion_policy" in phase_names or "randleman_report_readiness_policy" in phase_names:
        errors.append("Retired workflow monkey-patch remains in production composition")

    assessment_source = inspect.getsource(core._run_image_assessment)
    if "mandatory_source_set_policy.validate_source_set(extraction_results)" not in assessment_source:
        errors.append("Mandatory Pentacam source gate is not directly owned by app._run_image_assessment")
    if callable(getattr(mandatory_source_set_policy, "install", None)):
        errors.append("Mandatory Pentacam source policy must not expose a runtime installer")
    if "mandatory_source_set_policy" in phase_names:
        errors.append("Mandatory Pentacam source wrapper remains in runtime composition")

    extraction_source = inspect.getsource(core.extract_one_image)
    if "pentacam_targeted_reread.enrich_extraction(" not in extraction_source:
        errors.append("Targeted Pentacam reread is not directly owned by app.extract_one_image")
    if "geometric_srax_policy.enrich_extraction(" not in extraction_source:
        errors.append("Geometric SRAX is not directly owned by app.extract_one_image")
    if callable(getattr(pentacam_targeted_reread, "install", None)):
        errors.append("Targeted Pentacam reread must not expose a runtime installer")
    if callable(getattr(geometric_srax_policy, "install", None)):
        errors.append("Geometric SRAX must not expose a runtime installer")
    if "pentacam_targeted_reread" in phase_names or "geometric_srax_policy" in phase_names:
        errors.append("Per-image extraction wrapper remains in runtime composition")

    merge_source = inspect.getsource(core.merge_extractions)
    if core.merge_extractions.__module__ != "app":
        errors.append("Canonical merge_extractions is not owned directly by app.py")
    if "apply_extraction_validation(merged)" not in merge_source:
        errors.append("Canonical merge does not directly invoke extraction validation")
    if "merge_policy_base" in phase_names or "extraction_guard" in phase_names:
        errors.append("Retired merge wrapper remains in runtime composition")

    # Extraction/transport/operational boundaries still required at this stage.
    for marker, message in (
        ("_hc_readiness_installed", "Assessment workflow endpoints are not installed"),
        ("_cerai_report_builders_installed", "Report builders are not installed"),
        ("_cerai_named_user_access_installed", "Named-user access boundary is not active"),
        ("_cerai_operational_security_installed", "Operational security boundary is not active"),
        ("_cerai_case_archive_installed", "Case archive boundary is not active"),
        ("_cerai_audit_log_installed", "Audit log boundary is not active"),
        ("_cerai_case_catalog_installed", "Case catalog boundary is not active"),
        ("_cerai_historical_report_installed", "Historical report boundary is not active"),
        ("_cerai_research_export_installed", "Research export boundary is not active"),
        ("_cerai_named_user_ui_installed", "Named-user UI boundary is not active"),
    ):
        if not getattr(core, marker, False):
            errors.append(message)

    if getattr(composition.reports, "APP_VERSION", None) != CANONICAL_VERSION:
        errors.append("Report version is not synchronized with canonical runtime")
    if "reporting_pending_stage10" in composition.COMPOSITION_PHASES:
        errors.append("Legacy Stage 10 report wrapper phase remains active")
    if getattr(core, "_cerai_composition_phases", None) != composition.COMPOSITION_PHASES:
        errors.append("Canonical composition manifest is not active")
    if not getattr(app.state, "cerai_canonical_runtime_ready", False):
        errors.append("Canonical ASGI startup marker is not active")

    if errors:
        raise RuntimeError("Canonical CER-AI runtime invariant failure: " + "; ".join(errors))
    return True


runtime_invariants()
