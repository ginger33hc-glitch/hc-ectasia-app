"""Pure Randleman/ERSS scoring for the CER-AI clinical core.

This module contains no runtime mutation and no presentation or persistence
behavior. Randleman returns structured rows plus one canonical disposition.
"""
from __future__ import annotations

from math import isfinite
from typing import Optional

from .disposition import ASSESSMENT_INCOMPLETE, CAUTION, PASS, STOP_DEFER
from .rules import (
    ABNORMAL_ECTATIC,
    ASYMMETRIC_BOWTIE,
    INFERIOR_STEEPENING_SRA,
    NORMAL_SYMMETRIC,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
)


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def erss_rsb_points(rsb_um) -> Optional[int]:
    if not _finite(rsb_um):
        return None
    value = float(rsb_um)
    if value < 240:
        return 4
    if value < 260:
        return 3
    if value < 280:
        return 2
    if value < 300:
        return 1
    return 0


def erss_mrse_points(manifest_mrse_d) -> Optional[int]:
    if not _finite(manifest_mrse_d):
        return None
    value = float(manifest_mrse_d)
    if value < -14:
        return 4
    if value < -12:
        return 3
    if value < -10:
        return 2
    if value < -8:
        return 1
    return 0


def erss_topography_points(category: str) -> Optional[int]:
    return {
        NORMAL_SYMMETRIC: 0,
        ASYMMETRIC_BOWTIE: 1,
        INFERIOR_STEEPENING_SRA: 3,
        ABNORMAL_ECTATIC: 4,
    }.get(category)


def erss_total(age_years, thinnest_um, i_s_d, derived_srax_deg, rsb_um, manifest_mrse_d):
    category = erss_topography_category(i_s_d, derived_srax_deg)
    rows = {
        "topography": erss_topography_points(category),
        "RSB": erss_rsb_points(rsb_um),
        "age": erss_age_points(age_years),
        "pachymetry": erss_pachymetry_points(thinnest_um),
        "MRSE": erss_mrse_points(manifest_mrse_d),
    }
    total = None if any(value is None for value in rows.values()) else int(sum(rows.values()))
    return {"category": category, "rows": rows, "total": total}


def erss_disposition(total) -> str:
    if total is None:
        return ASSESSMENT_INCOMPLETE
    if total >= 4:
        return STOP_DEFER
    if total == 3:
        return CAUTION
    return PASS
