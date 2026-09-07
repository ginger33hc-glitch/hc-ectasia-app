"""Ordered production composition for CER-AI operational concerns.

Clinical assessment is not assembled through runtime wrapper order;
``assessment_workflow`` calls the canonical runtime directly. This composition
module installs extraction, transport, access, reporting, persistence, and the
still-pending planning/report concerns that will be migrated in their ordered
stages. Duplicate clinical scorers are not imported or installed here.
"""
import os

import bootstrap
import reports

import bad_display_source_policy  # noqa: E402
import merge_policy_base  # noqa: F401,E402
import extraction_guard  # noqa: F401,E402
import report_export_guard  # noqa: F401,E402
import critical_score_highlight  # noqa: E402
import microkeratome_planning_policy  # noqa: E402
import erss_numeric_extraction_policy  # noqa: E402
import ps3_extraction_policy  # noqa: E402
import mandatory_source_set_policy  # noqa: E402
import ps3_report_policy  # noqa: E402
import microkeratome_report_policy  # noqa: E402

import assessment_workflow  # noqa: E402
import user_access  # noqa: E402
import operational_security  # noqa: E402
import public_site  # noqa: E402
import analysis_job_service  # noqa: E402
import mobile_install_section  # noqa: E402
import case_archive  # noqa: E402
import audit_log  # noqa: E402
import case_catalog  # noqa: E402
import historical_report  # noqa: E402
import research_export  # noqa: E402
import named_user_ui  # noqa: E402
import pentacam_targeted_reread  # noqa: E402
import rmin_front_source_policy  # noqa: E402
import geometric_srax_policy  # noqa: E402
import pentacam_canonical_source_enforcement  # noqa: E402

core = bootstrap.core
app = bootstrap.app

COMPOSITION_PHASES = {
    "pentacam_extraction_pending_stage2_3": (
        "merge_policy_base", "extraction_guard", "erss_numeric_extraction_policy",
        "pentacam_canonical_source_enforcement", "ps3_extraction_policy",
        "mandatory_source_set_policy", "pentacam_targeted_reread",
        "rmin_front_source_policy", "geometric_srax_policy", "bad_display_source_policy",
    ),
    "planning_and_reporting_pending_stage9_10": (
        "microkeratome_planning_policy", "report_export_guard", "critical_score_highlight",
        "ps3_report_policy", "microkeratome_report_policy",
    ),
    "canonical_workflow": ("assessment_workflow",),
    "access_and_persistence": (
        "user_access", "operational_security", "public_site", "analysis_job_service",
        "mobile_install_section", "case_archive", "audit_log", "case_catalog",
        "historical_report", "research_export", "named_user_ui",
    ),
}


def compose(version: str):
    """Install the production runtime once and return archive state."""
    if getattr(core, "_cerai_runtime_composed", False):
        return getattr(core, "_cerai_case_archive_runtime", None)

    core.APP_VERSION = version
    core.app.title = f"CER-AI v{version}"
    reports.APP_VERSION = version

    # Presentation/report concerns remain until Stage 10, but do not own clinical truth.
    critical_score_highlight.install(core, reports)
    ps3_report_policy.install(reports)
    microkeratome_report_policy.install(reports)

    # Extraction/source wrappers remain only until Stages 2-3 flatten the source path.
    erss_numeric_extraction_policy.install(core)
    microkeratome_planning_policy.install(core)
    pentacam_canonical_source_enforcement.install(core, pentacam_targeted_reread)
    ps3_extraction_policy.install(core)
    mandatory_source_set_policy.install(core)

    # Canonical workflow calls canonical_runtime_service directly; no clinical scorer install.
    assessment_workflow.install(core)
    user_access.install(core)
    operational_security.install(core)
    public_site.install(core)
    analysis_job_service.install(core)
    mobile_install_section.install(core)

    archive_required = os.getenv("CERAI_ARCHIVE_REQUIRED", "0").strip() == "1"
    archive_enabled = os.getenv("CERAI_ARCHIVE_ENABLED", "0").strip() == "1" or archive_required
    if archive_enabled:
        archive_runtime = case_archive.install(core)
    else:
        archive_runtime = case_archive.install(
            core, runtime=case_archive.CaseArchiveRuntime(None, required=False)
        )

    audit_log.install(core, archive_runtime)
    case_catalog.install(core, archive_runtime)
    historical_report.install(core, archive_runtime)
    research_export.install(core, archive_runtime)
    named_user_ui.install(core)

    pentacam_targeted_reread.install(core)
    rmin_front_source_policy.install(core, pentacam_targeted_reread)
    geometric_srax_policy.install(core, rmin_front_source_policy)
    bad_display_source_policy.install(core)

    app.state.cerai_canonical_runtime_ready = True
    core._cerai_runtime_composed = True
    core._cerai_composition_phases = COMPOSITION_PHASES
    return archive_runtime
