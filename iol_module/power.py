"""Canonical Stage 2 IOL power-routing service."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .lens_catalog import get_lens
from .models import (
    AstigmatismType,
    IOLPowerPlan,
    IOLPowerPlanInput,
    PriorCornealSurgery,
)

COOKE_K6_URL = os.getenv(
    "COOKE_K6_API_URL", "https://cookeformula.com/api/v1/k6/v2024.01/preop"
)
ESCRS_URL = "https://iolcalculator.escrs.org/"
ASCRS_POST_REFRACTIVE_URL = "https://iolcalc.ascrs.org/"


def _target_from_acd(acd_mm: float) -> float:
    if acd_mm < 2.5:
        return 0.0
    if acd_mm > 3.5:
        return -0.5
    return -0.25


def _second_formula_required(al_mm: float) -> bool:
    return al_mm < 22.0 or al_mm > 26.0


def _base_inputs(case: IOLPowerPlanInput) -> dict[str, object]:
    values: dict[str, object] = {
        "eye": case.eye,
        "biological_sex": case.biological_sex,
        "axial_length_mm": case.axial_length_mm,
        "acd_internal_mm": case.acd_mm,
        "k1_d": case.k1_d,
        "k1_axis_deg": case.k1_axis_deg,
        "k2_d": case.k2_d,
        "k2_axis_deg": case.k2_axis_deg,
        "astigmatism_d": case.astigmatism_d,
        "target_refraction_d": _target_from_acd(case.acd_mm),
    }
    for key, value in {
        "cct_um": case.cct_um,
        "lens_thickness_mm": case.lens_thickness_mm,
        "wtw_mm": case.wtw_mm,
        "incision_axis_deg": case.incision_axis_deg,
        "sia_d": case.sia_d,
        "sia_axis_deg": case.sia_axis_deg,
    }.items():
        if value is not None:
            values[key] = value
    return values


def _external_plan(case: IOLPowerPlanInput, lens, *, route: str, name: str, url: str | None, message: str) -> IOLPowerPlan:
    status = "EXTERNAL_REQUIRED" if url else "CALCULATION_UNAVAILABLE"
    return IOLPowerPlan(
        route=route,
        calculation_status=status,
        selected_lens_id=lens.id,
        selected_lens_name=lens.name,
        lens_category=lens.category,
        a_constant=lens.a_constant,
        target_refraction_d=_target_from_acd(case.acd_mm),
        target_locked=True,
        target_warning=None,
        second_formula_required=_second_formula_required(case.axial_length_mm),
        calculator_name=name,
        calculator_url=url,
        escrs_url=None,
        inputs=_base_inputs(case),
        predictions=[],
        message=message,
    )


def _k6_payload(case: IOLPowerPlanInput, a_constant: float) -> dict[str, object]:
    eye: dict[str, object] = {
        "SpecialSituation": "None",
        "TgtRx": _target_from_acd(case.acd_mm),
        "K1": case.k1_d,
        "K2": case.k2_d,
        "Biometer": "Other",
        "AL": case.axial_length_mm,
        "ACD": case.acd_mm,
    }
    if case.cct_um is not None:
        eye["CCT"] = case.cct_um
    if case.lens_thickness_mm is not None:
        eye["LT"] = case.lens_thickness_mm
    if case.wtw_mm is not None:
        eye["WTW"] = case.wtw_mm
    return {
        "KIndex": 1.3375,
        "PredictionsPerIol": 7,
        "IOLs": [{"AConstant": a_constant, "Family": "Other", "Powers": [{"From": 6, "To": 30, "By": 0.5}]}],
        "Eyes": [eye],
    }


def _call_k6(case: IOLPowerPlanInput, a_constant: float) -> list[dict[str, object]]:
    raw = json.dumps(_k6_payload(case, a_constant)).encode("utf-8")
    request = Request(
        COOKE_K6_URL,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CER-AI-IOL/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    eyes = payload.get("Eyes") if isinstance(payload, dict) else payload
    if not isinstance(eyes, list) or not eyes:
        raise ValueError("Cooke K6 returned no eye result.")
    iols = eyes[0].get("IOLs", []) if isinstance(eyes[0], dict) else []
    predictions = iols[0].get("Predictions", []) if iols and isinstance(iols[0], dict) else []
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("Cooke K6 returned no power predictions.")
    return predictions


def plan_iol_power(case: IOLPowerPlanInput) -> IOLPowerPlan:
    lens = get_lens(case.selected_lens_id)
    if lens is None:
        raise ValueError("Selected lens is not in the clinic-approved catalog.")

    toric = case.astigmatism_d >= 1.0 and case.astigmatism_type == AstigmatismType.REGULAR
    if case.prior_corneal_surgery in {
        PriorCornealSurgery.MYOPIC_LASIK_PRK,
        PriorCornealSurgery.HYPEROPIC_LASIK_PRK,
    }:
        history = "history" if case.historical_data_available else "no-history"
        return _external_plan(
            case, lens, route="BARRETT_TRUE_K_EXTERNAL", name="ASCRS post-refractive / Barrett True-K",
            url=ASCRS_POST_REFRACTIVE_URL,
            message=f"Prior LASIK/PRK overrides the standard route. Use the Barrett True-K {history} pathway externally.",
        )
    if case.prior_corneal_surgery == PriorCornealSurgery.RK:
        return _external_plan(
            case, lens, route="POST_RK_EXTERNAL", name="ASCRS post-RK calculator",
            url=ASCRS_POST_REFRACTIVE_URL,
            message="Prior RK requires the external post-RK calculation pathway.",
        )
    if toric:
        inputs = _base_inputs(case)
        try:
            spherical_predictions = _call_k6(case, lens.a_constant)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            return IOLPowerPlan(
                route="MANUFACTURER_TORIC", calculation_status="CALCULATION_UNAVAILABLE",
                selected_lens_id=lens.id, selected_lens_name=lens.name,
                lens_category=lens.category, a_constant=lens.a_constant,
                target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
                target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm),
                calculator_name="Cooke K6 spherical power", calculator_url=lens.toric_calculator_url,
                escrs_url=None, inputs=inputs, predictions=[],
                message=f"Cooke K6 spherical calculation was unavailable ({type(exc).__name__}). No toric power or axis was selected.",
            )
        return IOLPowerPlan(
            route="MANUFACTURER_TORIC",
            calculation_status="EXTERNAL_REQUIRED" if lens.toric_calculator_url else "CALCULATION_UNAVAILABLE",
            selected_lens_id=lens.id, selected_lens_name=lens.name,
            lens_category=lens.category, a_constant=lens.a_constant,
            target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
            target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm),
            calculator_name=f"{lens.manufacturer} toric calculator", calculator_url=lens.toric_calculator_url,
            escrs_url=None, inputs=inputs, predictions=spherical_predictions,
            message=(
                "Cooke K6 spherical power is shown below. Its predicted refraction is spherical only; "
                "toric cylinder, residual cylinder and implantation axis require the official toric calculator. "
                "Enter the selected spherical power and verify all biometry there."
                if lens.toric_calculator_url else
                "Cooke K6 spherical power is shown below. No verified toric calculator is configured "
                "for this manufacturer; toric cylinder and implantation axis are unavailable."
            ),
        )

    inputs = _base_inputs(case)
    try:
        predictions = _call_k6(case, lens.a_constant)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return IOLPowerPlan(
            route="COOKE_K6", calculation_status="CALCULATION_UNAVAILABLE",
            selected_lens_id=lens.id, selected_lens_name=lens.name,
            lens_category=lens.category, a_constant=lens.a_constant,
            target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
            target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm), calculator_name="Cooke K6", calculator_url=None,
            escrs_url=ESCRS_URL, inputs=inputs, predictions=[],
            message=f"Cooke K6 could not complete the calculation. No substitute was used ({type(exc).__name__}).",
        )
    return IOLPowerPlan(
        route="COOKE_K6", calculation_status="COMPLETED",
        selected_lens_id=lens.id, selected_lens_name=lens.name,
        lens_category=lens.category, a_constant=lens.a_constant,
        target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
        target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm), calculator_name="Cooke K6", calculator_url=None,
        escrs_url=ESCRS_URL, inputs=inputs, predictions=predictions,
        message="Cooke K6 calculation completed. The ESCRS calculator is provided as the external comparison route.",
    )
