"""Canonical production runtime for the HC Ectasia App.

Single supported composition point. Production and production-runtime tests must import this
module rather than assembling policy wrappers independently.
"""
from pathlib import Path
import re
import pachymetry_policy as _runtime
import bootstrap
import randleman_bad_independence  # noqa: F401

core = bootstrap.core
app = _runtime.app
CANONICAL_VERSION = "0.7.38"
core.APP_VERSION = CANONICAL_VERSION
core.app.title = f"HC Ectasia App v{CANONICAL_VERSION}"


def runtime_invariants():
    """Fail startup if a decision-critical HC rule is disconnected or overwritten."""
    errors = []

    # HC age component.
    if [core.age_points(x) for x in (18, 19, 20, 21, 30)] != [3, 2, 2, 0, 0]:
        errors.append("HC age policy is not active")

    # HC-modified LASIK pachymetry component. <=480 is an independent hard stop.
    if [core.lasik_pachy_points(x) for x in (480, 481, 499, 500, 510, 511)] != [None, 2, 2, 1, 1, 0]:
        errors.append("HC pachymetry policy is not active")

    # Final BAD-D decision gate (current adopted HC boundary).
    if [core.bad_classification(x, final=True) for x in (1.6, 1.61, 2.99, 3.0)] != ["NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL"]:
        errors.append("HC Final BAD-D policy is not active")

    # Published Randleman topography point mapping must remain 0/1/3/4; there is no 2-point morphology bin.
    expected_topography = {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }
    for category, expected in expected_topography.items():
        try:
            actual = core.lasik_topography_points(category)
        except Exception as exc:
            errors.append(f"Randleman topography scorer failed for {category}: {type(exc).__name__}")
            continue
        if actual != expected:
            errors.append(f"Randleman topography mapping {category} expected {expected}, got {actual}")

    # Dedicated ERSS source isolation must be installed, not merely a generic scorer.
    try:
        import erss_topography_guard as erss
        if core.extract_one_image is not erss.extract_one_image_with_erss:
            errors.append("Dedicated ERSS anterior-curvature image reader is not active")
        if core.merge_extractions is not erss.merge_extractions_with_erss_source_guard:
            errors.append("ERSS source-aware multi-image merge is not the active merge layer")
        if core.scoring_morphology is not erss.scoring_morphology_with_dedicated_source:
            errors.append("Dedicated ERSS morphology handoff is not active")
    except Exception as exc:
        errors.append(f"ERSS source-isolation module unavailable: {type(exc).__name__}")

    # Randleman ERSS and BAD tomography must remain hard-separated.
    if not getattr(core, "_randleman_bad_independence_installed", False):
        errors.append("BAD-independent Randleman ERSS pathway is not active")

    # LASIK automatic fallback must be installed exactly once.
    if not getattr(core, "_hc_lasik_fallback_installed", False):
        errors.append("LASIK fallback planner is not active")

    # Structural constants used downstream must not drift silently.
    if getattr(core, "PRK_EPITHELIUM_UM", None) != 50:
        errors.append("PRK epithelial convention is not 50 µm")
    if getattr(core, "FINAL_KMEAN_MIN_D", None) != 36.0 or getattr(core, "FINAL_KMEAN_MAX_D", None) != 48.0:
        errors.append("Final keratometry safety bounds are not 36-48 D")

    if errors:
        raise RuntimeError("Canonical HC runtime invariant failure: " + "; ".join(errors))
    return True


runtime_invariants()

# Keep visible browser version synchronized with the canonical runtime version.
try:
    index_path = Path(__file__).parent / "static" / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = re.sub(r"HC Ectasia App v\d+\.\d+\.\d+", f"HC Ectasia App v{CANONICAL_VERSION}", html)
    html = re.sub(r"Software v\d+\.\d+\.\d+", f"Software v{CANONICAL_VERSION}", html)
    index_path.write_text(html, encoding="utf-8")
except OSError:
    pass
