"""Pre-assessment source-set gate for CER-AI.

The clinical engine must not run until the mandatory Pentacam source set is
present. The optional excimer treatment card does not participate in this gate.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException


MANDATORY_LABELS = (
    "OD Four Maps Refractive",
    "OS Four Maps Refractive",
    "OD Belin/Ambrosio Display",
    "OS Belin/Ambrosio Display",
    "Show 2 Exams Topometric",
)

_previous_merge_extractions = None


def _norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").upper()).strip("_")


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


def _eyes(result: dict[str, Any]) -> set[str]:
    return {
        str(eye.get("eye") or "").upper()
        for eye in result.get("eyes") or []
        if str(eye.get("eye") or "").upper() in {"OD", "OS"}
    }


def _is_four_maps(tokens: set[str]) -> bool:
    return any(
        token == "FOUR_MAPS_REFRACTIVE"
        or ("FOUR" in token and "MAP" in token and "REFRACT" in token)
        for token in tokens
    )


def _is_bad_display(tokens: set[str]) -> bool:
    return any(
        token in {"BAD_DISPLAY", "BELIN_AMBROSIO_DISPLAY", "BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY"}
        or ("BELIN" in token and "AMBROSIO" in token)
        or ("ENHANCED" in token and "ECTASIA" in token and "DISPLAY" in token)
        for token in tokens
    )


def _is_show_two_topometric(tokens: set[str]) -> bool:
    return any(
        token == "SHOW_2_EXAMS_TOPOMETRIC"
        or ("SHOW" in token and "2" in token and "EXAM" in token and "TOPOMETRIC" in token)
        for token in tokens
    )


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
        if _is_bad_display(tokens):
            for eye in eyes:
                label = f"{eye} Belin/Ambrosio Display"
                if label in present:
                    present[label] = True
                    recognized_this_image = True
        if _is_show_two_topometric(tokens):
            # One Show 2 Exams Topometric screenshot is the required source.
            # Per-eye numeric completeness is checked later by the existing field/readiness gates.
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
    validate_source_set(results)
    merged = _previous_merge_extractions(results)
    merged["mandatory_source_set"] = classify_source_set(results)
    return merged


def install(core) -> None:
    global _previous_merge_extractions
    if getattr(core, "_cerai_mandatory_source_set_installed", False):
        return
    _previous_merge_extractions = core.merge_extractions
    core.merge_extractions = merge_extractions_with_mandatory_source_gate
    core._cerai_mandatory_source_set_installed = True
