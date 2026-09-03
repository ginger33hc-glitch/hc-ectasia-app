"""Server-side transport for mobile CER-AI assessments.

Uploads complete first. The canonical /analyze function then runs in an
independent asyncio task while the browser polls a short-lived opaque job id.
This module does not alter clinical extraction, scoring, readiness, reporting,
or archive semantics.
"""
from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
import secrets
from time import monotonic
from typing import Any

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.datastructures import Headers


JOB_TTL_SECONDS = 60 * 60
MAX_JOBS = 64
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 80 * 1024 * 1024
_CLIENT_SCRIPT = "/static/analysis-jobs-client.js?v=1"
_APP_HTML = Path("static/index.html")

_jobs: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()


def _prune_locked() -> None:
    now = monotonic()
    expired = [job_id for job_id, job in _jobs.items() if job["expires"] <= now]
    for job_id in expired:
        job = _jobs.pop(job_id, None)
        task = (job or {}).get("task")
        if task and not task.done():
            task.cancel()
    while len(_jobs) > MAX_JOBS:
        oldest = min(_jobs, key=lambda key: _jobs[key]["created"])
        job = _jobs.pop(oldest)
        task = job.get("task")
        if task and not task.done():
            task.cancel()


async def _capture_uploads(images: list[UploadFile]) -> list[dict[str, Any]]:
    if not images:
        raise HTTPException(400, "No images supplied.")
    if len(images) > 6:
        raise HTTPException(422, "CER-AI accepts at most 6 images.")
    captured = []
    total = 0
    for image in images:
        data = await image.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(413, f"{image.filename or 'image'} exceeds the temporary upload limit.")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise HTTPException(413, "Uploaded images exceed the temporary assessment limit.")
        captured.append({
            "filename": image.filename or "image.jpg",
            "content_type": image.content_type or "application/octet-stream",
            "data": data,
        })
    return captured


def _uploads(captured: list[dict[str, Any]]) -> list[UploadFile]:
    return [
        UploadFile(
            file=BytesIO(item["data"]),
            filename=item["filename"],
            headers=Headers({"content-type": item["content_type"]}),
        )
        for item in captured
    ]


async def _run(core, job_id: str) -> None:
    async with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "PROCESSING"
        job["updated"] = monotonic()
        payload = dict(job["payload"])
        captured = list(job["images"])
    try:
        result = await core.analyze(
            images=_uploads(captured),
            age=payload["age"],
            eye_plans=payload["eye_plans"],
            patient_modifiers=payload["patient_modifiers"],
            patient_metadata=payload["patient_metadata"],
            assessment_request_id=job_id,
        )
    except HTTPException as exc:
        async with _lock:
            job = _jobs.get(job_id)
            if job:
                job.update(status="FAILED", http_status=exc.status_code, error=exc.detail,
                           updated=monotonic(), expires=monotonic() + JOB_TTL_SECONDS)
        return
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        async with _lock:
            job = _jobs.get(job_id)
            if job:
                job.update(status="FAILED", http_status=500, error=str(exc),
                           updated=monotonic(), expires=monotonic() + JOB_TTL_SECONDS)
        return
    async with _lock:
        job = _jobs.get(job_id)
        if job:
            job.update(status="COMPLETED", result=result, updated=monotonic(),
                       expires=monotonic() + JOB_TTL_SECONDS)
            # Raw image bytes are no longer needed after canonical /analyze has
            # created its readiness/report state. Release them promptly.
            job["images"] = []


def _render_app() -> HTMLResponse:
    html = _APP_HTML.read_text(encoding="utf-8")
    tag = f'<script src="{_CLIENT_SCRIPT}"></script>'
    if tag not in html:
        html = html.replace("</head>", f"  {tag}\n</head>", 1)
    return HTMLResponse(html)


def install(core) -> None:
    if getattr(core, "_cerai_analysis_jobs_installed", False):
        return

    # Replace only the presentation route so the client-side transport shim is
    # loaded before the existing inline application code. Clinical /analyze is
    # deliberately left untouched as the single clinical authority.
    core.app.router.routes[:] = [
        route for route in core.app.router.routes
        if not (getattr(route, "path", None) == "/app" and "GET" in (getattr(route, "methods", None) or set()))
    ]

    @core.app.get("/app", include_in_schema=False)
    async def clinical_app_with_jobs() -> HTMLResponse:
        return _render_app()

    @core.app.post("/analysis/jobs", include_in_schema=False, status_code=202)
    async def create_analysis_job(
        images: list[UploadFile] = File(...),
        age: int | None = Form(None),
        eye_plans: str = Form("{}"),
        patient_modifiers: str = Form("{}"),
        patient_metadata: str = Form("{}"),
        assessment_request_id: str | None = Form(None),
    ) -> JSONResponse:
        captured = await _capture_uploads(images)
        job_id = secrets.token_urlsafe(32)
        now = monotonic()
        async with _lock:
            _prune_locked()
            _jobs[job_id] = {
                "created": now,
                "updated": now,
                "expires": now + JOB_TTL_SECONDS,
                "status": "UPLOADED",
                "images": captured,
                "payload": {
                    "age": age,
                    "eye_plans": eye_plans,
                    "patient_modifiers": patient_modifiers,
                    "patient_metadata": patient_metadata,
                    "client_request_id": assessment_request_id,
                },
                "result": None,
                "error": None,
                "http_status": None,
                "task": None,
            }
            task = asyncio.create_task(_run(core, job_id))
            _jobs[job_id]["task"] = task
        return JSONResponse({
            "job_id": job_id,
            "status": "UPLOADED",
            "message": "Images received. CER-AI assessment is running on the server.",
        }, status_code=202)

    @core.app.get("/analysis/jobs/{job_id}", include_in_schema=False)
    async def analysis_job_status(job_id: str) -> JSONResponse:
        async with _lock:
            _prune_locked()
            job = _jobs.get(job_id)
            if not job:
                raise HTTPException(410, "Assessment job expired or the server restarted.")
            job["expires"] = monotonic() + JOB_TTL_SECONDS
            status = job["status"]
            if status == "COMPLETED":
                return JSONResponse({"job_id": job_id, "status": status, "result": job["result"]})
            if status == "FAILED":
                return JSONResponse({
                    "job_id": job_id,
                    "status": status,
                    "detail": job["error"],
                }, status_code=int(job.get("http_status") or 500))
            return JSONResponse({"job_id": job_id, "status": status}, status_code=202)

    core._cerai_analysis_jobs_installed = True
