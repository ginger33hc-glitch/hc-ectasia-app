"""Install the canonical three-category disposition contract."""
import bootstrap
from clinical_disposition import STATUS_RANK, combine_status

core = bootstrap.core

_STATUS_RANK = STATUS_RANK


def combine_status_hc(current: str, new: str) -> str:
    return combine_status(current, new)


core.combine_status = combine_status_hc
core._hc_status_rank_policy_installed = True
