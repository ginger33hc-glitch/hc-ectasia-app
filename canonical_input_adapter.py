"""Canonical read-only adapter from reconciled data to ``ClinicalCoreInput``.

This module owns treatment-role normalization exactly once. It performs no
clinical scoring and owns no screen-specific readers. Source extraction is
already complete before this boundary.

Treatment-role precedence is explicit:
1. surgeon-entered values for that role;
2. one unambiguous CONFIDENT Düzeltme Miktarı treatment-card value;
3. for intended treatment only, manifest refraction when the intended role is
   wholly blank.
A partially entered role is never completed from another source.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Optional

from clinical_core.pipeline import ClinicalCoreInput
from clinical_core.ps3 import PS3EyeInput, PS3InterEyeInput
from clinical_core.refraction import normalize_minus_cylinder


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _first_number(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = mapping.get(key)
        if _finite(value):
            return float(value)
    return None


def _role_keys(prefix: str) -> tuple[str, ...]:
    return (
        f"{prefix}_entered_sphere_D",
        f"{prefix}_cylinder_signed_D",
        f"{prefix}_sphere_D",
        f"{prefix}_cylinder_magnitude_D",
        f"{prefix}_axis_deg",
        f"{prefix}_entered_axis_deg",
        f"{prefix}_normalized_axis_deg",
    )


def _role_supplied(plan: Mapping[str, Any], prefix: str) -> bool:
    return any(plan.get(key) is not None for key in _role_keys(prefix))


def _raw_axis(mapping: Mapping[str, Any], prefix: str) -> Optional[float]:
    aliases = [f"{prefix}_axis_deg", f"{prefix}_entered_axis_deg"]
    # The existing browser/API contract may provide one shared entered axis.
    aliases.append("entered_axis_deg")
    return _first_number(mapping, *aliases)


def _normalized_axis(mapping: Mapping[str, Any], prefix: str) -> Optional[float]:
    aliases = [f"{prefix}_normalized_axis_deg", f"{prefix}_axis_deg"]
    if prefix == "intended":
        aliases.append("correction_axis_deg")
    return _first_number(mapping, *aliases)


def _refraction(mapping: Mapping[str, Any], prefix: str):
    """Normalize one role without mixing raw and already-normalized notation."""
    entered_sphere = _first_number(mapping, f"{prefix}_entered_sphere_D")
    signed_cylinder = _first_number(mapping, f"{prefix}_cylinder_signed_D")
    raw_present = (
        mapping.get(f"{prefix}_entered_sphere_D") is not None
        or mapping.get(f"{prefix}_cylinder_signed_D") is not None
    )
    if raw_present:
        if entered_sphere is None or signed_cylinder is None:
            return None
        axis = _raw_axis(mapping, prefix)
        if abs(signed_cylinder) <= 1e-12 and axis is None:
            axis = 0.0
        if axis is None:
            return None
        return normalize_minus_cylinder(entered_sphere, signed_cylinder, axis)

    sphere = _first_number(mapping, f"{prefix}_sphere_D")
    magnitude = _first_number(mapping, f"{prefix}_cylinder_magnitude_D")
    normalized_present = (
        mapping.get(f"{prefix}_sphere_D") is not None
        or mapping.get(f"{prefix}_cylinder_magnitude_D") is not None
    )
    if normalized_present:
        if sphere is None or magnitude is None:
            return None
        axis = _normalized_axis(mapping, prefix)
        if abs(magnitude) <= 1e-12 and axis is None:
            axis = 0.0
        if axis is None:
            return None
        return normalize_minus_cylinder(sphere, -abs(magnitude), axis)
    return None


def _mrse(mapping: Mapping[str, Any], prefix: str):
    normalized = _refraction(mapping, prefix)
    if normalized is not None:
        return normalized.mrse_d
    return _first_number(mapping, f"{prefix}_mrse_D", f"{prefix}_MRSE_D")


def _card_correction(extracted: Mapping[str, Any] | None, eye_name: str | None):
    if not isinstance(extracted, Mapping) or eye_name not in {"OD", "OS"}:
        return None
    candidates = []
    for item in extracted.get("treatment_corrections") or []:
        if not isinstance(item, Mapping) or item.get("eye") != eye_name:
            continue
        if str(item.get("source_label") or "").upper() != "DUZELTME_MIKTARI":
            continue
        if str(item.get("sphere_cylinder_status") or "").upper() != "CONFIDENT":
            continue
        sphere = item.get("sphere_D")
        cylinder = item.get("cylinder_D")
        if not _finite(sphere) or not _finite(cylinder):
            continue
        axis = item.get("axis_deg")
        axis_confident = str(item.get("axis_status") or "").upper() == "CONFIDENT"
        candidates.append((
            float(sphere),
            float(cylinder),
            float(axis) if axis_confident and _finite(axis) else None,
        ))
    unique = list(dict.fromkeys(candidates))
    return unique[0] if len(unique) == 1 else None


def _set_raw_role(plan: dict[str, Any], prefix: str, correction) -> None:
    sphere, cylinder, axis = correction
    plan[f"{prefix}_entered_sphere_D"] = sphere
    plan[f"{prefix}_cylinder_signed_D"] = cylinder
    if axis is not None:
        plan[f"{prefix}_axis_deg"] = axis


def _copy_manifest_to_intended(plan: dict[str, Any]) -> None:
    """Copy one complete notation family; never synthesize a partial role."""
    manifest_raw = (
        plan.get("manifest_entered_sphere_D"),
        plan.get("manifest_cylinder_signed_D"),
    )
    if all(value is not None for value in manifest_raw):
        plan["intended_entered_sphere_D"] = manifest_raw[0]
        plan["intended_cylinder_signed_D"] = manifest_raw[1]
        axis = _raw_axis(plan, "manifest")
        if axis is not None:
            plan["intended_axis_deg"] = axis
        return

    manifest_normalized = (
        plan.get("manifest_sphere_D"),
        plan.get("manifest_cylinder_magnitude_D"),
    )
    if all(value is not None for value in manifest_normalized):
        plan["intended_sphere_D"] = manifest_normalized[0]
        plan["intended_cylinder_magnitude_D"] = manifest_normalized[1]
        axis = _normalized_axis(plan, "manifest")
        if axis is not None:
            plan["intended_normalized_axis_deg"] = axis


def resolve_eye_plan(
    plan: Mapping[str, Any],
    *,
    extracted: Mapping[str, Any] | None = None,
    eye_name: str | None = None,
) -> dict[str, Any]:
    """Resolve source precedence without mutating the caller's plan."""
    resolved = deepcopy(dict(plan or {}))
    correction = _card_correction(extracted, eye_name)

    manifest_supplied = _role_supplied(resolved, "manifest")
    intended_supplied = _role_supplied(resolved, "intended")

    if not manifest_supplied and correction is not None:
        _set_raw_role(resolved, "manifest", correction)
        resolved["manifest_source"] = "TREATMENT_CARD_DUZELTME_MIKTARI"

    if not intended_supplied:
        if correction is not None:
            _set_raw_role(resolved, "intended", correction)
            resolved["intended_source"] = "TREATMENT_CARD_DUZELTME_MIKTARI"
        else:
            _copy_manifest_to_intended(resolved)
            if _role_supplied(resolved, "intended"):
                resolved["intended_source"] = "DEFAULTED_FROM_MANIFEST"

    return resolved


def resolve_case_plans(
    extracted: Mapping[str, Any],
    eye_plans: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        eye: resolve_eye_plan(plan, extracted=extracted, eye_name=eye)
        for eye, plan in eye_plans.items()
        if eye in {"OD", "OS"} and isinstance(plan, Mapping)
    }


def _ablation(plan):
    return _first_number(plan, "max_ablation_um", "ablation_um")


def _front_map_srax(eye):
    value = _first_number(eye, "srax_deg")
    return value if value is not None and 0.0 <= value <= 90.0 else None


def _surgeon_confirmed_srax(eye):
    state = str(eye.get("srax") or "").upper()
    if state not in {"YES", "NO"}:
        return None
    for item in (eye.get("field_provenance") or {}).get("srax") or []:
        if isinstance(item, dict) and str(item.get("source") or "").upper() == "SURGEON_CONFIRMED":
            return state
    return None


def _ps3_eye(eye, manifest):
    srax_deg = _front_map_srax(eye)
    return PS3EyeInput(
        anterior_km_d=_first_number(eye, "Kmean_D"),
        thinnest_um=_first_number(eye, "pachy_thinnest_um"),
        topographic_astig_d=_first_number(eye, "topographic_astig_D"),
        topographic_steep_axis_deg=_first_number(eye, "topographic_steep_axis_deg"),
        manifest_astig_d=abs(manifest.cylinder_d) if manifest is not None else None,
        manifest_axis_deg=manifest.axis_deg if manifest is not None else None,
        ppi_avg=_first_number(eye, "PPI_avg"),
        f_ele_th_um=_first_number(eye, "F_Ele_Th_um"),
        b_ele_th_um=_first_number(eye, "B_Ele_Th_um"),
        srax=None if srax_deg is not None else _surgeon_confirmed_srax(eye),
        srax_deg=srax_deg,
    )


def build_inter_eye_ps3(extracted):
    source = {
        item.get("eye"): item
        for item in extracted.get("eyes", [])
        if item.get("eye") in {"OD", "OS"}
    }
    if set(source) != {"OD", "OS"}:
        return None
    od, os = source["OD"], source["OS"]
    return PS3InterEyeInput(
        od_anterior_km_d=_first_number(od, "Kmean_D"),
        os_anterior_km_d=_first_number(os, "Kmean_D"),
        od_posterior_km_d=_first_number(od, "posterior_Kmean_D"),
        os_posterior_km_d=_first_number(os, "posterior_Kmean_D"),
        od_thinnest_um=_first_number(od, "pachy_thinnest_um"),
        os_thinnest_um=_first_number(os, "pachy_thinnest_um"),
        od_front_elevation_thinnest_um=_first_number(od, "F_Ele_Th_um"),
        os_front_elevation_thinnest_um=_first_number(os, "F_Ele_Th_um"),
        od_back_elevation_thinnest_um=_first_number(od, "B_Ele_Th_um"),
        os_back_elevation_thinnest_um=_first_number(os, "B_Ele_Th_um"),
    )


def build_clinical_core_input(eye, plan, *, age_years, extracted=None):
    resolved = resolve_eye_plan(
        plan,
        extracted=extracted,
        eye_name=eye.get("eye") if isinstance(eye, Mapping) else None,
    )
    manifest = _refraction(resolved, "manifest")
    intended = _refraction(resolved, "intended")
    manifest_mrse = manifest.mrse_d if manifest is not None else _mrse(resolved, "manifest")
    intended_mrse = intended.mrse_d if intended is not None else _mrse(resolved, "intended")

    intended_sphere = intended.sphere_d if intended is not None else _first_number(
        resolved, "intended_sphere_D", "intended_entered_sphere_D"
    )
    intended_cylinder = intended.cylinder_d if intended is not None else _first_number(
        resolved, "intended_cylinder_signed_D"
    )
    if intended_cylinder is None:
        magnitude = _first_number(resolved, "intended_cylinder_magnitude_D")
        if magnitude is not None:
            intended_cylinder = -abs(magnitude)
    intended_axis = intended.axis_deg if intended is not None else _normalized_axis(resolved, "intended")

    i_s = _first_number(resolved, "surgeon_I_S_D")
    if i_s is None:
        i_s = _first_number(eye, "I_S")

    return ClinicalCoreInput(
        procedure=str(resolved.get("procedure") or "").strip().upper(),
        age_years=age_years,
        thinnest_um=_first_number(eye, "pachy_thinnest_um"),
        i_s_d=i_s,
        derived_srax_deg=_front_map_srax(eye),
        manifest_mrse_d=manifest_mrse,
        intended_sphere_d=intended_sphere,
        intended_cylinder_d=intended_cylinder,
        intended_axis_deg=intended_axis,
        flap_um=_first_number(resolved, "flap_um"),
        ablation_um=_ablation(resolved),
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
        nice_k2_d=_first_number(eye, "K2_D"),
        nice_central_pachy_um=_first_number(eye, "central_pachy_um"),
        nice_b_ele_th_um=_first_number(eye, "B_Ele_Th_um"),
        ps3_eye=_ps3_eye(eye, manifest),
        ps3_inter_eye=build_inter_eye_ps3(extracted) if extracted is not None else None,
    )
