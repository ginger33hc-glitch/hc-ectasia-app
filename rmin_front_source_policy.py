"""Canonical source enforcement for Pentacam posterior Rmin.

Compatibility note: the module/function names are retained because the canonical
runtime invariants reference them. The former Four Maps/Cornea Front rule is
retired. CER-AI now accepts Rmin_mm ONLY from Show 2 Exams Topometric -> Cornea
Back -> Rmin, per the binding 2026-09-04 owner source definition.
"""
from copy import deepcopy
import re

_previous_extract_one_image = None
extract_one_image_with_front_rmin = None  # legacy symbol name; behavior is Cornea Back.


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _is_show_two_topometric(result):
    for eye in result.get("eyes") or []:
        for screen_type in eye.get("screen_types") or []:
            text = re.sub(r"[^A-Z0-9]+", "_", str(screen_type).upper())
            if text in {"SHOW_2_EXAMS_TOPOMETRIC", "SHOW_TWO_EXAMS_TOPOMETRIC"}:
                return True
            if "SHOW" in text and ("_2_" in f"_{text}_" or "TWO" in text) and "EXAM" in text and "TOPOMETRIC" in text:
                return True
    return False


def _requested_eyes(result):
    return {
        eye.get("eye"): ["Rmin_mm"]
        for eye in result.get("eyes") or []
        if eye.get("eye") in {"OD", "OS"}
    }


def _clear_rmin(result):
    working = deepcopy(result)
    for eye in working.get("eyes") or []:
        if eye.get("eye") not in {"OD", "OS"}:
            continue
        eye["Rmin_mm"] = None
        eye["table_verified_numeric_fields"] = [
            name for name in eye.get("table_verified_numeric_fields") or [] if name != "Rmin_mm"
        ]
        eye["map_fallback_numeric_fields"] = [
            name for name in eye.get("map_fallback_numeric_fields") or [] if name != "Rmin_mm"
        ]
        eye.setdefault("field_provenance", {}).pop("Rmin_mm", None)
    return working


def make_extractor(core, previous, targeted_module):
    def wrapped(raw, filename):
        base = _clear_rmin(previous(raw, filename))
        if not _is_show_two_topometric(base):
            return base
        requested = _requested_eyes(base)
        if not requested:
            return base
        try:
            reread = targeted_module.targeted_reread(
                core, raw, filename, requested,
                patient_age_requested=False,
                pentacam_qs_requested=False,
            )
        except Exception as exc:
            base.setdefault("global_warnings", []).append(
                f"Rmin Cornea Back reread failed for {filename}: {type(exc).__name__}; Rmin left unread."
            )
            return base
        if reread.get("screen_family") != "SHOW_2_EXAMS_TOPOMETRIC":
            return base
        eyes = {eye.get("eye"): eye for eye in base.get("eyes") or [] if eye.get("eye") in {"OD", "OS"}}
        candidates = {}
        for reading in reread.get("readings") or []:
            if reading.get("field") != "Rmin_mm" or reading.get("eye") not in eyes:
                continue
            if reading.get("status") != "CONFIDENT" or not core.is_number(reading.get("value")):
                continue
            if _normalize(reading.get("printed_label")) not in {"rmin", "rminmm"}:
                continue
            if _normalize(reading.get("group_label")) != "corneaback":
                continue
            candidates.setdefault(reading["eye"], []).append(reading)
        for eye_id, readings in candidates.items():
            values = {float(item["value"]) for item in readings}
            if len(values) != 1:
                continue
            value = values.pop()
            eye = eyes[eye_id]
            eye["Rmin_mm"] = value
            verified = set(eye.get("table_verified_numeric_fields") or [])
            verified.add("Rmin_mm")
            eye["table_verified_numeric_fields"] = sorted(verified)
            eye["map_fallback_numeric_fields"] = [
                name for name in eye.get("map_fallback_numeric_fields") or [] if name != "Rmin_mm"
            ]
            eye.setdefault("field_provenance", {})["Rmin_mm"] = [{
                "source": "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK",
                "file": filename,
            }]
            best = readings[0]
            eye.setdefault("targeted_reread_evidence", {}).setdefault("Rmin_mm", []).append({
                "file": filename,
                "source": "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK",
                "tile": best.get("source_tile"),
                "printed_label": best.get("printed_label"),
                "group_label": best.get("group_label"),
                "value": value,
            })
        return base
    return wrapped


def install(core, targeted_module):
    global _previous_extract_one_image, extract_one_image_with_front_rmin
    if getattr(core, "_cerai_rmin_front_source_installed", False):
        return
    _previous_extract_one_image = core.extract_one_image
    extract_one_image_with_front_rmin = make_extractor(core, _previous_extract_one_image, targeted_module)
    core.extract_one_image = extract_one_image_with_front_rmin
    core.MAP_FALLBACK_NUMERIC_FIELDS = tuple(
        field for field in core.MAP_FALLBACK_NUMERIC_FIELDS if field != "Rmin_mm"
    )
    if "CER-AI RMIN SOURCE LOCK" not in core.PROMPT:
        core.PROMPT += """

CER-AI RMIN SOURCE LOCK — BINDING 2026-09-04:
Rmin_mm has exactly one accepted source: SHOW 2 EXAMS TOPOMETRIC -> CORNEA BACK -> printed Rmin row.
Never return Cornea Front Rmin, Four Maps Rmin, the center topometric RMin index, a map spot, colour
scale, calculated value, or another page/panel as Rmin_mm. If Show 2 Exams Cornea Back Rmin is not
visible and readable, return Rmin_mm=null.
"""
    core._cerai_rmin_front_source_installed = True
