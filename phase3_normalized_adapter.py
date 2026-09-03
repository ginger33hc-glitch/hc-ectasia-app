"""Read-only Phase 3 adapter from reconciled production data to ClinicalCoreInput.

This module is the cutover boundary between the existing extraction/readiness
workflow and the new linear clinical core. It must never mutate extraction,
plans, reports, sessions, or archive state.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from clinical_core.pipeline import ClinicalCoreInput
from derived_srax import derive_srax_deg
import nice_policy
import ps3_runtime_policy


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _first_number(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = mapping.get(key)
        if _finite(value):
            return float(value)
    return None


def _signed_cylinder(mapping: Mapping[str, Any], prefix: str) -> Optional[float]:
    signed = _first_number(mapping, f"{prefix}_cylinder_signed_D")
    if signed is not None:
        return signed
    magnitude = _first_number(mapping, f"{prefix}_cylinder_magnitude_D")
    if magnitude is None:
        return None
    return -abs(magnitude)


def _mrse(mapping: Mapping[str, Any], prefix: str) -> Optional[float]:
    explicit = _first_number(mapping, f"{prefix}_mrse_D", f"{prefix}_MRSE_D")
    if explicit is not None:
        return explicit
    sphere = _first_number(mapping, f"{prefix}_sphere_D", f"{prefix}_entered_sphere_D")
    cylinder = _signed_cylinder(mapping, prefix)
    if sphere is None or cylinder is None:
        return None
    return sphere + cylinder / 2.0


def _ablation(plan: Mapping[str, Any]) -> Optional[float]:
    return _first_number(plan, "max_ablation_um", "ablation_um")


def _derived_srax(eye: Mapping[str, Any]) -> Optional[float]:
    return derive_srax_deg(
        kisa_percent=eye.get("KISA"),
        kmax_d=eye.get("Kmax_D"),
        i_s_d=eye.get("I_S"),
        astig_d=eye.get("topographic_astig_D"),
    )


def _nice_values(eye: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse the current production NICE adapter so the Phase 3 bridge does not
    # introduce a competing interpretation of Pupil Center or B.Ele.Th.
    return nice_policy.evaluate(dict(eye), dict(plan))["values"]


def build_inter_eye_ps3(extracted: Mapping[str, Any]):
    source = {
        item.get("eye"): item
        for item in extracted.get("eyes", [])
        if item.get("eye") in {"OD", "OS"}
    }
    return ps3_runtime_policy._inter_eye(source)


def build_clinical_core_input(
    eye: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    age_years: Optional[float],
    extracted: Optional[Mapping[str, Any]] = None,
) -> ClinicalCoreInput:
    """Build one immutable normalized clinical-core input from production data."""
    procedure = str(plan.get("procedure") or "").strip().upper()
    nice_values = _nice_values(eye, plan)
    manifest_mrse = _mrse(plan, "manifest")
    intended_mrse = _mrse(plan, "intended")
    intended_sphere = _first_number(plan, "intended_sphere_D", "intended_entered_sphere_D")

    ps3_eye = ps3_runtime_policy._eye_input(dict(eye), dict(plan))
    ps3_inter_eye = build_inter_eye_ps3(extracted) if extracted is not None else None

    return ClinicalCoreInput(
        procedure=procedure,
        age_years=age_years,
        thinnest_um=_first_number(eye, "pachy_thinnest_um"),
        i_s_d=_first_number(plan, "surgeon_I_S_D") if _first_number(plan, "surgeon_I_S_D") is not None else _first_number(eye, "I_S"),
        derived_srax_deg=_derived_srax(eye),
        manifest_mrse_d=manifest_mrse,
        intended_sphere_d=intended_sphere,
        flap_um=_first_number(plan, "flap_um"),
        ablation_um=_ablation(plan),
        preop_kmean_d=_first_number(eye, "Kmean_D"),
        intended_mrse_d=intended_mrse,
        final_bad_d=_first_number(eye, "BAD_D"),
        nice_k2_d=nice_values.get("K2_D"),
        nice_central_pachy_um=nice_values.get("central_pachy_um"),
        nice_b_ele_th_um=nice_values.get("B_Ele_Th_um"),
        ps3_eye=ps3_eye,
        ps3_inter_eye=ps3_inter_eye,
    )
