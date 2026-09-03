"""Phase 4 compatibility marker for the canonical disposition contract.

The production core already defines ``combine_status`` as a direct delegate to
``clinical_disposition.combine_status``.  This module therefore no longer
replaces that callable at install time; it only verifies the canonical wiring
and records the compatibility marker expected by the current composition.
"""
from clinical_disposition import STATUS_RANK, combine_status

_STATUS_RANK = STATUS_RANK


def combine_status_hc(current: str, new: str) -> str:
    """Compatibility alias retained for historical tests/importers."""
    return combine_status(current, new)


def install(core) -> None:
    """Verify native status aggregation without monkey-patching the core."""
    if getattr(core, "_hc_status_rank_policy_installed", False):
        return

    native = getattr(core, "combine_status", None)
    if not callable(native):
        raise RuntimeError("Canonical core combine_status is unavailable")
    if native("PASS", "CAUTION") != "CAUTION":
        raise RuntimeError("Canonical CAUTION status aggregation is invalid")
    if native("CAUTION", "STOP-DEFER") != "STOP-DEFER":
        raise RuntimeError("Canonical STOP-DEFER status aggregation is invalid")

    core._hc_status_rank_policy_installed = True
