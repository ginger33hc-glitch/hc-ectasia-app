"""Canonical aggregate-status ranking for HC decisions.

Adds PASS WITH CAUTION as a valid engine status so bilateral/overall aggregation cannot
raise KeyError after the final-decision hierarchy returns the new classification.
"""
import bootstrap

core = bootstrap.core

_STATUS_RANK = {
    "PASS": 0,
    "PASS WITH CAUTION": 1,
    "POST-REFRACTIVE PATHWAY REQUIRED": 2,
    "DATA INSUFFICIENT": 3,
    "REVIEW — NOT CLEARED": 4,
    "CAUTION — DEFER": 5,
    "CAUTION — STOP/DEFER": 5,
    "DO NOT PROCEED": 6,
    "FAIL": 6,
}


def combine_status_hc(current: str, new: str) -> str:
    """Return the more restrictive known HC status without crashing on a valid status."""
    current_rank = _STATUS_RANK.get(current)
    new_rank = _STATUS_RANK.get(new)
    if current_rank is None or new_rank is None:
        raise ValueError(f"Unknown HC decision status: current={current!r}, new={new!r}")
    return new if new_rank > current_rank else current


core.combine_status = combine_status_hc
core._hc_status_rank_policy_installed = True
