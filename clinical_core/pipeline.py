"""Explicit side-effect-free CER-AI clinical-core pipeline.

Pipeline stages calculate structured findings only. ``finalize_disposition`` is
the sole owner of final PASS/CAUTION/STOP-DEFER/ASSESSMENT INCOMPLETE.

External workflow boundaries remain deliberately outside this clinical core:
readiness, identity/source validation, contact-lens washout, clinical eligibility,
planning fallback orchestration, reporting/rendering, and archive persistence.
External clinical findings may be supplied to the finalizer, but this module does
not calculate those external rules and no downstream layer may override the final
canonical disposition.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Optional

from .bad import BADContext, evaluate_bad
from .disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from .erss import erss_disposition, erss_total
from .nice import nice_disposition, score_nice
from .ps3 import PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from .refraction import MIXED, normalize_minus_cylinder, refractive_group, scalar_final_k_is_valid
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
    "final_disposition",
)


@dataclass(frozen=True)
class ClinicalCoreInput:
    procedure: str
    age_years: Optional[float] = None
    thinnest_um: Optional[float] = None
    i_s_d: Optional[float] = None
    derived_srax_deg: Optional[float] = None
    srax_gt20_confirmed: Optional[bool] = None
    manifest_mrse_d: Optional[float] = None
    intended_sphere_d: Optional[float] = None
    intended_cylinder_d: Optional[float] = None
    intended_axis_deg: Optional[float] = None
    flap_um: Optional[float] = None
    ablation_um: Optional[float] = None
    preop_kmean_d: Optional[float] = None
    intended_mrse_d: Optional[float] = None
    final_bad_d: Optional[float] = None
    bad_df: Optional[float] = None
    bad_db: Optional[float] = None
    bad_dp: Optional[float] = None
    bad_dt: Optional[float] = None
    bad_da: Optional[float] = None
    artmax_um: Optional[float] = None
    ppi_min: Optional[float] = None
    ppi_avg: Optional[float] = None
    ppi_max: Optional[float] = None
    nice_k2_d: Optional[float] = None
    nice_central_pachy_um: Optional[float] = None
    nice_b_ele_th_um: Optional[float] = None
    ps3_eye: Optional[PS3EyeInput] = None
    ps3_inter_eye: Optional[PS3InterEyeInput] = None


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _bad_d_disposition(classification: str) -> str:
    if classification == "ABNORMAL":
        return STOP_DEFER
    if classification == "SUSPICIOUS":
        return CAUTION
    if classification == "NORMAL":
        return PASS
    return ASSESSMENT_INCOMPLETE


def _ps3_procedure_disposition(ps3_result, procedure: str) -> str:
    if ps3_result is None:
        return ASSESSMENT_INCOMPLETE
    selected = {
        "LASIK": ps3_result.disposition.lasik,
        "PRK": ps3_result.disposition.prk,
        "SMILE": ps3_result.disposition.smile,
    }.get((procedure or "").strip().upper())
    if selected == "DEFER":
        return STOP_DEFER
    if selected == "ALLOWED" and ps3_result.complete:
        return PASS
    return ASSESSMENT_INCOMPLETE


def _intended_refraction(inp: ClinicalCoreInput):
    if not _finite(inp.intended_sphere_d) or not _finite(inp.intended_cylinder_d):
        return None
    cylinder = float(inp.intended_cylinder_d)
    if abs(cylinder) <= 1e-12:
        axis = float(inp.intended_axis_deg) if _finite(inp.intended_axis_deg) else 0.0
    elif _finite(inp.intended_axis_deg):
        axis = float(inp.intended_axis_deg)
    else:
        return None
    return normalize_minus_cylinder(inp.intended_sphere_d, cylinder, axis)


def _safety_status(
    procedure: str,
    inp: ClinicalCoreInput,
    rsb,
    rst,
    pta,
    final_k,
    intended_group,
) -> tuple[str, dict, list[str]]:
    hard_stops = {
        "preop_thickness": preop_thickness_hard_stop(inp.thinnest_um),
        "sphere_magnitude": sphere_magnitude_hard_stop(inp.intended_sphere_d),
        "lasik_rsb": procedure == "LASIK" and lasik_rsb_hard_stop(rsb),
        "lasik_pta": procedure == "LASIK" and lasik_pta_hard_stop(pta),
        "prk_rst": procedure == "PRK" and prk_rst_hard_stop(rst),
        "final_kmean": final_kmean_hard_stop(final_k),
    }

    missing: list[str] = []
    required = (
        ("thinnest_um", inp.thinnest_um),
        ("intended_sphere_d", inp.intended_sphere_d),
        ("intended_cylinder_d", inp.intended_cylinder_d),
        ("ablation_um", inp.ablation_um),
        ("preop_kmean_d", inp.preop_kmean_d),
        ("intended_mrse_d", inp.intended_mrse_d),
    )
    missing.extend(name for name, value in required if not _finite(value))
    if _finite(inp.intended_cylinder_d) and abs(float(inp.intended_cylinder_d)) > 1e-12 and not _finite(inp.intended_axis_deg):
        missing.append("intended_axis_deg")
    if procedure == "LASIK" and not _finite(inp.flap_um):
        missing.append("flap_um")
    if procedure == "LASIK" and rsb is None and "flap_um" not in missing:
        missing.append("LASIK_RSB_um")
    if procedure == "PRK" and rst is None:
        missing.append("PRK_RST_um")
    if intended_group == MIXED:
        missing.append("mixed_astigmatism_meridional_final_k_assessment")
    elif intended_group is None:
        missing.append("intended_refractive_group")
    elif final_k is None:
        missing.append("estimated_final_Kmean_D")

    missing = list(dict.fromkeys(missing))
    if any(hard_stops.values()):
        return STOP_DEFER, hard_stops, missing
    if missing:
        return ASSESSMENT_INCOMPLETE, hard_stops, missing
    return PASS, hard_stops, []


def evaluate_normalized_case(
    inp: ClinicalCoreInput,
    *,
    external_findings: Iterable[DecisionFinding] = (),
) -> dict:
    procedure = (inp.procedure or "").strip().upper()

    intended_refraction = _intended_refraction(inp)
    intended_group = refractive_group(intended_refraction) if intended_refraction is not None else None

    rsb = lasik_rsb_um(inp.thinnest_um, inp.flap_um, inp.ablation_um) if procedure == "LASIK" else None
    rst = prk_rst_um(inp.thinnest_um, inp.ablation_um) if procedure == "PRK" else None
    pta = lasik_pta_percent(inp.thinnest_um, inp.flap_um, inp.ablation_um) if procedure == "LASIK" else None

    scalar_final_k_valid = intended_refraction is not None and scalar_final_k_is_valid(intended_refraction)
    final_k = estimated_final_kmean_d(inp.preop_kmean_d, inp.intended_mrse_d) if scalar_final_k_valid else None

    erss = None
    erss_status = PASS
    if procedure in {"LASIK", "PRK"}:
        erss = erss_total(
            inp.age_years,
            inp.thinnest_um,
            inp.i_s_d,
            inp.derived_srax_deg,
            rsb if procedure == "LASIK" else rst,
            inp.manifest_mrse_d,
            inp.srax_gt20_confirmed,
        )
        erss_status = erss_disposition(erss["total"])

    bad = evaluate_bad(
        inp.final_bad_d,
        context=BADContext(
            df=inp.bad_df,
            db=inp.bad_db,
            dp=inp.bad_dp,
            dt=inp.bad_dt,
            da=inp.bad_da,
            artmax_um=inp.artmax_um,
            ppi_min=inp.ppi_min,
            ppi_avg=inp.ppi_avg,
            ppi_max=inp.ppi_max,
        ),
    )
    bad_status = _bad_d_disposition(bad.classification)

    nice = score_nice(
        inp.nice_k2_d,
        inp.nice_central_pachy_um,
        inp.nice_b_ele_th_um,
        inp.i_s_d,
    )
    nice_status = nice_disposition(nice["total"])

    ps3_result = evaluate_ps3(inp.ps3_eye, inp.ps3_inter_eye) if inp.ps3_eye is not None else None
    ps3_status = _ps3_procedure_disposition(ps3_result, procedure)

    safety_status, safety_stops, safety_missing = _safety_status(
        procedure, inp, rsb, rst, pta, final_k, intended_group
    )

    safety_detail = "Independent tissue/refractive safety gates"
    if intended_group == MIXED:
        safety_detail += "; scalar MRSE/Kmean final-K model prohibited for mixed astigmatism"

    core_findings = (
        DecisionFinding("randleman_erss", erss_status, "ERSS" if procedure in {"LASIK", "PRK"} else "Not applicable"),
        DecisionFinding("bad_d", bad_status, f"Final BAD-D: {bad.classification}"),
        DecisionFinding("nice", nice_status, f"NICE total: {nice.get('total')!r}"),
        DecisionFinding("ps3", ps3_status, "PS3 procedure disposition"),
        DecisionFinding("procedural_safety", safety_status, safety_detail),
    )
    supplied_findings = tuple(external_findings)
    if any(not isinstance(item, DecisionFinding) for item in supplied_findings):
        raise TypeError("external_findings must contain DecisionFinding objects only")
    findings = core_findings + supplied_findings
    final = finalize_disposition(findings)

    return {
        "pipeline_order": PIPELINE_ORDER,
        "procedure": procedure,
        "intended_refractive_group": intended_group,
        "erss": erss,
        "erss_status": erss_status,
        "bad_d": {"result": bad, "classification": bad.classification, "status": bad_status},
        "nice": nice,
        "nice_status": nice_status,
        "ps3": ps3_result,
        "ps3_status": ps3_status,
        "procedural_safety": {
            "LASIK_RSB_um": rsb,
            "PRK_RST_um": rst,
            "LASIK_PTA_percent": pta,
            "estimated_final_Kmean_D": final_k,
            "scalar_final_Kmean_model_valid": scalar_final_k_valid,
            "hard_stops": safety_stops,
            "missing": safety_missing,
            "status": safety_status,
        },
        "decision_findings": findings,
        "external_findings": supplied_findings,
        "final_disposition": final,
        "status": final.status,
    }
