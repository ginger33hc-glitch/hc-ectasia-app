"""Server-authoritative CER-AI assessment workflow.

This module owns transport/session/readiness/completion only. Clinical scoring is
performed exactly once by ``canonical_runtime_service.evaluate_case``. No clinical
threshold, score formula, or downstream disposition correction belongs here.
"""
from copy import deepcopy
from math import isfinite
from threading import RLock
from time import monotonic
import re
import secrets

from fastapi import Body, HTTPException, Response

from canonical_readiness import evaluate_precore_readiness
from canonical_runtime_service import evaluate_case
from pentacam_field_registry import COMPLETION_NUMERIC_FIELDS
from pentacam_canonical_source_lock import canonical_source_region
from pentacam_quality_policy import is_quality_only_issue
from pentacam_source_regions import region_hints

_lock = RLock()
_sessions = {}
TTL_SECONDS = 3600
MAX_SESSIONS = 64

NUMERIC_FIELDS = COMPLETION_NUMERIC_FIELDS
SELECT_FIELDS = {"srax": ("YES", "NO")}


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _eye_record(extracted, eye_id):
    return next(
        (item for item in (extracted or {}).get("eyes") or [] if item.get("eye") == eye_id),
        {},
    )


def _expanded_ps3_missing(eye_id, message, decision, extracted):
    """Translate a PS3 factor dependency into the exact missing source/form fields."""
    if not str(message).lower().startswith("ps3: "):
        return [(eye_id, str(message))]
    factor = str(message).split(":", 1)[1].strip().lower()
    eye = _eye_record(extracted, eye_id)
    direct = {
        "anterior_km": ("Kmean_D",),
        "thinnest": ("pachy_thinnest_um",),
        "elevation": ("F_Ele_Th_um", "B_Ele_Th_um"),
        "ppi_average": ("PPI_avg",),
    }
    if factor in direct:
        missing = [key for key in direct[factor] if not _finite(eye.get(key))]
        return [(eye_id, f"PS3: {key}") for key in missing] or [(eye_id, str(message))]
    if factor == "astigmatic_study":
        missing = [
            key for key in ("topographic_astig_D", "bad_flat_axis_deg")
            if not _finite(eye.get(key))
        ]
        plan = (decision.get("effective_eye_plans") or {}).get(eye_id) or {}
        if not _finite(plan.get("manifest_cylinder_signed_D")):
            missing.append("manifest_cylinder_signed_D")
        if not any(_finite(plan.get(key)) for key in ("manifest_axis_deg", "manifest_entered_axis_deg", "entered_axis_deg")):
            missing.append("manifest_axis_deg")
        return [(eye_id, f"PS3: {key}") for key in missing] or [(eye_id, str(message))]
    if factor == "inter_eye_asymmetry":
        missing = []
        for candidate_eye in ("OD", "OS"):
            record = _eye_record(extracted, candidate_eye)
            for key in ("Kmean_D", "posterior_Kmean_D", "pachy_thinnest_um", "F_Ele_Th_um", "B_Ele_Th_um"):
                if not _finite(record.get(key)):
                    missing.append((candidate_eye, f"PS3: {key}"))
        return missing or [(eye_id, str(message))]
    return [(eye_id, str(message))]


def _prune():
    now = monotonic()
    for token in list(_sessions):
        if _sessions[token]["expires"] <= now:
            del _sessions[token]


def _session(token):
    _prune()
    if not isinstance(token, str) or token not in _sessions:
        raise HTTPException(
            410,
            "Assessment session expired or restarted. Upload the images again; entered form values can be retained.",
        )
    return _sessions[token]


def missing_items(decision, extracted=None):
    """Collect source-validation and canonical-runtime missing dependencies."""
    items = []
    if isinstance(extracted, dict):
        items.extend(
            ("GLOBAL", str(issue))
            for issue in extracted.get("critical_input_issues") or []
            if not is_quality_only_issue(issue)
        )
    for eye in decision.get("eyes") or []:
        eye_id = eye.get("eye", "GLOBAL")
        if eye.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED":
            items.append((eye_id, "POST-REFRACTIVE PATHWAY REQUIRED"))
        for message in eye.get("missing") or []:
            if not is_quality_only_issue(message):
                items.extend(_expanded_ps3_missing(eye_id, message, decision, extracted))
    if not decision.get("eyes"):
        items.append(("GLOBAL", "No classifiable OD/OS tomography was extracted."))
    return list(dict.fromkeys(items))


def _with_region(item, extracted):
    hints = region_hints(extracted, item.get("eye"), item.get("key"))
    if hints:
        return {**item, "source_region": True, "source_region_count": len(hints)}
    return item


def _required_system(message):
    prefix = str(message).split(":", 1)[0].strip()
    return prefix if prefix in {"Randleman", "NICE", "PS3", "Safety"} else "CER-AI"


def _source_number_request(eye, key, label, extracted, *, required_for="CER-AI"):
    source = canonical_source_region(key) or {}
    return _with_region(
        {
            "eye": eye,
            "label": label,
            "kind": "number",
            "key": key,
            "destination": "measurement",
            "required_for": [required_for],
            "source_screen": source.get("screen", "Canonical source not available in registry"),
            "source_box": source.get("box", label),
            "help": "Enter the value only after confirming the indicated canonical Pentacam source box.",
        },
        extracted,
    )


def _srax_request(eye):
    return {
        "eye": eye,
        "label": "Is SRAX / skewed axis >20° on the Axial/Sagittal Curvature (Front) map?",
        "kind": "select",
        "key": "srax",
        "destination": "measurement",
        "options": ["YES", "NO"],
        "required_for": ["Randleman", "PS3"],
        "source_screen": "4 Maps Refractive",
        "source_box": "Axial/Sagittal Curvature (Front) map",
        "help": (
            "Inspect only the Axial/Sagittal Curvature (Front) map. Choose YES only when the skew amount is greater than 20°. "
            "Exact 20.0° is NO. Do not infer SRAX from KISA, I-S, Kmax, BAD-D, elevation, or another surrogate."
        ),
    }


def _request(eye, message, extracted):
    if eye == "GLOBAL" and str(message)[:2] in {"OD", "OS"}:
        eye = str(message)[:2]
        message = str(message)[3:] if str(message).startswith(f"{eye} ") else str(message)
    prefix = str(eye).lower()
    text = str(message)
    lower = text.lower()

    if text == "POST-REFRACTIVE PATHWAY REQUIRED":
        return {
            "eye": eye,
            "label": "Previous LASIK/PRK/SMILE documented — virgin-cornea assessment is blocked",
            "kind": "instruction",
            "key": "prior_surgery_pathway",
            "destination": "separate_pathway",
            "required_for": ["CER-AI"],
            "source_screen": "Clinical history",
            "source_box": "Previous corneal refractive surgery",
            "help": "Use the separate prior-refractive-surgery pathway. Do not generate a virgin-cornea CER-AI report.",
        }

    if eye == "PATIENT" and (lower == "age" or "patient age" in lower):
        return {
            "eye": "PATIENT", "label": "Patient age (years)", "kind": "form",
            "key": "age", "destination": "source", "form_id": "age",
            "help": "Enter the patient's age in whole years.",
            "required_for": ["Randleman"],
            "source_screen": "Pentacam patient identity / surgeon entry",
            "source_box": "Patient age",
        }

    if "contact lens" in lower or "contact-lens" in lower:
        form_id = "contact_lens_days" if "day" in lower or "discontinu" in lower else "contact_lens_type"
        return {
            "eye": "PATIENT", "label": text, "kind": "form",
            "key": "contact_lens_discontinuation_days" if form_id == "contact_lens_days" else "contact_lens_type",
            "destination": "source", "form_id": form_id,
            "help": "Complete the contact-lens washout documentation before assessment.",
            "required_for": ["Clinical readiness"],
            "source_screen": "Clinical history",
            "source_box": "Contact-lens type and discontinuation interval",
        }

    if lower in {"randleman: srax", "ps3: srax"} or ("srax" in lower and "20" in lower):
        return _srax_request(eye)

    if lower in {"randleman: i_s", "nice: i_s_d"} or "signed i-s" in lower:
        return _source_number_request(eye, "I_S", "Signed I-S (D)", extracted, required_for=_required_system(text))

    exact_source_fields = {
        "nice: k2_d": "K2_D",
        "nice: central_pachy_um": "central_pachy_um",
        "nice: b_ele_th_um": "B_Ele_Th_um",
        "ps3: ppi_average": "PPI_avg",
        "randleman: pachymetry": "pachy_thinnest_um",
        "safety: thinnest_um": "pachy_thinnest_um",
        "safety: preop_kmean_d": "Kmean_D",
    }
    if lower in exact_source_fields:
        key = exact_source_fields[lower]
        return _source_number_request(eye, key, NUMERIC_FIELDS[key], extracted, required_for=_required_system(text))

    plan_missing = {
        "safety: intended_sphere_d": ("intended_sphere_D", "Intended sphere", f"{prefix}_sphere"),
        "safety: intended_cylinder_d": ("intended_cylinder_signed_D", "Intended cylinder", f"{prefix}_cylinder"),
        "safety: intended_axis_deg": ("intended_axis_deg", "Intended cylinder axis", f"{prefix}_axis"),
        "safety: ablation_um": ("ablation_um", "Maximum ablation depth", f"{prefix}_ablation"),
        "safety: flap_um": ("flap_um", "LASIK flap thickness", f"{prefix}_flap"),
        "randleman: rsb": ("flap_um", "Complete LASIK flap thickness / ablation inputs for RSB", f"{prefix}_flap"),
        "randleman: mrse": ("manifest_entered_sphere_D", "Complete preoperative manifest refraction for MRSE", f"{prefix}_manifest_sphere"),
        "ps3: manifest_cylinder_signed_d": ("manifest_cylinder_signed_D", "Manifest cylinder required for PS3 astigmatic study", f"{prefix}_manifest_cylinder"),
        "ps3: manifest_axis_deg": ("manifest_axis_deg", "Manifest axis required for PS3 astigmatic study", f"{prefix}_axis"),
    }
    if lower in plan_missing:
        key, label, form_id = plan_missing[lower]
        return {
            "eye": eye, "label": label, "kind": "form", "key": key,
            "destination": "source", "form_id": form_id,
            "help": "Complete the treatment/refraction input required by the canonical calculation.",
            "required_for": [_required_system(text)],
            "source_screen": "Surgeon treatment/refraction inputs",
            "source_box": label,
        }

    if lower.startswith("clinical eligibility: "):
        key = text.split(":", 1)[1].strip()
        per_eye_forms = {
            "stable": "stable", "progression": "progression", "cdva_below_20_20": "cdva",
        }
        form_id = f"{prefix}_{per_eye_forms[key]}" if key in per_eye_forms else key
        return {
            "eye": eye if key in per_eye_forms else "PATIENT",
            "label": f"Clinical eligibility: document {key.replace('_', ' ')}",
            "kind": "form", "key": key, "destination": "source", "form_id": form_id,
            "help": "Document this clinical eligibility item before a final assessment can be issued.",
            "required_for": ["Clinical eligibility"],
            "source_screen": "Clinical eligibility and stability",
            "source_box": key.replace("_", " "),
        }

    if lower == "procedure" or "select lasik, prk, or smile" in lower:
        return {
            "eye": eye, "label": "Procedure", "kind": "form", "key": "procedure",
            "destination": "source", "form_id": f"{prefix}_procedure",
            "help": "Select LASIK, PRK, or SMILE.",
            "required_for": ["Procedure planning"],
            "source_screen": "Surgeon plan",
            "source_box": "Procedure",
        }
    if lower == "prior" or "prior corneal refractive" in lower:
        return {
            "eye": eye, "label": "Prior corneal refractive surgery", "kind": "form", "key": "prior",
            "destination": "source", "form_id": f"{prefix}_prior",
            "help": "Document prior PRK/LASIK/SMILE status.",
            "required_for": ["Pathway selection"],
            "source_screen": "Clinical history",
            "source_box": "Previous corneal refractive surgery",
        }

    # Canonical Pentacam field token, not arbitrary substring matching.
    fields = [
        key for key in NUMERIC_FIELDS
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(key) + r"(?![A-Za-z0-9_])", text)
    ]
    if len(fields) == 1 and eye in {"OD", "OS"}:
        key = fields[0]
        return _source_number_request(eye, key, NUMERIC_FIELDS[key], extracted, required_for=_required_system(text))

    return {
        "eye": eye,
        "label": text,
        "kind": "instruction",
        "key": text,
        "destination": "source",
        "help": "Correct the clinical input or upload/inspect the canonical source identified by CER-AI.",
        "required_for": [_required_system(text)],
        "source_screen": "Canonical source identified in the message",
        "source_box": text,
    }


def _dedupe_requests(requests):
    result = []
    seen = set()
    for item in requests:
        identity = (item.get("eye"), item.get("key"), item.get("form_id"))
        if identity in seen:
            existing = next(item for item in result if (item.get("eye"), item.get("key"), item.get("form_id")) == identity)
            existing["required_for"] = list(dict.fromkeys((existing.get("required_for") or []) + (item.get("required_for") or [])))
            continue
        seen.add(identity)
        result.append(item)
    return result


def _overrides(extracted, overrides):
    """Apply explicit surgeon confirmations while preserving original audit history."""
    from extraction_guard import _audit_eye

    working = deepcopy(extracted)
    if not isinstance(overrides, dict) or set(overrides) - {"OD", "OS"}:
        raise HTTPException(422, "Invalid eye-specific completion inputs.")

    for eye in working.get("eyes", []):
        eye_id = eye.get("eye")
        values = overrides.get(eye_id, {})
        if not isinstance(values, dict):
            raise HTTPException(422, "Completion values must be objects.")

        for key, value in values.items():
            if key in NUMERIC_FIELDS:
                if not _finite(value):
                    raise HTTPException(422, f"{eye_id} {key}: a finite numeric value is required.")
            elif key in SELECT_FIELDS:
                if value not in SELECT_FIELDS[key]:
                    raise HTTPException(422, f"{eye_id} {key}: choose one of {', '.join(SELECT_FIELDS[key])}.")
            else:
                raise HTTPException(422, f"Manual override of {key} is not supported; use the canonical source/form input.")

            eye.setdefault("surgeon_corrections", []).append(
                {"field": key, "original": eye.get(key), "value": value}
            )
            eye[key] = value
            eye.setdefault("field_provenance", {})[key] = [{"source": "SURGEON_CONFIRMED"}]
            if key in NUMERIC_FIELDS:
                eye["surgeon_verified_numeric_fields"] = sorted(
                    set(eye.get("surgeon_verified_numeric_fields") or []) | {key}
                )

            resolved = [
                item for item in eye.get("data_conflicts") or []
                if str(item).split(":", 1)[0].strip() == key
            ]
            eye.setdefault("surgeon_resolved_conflicts", []).extend(resolved)
            eye["data_conflicts"] = [
                item for item in eye.get("data_conflicts") or [] if item not in resolved
            ]

        if values:
            old_audit = eye.get("extraction_validation") or {}
            old_messages = {
                f"{eye_id} extraction validation: {item}"
                for item in old_audit.get("issues") or []
            }
            working["critical_input_issues"] = [
                item for item in working.get("critical_input_issues") or []
                if item not in old_messages
            ]
            audit = _audit_eye(eye)
            eye["extraction_validation"] = audit
            working.setdefault("extraction_validation", {})[eye_id] = audit
            working.setdefault("critical_input_issues", []).extend(
                f"{eye_id} extraction validation: {item}" for item in audit["issues"]
            )

    working["critical_input_issues"] = [
        issue for issue in working.get("critical_input_issues") or []
        if not is_quality_only_issue(issue)
    ]
    return working


def _precore_response(token, session, readiness, plans):
    blockers = readiness.get("blockers") or []
    lens = readiness.get("contact_lens_washout")
    requests = _dedupe_requests([
        _request(item.get("eye", "GLOBAL"), item.get("message", item.get("key", "")), session["extracted"])
        for item in blockers
    ])
    status = "CONTACT_LENS_WASHOUT_REQUIRED" if lens else "NEEDS_INPUT"
    response = {
        "assessment_token": token,
        "extracted": deepcopy(session["extracted"]),
        "effective_eye_plans": deepcopy(plans),
        "workflow_status": status,
        "missing": [
            {"eye": item.get("eye", "GLOBAL"), "message": item.get("message", item.get("key", ""))}
            for item in blockers
        ],
        "input_requests": requests,
        "report_token": None,
        "message": (
            lens.get("message") if lens
            else "Complete the required pre-assessment information before canonical clinical evaluation."
        ),
    }
    if lens:
        response["contact_lens_washout"] = lens
    session["ready"] = None
    session["region_requests"] = {
        (item.get("eye"), item.get("key")) for item in requests if item.get("source_region")
    }
    session["expires"] = monotonic() + TTL_SECONDS
    return response


def _respond(core, token, session, age, plans, modifiers, metadata, overrides):
    for value in (plans, modifiers, metadata):
        if not isinstance(value, dict):
            raise HTTPException(422, "Clinical inputs must be objects.")
    if set(plans) - {"OD", "OS"} or any(not isinstance(value, dict) for value in plans.values()):
        raise HTTPException(422, "Plans must contain OD/OS objects.")
    overrides = deepcopy(overrides)
    if not isinstance(overrides, dict) or any(not isinstance(value, dict) for value in overrides.values()):
        raise HTTPException(422, "Clinical overrides must be an object.")

    readiness = evaluate_precore_readiness(
        age_years=age,
        eye_plans=plans,
        patient_modifiers=modifiers,
    )
    if not readiness["ready"]:
        return _precore_response(token, session, readiness, plans)

    # A surgeon-entered I-S uses the same canonical correction/provenance path as image-derived I-S.
    for eye_id, plan in plans.items():
        if plan.get("surgeon_I_S_D") is not None:
            overrides.setdefault(eye_id, {})["I_S"] = plan["surgeon_I_S_D"]

    extracted = _overrides(session["extracted"], overrides)
    decision = evaluate_case(
        deepcopy(extracted),
        age,
        deepcopy(plans),
        deepcopy(modifiers),
        software_version=getattr(core, "APP_VERSION", None),
    )
    effective = deepcopy(decision.get("effective_eye_plans") or {})
    missing = missing_items(decision, extracted)
    requests = _dedupe_requests([
        _request(eye, message, extracted) for eye, message in missing
    ])

    response = {
        "assessment_token": token,
        "extracted": extracted,
        "effective_eye_plans": effective,
        "procedure_transitions": deepcopy(decision.get("procedure_transitions") or []),
        "workflow_status": "NEEDS_INPUT" if missing else "READY",
        "missing": [],
        "input_requests": [],
        "report_token": None,
    }
    session["ready"] = None

    if missing:
        response["missing"] = [
            {"eye": eye, "message": message} for eye, message in missing
        ]
        response["input_requests"] = requests
        response["message"] = "Complete all decision-critical information before a clinical report can be produced."
        stopped = [
            {
                "eye": eye.get("eye"),
                "status": "STOP-DEFER",
                "reasons": list(eye.get("reasons") or eye.get("hard_stops") or []),
            }
            for eye in decision.get("eyes") or []
            if eye.get("status") == "STOP-DEFER"
        ]
        if stopped:
            response["hard_stop_summary"] = {
                "status": "STOP-DEFER",
                "eyes": stopped,
                "complete_report": False,
            }
    else:
        report_token = secrets.token_urlsafe(32)
        session["ready"] = {
            "report_token": report_token,
            "patient": deepcopy(metadata),
            "decision": deepcopy(decision),
            "extracted": deepcopy(extracted),
        }
        response.update({"decision": decision, "report_token": report_token})

    session["region_requests"] = {
        (item.get("eye"), item.get("key"))
        for item in response["input_requests"]
        if item.get("source_region")
    }
    session["extracted"] = extracted
    session["expires"] = monotonic() + TTL_SECONDS
    return response


def _attributed_metadata(core, metadata):
    """Bind report attribution to the authenticated user without changing clinical logic."""
    attributed = deepcopy(metadata) if isinstance(metadata, dict) else metadata
    current_principal = getattr(core, "_cerai_current_principal", None)
    principal = current_principal() if callable(current_principal) else None
    if principal is not None:
        attributed["reviewer"] = principal.display_name
    return attributed


def _finalize_archive(core, response, session):
    runtime = getattr(core, "_cerai_case_archive_runtime", None)
    if runtime is None:
        return response
    return runtime.finalize_ready(core, response, deepcopy(session.get("ready")))


def begin(core, extracted, age, plans, modifiers, metadata, source_images=None):
    metadata = _attributed_metadata(core, metadata)
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
        response = _respond(core, token, session, age, plans, modifiers, metadata, {})
    runtime = getattr(core, "_cerai_case_archive_runtime", None)
    if runtime is not None:
        archive_state = runtime.begin_case(
            token,
            list(source_images or []),
            patient_metadata=metadata,
            extracted=deepcopy(extracted),
        )
        if archive_state:
            response["archive"] = archive_state
    return _finalize_archive(core, response, session)


def complete(core, payload):
    metadata = _attributed_metadata(core, payload.get("patient_metadata", {}))
    with _lock:
        token = payload.get("assessment_token")
        session = _session(token)
        session["ready"] = None
        response = _respond(
            core,
            token,
            session,
            payload.get("age"),
            payload.get("eye_plans", {}),
            payload.get("patient_modifiers", {}),
            metadata,
            payload.get("clinical_overrides", {}),
        )
    return _finalize_archive(core, response, session)


def export_payload(payload):
    with _lock:
        session = _session(payload.get("assessment_token"))
        ready = session.get("ready")
        if not ready or not secrets.compare_digest(
            str(payload.get("report_token") or ""), ready["report_token"]
        ):
            raise HTTPException(
                409,
                "Complete all required inputs and obtain a current ready assessment before exporting.",
            )
        exported = deepcopy(ready)
        exported["locale"] = (
            "tr" if str(payload.get("locale") or "").lower().startswith("tr") else "en"
        )
        return exported


def install(core):
    """Install transport endpoints only; no clinical function is replaced."""
    if getattr(core, "_hc_readiness_installed", False):
        return

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
            hints = deepcopy(region_hints(session["extracted"], eye, key))
            index = payload.get("index", 0)
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(hints):
                raise HTTPException(404, "No localized unread source region is available at that index.")
            hint = hints[index]
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
