"""Read-only adapter from reconciled canonical data to ClinicalCoreInput.

The adapter performs no clinical scoring and owns no screen-specific readers.
It maps already-reconciled canonical fields into the pure clinical core.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from clinical_core.pipeline import ClinicalCoreInput
from clinical_core.refraction import normalize_minus_cylinder
import ps3_runtime_policy


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _first_number(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = mapping.get(key)
        if _finite(value):
            return float(value)
    return None


def _refraction(mapping: Mapping[str, Any], prefix: str):
    sphere = _first_number(mapping, f"{prefix}_sphere_D", f"{prefix}_entered_sphere_D")
    cylinder = _first_number(mapping, f"{prefix}_cylinder_signed_D")
    if cylinder is None:
        magnitude = _first_number(mapping, f"{prefix}_cylinder_magnitude_D")
        if magnitude is not None:
            cylinder = -abs(magnitude)
    axis = _first_number(mapping, f"{prefix}_axis_deg")
    if sphere is None or cylinder is None or axis is None:
        return None
    return normalize_minus_cylinder(sphere, cylinder, axis)


def _mrse(mapping: Mapping[str, Any], prefix: str):
    normalized = _refraction(mapping, prefix)
    if normalized is not None:
        return normalized.mrse_d
    return _first_number(mapping, f"{prefix}_mrse_D", f"{prefix}_MRSE_D")


def _ablation(plan):
    return _first_number(plan, "max_ablation_um", "ablation_um")


def _front_map_srax(eye):
    value = _first_number(eye, "srax_deg")
    return value if value is not None and 0.0 <= value <= 90.0 else None


def build_inter_eye_ps3(extracted):
    source = {
        item.get("eye"): item
        for item in extracted.get("eyes", [])
        if item.get("eye") in {"OD", "OS"}
    }
    return ps3_runtime_policy._inter_eye(source)


def build_clinical_core_input(eye, plan, *, age_years, extracted=None):
    procedure = str(plan.get("procedure") or "").strip().upper()
    manifest = _refraction(plan, "manifest")
    intended = _refraction(plan, "intended")
    manifest_mrse = manifest.mrse_d if manifest is not None else _mrse(plan, "manifest")
    intended_mrse = intended.mrse_d if intended is not None else _mrse(plan, "intended")

    intended_sphere = intended.sphere_d if intended is not None else _first_number(
        plan, "intended_sphere_D", "intended_entered_sphere_D"
    )
    intended_cylinder = intended.cylinder_d if intended is not None else _first_number(
        plan, "intended_cylinder_signed_D"
    )
    intended_axis = intended.axis_deg if intended is not None else _first_number(plan, "intended_axis_deg")

    i_s = _first_number(plan, "surgeon_I_S_D")
    if i_s is None:
        i_s = _first_number(eye, "I_S")

    ps3_eye = ps3_runtime_policy._eye_input(dict(eye), dict(plan))
    ps3_inter_eye = build_inter_eye_ps3(extracted) if extracted is not None else None

    return ClinicalCoreInput(
        procedure=procedure,
        age_years=age_years,
        thinnest_um=_first_number(eye, "pachy_thinnest_um"),
        i_s_d=i_s,
        derived_srax_deg=_front_map_srax(eye),
        manifest_mrse_d=manifest_mrse,
        intended_sphere_d=intended_sphere,
        intended_cylinder_d=intended_cylinder,
        intended_axis_deg=intended_axis,
        flap_um=_first_number(plan, "flap_um"),
        ablation_um=_ablation(plan),
        preop_kmean_d=_first_number(eye, "Kmean_D"),
        intended_mrse_d=intended_mrse,
        final_bad_d=_first_number(eye, "BAD_D"),
        bad_df=_first_number(eye, "Df"),
        bad_db=_first_number(eye, "Db"),
        bad_dp=_first_number(eye, "Dp"),
        bad_dt=_first_number(eye, "Dt"),
        bad_da=_first_number(eye, "Da"),
        artmax_um=_first_number(eye, "ARTmax_um"),
        ppi_min=_first_number(eye, "PPI_min"),
        ppi_avg=_first_number(eye, "PPI_avg"),
        ppi_max=_first_number(eye, "PPI_max"),
        # NICE consumes the same canonical fields; there is no NICE-specific reader.
        nice_k2_d=_first_number(eye, "K2_D"),
        nice_central_pachy_um=_first_number(eye, "central_pachy_um"),
        nice_b_ele_th_um=_first_number(eye, "B_Ele_Th_um"),
        ps3_eye=ps3_eye,
        ps3_inter_eye=ps3_inter_eye,
    )
