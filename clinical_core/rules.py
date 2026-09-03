"""Pure CER-AI launch-contract rules.

No runtime mutation, no application imports, and no presentation behavior.
These functions encode only rules already frozen by the Phase 1 launch
behavior contract. They are introduced in parallel first; production wiring
must not move here until equivalence tests are green.
"""
from __future__ import annotations

from math import isfinite
from typing import Optional


NORMAL = "NORMAL"
SUSPICIOUS = "SUSPICIOUS"
ABNORMAL = "ABNORMAL"

NORMAL_SYMMETRIC = "NORMAL_SYMMETRIC"
ASYMMETRIC_BOWTIE = "ASYMMETRIC_BOWTIE"
INFERIOR_STEEPENING_SRA = "INFERIOR_STEEPENING_SRA"
ABNORMAL_ECTATIC = "ABNORMAL_ECTATIC"
UNCERTAIN = "UNCERTAIN"

_CATEGORY_RANK = {
    NORMAL_SYMMETRIC: 0,
    ASYMMETRIC_BOWTIE: 1,
    INFERIOR_STEEPENING_SRA: 3,
    ABNORMAL_ECTATIC: 4,
}


def _finite(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def erss_age_points(age_years) -> Optional[int]:
    """CER-AI age component frozen at launch."""
    if not _finite(age_years) or float(age_years) < 18:
        return None
    age = float(age_years)
    if age < 19:
        return 3
    if age < 21:
        return 2
    return 0


def erss_pachymetry_points(thinnest_um) -> Optional[int]:
    """CER-AI LASIK pachymetry component; <480 is handled as a hard stop."""
    if not _finite(thinnest_um):
        return None
    value = float(thinnest_um)
    if value < 480:
        return None
    if value < 500:
        return 2
    if value < 510:
        return 1
    return 0


def bad_d_classification(value) -> str:
    """Final BAD-D launch classification."""
    if not _finite(value):
        return "UNAVAILABLE"
    value = float(value)
    if value <= 1.60:
        return NORMAL
    if value < 2.60:
        return SUSPICIOUS
    return ABNORMAL


def signed_i_s_category(i_s_d) -> str:
    """Return the mutually exclusive CER-AI signed Topometric I-S category."""
    if not _finite(i_s_d):
        return UNCERTAIN
    value = float(i_s_d)
    if value >= 1.40:
        return ABNORMAL_ECTATIC
    if value > 1.00:
        return INFERIOR_STEEPENING_SRA
    if value > 0.50:
        return ASYMMETRIC_BOWTIE
    if value < -0.50:
        return ASYMMETRIC_BOWTIE
    return NORMAL_SYMMETRIC


def erss_topography_category(i_s_d, derived_srax_deg=None) -> str:
    """Select one ERSS topography category from numeric authorities only.

    Signed Topometric I-S and derived SRAX are the only authorities. The
    original Randleman SRA/SRAX threshold is >=20 degrees. The higher-risk
    single category wins; categories are never added together.
    """
    candidates = []
    i_s_category = signed_i_s_category(i_s_d)
    if i_s_category != UNCERTAIN:
        candidates.append(i_s_category)

    if _finite(derived_srax_deg) and float(derived_srax_deg) >= 20.0:
        candidates.append(INFERIOR_STEEPENING_SRA)

    if not candidates:
        return UNCERTAIN
    return max(candidates, key=_CATEGORY_RANK.__getitem__)
