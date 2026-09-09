"""Canonical SRAX scoring evidence shared by ERSS and PS3.

Independent of extraction, report generation and either scorer's import graph.
"""
from math import isfinite
from typing import Optional


def srax_positive(derived_srax_deg=None, confirmed: Optional[bool] = None) -> Optional[bool]:
    """Shared ERSS/PS3 evidence decision: positive geometry needs surgeon confirmation.

    Preserve the measured degrees independently. A surgeon's explicit YES/NO
    controls the scoring decision; absence of an answer is never a NO.
    """
    if isinstance(confirmed, bool):
        return confirmed
    if (
        isinstance(derived_srax_deg, (int, float))
        and not isinstance(derived_srax_deg, bool)
        and isfinite(float(derived_srax_deg))
        and 0.0 <= float(derived_srax_deg) <= 20.0
    ):
        return False
    return None


