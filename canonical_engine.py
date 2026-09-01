"""Canonical production runtime for CER-AI.

Single supported composition point. Production and production-runtime tests must import this
module rather than assembling policy wrappers independently.
"""
import runtime_composition as composition

core = composition.core
app = composition.app
CANONICAL_VERSION = "0.7.66"
_archive_runtime = composition.compose(CANONICAL_VERSION)


def runtime_invariants():
    """Fail startup if a decision-critical CER-AI rule is disconnected or overwritten."""
    errors = []

    if [core.age_points(x) for x in (18, 19, 20, 21, 30)] != [3, 2, 2, 0, 0]:
        errors.append("CER-AI age policy is not active")
    if [core.lasik_pachy_points(x) for x in (479, 480, 481, 499, 500, 509, 510, 511)] != [None, 2, 2, 2, 1, 1, 0, 0]:
        errors.append("CER-AI pachymetry policy is not active")
    if [core.bad_classification(x, final=True) for x in (1.6, 1.61, 2.5999, 2.6)] != ["NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL"]:
        errors.append("CER-AI Final BAD-D policy is not active")

    expected_topography = {"NORMAL_SYMMETRIC":0,"ASYMMETRIC_BOWTIE":1,"INFERIOR_STEEPENING_SRA":3,"ABNORMAL_ECTATIC":4}
    for category, expected in expected_topography.items():
        try:actual=core.lasik_topography_points(category)
        except Exception as exc:
            errors.append(f"Randleman topography scorer failed for {category}: {type(exc).__name__}");continue
        if actual != expected:errors.append(f"Randleman topography mapping {category} expected {expected}, got {actual}")

    try:
        erss = composition.erss_topography_guard
        erss_evidence = composition.erss_topography_evidence_policy
        targeted = composition.pentacam_targeted_reread
        if core.extract_one_image is not targeted.extract_one_image_with_targeted_reread:errors.append("Targeted Pentacam numeric reread is not active")
        if targeted._previous_extract_one_image is not erss.extract_one_image_with_erss:errors.append("Dedicated ERSS reader is not preserved immediately below the targeted numeric reread")
        if core.merge_extractions is not erss.merge_extractions_with_erss_source_guard:errors.append("ERSS source-aware multi-image merge is not the active merge layer")
        if core.scoring_morphology is not erss_evidence.scoring_morphology_with_i_s_evidence_gate:errors.append("ERSS I-S evidence gate is not the active morphology handoff")
        if erss_evidence._previous_scoring_morphology is not erss.scoring_morphology_with_dedicated_source:errors.append("Dedicated ERSS morphology reader is not preserved immediately below the I-S evidence gate")
    except Exception as exc:errors.append(f"ERSS source-isolation module unavailable: {type(exc).__name__}")

    if not getattr(core,"_erss_visual_morphology_policy_installed",False):errors.append("Improved ERSS visual morphology policy is not active")
    if not getattr(core,"_randleman_bad_independence_installed",False):errors.append("BAD-independent Randleman ERSS pathway is not active")
    if not getattr(core,"_hc_final_decision_hierarchy_installed",False):errors.append("CER-AI final BAD-D/Randleman decision hierarchy is not active")
    if not getattr(core,"_hc_status_rank_policy_installed",False):errors.append("CER-AI aggregate status ranking is not active")
    if not getattr(core,"_hc_inter_eye_tomography_policy_installed",False):errors.append("Automated inter-eye tomography concern layer is not active")
    if not getattr(core,"_hc_microkeratome_planning_installed",False):errors.append("Post-assessment ML7 microkeratome planning layer is not active")
    if not getattr(core,"_hc_nice_installed",False):errors.append("Independent CER-AI NICE policy is not active")
    if not getattr(core,"_hc_readiness_installed",False):errors.append("Pre-report readiness workflow is not active")
    if not getattr(core,"_cerai_named_user_access_installed",False):errors.append("Named-user access boundary is not active")
    if not getattr(core,"_cerai_operational_security_installed",False):errors.append("Operational security boundary is not active")
    if not getattr(core,"_cerai_case_archive_installed",False):errors.append("Encrypted case archive boundary is not active")
    if not getattr(core,"_cerai_audit_log_installed",False):errors.append("Encrypted audit-log boundary is not active")
    if not getattr(core,"_cerai_case_catalog_installed",False):errors.append("Encrypted case catalog boundary is not active")
    if not getattr(core,"_cerai_historical_report_installed",False):errors.append("Historical report regeneration boundary is not active")
    if not getattr(core,"_cerai_research_export_installed",False):errors.append("Research export boundary is not active")
    if not getattr(core,"_cerai_named_user_ui_installed",False):errors.append("Named-user archive UI boundary is not active")
    if not getattr(core,"_erss_topography_evidence_policy_installed",False):errors.append("ERSS I-S/topography evidence gate is not active")
    if not getattr(core,"_erss_auto_read_policy_installed",False):errors.append("ERSS morphology auto-read separation policy is not active")
    if not getattr(core,"_cerai_targeted_pentacam_reread_installed",False):errors.append("Targeted Pentacam numeric reread layer is not active")
    if getattr(core.lasik_topography_points, "__module__", None) != "app":errors.append("ERSS evidence gate must not replace or duplicate the canonical topography point mapper")
    try:
        if core.combine_status("PASS", "PASS WITH CAUTION") != "PASS WITH CAUTION":errors.append("PASS WITH CAUTION aggregate ranking is invalid")
        if core.combine_status("PASS WITH CAUTION", "DO NOT PROCEED") != "DO NOT PROCEED":errors.append("Hard-stop aggregate ranking is invalid")
    except Exception as exc:errors.append(f"Aggregate status ranking failed: {type(exc).__name__}")
    if not getattr(core,"_hc_lasik_fallback_installed",False):errors.append("LASIK fallback planner is not active")
    if getattr(core,"PRK_EPITHELIUM_UM",None) != 50:errors.append("PRK epithelial convention is not 50 µm")
    if getattr(core,"FINAL_KMEAN_MIN_D",None) != 36.0 or getattr(core,"FINAL_KMEAN_MAX_D",None) != 48.0:errors.append("Final keratometry safety bounds are not 36-48 D")
    if getattr(composition.reports,"APP_VERSION",None) != CANONICAL_VERSION:errors.append("Report version is not synchronized with canonical runtime")
    if getattr(core, "_cerai_composition_phases", None) != composition.COMPOSITION_PHASES:errors.append("Canonical composition manifest is not active")

    if errors:raise RuntimeError("Canonical CER-AI runtime invariant failure: " + "; ".join(errors))
    return True


runtime_invariants()
