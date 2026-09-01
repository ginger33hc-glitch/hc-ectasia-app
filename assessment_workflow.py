"""Server-authoritative readiness and resumable completion, outside the scoring engines.

Only canonical missing-data results decide readiness; no duplicated clinical score table.
Opaque random tokens reference bounded, expiring in-memory snapshots. They are never put in URLs.
Process restart/expiry requires a new upload, never trusts a client-supplied report as evidence.
"""
from copy import deepcopy
from threading import RLock
from time import monotonic
import secrets

from fastapi import HTTPException, Body, Response
from nice_scoring import finite
from pentacam_field_registry import COMPLETION_NUMERIC_FIELDS

_lock = RLock()
_sessions = {}
TTL_SECONDS = 3600
MAX_SESSIONS = 64

NUMERIC_FIELDS = COMPLETION_NUMERIC_FIELDS
PATTERNS = {"anterior_pattern": ["REASSURING", "BORDERLINE", "ABNORMAL"],
            "posterior_pattern": ["REASSURING", "BORDERLINE", "ABNORMAL"]}


def _prune():
    now = monotonic()
    for token in list(_sessions):
        if _sessions[token]["expires"] <= now:
            del _sessions[token]


def _session(token):
    _prune()
    if not isinstance(token, str) or token not in _sessions:
        raise HTTPException(410, "Assessment session expired or restarted. Upload the images again; entered form values can be retained.")
    return _sessions[token]


def missing_items(decision):
    items = [("GLOBAL", str(x)) for x in decision.get("critical_input_issues") or []]
    for eye in decision.get("eyes") or []:
        for message in eye.get("missing") or []:
            text = str(message)
            normalized = text.lower()
            if normalized == "age" or "age within" in normalized:
                items.append(("PATIENT", "age"))
            else:
                items.append((eye.get("eye", "GLOBAL"), text))
    if not decision.get("eyes"):
        items.append(("GLOBAL", "No classifiable OD/OS tomography was extracted."))
    return list(dict.fromkeys(items))


def _region_hint(extracted, eye, key):
    if eye == "PATIENT" and key == "age":
        direct = (extracted.get("document_context") or {}).get("targeted_unreadable_age_region")
        if direct:
            return direct
        hints = [
            context.get("targeted_unreadable_age_region")
            for context in extracted.get("document_contexts") or []
            if context.get("targeted_unreadable_age_region")
        ]
        return hints[0] if len(hints) == 1 else None
    for candidate in extracted.get("eyes") or []:
        if candidate.get("eye") == eye:
            return (candidate.get("targeted_unreadable_regions") or {}).get(key)
    return None


def _with_region(item, extracted):
    hint = _region_hint(extracted, item.get("eye"), item.get("key"))
    if hint and hint.get("file") and hint.get("tile"):
        return {**item, "source_region": True}
    return item


def _request(eye, message, extracted):
    if eye == "GLOBAL" and message[:2] in {"OD", "OS"}:
        eye = message[:2]
    prefix = eye.lower()
    item = {"eye": eye, "label": message, "kind": "instruction", "key": message,
            "destination": "source", "help": "Correct the clinical form or upload a clearer/correct source image."}
    exact = {
        "NICE: central_pachy_um": ("surgeon_nice_central_um", "Central pachymetry (µm; not thinnest)", "nice_central"),
        "NICE: posterior_pupil_max_um": ("surgeon_nice_pe_um", "Highest positive posterior elevation inside pupil (µm), standard 8-mm BFS Float", "nice_pe"),
        "NICE: I_S_D": ("surgeon_I_S_D", "Signed I-S (D)", "surgeon_i_s"),
    }
    if message in exact:
        key, label, suffix = exact[message]
        return _with_region({**item, "key": key, "label": label, "kind": "form", "form_id": f"{prefix}_{suffix}"}, extracted)
    text = message.lower()
    if "i-s" in text or "i_s" in text:
        return _with_region({**item, "kind": "form", "form_id": f"{prefix}_surgeon_i_s"}, extracted)
    if "topograph" in text and ("category" in text or "morphology" in text):
        return {**item, "kind": "form", "form_id": f"{prefix}_surgeon_topography"}
    for term, suffix in (("manifest sphere", "manifest_sphere"), ("manifest cylinder magnitude", "manifest_cylinder"),
                         ("intended sphere", "sphere"), ("intended cylinder magnitude", "cylinder"),
                         ("cylinder axis", "axis"), ("optical zone", "optical"), ("transition zone", "transition"),
                         ("flap thickness", "flap"), ("ablation", "ablation"), ("refractive stability", "stable"),
                         ("progression status", "progression"), ("cdva", "cdva"), ("enhancement", "enhancement"),
                         ("prior corneal", "prior")):
        if term in text:
            return {**item, "kind": "form", "form_id": f"{prefix}_{suffix}"}
    if "age" == text or "age within" in text or "age conflicts" in text:
        return _with_region({
            **item,
            "eye": "PATIENT" if eye != "GLOBAL" else eye,
            "key": "age",
            "label": "Patient age (years)",
            "kind": "form",
            "form_id": "age",
        }, extracted)
    if "contact lens" in text or "contact-lens" in text:
        return {**item, "kind": "form", "form_id": "contact_lens_days" if "discontinued" in text else "contact_lens_type"}
    if "preoperative kmean" in text:
        message = "Kmean_D"
    # Exact field tokens, not arbitrary substring replacement (Db must not match BAD_D).
    import re
    fields = [key for key in NUMERIC_FIELDS if re.search(r"(?<![A-Za-z0-9_])" + re.escape(key) + r"(?![A-Za-z0-9_])", message)]
    if message == "NICE: K2_D":
        fields = ["K2_D"]
    if len(fields) == 1 and eye in {"OD", "OS"}:
        key = fields[0]
        return _with_region({**item, "kind": "number", "key": key, "destination": "measurement", "label": NUMERIC_FIELDS[key] + " — " + item["label"]}, extracted)
    for key in PATTERNS:
        if message == "readable " + key.replace("_", " "):
            return {**item, "kind": "select", "key": key, "destination": "measurement", "options": PATTERNS[key]}
    return item


def _overrides(extracted, overrides):
    """Explicit surgeon corrections; preserve original readings and re-run the audit."""
    from extraction_guard import _audit_eye
    working = deepcopy(extracted)
    if not isinstance(overrides, dict) or set(overrides) - {"OD", "OS"}:
        raise HTTPException(422, "Invalid eye-specific completion inputs.")
    for eye in working.get("eyes", []):
        values = overrides.get(eye["eye"], {})
        if not isinstance(values, dict):
            raise HTTPException(422, "Completion values must be objects.")
        for key, value in values.items():
            if key in NUMERIC_FIELDS:
                if not finite(value):
                    raise HTTPException(422, f"{eye['eye']} {key}: a finite numeric value is required.")
            elif key in PATTERNS:
                if value not in PATTERNS[key]:
                    raise HTTPException(422, f"Invalid {key}.")
            else:
                raise HTTPException(422, f"Manual override of {key} is not supported; upload the correct source.")
            eye.setdefault("surgeon_corrections", []).append({"field": key, "original": eye.get(key), "value": value})
            eye[key] = value
            if key in NUMERIC_FIELDS:
                eye["surgeon_verified_numeric_fields"] = sorted(set(eye.get("surgeon_verified_numeric_fields") or []) | {key})
                eye.setdefault("field_provenance", {})[key] = [{"source": "SURGEON_CONFIRMED"}]
            resolved = [x for x in eye.get("data_conflicts") or [] if str(x).split(":", 1)[0].strip() == key]
            eye.setdefault("surgeon_resolved_conflicts", []).extend(resolved)
            eye["data_conflicts"] = [x for x in eye.get("data_conflicts") or [] if x not in resolved]
        if values:
            old_audit = eye.get("extraction_validation") or {}
            old_messages = {f"{eye['eye']} extraction validation: {x}" for x in old_audit.get("issues") or []}
            working["critical_input_issues"] = [x for x in working.get("critical_input_issues") or [] if x not in old_messages]
            audit = _audit_eye(eye)
            eye["extraction_validation"] = audit
            working.setdefault("extraction_validation", {})[eye["eye"]] = audit
            working.setdefault("critical_input_issues", []).extend(f"{eye['eye']} extraction validation: {x}" for x in audit["issues"])
    return working


def _respond(core, token, session, age, plans, modifiers, metadata, overrides):
    for value in (plans, modifiers, metadata):
        if not isinstance(value, dict):
            raise HTTPException(422, "Clinical inputs must be objects.")
    if set(plans) - {"OD", "OS"} or any(not isinstance(value, dict) for value in plans.values()):
        raise HTTPException(422, "Plans must contain OD/OS objects.")
    if age is not None and (not finite(age) or int(age) != age):
        raise HTTPException(422, "Age must be a whole number.")
    overrides = deepcopy(overrides)
    if not isinstance(overrides, dict) or any(not isinstance(value, dict) for value in overrides.values()):
        raise HTTPException(422, "Clinical overrides must be an object.")
    # A surgeon-confirmed I-S resolves the same source conflict for BOTH ERSS and NICE.
    for eye, plan in plans.items():
        if plan.get("surgeon_I_S_D") is not None:
            overrides.setdefault(eye, {})["I_S"] = plan["surgeon_I_S_D"]
    extracted = _overrides(session["extracted"], overrides)
    for eye in extracted.get("eyes", []):
        plan = plans.get(eye["eye"], {})
        category = plan.get("surgeon_topography_category")
        if plan.get("procedure") == "PRK" and category in core.MORPHOLOGY and category != "UNCERTAIN" and eye.get("morphology") in {None, "UNCERTAIN"}:
            eye["morphology"] = category
            eye.setdefault("morphology_evidence", []).append("Category explicitly confirmed by surgeon during input completion.")
    effective = core.apply_extracted_corrections(deepcopy(extracted), deepcopy(plans))
    decision = core.hc_engine(deepcopy(extracted), age, effective, modifiers, metadata)
    missing = missing_items(decision)
    response = {"assessment_token": token, "extracted": extracted, "effective_eye_plans": effective,
                "workflow_status": "NEEDS_INPUT" if missing else "READY", "missing": [],
                "input_requests": [], "report_token": None}
    session["ready"] = None
    if missing:
        response["missing"] = [{"eye": eye, "message": message} for eye, message in missing]
        response["input_requests"] = [_request(eye, message, extracted) for eye, message in missing]
        response["message"] = "Complete all required information below before any clinical report can be produced."
    else:
        report_token = secrets.token_urlsafe(32)
        session["ready"] = {"report_token": report_token, "patient": deepcopy(metadata),
                            "decision": deepcopy(decision), "extracted": deepcopy(extracted)}
        response.update({"decision": decision, "report_token": report_token})
    session["region_requests"] = {
        (item.get("eye"), item.get("key"))
        for item in response["input_requests"]
        if item.get("source_region")
    }
    # Preserve corrections across resume attempts, but never overwrite the original image values silently.
    session["extracted"] = extracted
    session["expires"] = monotonic() + TTL_SECONDS
    return response


def begin(core, extracted, age, plans, modifiers, metadata, source_images=None):
    with _lock:
        _prune()
        if len(_sessions) >= MAX_SESSIONS:
            raise HTTPException(
                503,
                "Assessment capacity is temporarily full. Existing active assessments were preserved; retry after an earlier session expires.",
                headers={"Retry-After": "60"},
            )
        token = secrets.token_urlsafe(32)
        session = {
            "extracted": deepcopy(extracted),
            "expires": monotonic() + TTL_SECONDS,
            "ready": None,
            "source_images": list(source_images or []),
        }
        _sessions[token] = session
        return _respond(core, token, session, age, plans, modifiers, metadata, {})


def complete(core, payload):
    with _lock:
        token = payload.get("assessment_token")
        session = _session(token)
        # Invalidate any earlier ready snapshot before accepting edits, including invalid edits.
        session["ready"] = None
        return _respond(core, token, session, payload.get("age"), payload.get("eye_plans", {}),
                        payload.get("patient_modifiers", {}), payload.get("patient_metadata", {}),
                        payload.get("clinical_overrides", {}))


def export_payload(payload):
    with _lock:
        session = _session(payload.get("assessment_token"))
        ready = session.get("ready")
        if not ready or not secrets.compare_digest(str(payload.get("report_token") or ""), ready["report_token"]):
            raise HTTPException(409, "Complete all required inputs and obtain a current ready assessment before exporting.")
        exported = deepcopy(ready)
        # Locale is presentation-only and may be selected after the locked
        # clinical assessment. Never copy decision data from the export request.
        exported["locale"] = "tr" if str(payload.get("locale") or "").lower().startswith("tr") else "en"
        return exported


def install(core):
    @core.app.post("/assessment/complete")
    def complete_assessment(payload: dict = Body(...)):
        return complete(core, payload)

    @core.app.post("/assessment/source-region")
    def assessment_source_region(payload: dict = Body(...)):
        eye = payload.get("eye")
        key = payload.get("key")
        if eye not in {"OD", "OS", "PATIENT"} or not isinstance(key, str):
            raise HTTPException(422, "Invalid source-region request.")
        with _lock:
            session = _session(payload.get("assessment_token"))
            if (eye, key) not in session.get("region_requests", set()):
                raise HTTPException(404, "No unresolved localized source region is available.")
            hint = deepcopy(_region_hint(session["extracted"], eye, key))
            matches = [
                raw for raw, filename in session.get("source_images") or []
                if hint and filename == hint.get("file")
            ]
        if not hint:
            raise HTTPException(404, "No localized unread source region is available.")
        if len(matches) != 1:
            raise HTTPException(404, "The localized source image is unavailable or ambiguous.")
        from pentacam_targeted_reread import render_source_region
        try:
            content = render_source_region(matches[0], hint.get("tile"), hint.get("source_box"))
        except (OSError, ValueError) as exc:
            raise HTTPException(422, "The localized source region could not be rendered.") from exc
        return Response(
            content=content,
            media_type="image/png",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    core._hc_readiness_installed = True
