"""Runtime enforcement for the 2026-09-04 owner-defined Pentacam source lock.

Locked fields are direct transcription only. Wrong-screen values are rejected
before merge; no fallback, cross-screen substitute, calculation, reconstruction,
or conservative reconciliation is permitted for locked fields.
"""
from __future__ import annotations
from typing import Any
from pentacam_canonical_source_lock import LOCKED_FIELDS

SHOW2 = "SHOW_2_EXAMS_TOPOMETRIC"
FOURMAPS = "FOUR_MAPS_REFRACTIVE"
BAD = "BAD_DISPLAY"
SHOW2_FIELDS = frozenset({
    "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D",
    "topographic_astig_D", "topographic_steep_axis_deg", "Rmin_mm",
    "ISV", "IVA", "KI", "CKI", "IHA", "IHD", "TKC", "KISA", "I_S", "topometric_RMin",
})
FOURMAPS_FIELDS = frozenset({"central_pachy_um", "pachy_thinnest_um", "Kmax_D", "corneal_diameter_mm"})
BAD_FIELDS = frozenset({
    "F_Ele_Th_um", "B_Ele_Th_um", "PPI_min", "PPI_avg", "PPI_max",
    "ARTmax_um", "Df", "Db", "Dp", "Dt", "Da", "BAD_D",
})

SOURCE_LOCK_PROMPT = r"""

BINDING CER-AI PENTACAM SOURCE LOCK (2026-09-04) — OVERRIDES EVERY EARLIER
SOURCE/FALLBACK STATEMENT FOR THESE FIELDS:
1. SHOW 2 EXAMS TOPOMETRIC only:
- Cornea Front: K1, K1 axis, K2, K2 axis, Km, Astig and displayed steep axis.
- Cornea Back: Rmin_mm ONLY from Cornea Back -> Rmin.
- Center 'Indices (in 8 mm zone)': ISV, IVA, KI, CKI, IHA, IHD, RMin
  (topometric_RMin), TKC, KISA and signed I-S. Read directly from each labeled box.
2. 4 MAPS REFRACTIVE only, lower-left labeled numerical box:
- central_pachy_um = Pupil Center (+); pachy_thinnest_um = Thinnest Location
  (circle); Kmax_D = K Max (Front); corneal_diameter_mm = HWTW.
3. BELIN/AMBROSIO BAD DISPLAY only:
- central numerical box: F.Ele.Th, B.Ele.Th.
- Progression Index box: PPI Min, Avg, Max, ARTmax.
- bottom BAD-D strip: Df, Db, Dp, Dt, Da, final D (BAD_D).
For every locked field, if its canonical labeled value is not confidently readable,
return null/UNREADABLE. NO fallback, NO cross-screen substitution, NO map-derived
substitute, NO formula, NO inference, NO reverse calculation, NO conservative merge.
Duplicate appearances elsewhere are not sources.
"""


def _screen_tokens(eye: dict[str, Any]) -> set[str]:
    return {str(item or "").upper().replace(" ", "_") for item in eye.get("screen_types") or []}


def _has_family(tokens: set[str], family: str) -> bool:
    if family == SHOW2:
        return any("SHOW_2" in t and ("TOPOMETRIC" in t or "TOPO" in t) for t in tokens)
    if family == FOURMAPS:
        return any("4_MAP" in t or "FOUR_MAP" in t for t in tokens)
    if family == BAD:
        return any("BAD" in t or "BELIN" in t or "AMBROSIO" in t for t in tokens)
    return False


def _required_family(field: str) -> str | None:
    if field in SHOW2_FIELDS: return SHOW2
    if field in FOURMAPS_FIELDS: return FOURMAPS
    if field in BAD_FIELDS: return BAD
    return None


def _strip_noncanonical(result: dict[str, Any]) -> dict[str, Any]:
    if (result.get("document_context") or {}).get("document_type") != "PENTACAM_TOPOGRAPHY":
        return result
    for eye in result.get("eyes") or []:
        if not isinstance(eye, dict): continue
        tokens = _screen_tokens(eye)
        verified = set(eye.get("table_verified_numeric_fields") or [])
        fallback = set(eye.get("map_fallback_numeric_fields") or [])
        missing = list(eye.get("missing_or_unreadable") or [])
        for field in LOCKED_FIELDS:
            family = _required_family(field)
            fallback.discard(field)
            if family and not _has_family(tokens, family):
                if field in eye: eye[field] = None
                verified.discard(field)
                missing.append(field)
        eye["table_verified_numeric_fields"] = sorted(verified)
        eye["map_fallback_numeric_fields"] = sorted(fallback)
        eye["missing_or_unreadable"] = list(dict.fromkeys(missing))
    return result


def _reread_family_ok(screen_family: Any, field: str) -> bool:
    required = _required_family(field)
    if required is None: return True
    return str(screen_family or "") == required


def install(core: Any, targeted_reread: Any) -> None:
    if getattr(core, "_canonical_pentacam_source_lock_installed", False): return
    if SOURCE_LOCK_PROMPT not in core.PROMPT: core.PROMPT += SOURCE_LOCK_PROMPT
    if SOURCE_LOCK_PROMPT not in targeted_reread.REREAD_PROMPT: targeted_reread.REREAD_PROMPT += SOURCE_LOCK_PROMPT

    # Extend exact-label validation for newly canonicalized Show-2 fields.
    prior_label_support = targeted_reread.label_supports_field
    def label_supports_field_locked(field, printed_label, group_label=None):
        label = targeted_reread._normalize_label(printed_label)
        group = targeted_reread._normalize_label(group_label)
        if field == "TKC": return label == "tkc"
        if field == "topometric_RMin":
            return label in {"rmin", "rminmm"} and any(x in group for x in ("indicesin8mmzone", "indices8mm", "indices"))
        if field == "F_Ele_Th_um": return label in {"feleth", "felethum", "fronteleth"}
        return prior_label_support(field, printed_label, group_label)
    targeted_reread.label_supports_field = label_supports_field_locked

    # Reject wrong-screen candidates before the existing targeted-reread acceptance code sees them.
    prior_apply = targeted_reread.apply_targeted_readings
    def apply_targeted_readings_locked(core_arg, result, reread, requested, filename,
                                       patient_age_requested=False, pentacam_qs_requested=False):
        reread = dict(reread or {})
        family = reread.get("screen_family")
        reread["readings"] = [
            reading for reading in reread.get("readings") or []
            if not isinstance(reading, dict) or _reread_family_ok(family, str(reading.get("field") or ""))
        ]
        return prior_apply(core_arg, result, reread, requested, filename,
                           patient_age_requested, pentacam_qs_requested)
    targeted_reread.apply_targeted_readings = apply_targeted_readings_locked

    prior_merge = core.merge_extractions
    def merge_source_locked(results):
        merged = prior_merge([_strip_noncanonical(result) for result in results])
        for eye in merged.get("eyes") or []:
            fallback = set(eye.get("map_fallback_numeric_fields") or [])
            illegal = fallback & LOCKED_FIELDS
            for field in illegal: eye[field] = None
            if illegal:
                eye["map_fallback_numeric_fields"] = sorted(fallback - illegal)
                eye["missing_or_unreadable"] = sorted(set(list(eye.get("missing_or_unreadable") or []) + list(illegal)))
        return merged
    core.merge_extractions = merge_source_locked
    core._canonical_pentacam_source_lock_installed = True
