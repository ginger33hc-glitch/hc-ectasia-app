"""Server-authoritative readiness and resumable completion, outside the scoring engines.

Only canonical missing-data results decide readiness; no duplicated clinical score table.
Opaque random tokens reference bounded, expiring in-memory snapshots. They are never put in URLs.
Process restart/expiry requires a new upload, never trusts a client-supplied report as evidence.
"""
from copy import deepcopy
from threading import RLock
from time import monotonic
import secrets

from fastapi import HTTPException, Body
from nice_scoring import finite

_lock = RLock()
_sessions = {}
TTL_SECONDS = 3600
MAX_SESSIONS = 64

NUMERIC_FIELDS = {
    "pachy_thinnest_um": "Thinnest pachymetry (µm)", "BAD_D": "Final BAD-D",
    "Df": "BAD Df", "Db": "BAD Db", "Dp": "BAD Dp", "Dt": "BAD Dt", "Da": "BAD Da",
    "ARTmax_um": "ARTmax (µm)", "PPI_min": "PPI minimum", "PPI_avg": "PPI average",
    "PPI_max": "PPI maximum", "K1_D": "K1 (D)", "K2_D": "K2 (D; not Kmax)",
    "Kmean_D": "Preoperative Kmean (D)", "Kmax_D": "Kmax (D)",
    "srax_deg": "SRAX (degrees)", "inferior_opposite_steepening_D": "Inferior-opposite steepening (D)",
    "Rmin_mm": "Rmin (mm)", "I_S": "Signed I-S (D; not ISV/IVA)",
}
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
        items.extend((eye.get("eye", "GLOBAL"), str(x)) for x in eye.get("missing") or [])
    if not decision.get("eyes"):
        items.append(("GLOBAL", "No classifiable OD/OS tomography was extracted."))
    return list(dict.fromkeys(items))


def _request(eye, message):
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
        return {**item, "key": key, "label": label, "kind": "form", "form_id": f"{prefix}_{suffix}"}
    text = message.lower()
    if "i-s" in text or "i_s" in text:
        return {**item, "kind": "form", "form_id": f"{prefix}_surgeon_i_s"}
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
        return {**item, "kind": "form", "form_id": "age"}
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
        return {**item, "kind": "number", "key": key, "destination": "measurement", "label": NUMERIC_FIELDS[key] + " — " + item["label"]}
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
        response["input_requests"] = [_request(eye, message) for eye, message in missing]
        response["message"] = "Complete all required information below before any clinical report can be produced."
    else:
        report_token = secrets.token_urlsafe(32)
        session["ready"] = {"report_token": report_token, "patient": deepcopy(metadata),
                            "decision": deepcopy(decision), "extracted": deepcopy(extracted)}
        response.update({"decision": decision, "report_token": report_token})
    # Preserve corrections across resume attempts, but never overwrite the original image values silently.
    session["extracted"] = extracted
    session["expires"] = monotonic() + TTL_SECONDS
    return response


def begin(core, extracted, age, plans, modifiers, metadata):
    with _lock:
        _prune()
        if len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions, key=lambda token: _sessions[token]["expires"])
            del _sessions[oldest]
        token = secrets.token_urlsafe(32)
        session = {"extracted": deepcopy(extracted), "expires": monotonic() + TTL_SECONDS, "ready": None}
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
        return deepcopy(ready)


def install(core):
    @core.app.post("/assessment/complete")
    def complete_assessment(payload: dict = Body(...)):
        return complete(core, payload)
    core._hc_readiness_installed = True
