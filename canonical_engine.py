"""Canonical production runtime for CERAI.

Single supported composition point. Production and production-runtime tests must import this
module rather than assembling policy wrappers independently.
"""
import pachymetry_policy as _runtime
import bootstrap
import reports
import randleman_bad_independence  # noqa: F401
import erss_visual_morphology_policy  # noqa: F401
import hc_final_decision_policy  # noqa: F401
import status_rank_policy  # noqa: F401
import inter_eye_tomography_policy  # noqa: F401
import microkeratome_planning_policy  # noqa: F401
import erss_topography_evidence_policy  # noqa: F401
import nice_policy
import assessment_workflow

core = bootstrap.core
app = _runtime.app
CANONICAL_VERSION = "0.7.50"
core.APP_VERSION = CANONICAL_VERSION
core.app.title = f"CERAI v{CANONICAL_VERSION}"
reports.APP_VERSION = CANONICAL_VERSION
nice_policy.install(core)
assessment_workflow.install(core)

# ERSS morphology auto-read cleanup must wrap the fully installed assessment workflow.
# Keep it out of bootstrap so the production composition order remains explicit here.
import erss_auto_read_policy  # noqa: E402,F401


def runtime_invariants():
    """Fail startup if a decision-critical CERAI rule is disconnected or overwritten."""
    errors = []

    if [core.age_points(x) for x in (18, 19, 20, 21, 30)] != [3, 2, 2, 0, 0]:
        errors.append("CERAI age policy is not active")
    if [core.lasik_pachy_points(x) for x in (479, 480, 481, 499, 500, 509, 510, 511)] != [None, 2, 2, 2, 1, 1, 0, 0]:
        errors.append("CERAI pachymetry policy is not active")
    if [core.bad_classification(x, final=True) for x in (1.6, 1.61, 2.99, 3.0)] != ["NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL"]:
        errors.append("CERAI Final BAD-D policy is not active")

    expected_topography = {"NORMAL_SYMMETRIC":0,"ASYMMETRIC_BOWTIE":1,"INFERIOR_STEEPENING_SRA":3,"ABNORMAL_ECTATIC":4}
    for category, expected in expected_topography.items():
        try:actual=core.lasik_topography_points(category)
        except Exception as exc:
            errors.append(f"Randleman topography scorer failed for {category}: {type(exc).__name__}");continue
        if actual != expected:errors.append(f"Randleman topography mapping {category} expected {expected}, got {actual}")

    try:
        import erss_topography_guard as erss
        import erss_topography_evidence_policy as erss_evidence
        if core.extract_one_image is not erss.extract_one_image_with_erss:errors.append("Dedicated ERSS anterior-curvature image reader is not active")
        if core.merge_extractions is not erss.merge_extractions_with_erss_source_guard:errors.append("ERSS source-aware multi-image merge is not the active merge layer")
        if core.scoring_morphology is not erss_evidence.scoring_morphology_with_i_s_evidence_gate:errors.append("ERSS I-S evidence gate is not the active morphology handoff")
        if erss_evidence._previous_scoring_morphology is not erss.scoring_morphology_with_dedicated_source:errors.append("Dedicated ERSS morphology reader is not preserved immediately below the I-S evidence gate")
    except Exception as exc:errors.append(f"ERSS source-isolation module unavailable: {type(exc).__name__}")

    if not getattr(core,"_erss_visual_morphology_policy_installed",False):errors.append("Improved ERSS visual morphology policy is not active")
    if not getattr(core,"_randleman_bad_independence_installed",False):errors.append("BAD-independent Randleman ERSS pathway is not active")
    if not getattr(core,"_hc_final_decision_hierarchy_installed",False):errors.append("CERAI final BAD-D/Randleman decision hierarchy is not active")
    if not getattr(core,"_hc_status_rank_policy_installed",False):errors.append("CERAI aggregate status ranking is not active")
    if not getattr(core,"_hc_inter_eye_tomography_policy_installed",False):errors.append("Automated inter-eye tomography concern layer is not active")
    if not getattr(core,"_hc_microkeratome_planning_installed",False):errors.append("Post-assessment ML7 microkeratome planning layer is not active")
    if not getattr(core,"_hc_nice_installed",False):errors.append("Independent CERAI NICE policy is not active")
    if not getattr(core,"_hc_readiness_installed",False):errors.append("Pre-report readiness workflow is not active")
    if not getattr(core,"_erss_topography_evidence_policy_installed",False):errors.append("ERSS I-S/topography evidence gate is not active")
    if not getattr(core,"_erss_auto_read_policy_installed",False):errors.append("ERSS morphology auto-read separation policy is not active")
    if getattr(core.lasik_topography_points, "__module__", None) != "app":errors.append("ERSS evidence gate must not replace or duplicate the canonical topography point mapper")
    try:
        if core.combine_status("PASS", "PASS WITH CAUTION") != "PASS WITH CAUTION":errors.append("PASS WITH CAUTION aggregate ranking is invalid")
        if core.combine_status("PASS WITH CAUTION", "DO NOT PROCEED") != "DO NOT PROCEED":errors.append("Hard-stop aggregate ranking is invalid")
    except Exception as exc:errors.append(f"Aggregate status ranking failed: {type(exc).__name__}")
    if not getattr(core,"_hc_lasik_fallback_installed",False):errors.append("LASIK fallback planner is not active")
    if getattr(core,"PRK_EPITHELIUM_UM",None) != 50:errors.append("PRK epithelial convention is not 50 µm")
    if getattr(core,"FINAL_KMEAN_MIN_D",None) != 36.0 or getattr(core,"FINAL_KMEAN_MAX_D",None) != 48.0:errors.append("Final keratometry safety bounds are not 36-48 D")
    if getattr(reports,"APP_VERSION",None) != CANONICAL_VERSION:errors.append("Report version is not synchronized with canonical runtime")

    if errors:raise RuntimeError("Canonical CERAI runtime invariant failure: " + "; ".join(errors))
    return True


runtime_invariants()
