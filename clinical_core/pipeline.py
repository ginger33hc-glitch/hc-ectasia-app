"""Explicit side-effect-free CER-AI clinical-core pipeline.

This is the Phase 2 parallel orchestrator.  It starts from already-normalized
clinical values and calls pure modules in a fixed, auditable order.  It is not
yet wired into the production FastAPI runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .disposition import CAUTION, DATA_INSUFFICIENT, PASS, STOP_DEFER, combine_status
from .erss import erss_disposition, erss_total
from .nice import nice_disposition, score_nice
from .ps3 import PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from .rules import bad_d_classification
from .safety import (
    estimated_final_kmean_d,
    final_kmean_hard_stop,
    lasik_pta_hard_stop,
    lasik_pta_percent,
    lasik_rsb_hard_stop,
    lasik_rsb_um,
    preop_thickness_hard_stop,
    prk_rst_hard_stop,
    prk_rst_um,
    sphere_magnitude_hard_stop,
)

PIPELINE_ORDER = (
    "normalized_input",
    "erss",
    "bad_d",
    "nice",
    "ps3",
    "procedural_safety",
    "disposition_aggregation",
)


@dataclass(frozen=True)
class ClinicalCoreInput:
    procedure: str
    age_years: Optional[float] = None
    thinnest_um: Optional[float] = None
    i_s_d: Optional[float] = None
    derived_srax_deg: Optional[float] = None
    manifest_mrse_d: Optional[float] = None
    intended_sphere_d: Optional[float] = None
    flap_um: Optional[float] = None
    ablation_um: Optional[float] = None
    preop_kmean_d: Optional[float] = None
    intended_mrse_d: Optional[float] = None
    final_bad_d: Optional[float] = None
    nice_k2_d: Optional[float] = None
    nice_central_pachy_um: Optional[float] = None
    nice_b_ele_th_um: Optional[float] = None
    ps3_eye: Optional[PS3EyeInput] = None
    ps3_inter_eye: Optional[PS3InterEyeInput] = None


def _bad_d_disposition(classification: str) -> str:
    if classification == "ABNORMAL":
        return STOP_DEFER
    if classification == "SUSPICIOUS":
        return CAUTION
    if classification == "NORMAL":
        return PASS
    return DATA_INSUFFICIENT


def _ps3_procedure_disposition(ps3_result, procedure: str) -> str:
    if ps3_result is None:
        return DATA_INSUFFICIENT
    key = (procedure or "").strip().upper()
    value = {
        "LASIK": ps3_result.disposition.lasik,
        "PRK": ps3_result.disposition.prk,
        "SMILE": ps3_result.disposition.smile,
    }.get(key)
    if value == "DEFER":
        return STOP_DEFER
    if value == "ALLOWED":
        return PASS
    return DATA_INSUFFICIENT


def evaluate_normalized_case(inp: ClinicalCoreInput) -> dict:
    """Evaluate the extracted pure-core stages in one explicit order.

    This is intentionally not the complete production engine yet: readiness,
    identity/source validation, contact-lens washout, clinical eligibility,
    treatment-card reconciliation, planning fallback, reporting and archive
    remain outside this function until their own Phase 2 extraction gates pass.
    """
    procedure = (inp.procedure or "").strip().upper()

    rsb = lasik_rsb_um(inp.thinnest_um, inp.flap_um, inp.ablation_um) if procedure == "LASIK" else None
    rst = prk_rst_um(inp.thinnest_um, inp.ablation_um) if procedure == "PRK" else None
    pta = lasik_pta_percent(inp.thinnest_um, inp.flap_um, inp.ablation_um) if procedure == "LASIK" else None
    final_k = estimated_final_kmean_d(inp.preop_kmean_d, inp.intended_mrse_d)

    erss = None
    erss_status = PASS
    if procedure == "LASIK":
        erss = erss_total(
            inp.age_years,
            inp.thinnest_um,
            inp.i_s_d,
            inp.derived_srax_deg,
            rsb,
            inp.manifest_mrse_d,
        )
        erss_status = erss_disposition(erss["total"])

    bad_class = bad_d_classification(inp.final_bad_d)
    bad_status = _bad_d_disposition(bad_class)

    nice = score_nice(
        inp.nice_k2_d,
        inp.nice_central_pachy_um,
        inp.nice_b_ele_th_um,
        inp.i_s_d,
    )
    nice_status = nice_disposition(nice["total"])

    ps3_result = evaluate_ps3(inp.ps3_eye, inp.ps3_inter_eye) if inp.ps3_eye is not None else None
    ps3_status = _ps3_procedure_disposition(ps3_result, procedure)

    safety_stops = {
        "preop_thickness": preop_thickness_hard_stop(inp.thinnest_um),
        "sphere_magnitude": sphere_magnitude_hard_stop(inp.intended_sphere_d),
        "lasik_rsb": procedure == "LASIK" and lasik_rsb_hard_stop(rsb),
        "lasik_pta": procedure == "LASIK" and lasik_pta_hard_stop(pta),
        "prk_rst": procedure == "PRK" and prk_rst_hard_stop(rst),
        "final_kmean": final_kmean_hard_stop(final_k),
    }
    safety_status = STOP_DEFER if any(safety_stops.values()) else PASS

    overall = PASS
    for status in (erss_status, bad_status, nice_status, ps3_status, safety_status):
        overall = combine_status(overall, status)

    return {
        "pipeline_order": PIPELINE_ORDER,
        "procedure": procedure,
        "erss": erss,
        "erss_status": erss_status,
        "bad_d": {"classification": bad_class, "status": bad_status},
        "nice": nice,
        "nice_status": nice_status,
        "ps3": ps3_result,
        "ps3_status": ps3_status,
        "procedural_safety": {
            "LASIK_RSB_um": rsb,
            "PRK_RST_um": rst,
            "LASIK_PTA_percent": pta,
            "estimated_final_Kmean_D": final_k,
            "hard_stops": safety_stops,
            "status": safety_status,
        },
        "status": overall,
    }
