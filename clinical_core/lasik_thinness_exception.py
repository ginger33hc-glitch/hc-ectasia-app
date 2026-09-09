"""Canonical CER-AI exception for a thickness-only PS3 LASIK defer.

The underlying PS3 classification remains unchanged and traceable.  This policy
owns the single cross-system exception requested for LASIK: a sole PS3 moderate
finding caused by thinnest pachymetry from 490 through 500 microns may become
PASS WITH CAUTION only when ERSS, NICE, and Final BAD-D are all PASS.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from .disposition import (
    ASSESSMENT_INCOMPLETE,
    PASS,
    PASS_WITH_CAUTION,
    STOP_DEFER,
)
from .ps3 import ALLOWED, DEFER, MODERATE

LASIK_THINNESS_EXCEPTION_MIN_UM = 490.0
LASIK_THINNESS_EXCEPTION_MAX_UM = 500.0
LASIK_THINNESS_EXCEPTION_VERSION = "CERAI-PS3-THINNESS-ONLY-LASIK-490-500-V1"


@dataclass(frozen=True)
class PS3ProcedureDecision:
    status: str
    detail: str
    modification_applied: bool = False


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _raw_ps3_status(ps3_result: Any, procedure: str) -> PS3ProcedureDecision:
    if ps3_result is None:
        return PS3ProcedureDecision(
            ASSESSMENT_INCOMPLETE,
            "PS3 procedure disposition unavailable.",
        )
    selected = {
        "LASIK": ps3_result.disposition.lasik,
        "PRK": ps3_result.disposition.prk,
        "SMILE": ps3_result.disposition.smile,
    }.get(procedure)
    if selected == DEFER:
        return PS3ProcedureDecision(STOP_DEFER, f"Raw PS3 {procedure} disposition: DEFER.")
    if selected == ALLOWED and ps3_result.complete:
        return PS3ProcedureDecision(PASS, f"Raw PS3 {procedure} disposition: ALLOWED.")
    return PS3ProcedureDecision(
        ASSESSMENT_INCOMPLETE,
        f"Raw PS3 {procedure or 'selected procedure'} disposition is incomplete.",
    )


def resolve_ps3_procedure_decision(
    ps3_result: Any,
    procedure: str,
    *,
    thinnest_um: Any,
    erss_status: str,
    nice_status: str,
    bad_d_status: str,
) -> PS3ProcedureDecision:
    """Return the effective PS3 procedure decision without changing raw PS3.

    The exception is deliberately counterfactual: it applies only when the
    thinnest-pachymetry finding is the sole PS3 moderate factor.  Therefore a
    different moderate factor, two moderates, or any high factor cannot be
    relaxed by this policy.
    """
    procedure = (procedure or "").strip().upper()
    raw = _raw_ps3_status(ps3_result, procedure)
    if procedure != "LASIK" or raw.status != STOP_DEFER or ps3_result is None:
        return raw
    if not _finite(thinnest_um):
        return raw
    thickness = float(thinnest_um)
    if not LASIK_THINNESS_EXCEPTION_MIN_UM <= thickness <= LASIK_THINNESS_EXCEPTION_MAX_UM:
        return raw
    if (erss_status, nice_status, bad_d_status) != (PASS, PASS, PASS):
        return raw
    if not ps3_result.complete or ps3_result.high_count != 0 or ps3_result.moderate_count != 1:
        return raw
    thickness_findings = tuple(
        finding
        for finding in ps3_result.findings
        if finding.key == "thinnest" and finding.status == MODERATE
    )
    if len(thickness_findings) != 1:
        return raw

    return PS3ProcedureDecision(
        PASS_WITH_CAUTION,
        (
            "CER-AI modified PS3 LASIK rule: thinnest pachymetry "
            f"{thickness:g} µm is the sole PS3 moderate factor (490-500 µm), "
            "and Randleman/ERSS, NICE, and Final BAD-D are all PASS. "
            "Raw PS3 LASIK disposition DEFER is conditionally accepted as "
            "PASS WITH CAUTION."
        ),
        True,
    )
