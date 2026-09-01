"""Install the canonical three-category disposition contract."""
from clinical_disposition import STATUS_RANK, combine_status

_STATUS_RANK = STATUS_RANK


def combine_status_hc(current: str, new: str) -> str:
    return combine_status(current, new)


def install(core) -> None:
    """Attach status aggregation explicitly and at most once."""
    if getattr(core, "_hc_status_rank_policy_installed", False):
        return
    core.combine_status = combine_status_hc
    core._hc_status_rank_policy_installed = True
