"""Pure CER-AI ERSS/topography rules.

No runtime mutation, application imports, presentation behavior, or downstream
correction layers belong here. BAD, NICE, PS3, safety and planning rules live in
their own canonical modules.
"""
from __future__ import annotations

from math import isfinite
from typing import Optional

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
    needed and is not consulted. When I-S is <= +1.00 D, SRAX must be known
    because a value >20.0° escalates the same single topography row to the
    inferior-steepening/SRA category. Missing SRAX is therefore UNCERTAIN, not
    silently equivalent to a negative SRAX finding. Exact 20.0° is negative.
    I-S and SRAX are never added.
    """
    i_s_category = signed_i_s_category(i_s_d)
    if i_s_category == UNCERTAIN:
        return UNCERTAIN
    if i_s_category in {INFERIOR_STEEPENING_SRA, ABNORMAL_ECTATIC}:
        return i_s_category
    if not _finite(derived_srax_deg):
        return UNCERTAIN
    if float(derived_srax_deg) > 20.0:
        return INFERIOR_STEEPENING_SRA
    return i_s_category
