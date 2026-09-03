"""Pre-assessment source-set gate for CER-AI.

The clinical engine must not run until the mandatory Pentacam source set is
present. The optional excimer treatment card does not participate in this gate.
The gate is active only during an actual clinical image-assessment request so
internal merge utilities and isolated regression fixtures remain reusable.
"""
from __future__ import annotations

from contextvars import ContextVar
import re
import unicodedata
from typing import Any

from fastapi import HTTPException
from pentacam_field_registry import CORNEA_FRONT_KERATOMETRY_SOURCE


MANDATORY_LABELS = (
    "OD Four Maps Refractive",
    "OS Four Maps Refractive",
    "OD Belin/Ambrosio Display",
    "OS Belin/Ambrosio Display",
    "Show 2 Exams Topometric",
)

BAD_DISPLAY_RECOGNITION_PROMPT = r"""
MANDATORY BELIN/AMBROSIO PAGE RECOGNITION:
A Pentacam page whose visible header says "Belin/Ambrosio Display" must be
classified as a Belin/Ambrosio Display even when it uses an older Pentacam
layout and does not literally contain the words "Enhanced Ectasia Display".
For that page, include BELIN_AMBROSIO_DISPLAY in screen_types. Read laterality
from an explicit visible OD/OS (or Right/Left) label on the page/maps and set
both the eye item and document laterality consistently. Never infer laterality
from upload order or neighboring files.
"""

_previous_merge_extractions = None
_previous_run_image_assessment = None
_gate_active: ContextVar[bool] = ContextVar("cerai_mandatory_source_gate_active", default=False)


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")


def _screen_tokens(result: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    context = result.get("document_context") or {}
    for key in ("document_type", "display_type", "screen_type"):
        if context.get(key):
            tokens.add(_norm(context.get(key)))
    for eye in result.get("eyes") or []:
        for item in eye.get("screen_types") or []:
            tokens.add(_norm(item))
    return tokens


def _canonical_eye(value: Any) -> str | None:
    """Map explicit Pentacam laterality aliases to canonical OD/OS only."""
    token = _norm(value)
    if token in {"OD", "R", "RIGHT", "RIGHT_EYE", "RE"}:
        return "OD"
    if token in {"OS", "L", "LEFT", "LEFT_EYE", "LE"}:
        return "OS"
    return None


def _eyes(result: dict[str, Any]) -> set[str]:
    eyes = {
        canonical
        for eye in result.get("eyes") or []
        if (canonical := _canonical_eye(eye.get("eye"))) is not None
    }
    context_laterality = _canonical_eye(
        (result.get("document_context") or {}).get("laterality")
    )
    if context_laterality is not None:
        eyes.add(context_laterality)
    return eyes


def _is_four_maps(tokens: set[str]) -> bool:
    return any(
        token in {"FOUR_MAPS_REFRACTIVE", "4_MAPS_REFRACTIVE", "PENTACAM_4_MAPS_REFRACTIVE"}
        or (("FOUR" in token or re.search(r"(^|_)4(_|$)", token)) and "MAP" in token and "REFRACT" in token)
        for token in tokens
    )


def _is_bad_display(tokens: set[str]) -> bool:
    return any(
        token in {
            "BAD_DISPLAY",
            "BELIN_AMBROSIO_DISPLAY",
            "BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY",
            "BELIN_AMBROSIO_ENHANCED_ECTASIA",
        }
        or ("BELIN" in token and "AMBROSIO" in token)
        or ("ENHANCED" in token and "ECTASIA" in token and "DISPLAY" in token)
        for token in tokens
    )


def _is_show_two_topometric(tokens: set[str]) -> bool:
    return any(
        token in {"SHOW_2_EXAMS_TOPOMETRIC", "SHOW_TWO_EXAMS_TOPOMETRIC"}
        or (
            "SHOW" in token
            and ("2" in token or "TWO" in token)
            and "EXAM" in token
            and "TOPOMETRIC" in token
        )
        for token in tokens
    )


def _has_show_two_numeric_signature(result: dict[str, Any]) -> bool:
    for eye in result.get("eyes") or []:
        if eye.get("keratometry_source") == CORNEA_FRONT_KERATOMETRY_SOURCE:
            return True
    return False


def _has_bad_display_signature(result: dict[str, Any]) -> bool:
    for reading in result.get("nice_readings") or []:
        if reading.get("b_ele_th_page") == "BAD_DISPLAY":
            return True
    bad_fields = {"BAD_D", "Df", "Db", "Dp", "Dt", "Da"}
    for eye in result.get("eyes") or []:
        verified = set(eye.get("table_verified_numeric_fields") or [])
        for field in bad_fields & verified:
            if eye.get(field) is not None:
                return True
    return False


def _is_treatment_card(result: dict[str, Any], tokens: set[str]) -> bool:
    context = result.get("document_context") or {}
    if context.get("document_type") == "TREATMENT_CARD":
        return True
    if any("TREATMENT_CARD" in token or "EXCIMER" in token for token in tokens):
        return True
    return bool(result.get("treatment_corrections"))


def classify_source_set(results: list[dict[str, Any]]) -> dict[str, Any]:
    present = {label: False for label in MANDATORY_LABELS}
    treatment_cards = 0
    recognized_mandatory_images = 0

    for result in results:
        tokens = _screen_tokens(result)
        eyes = _eyes(result)
        recognized_this_image = False

        if _is_four_maps(tokens):
            for eye in eyes:
                label = f"{eye} Four Maps Refractive"
                if label in present:
                    present[label] = True
                    recognized_this_image = True

        if _is_bad_display(tokens) or _has_bad_display_signature(result):
            for eye in eyes:
                label = f"{eye} Belin/Ambrosio Display"
                if label in present:
                    present[label] = True
                    recognized_this_image = True

        if _is_show_two_topometric(tokens) or _has_show_two_numeric_signature(result):
            present["Show 2 Exams Topometric"] = True
            recognized_this_image = True

        if _is_treatment_card(result, tokens):
            treatment_cards += 1
        if recognized_this_image:
            recognized_mandatory_images += 1

    return {
        "present": present,
        "missing": [label for label, available in present.items() if not available],
        "mandatory_count": sum(present.values()),
        "recognized_mandatory_images": recognized_mandatory_images,
        "treatment_card_count": treatment_cards,
        "uploaded_count": len(results),
    }


def validate_source_set(results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(results) > 6:
        raise HTTPException(
            422,
            "CER-AI accepts at most 6 images: the 5 mandatory Pentacam images plus one optional excimer laser treatment card.",
        )
    summary = classify_source_set(results)
    if summary["missing"]:
        missing_text = "; ".join(summary["missing"])
        raise HTTPException(
            422,
            "Assessment not started. Required Pentacam source image(s) are missing or could not be identified: "
            + missing_text
            + ". Upload the missing image(s) and run the assessment again. The excimer laser treatment card is optional.",
        )
    return summary


def merge_extractions_with_mandatory_source_gate(results):
    summary = validate_source_set(results) if _gate_active.get() else None
    merged = _previous_merge_extractions(results)
    if summary is not None:
        merged["mandatory_source_set"] = summary
    return merged


async def run_image_assessment_with_mandatory_gate(*args, **kwargs):
    token = _gate_active.set(True)
    try:
        return await _previous_run_image_assessment(*args, **kwargs)
    finally:
        _gate_active.reset(token)


def install(core) -> None:
    global _previous_merge_extractions, _previous_run_image_assessment
    if getattr(core, "_cerai_mandatory_source_set_installed", False):
        return
    _previous_merge_extractions = core.merge_extractions
    _previous_run_image_assessment = core._run_image_assessment
    if BAD_DISPLAY_RECOGNITION_PROMPT not in core.PROMPT:
        core.PROMPT += "\n" + BAD_DISPLAY_RECOGNITION_PROMPT
    core.merge_extractions = merge_extractions_with_mandatory_source_gate
    core._run_image_assessment = run_image_assessment_with_mandatory_gate
    core._cerai_mandatory_source_set_installed = True
