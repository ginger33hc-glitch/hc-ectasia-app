"""HTTP boundary for the independent IOL module."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import Body, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

import operational_security

from .engine import evaluate_case
from .extraction import extract_image, validate_source_bundle
from .lens_catalog import public_catalog
from .escrs_transfer import create_escrs_transfer
from .models import EscrsTransferInput, IOLCaseInput, IOLPowerPlanInput
from .power import plan_iol_power

IOL_HTML = Path("static/iol.html")


def install(core: Any) -> None:
    if getattr(core, "_cerai_iol_module_installed", False):
        return

    @core.app.get("/iol", include_in_schema=False)
    def iol_page():
        return HTMLResponse(
            IOL_HTML.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-store"},
        )

    @core.app.post("/iol/extract")
    async def iol_extract(images: list[UploadFile] = File(...)):
        if len(images) != 3:
            raise HTTPException(422, "Exactly three IOL source images are required.")
        payloads = await operational_security.read_uploads(images)
        results = []
        for raw, filename in payloads:
            try:
                result = await asyncio.to_thread(extract_image, core, raw, filename)
            except Exception as exc:
                raise HTTPException(502, f"Unable to transcribe {filename}.") from exc
            results.append({"filename": filename, "extraction": result})
        try:
            identity = validate_source_bundle(results)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"sources": results, "identity": identity}

    @core.app.post("/iol/evaluate")
    def iol_evaluate(payload: dict[str, Any] = Body(...)):
        try:
            case = IOLCaseInput.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        return evaluate_case(case).model_dump(mode="json")

    @core.app.get("/iol/lenses")
    def iol_lenses():
        return {"lenses": public_catalog()}

    @core.app.post("/iol/power/plan")
    def iol_power_plan(payload: dict[str, Any] = Body(...)):
        try:
            case = IOLPowerPlanInput.model_validate(payload)
            return plan_iol_power(case).model_dump(mode="json")
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @core.app.post("/iol/escrs-transfer")
    def iol_escrs_transfer(payload: dict[str, Any] = Body(...)):
        try:
            case = EscrsTransferInput.model_validate(payload)
            return create_escrs_transfer(case)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc

    core._cerai_iol_module_installed = True
