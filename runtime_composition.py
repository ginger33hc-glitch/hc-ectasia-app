"""Ordered production composition for the canonical CER-AI runtime.

This is the only module that assembles production concerns.  Leaf modules own
one topic and may expose compatibility symbols for tests, but they must not
decide installation order by importing unrelated policy modules.

The order below is behavior-critical because the established runtime uses
small wrappers around the legacy core.  Keeping that order explicit here makes
the dependency chain reviewable and prevents accidental import-order changes.
"""
import os

import bootstrap
import reports

# Base clinical policies and extraction pipeline. Some legacy-compatible
# modules still install narrowly scoped wrappers when imported; their order is
# deliberately centralized here while they are migrated to explicit installers.
import hc_age_policy  # noqa: E402
import hc_bad_final_policy  # noqa: F401,E402
import merge_policy_base  # noqa: F401,E402
import extraction_guard  # noqa: F401,E402
import report_export_guard  # noqa: F401,E402
import critical_score_highlight  # noqa: E402
import pachymetry_policy  # noqa: F401,E402
import randleman_bad_independence  # noqa: F401,E402
import hc_final_decision_policy  # noqa: F401,E402
import status_rank_policy  # noqa: E402
import inter_eye_tomography_policy  # noqa: E402
import microkeratome_planning_policy  # noqa: E402
import erss_numeric_extraction_policy  # noqa: E402
import erss_topography_evidence_policy  # noqa: E402
import ps3_extraction_policy  # noqa: E402
import mandatory_source_set_policy  # noqa: E402
import ps3_runtime_policy  # noqa: E402
import ps3_report_policy  # noqa: E402
import microkeratome_report_policy  # noqa: E402

# Explicitly installed clinical workflow and operational services.
import nice_policy  # noqa: E402
import assessment_workflow  # noqa: E402
import user_access  # noqa: E402
import operational_security  # noqa: E402
import public_site  # noqa: E402
import mobile_install_section  # noqa: E402
import case_archive  # noqa: E402
import audit_log  # noqa: E402
import case_catalog  # noqa: E402
import historical_report  # noqa: E402
import research_export  # noqa: E402
import named_user_ui  # noqa: E402
import pentacam_targeted_reread  # noqa: E402
import rmin_front_source_policy  # noqa: E402
import erss_auto_read_policy  # noqa: E402


core = bootstrap.core
app = bootstrap.app

COMPOSITION_PHASES = {
    "clinical_policy": (
        "hc_age_policy",
        "hc_bad_final_policy",
        "pachymetry_policy",
        "randleman_bad_independence",
        "hc_final_decision_policy",
        "status_rank_policy",
        "inter_eye_tomography_policy",
        "microkeratome_planning_policy",
        "nice_policy",
        "ps3_runtime_policy",
    ),
    "pentacam_extraction": (
        "merge_policy_base",
        "extraction_guard",
        "erss_numeric_extraction_policy",
        "erss_topography_evidence_policy",
        "ps3_extraction_policy",
        "mandatory_source_set_policy",
        "pentacam_targeted_reread",
        "rmin_front_source_policy",
        "erss_auto_read_policy",
    ),
    "reporting_and_readiness": (
        "report_export_guard",
        "critical_score_highlight",
        "ps3_report_policy",
        "microkeratome_report_policy",
        "assessment_workflow",
    ),
    "access_and_persistence": (
        "user_access",
        "operational_security",
        "public_site",
        "mobile_install_section",
        "case_archive",
        "audit_log",
        "case_catalog",
        "historical_report",
        "research_export",
        "named_user_ui",
    ),
}


def compose(version: str):
    """Install the complete production runtime once and return archive state."""
    if getattr(core, "_cerai_runtime_composed", False):
        return getattr(core, "_cerai_case_archive_runtime", None)

    core.APP_VERSION = version
    core.app.title = f"CER-AI v{version}"
    reports.APP_VERSION = version

    hc_age_policy.install(core, score_audit_owner=bootstrap)
    status_rank_policy.install(core)
    critical_score_highlight.install(core, reports)
    ps3_report_policy.install(reports)
    microkeratome_report_policy.install(reports)
    erss_numeric_extraction_policy.install(core)
    erss_topography_evidence_policy.install(
        core,
        prior_assess_eye=bootstrap._original_assess_eye,
    )
    inter_eye_tomography_policy.install(core, compatibility_owner=bootstrap)
    microkeratome_planning_policy.install(core)
    nice_policy.install(core)
    ps3_extraction_policy.install(core)
    mandatory_source_set_policy.install(core)
    ps3_runtime_policy.install(core)
    assessment_workflow.install(core)
    user_access.install(core)
    operational_security.install(core)
    public_site.install(core)
    mobile_install_section.install(core)

    archive_required = os.getenv("CERAI_ARCHIVE_REQUIRED", "0").strip() == "1"
    archive_enabled = os.getenv("CERAI_ARCHIVE_ENABLED", "0").strip() == "1" or archive_required
    if archive_enabled:
        archive_runtime = case_archive.install(core)
    else:
        archive_runtime = case_archive.install(
            core,
            runtime=case_archive.CaseArchiveRuntime(None, required=False),
        )

    audit_log.install(core, archive_runtime)
    case_catalog.install(core, archive_runtime)
    historical_report.install(core, archive_runtime)
    research_export.install(core, archive_runtime)
    named_user_ui.install(core)
    pentacam_targeted_reread.install(core)
    rmin_front_source_policy.install(core, pentacam_targeted_reread)
    # This cleanup remains outside the fully installed NICE engine and removes
    # superseded legacy morphology completion requests.
    erss_auto_read_policy.install(core)

    app.state.cerai_canonical_runtime_ready = True
    core._cerai_runtime_composed = True
    core._cerai_composition_phases = COMPOSITION_PHASES
    return archive_runtime
