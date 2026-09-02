"""Canonical source enforcement for Pentacam Rmin.

CER-AI uses only the anterior-surface Rmin printed in Four Maps Refractive ->
Cornea Front. Cornea Back Rmin and map-spot/fallback values are never accepted.
"""
from copy import deepcopy
import re

_previous_extract_one_image = None
extract_one_image_with_front_rmin = None


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _is_four_maps(result):
    for eye in result.get("eyes") or []:
        for screen_type in eye.get("screen_types") or []:
            text = str(screen_type).upper()
            if "FOUR_MAPS_REFRACTIVE" in re.sub(r"[^A-Z0-9]+", "_", text):
                return True
            if "FOUR" in text and "MAP" in text and "REFRACT" in text:
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
        if not _is_four_maps(base):
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
                f"Rmin Cornea Front reread failed for {filename}: {type(exc).__name__}; Rmin left unread."
            )
            return base
        if reread.get("screen_family") != "FOUR_MAPS_REFRACTIVE":
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
            if _normalize(reading.get("group_label")) != "corneafront":
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
                "source": "FOUR_MAPS_REFRACTIVE_CORNEA_FRONT",
                "file": filename,
            }]
            best = readings[0]
            eye.setdefault("targeted_reread_evidence", {}).setdefault("Rmin_mm", []).append({
                "file": filename,
                "source": "FOUR_MAPS_REFRACTIVE_CORNEA_FRONT",
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
    # Rmin is no longer an accepted map fallback anywhere in CER-AI.
    core.MAP_FALLBACK_NUMERIC_FIELDS = tuple(
        field for field in core.MAP_FALLBACK_NUMERIC_FIELDS if field != "Rmin_mm"
    )
    # Strong first-pass instruction; the source-enforcement reread remains authoritative.
    if "CER-AI RMIN SOURCE LOCK" not in core.PROMPT:
        core.PROMPT += """

CER-AI RMIN SOURCE LOCK:
Rmin_mm has exactly one accepted source: Pentacam FOUR MAPS REFRACTIVE, the printed Rmin row inside
CORNEA FRONT. Never return the Cornea Back Rmin. Never use a map spot, colour scale, calculated value,
or another page/panel as Rmin_mm. If the Four Maps Refractive Cornea Front Rmin is not visible and
readable, return Rmin_mm=null.
"""
    core._cerai_rmin_front_source_installed = True
