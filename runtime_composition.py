"""Ordered production composition for the approved CER-AI recovery runtime."""
import os
import bootstrap
import reports
import hc_age_policy
import hc_bad_final_policy  # noqa:F401
import merge_policy_base  # noqa:F401
import extraction_guard  # noqa:F401
import erss_topography_guard  # noqa:F401
import report_export_guard  # noqa:F401
import critical_score_highlight
import pachymetry_policy  # noqa:F401
import randleman_bad_independence  # noqa:F401
import erss_visual_morphology_policy
import hc_final_decision_policy  # noqa:F401
import status_rank_policy
import inter_eye_tomography_policy
import microkeratome_planning_policy
import erss_topography_evidence_policy
import ps3_extraction_policy
import ps3_runtime_policy
import ps3_report_policy
import nice_policy
import assessment_workflow
import randleman_report_readiness_policy
import user_access
import operational_security
import case_archive
import audit_log
import case_catalog
import historical_report
import research_export
import named_user_ui
import pentacam_targeted_reread
import topometric_index_review_policy
import erss_auto_read_policy

core=bootstrap.core;app=bootstrap.app
COMPOSITION_PHASES={
 "clinical_policy":("hc_age_policy","hc_bad_final_policy","pachymetry_policy","randleman_bad_independence","hc_final_decision_policy","status_rank_policy","inter_eye_tomography_policy","microkeratome_planning_policy","nice_policy","ps3_runtime_policy"),
 "pentacam_extraction":("merge_policy_base","extraction_guard","erss_topography_guard","erss_visual_morphology_policy","erss_topography_evidence_policy","ps3_extraction_policy","pentacam_targeted_reread","erss_auto_read_policy"),
 "reporting_and_readiness":("report_export_guard","critical_score_highlight","assessment_workflow","randleman_report_readiness_policy","ps3_report_policy","topometric_index_review_policy"),
 "access_and_persistence":("user_access","operational_security","case_archive","audit_log","case_catalog","historical_report","research_export","named_user_ui"),
}

def compose(version:str):
 if getattr(core,"_cerai_runtime_composed",False):return getattr(core,"_cerai_case_archive_runtime",None)
 core.APP_VERSION=version;core.app.title=f"CER-AI v{version}";reports.APP_VERSION=version
 hc_age_policy.install(core,score_audit_owner=bootstrap);status_rank_policy.install(core);critical_score_highlight.install(core,reports)
 erss_visual_morphology_policy.install(erss_topography_guard);erss_topography_evidence_policy.install(core)
 # Add source-locked PS3 fields beneath the canonical ERSS merge; core.merge_extractions identity remains unchanged.
 ps3_extraction_policy.install(core,erss_topography_guard)
 inter_eye_tomography_policy.install(core,compatibility_owner=bootstrap);microkeratome_planning_policy.install(core);nice_policy.install(core)
 ps3_runtime_policy.install(core)
 assessment_workflow.install(core);randleman_report_readiness_policy.install(assessment_workflow);ps3_report_policy.install(reports)
 user_access.install(core);operational_security.install(core)
 archive_required=os.getenv("CERAI_ARCHIVE_REQUIRED","0").strip()=="1";archive_enabled=os.getenv("CERAI_ARCHIVE_ENABLED","0").strip()=="1" or archive_required
 archive_runtime=case_archive.install(core) if archive_enabled else case_archive.install(core,runtime=case_archive.CaseArchiveRuntime(None,required=False))
 audit_log.install(core,archive_runtime);case_catalog.install(core,archive_runtime);historical_report.install(core,archive_runtime);research_export.install(core,archive_runtime);named_user_ui.install(core);pentacam_targeted_reread.install(core);topometric_index_review_policy.install(core,reports);erss_auto_read_policy.install(core)
 app.state.cerai_canonical_runtime_ready=True;core._cerai_runtime_composed=True;core._cerai_composition_phases=COMPOSITION_PHASES;return archive_runtime
