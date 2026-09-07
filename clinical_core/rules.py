"""Pure CER-AI clinical rules.

No runtime mutation, application imports, presentation behavior, or downstream
correction layers belong here. Clinical thresholds are changed at this source.
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


def _finite(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def erss_age_points(age_years) -> Optional[int]:
    if not _finite(age_years) or float(age_years) < 18:
        return None
    age = float(age_years)
    if age < 19:
        return 3
    if age < 21:
        return 2
    return 0


def erss_pachymetry_points(thinnest_um) -> Optional[int]:
    """<480 µm is an independent hard stop and leaves this score row unscored."""
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
    if not _finite(value):
        return "UNAVAILABLE"
    value = float(value)
    if value <= 1.60:
        return NORMAL
    if value < 2.60:
        return SUSPICIOUS
    return ABNORMAL


def signed_i_s_category(i_s_d) -> str:
    """Mutually exclusive signed Topometric I-S category."""
    if not _finite(i_s_d):
        return UNCERTAIN
    value = float(i_s_d)
    if value >= 1.40:
        return ABNORMAL_ECTATIC
    if value > 1.00:
        return INFERIOR_STEEPENING_SRA
    if value > 0.50 or value < -0.50:
        return ASYMMETRIC_BOWTIE
    return NORMAL_SYMMETRIC


def erss_topography_category(i_s_d, derived_srax_deg=None) -> str:
    """Return the single Randleman topography category.

    I-S is mandatory and evaluated first. If I-S already gives inferior
    steepening (3 points) or abnormal/ectatic topography (4 points), SRAX is not
    needed and is not consulted. Only when I-S is <= +1.00 D may SRAX increase
    the category to inferior-steepening/SRA. SRAX is positive only when >20.0°;
    exactly 20.0° is negative. I-S and SRAX are never added.
    """
    i_s_category = signed_i_s_category(i_s_d)
    if i_s_category == UNCERTAIN:
        return UNCERTAIN
    if i_s_category in {INFERIOR_STEEPENING_SRA, ABNORMAL_ECTATIC}:
        return i_s_category
    if _finite(derived_srax_deg) and float(derived_srax_deg) > 20.0:
        return INFERIOR_STEEPENING_SRA
    return i_s_category
