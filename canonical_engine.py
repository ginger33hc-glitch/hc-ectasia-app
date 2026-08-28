"""Canonical production runtime for the HC Ectasia App.

This is the single supported application composition point.  Legacy policy modules remain
small, testable implementation units, but no server/test should assemble them independently.
Importing this module loads the complete HC clinical policy chain exactly once and exposes
one `app` and one `core` object.
"""
import pachymetry_policy as _runtime
import bootstrap

core = bootstrap.core
app = _runtime.app

CANONICAL_VERSION = "0.7.36"
core.APP_VERSION = CANONICAL_VERSION
core.app.title = f"HC Ectasia App v{CANONICAL_VERSION}"


def runtime_invariants():
    """Fail fast if a future edit bypasses a decision-critical HC policy."""
    errors = []
    # HC age policy
    if [core.age_points(x) for x in (18, 19, 20, 21, 30)] != [3, 2, 2, 0, 0]:
        errors.append("HC age policy is not active")
    # HC pachymetry score bands; <=480 is handled as an independent hard stop.
    if [core.lasik_pachy_points(x) for x in (480, 481, 499, 500, 510, 511)] != [None, 2, 2, 1, 1, 0]:
        errors.append("HC pachymetry policy is not active")
    # Final BAD-D gate currently follows the explicitly adopted HC boundary.
    if [core.bad_classification(x, final=True) for x in (1.6, 1.61, 2.99, 3.0)] != ["NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL"]:
        errors.append("HC Final BAD-D policy is not active")
    # Randleman source/scoring machinery must be installed independently of BAD.
    if not hasattr(core, "scoring_morphology") or not hasattr(core, "merge_extractions"):
        errors.append("Randleman/ERSS source/scoring path is unavailable")
    # LASIK fallback must have been installed exactly once.
    if not getattr(core, "_hc_lasik_fallback_installed", False):
        errors.append("LASIK fallback planner is not active")
    if errors:
        raise RuntimeError("Canonical HC runtime invariant failure: " + "; ".join(errors))
    return True


runtime_invariants()
