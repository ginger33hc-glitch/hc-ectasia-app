"""Legacy-runtime adapter for the canonical Pentacam source registry.

This module contains no independent field/source definitions. It reads all locked
field ownership from ``pentacam_canonical_source_lock``. It exists only while the
legacy composed runtime is being retired.
"""
from __future__ import annotations
from typing import Any
from pentacam_canonical_source_lock import (
    BAD,
    FOURMAPS,
    LOCKED_FIELDS,
    SHOW2,
    canonical_label,
    source_family,
)

SOURCE_LOCK_PROMPT = r"""

BINDING CER-AI PENTACAM SOURCE REGISTRY (2026-09-07):
1. SHOW 2 EXAMS TOPOMETRIC:
- Cornea Front: K1, K1 axis, K2, K2 axis, Km, Astig and displayed steep axis.
- Cornea Back: Rmin and posterior Km.
- Center 'Indices (in 8 mm zone)': ISV, IVA, KI, CKI, IHA, IHD, RMin
  (topometric_RMin), TKC, KISA and signed I-S.
2. 4 MAPS REFRACTIVE lower-left labeled numerical box:
- central pachymetry = Pupil Center (+); thinnest pachymetry = Thinnest Location
  (circle); Kmax = K Max (Front); HWTW = corneal diameter.
3. BELIN/AMBROSIO BAD DISPLAY:
- central labeled box: F.Ele.Th and B.Ele.Th.
- Progression Index box: PPI Min, Avg, Max and ARTmax.
- bottom BAD-D strip: Df, Db, Dp, Dt, Da and Final D.
Locked fields are direct-read only. If the canonical value is unreadable, return
null/UNREADABLE. Do not substitute another screen, infer, derive, reverse-calculate,
or conservatively reconcile a wrong-screen value.
"""


def _screen_tokens(eye: dict[str, Any]) -> set[str]:
    return {str(item or "").upper().replace(" ", "_") for item in eye.get("screen_types") or []}


def _has_family(tokens: set[str], family: str) -> bool:
    if family == SHOW2:
        return any("SHOW_2" in token and ("TOPOMETRIC" in token or "TOPO" in token) for token in tokens)
    if family == FOURMAPS:
        return any("4_MAP" in token or "FOUR_MAP" in token for token in tokens)
    if family == BAD:
        return any("BAD" in token or "BELIN" in token or "AMBROSIO" in token for token in tokens)
    return False


def _required_family(field: str) -> str | None:
    return source_family(field)


def _strip_noncanonical(result: dict[str, Any]) -> dict[str, Any]:
    if (result.get("document_context") or {}).get("document_type") != "PENTACAM_TOPOGRAPHY":
        return result
    for eye in result.get("eyes") or []:
        if not isinstance(eye, dict):
            continue
        tokens = _screen_tokens(eye)
        verified = set(eye.get("table_verified_numeric_fields") or [])
        fallback = set(eye.get("map_fallback_numeric_fields") or [])
        missing = list(eye.get("missing_or_unreadable") or [])
        for field in LOCKED_FIELDS:
            family = source_family(field)
            fallback.discard(field)
            if family and not _has_family(tokens, family):
                if field in eye:
                    eye[field] = None
                verified.discard(field)
                missing.append(field)
        eye["table_verified_numeric_fields"] = sorted(verified)
        eye["map_fallback_numeric_fields"] = sorted(fallback)
        eye["missing_or_unreadable"] = list(dict.fromkeys(missing))
    return result


def _reread_family_ok(screen_family: Any, field: str) -> bool:
    required = source_family(field)
    return required is None or str(screen_family or "") == required


def _source_rejection_message(eye: Any, field: str, actual: Any) -> str:
    if field == "B_Ele_Th_um":
        return (
            f"Targeted Pentacam reread rejected {eye} {field}: canonical source is the "
            "verified BAD Display labeled B. Ele.Th box; alternate screens/maps are not accepted."
        )
    return (
        f"Targeted Pentacam reread rejected {eye} {field}: source family "
        f"{actual or 'UNKNOWN'} is not canonical; required family is "
        f"{source_family(field)} and required label is {canonical_label(field)}."
    )


def install(core: Any, targeted_reread: Any) -> None:
    """Temporary legacy adapter. New clinical code must not depend on this installer."""
    if getattr(core, "_canonical_pentacam_source_lock_installed", False):
        return
    if SOURCE_LOCK_PROMPT not in core.PROMPT:
        core.PROMPT += SOURCE_LOCK_PROMPT
    if SOURCE_LOCK_PROMPT not in targeted_reread.REREAD_PROMPT:
        targeted_reread.REREAD_PROMPT += SOURCE_LOCK_PROMPT

    prior_label_support = targeted_reread.label_supports_field

    def label_supports_field_locked(field, printed_label, group_label=None):
        label = targeted_reread._normalize_label(printed_label)
        group = targeted_reread._normalize_label(group_label)
        if field == "TKC":
            return label == "tkc"
        if field == "topometric_RMin":
            return label in {"rmin", "rminmm"} and any(
                token in group for token in ("indicesin8mmzone", "indices8mm", "indices")
            )
        if field == "F_Ele_Th_um":
            return label in {"feleth", "felethum", "fronteleth"}
        return prior_label_support(field, printed_label, group_label)

    targeted_reread.label_supports_field = label_supports_field_locked

    prior_apply = targeted_reread.apply_targeted_readings

    def apply_targeted_readings_locked(
        core_arg,
        result,
        reread,
        requested,
        filename,
        patient_age_requested=False,
        pentacam_qs_requested=False,
    ):
        reread = dict(reread or {})
        family = reread.get("screen_family")
        kept = []
        for reading in reread.get("readings") or []:
            if not isinstance(reading, dict):
                kept.append(reading)
                continue
            field = str(reading.get("field") or "")
            if _reread_family_ok(family, field):
                kept.append(reading)
                continue
            if reading.get("status") == "CONFIDENT" and core_arg.is_number(reading.get("value")):
                result.setdefault("global_warnings", []).append(
                    _source_rejection_message(reading.get("eye"), field, family)
                )
        reread["readings"] = kept
        return prior_apply(
            core_arg,
            result,
            reread,
            requested,
            filename,
            patient_age_requested,
            pentacam_qs_requested,
        )

    targeted_reread.apply_targeted_readings = apply_targeted_readings_locked

    prior_merge = core.merge_extractions

    def merge_source_locked(results):
        merged = prior_merge([_strip_noncanonical(result) for result in results])
        for eye in merged.get("eyes") or []:
            fallback = set(eye.get("map_fallback_numeric_fields") or [])
            illegal = fallback & LOCKED_FIELDS
            for field in illegal:
                eye[field] = None
            if illegal:
                eye["map_fallback_numeric_fields"] = sorted(fallback - illegal)
                eye["missing_or_unreadable"] = sorted(
                    set(list(eye.get("missing_or_unreadable") or []) + list(illegal))
                )
        return merged

    core.merge_extractions = merge_source_locked
    core._canonical_pentacam_source_lock_installed = True
