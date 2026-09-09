"""Pre-assessment source-set and conditional manual-input gate for CER-AI.

The clinical engine must not run until the mandatory Pentacam source set is
present. The excimer treatment card is optional; when it is absent, the surgeon
must provide complete bilateral manifest and intended refraction before the
engine runs. The gate is active only during an actual clinical image-assessment
request so internal merge utilities and isolated regression fixtures remain
reusable.
"""
from __future__ import annotations

import re
import unicodedata
from math import isfinite
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
OPTIONAL_TREATMENT_CARD_LABEL = "Excimer laser treatment card"
MAX_UPLOAD_IMAGES = 6

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


def _mandatory_labels_for(result: dict[str, Any]) -> set[str]:
    """Return only the mandatory source roles established by this image."""
    tokens = _screen_tokens(result)
    eyes = _eyes(result)
    labels: set[str] = set()
    if _is_four_maps(tokens):
        labels.update(
            label for eye in eyes
            if (label := f"{eye} Four Maps Refractive") in MANDATORY_LABELS
        )
    if _is_bad_display(tokens) or _has_bad_display_signature(result):
        labels.update(
            label for eye in eyes
            if (label := f"{eye} Belin/Ambrosio Display") in MANDATORY_LABELS
        )
    if _is_show_two_topometric(tokens) or _has_show_two_numeric_signature(result):
        labels.add("Show 2 Exams Topometric")
    return labels


def _unreadable_optional_card_results(
    results: list[dict[str, Any]], *, mandatory_complete: bool,
) -> list[dict[str, Any]]:
    recognized = [
        result for result in results
        if _is_treatment_card(result, _screen_tokens(result))
        and not result.get("treatment_corrections")
    ]
    residual = []
    if mandatory_complete and len(results) == len(MANDATORY_LABELS) + 1:
        residual = [
            result for result in results
            if not _mandatory_labels_for(result)
            and not _is_treatment_card(result, _screen_tokens(result))
        ]
        if len(residual) != 1:
            residual = []
    return list({id(result): result for result in recognized + residual}.values())


def classify_source_set(results: list[dict[str, Any]]) -> dict[str, Any]:
    present = {label: False for label in MANDATORY_LABELS}
    treatment_cards = 0
    recognized_mandatory_images = 0

    for result in results:
        tokens = _screen_tokens(result)
        mandatory_labels = _mandatory_labels_for(result)
        for label in mandatory_labels:
            present[label] = True
        if _is_treatment_card(result, tokens):
            treatment_cards += 1
        if mandatory_labels:
            recognized_mandatory_images += 1

    missing = [label for label, available in present.items() if not available]
    unreadable_cards = _unreadable_optional_card_results(
        results, mandatory_complete=not missing,
    )
    recognized_unreadable_cards = [
        result for result in unreadable_cards
        if _is_treatment_card(result, _screen_tokens(result))
    ]
    recognized_unreadable_ids = {id(result) for result in recognized_unreadable_cards}
    unreadable_card_candidates = [
        result for result in unreadable_cards if id(result) not in recognized_unreadable_ids
    ]
    usable_cards = treatment_cards - len(recognized_unreadable_cards)
    card_status = (
        "READABLE" if usable_cards > 0
        else "UNREADABLE" if unreadable_cards
        else "NOT_PROVIDED"
    )
    return {
        "present": present,
        "required_sources": [
            {"label": label, "present": available}
            for label, available in present.items()
        ],
        "missing": missing,
        "mandatory_count": sum(present.values()),
        "recognized_mandatory_images": recognized_mandatory_images,
        "treatment_card_count": treatment_cards,
        "optional_treatment_card": {
            "label": OPTIONAL_TREATMENT_CARD_LABEL,
            "present": treatment_cards > 0 or bool(unreadable_card_candidates),
            "usable": usable_cards > 0,
            "status": card_status,
            "count": treatment_cards + len(unreadable_card_candidates),
            "unreadable_count": len(unreadable_cards),
        },
        "confirmed": not missing,
        "uploaded_count": len(results),
    }


def validate_upload_count(count: int) -> None:
    if count > MAX_UPLOAD_IMAGES:
        raise HTTPException(
            422,
            "CER-AI accepts at most 6 images: the 5 mandatory Pentacam images plus one optional excimer laser treatment card.",
        )


def validate_source_set(results: list[dict[str, Any]]) -> dict[str, Any]:
    validate_upload_count(len(results))
    summary = classify_source_set(results)
    if summary["missing"]:
        missing_text = ", ".join(summary["missing"])
        optional = "present" if summary["optional_treatment_card"]["present"] else "not provided"
        raise HTTPException(
            422,
            {
                "code": "MANDATORY_SOURCE_SET_INCOMPLETE",
                "message": (
                    "Assessment not started. Upload the missing required image(s): "
                    f"{missing_text}. Optional treatment card: {optional}."
                ),
                "source_set": summary,
            },
        )
    return summary


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def missing_manual_refraction(plans: dict[str, Any]) -> list[dict[str, str]]:
    """Return surgeon fields required when no treatment card was uploaded."""
    missing: list[dict[str, str]] = []
    for eye, prefix in (("OD", "od"), ("OS", "os")):
        plan = plans.get(eye) if isinstance(plans, dict) else None
        plan = plan if isinstance(plan, dict) else {}
        roles = (
            ("manifest", "manifest_entered_sphere_D", "manifest_cylinder_signed_D"),
            ("intended", "intended_entered_sphere_D", "intended_cylinder_signed_D"),
        )
        axis_required = False
        axis_available_for_every_role = True
        for role, sphere_key, cylinder_key in roles:
            if not _finite(plan.get(sphere_key)):
                missing.append({
                    "eye": eye,
                    "field": sphere_key,
                    "form_id": f"{prefix}_{'manifest_sphere' if role == 'manifest' else 'sphere'}",
                    "label": f"{eye} {role} sphere",
                })
            if not _finite(plan.get(cylinder_key)):
                missing.append({
                    "eye": eye,
                    "field": cylinder_key,
                    "form_id": f"{prefix}_{'manifest_cylinder' if role == 'manifest' else 'cylinder'}",
                    "label": f"{eye} {role} cylinder",
                })
            else:
                axis_required = True
                role_axis = any(_finite(plan.get(key)) for key in (
                    "entered_axis_deg", f"{role}_axis_deg", f"{role}_entered_axis_deg",
                ))
                axis_available_for_every_role &= role_axis
        if axis_required and not axis_available_for_every_role:
            missing.append({
                "eye": eye,
                "field": "entered_axis_deg",
                "form_id": f"{prefix}_axis",
                "label": f"{eye} cylinder axis",
            })
    return missing


def validate_preassessment_requirements(
    results: list[dict[str, Any]], plans: dict[str, Any],
) -> dict[str, Any]:
    """Confirm source identity and any conditional manual inputs before enrichment."""
    summary = validate_source_set(results)
    card = summary["optional_treatment_card"]
    card_usable = card["usable"]
    if card["status"] == "UNREADABLE":
        for result in _unreadable_optional_card_results(
            results, mandatory_complete=summary["confirmed"],
        ):
            (result.setdefault("document_context", {}))[
                "optional_treatment_card_status"
            ] = "UNREADABLE"
    missing_refraction = [] if card_usable else missing_manual_refraction(plans)
    summary["manual_refraction"] = {
        "required": not card_usable,
        "complete": not missing_refraction,
        "missing": missing_refraction,
    }
    if missing_refraction:
        labels = ", ".join(item["label"] for item in missing_refraction)
        source_message = (
            "No treatment card was provided."
            if card["status"] == "NOT_PROVIDED"
            else "The optional treatment card did not provide complete readable refraction."
        )
        raise HTTPException(
            422,
            {
                "code": "PREASSESSMENT_REFRACTION_REQUIRED",
                "message": (
                    f"Assessment not started. {source_message} Enter the complete "
                    f"manifest and intended refraction for both eyes: {labels}."
                ),
                "refraction_reason": card["status"],
                "source_set": summary,
                "missing_refraction": missing_refraction,
            },
        )
    return summary
