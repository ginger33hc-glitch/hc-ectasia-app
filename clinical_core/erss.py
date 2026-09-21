"""Pure Randleman/ERSS scoring for the CER-AI clinical core.

This module contains no runtime mutation and no presentation or persistence
behavior. Randleman returns structured rows, explicit missing dependencies, and
one canonical disposition.
"""
from __future__ import annotations

from math import isfinite
from typing import Optional

from srax_policy import srax_positive

from .disposition import ASSESSMENT_INCOMPLETE, CAUTION, PASS, STOP_DEFER
from .rules import (
    ABNORMAL_ECTATIC,
    ASYMMETRIC_BOWTIE,
    INFERIOR_STEEPENING_SRA,
    NORMAL_SYMMETRIC,
    UNCERTAIN,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
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


def _topography_missing(i_s_d, derived_srax_deg, srax_gt20_confirmed) -> list[str]:
    if signed_i_s_category(i_s_d) == UNCERTAIN:
        return ["I_S"]
    i_s_category = signed_i_s_category(i_s_d)
    if i_s_category in {INFERIOR_STEEPENING_SRA, ABNORMAL_ECTATIC}:
        return []
    if _finite(i_s_d) and float(i_s_d) < 0.0:
        return []
    if srax_positive(derived_srax_deg, srax_gt20_confirmed) is None:
        return ["SRAX"]
    return []


def erss_total(
    age_years,
    thinnest_um,
    i_s_d,
    derived_srax_deg,
    rsb_um,
    manifest_mrse_d,
    srax_gt20_confirmed: Optional[bool] = None,
):
    category = erss_topography_category(
        i_s_d,
        derived_srax_deg,
        srax_gt20_confirmed,
    )
    rows = {
        "topography": erss_topography_points(category),
        "RSB": erss_rsb_points(rsb_um),
        "age": erss_age_points(age_years),
        "pachymetry": erss_pachymetry_points(thinnest_um),
        "MRSE": erss_mrse_points(manifest_mrse_d),
    }
    missing = _topography_missing(i_s_d, derived_srax_deg, srax_gt20_confirmed)
    if rows["RSB"] is None:
        missing.append("RSB")
    if rows["age"] is None:
        missing.append("age")
    # A finite value below 480 µm is intentionally unscored by ERSS because it
    # is already an independent tissue hard stop. It is known, not missing,
    # and must never send the completion workflow back to the surgeon.
    if not _finite(thinnest_um):
        missing.append("pachymetry")
    if rows["MRSE"] is None:
        missing.append("MRSE")
    missing = list(dict.fromkeys(missing))
    total = None if missing or any(value is None for value in rows.values()) else int(sum(rows.values()))
    # A finite pachymetry value below the CER-AI clearance boundary is known
    # clinical evidence, not an unanswered ERSS input.  Preserve the absence of
    # a clearance score explicitly so readiness and every report renderer can
    # distinguish it from genuinely incomplete data without duplicating the
    # pachymetry threshold outside the canonical rule owner.
    no_clearance_score_reason = (
        "PREOP_THICKNESS_HARD_STOP"
        if _finite(thinnest_um) and rows["pachymetry"] is None and "pachymetry" not in missing
        else None
    )
    return {
        "category": category,
        "rows": rows,
        "total": total,
        "missing": missing,
        "no_clearance_score_reason": no_clearance_score_reason,
    }


def erss_disposition(total) -> str:
    if total is None:
        return ASSESSMENT_INCOMPLETE
    if total >= 4:
        return STOP_DEFER
    if total == 3:
        return CAUTION
    return PASS
