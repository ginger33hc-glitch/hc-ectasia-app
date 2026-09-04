"""Runtime enforcement for the 2026-09-04 owner-defined Pentacam source lock.

Locked fields are direct transcription only. A value from the wrong Pentacam
screen/panel is nulled before merge; no map fallback, cross-screen substitute,
calculation, reconstruction, or conservative reconciliation is permitted.
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
    "ISV", "IVA", "KI", "CKI", "IHA", "IHD", "TKC", "KISA", "I_S",
})
FOURMAPS_FIELDS = frozenset({
    "central_pachy_um", "pachy_thinnest_um", "Kmax_D", "corneal_diameter_mm",
})
BAD_FIELDS = frozenset({
    "F_Ele_Th_um", "B_Ele_Th_um", "PPI_min", "PPI_avg", "PPI_max",
    "ARTmax_um", "Df", "Db", "Dp", "Dt", "Da", "BAD_D",
})

SOURCE_LOCK_PROMPT = r"""

BINDING CER-AI PENTACAM SOURCE LOCK (2026-09-04) — OVERRIDES EVERY EARLIER
SOURCE/FALLBACK STATEMENT FOR THESE FIELDS:
1. SHOW 2 EXAMS TOPOMETRIC only:
   - Cornea Front labeled rows: K1, K1 axis, K2, K2 axis, Km, Astig and its
     displayed steep axis. Never use Cornea Back, True Net Power, another map,
     another display, or a calculation for these fields.
   - Cornea Back labeled row: Rmin_mm ONLY from Cornea Back -> Rmin. No local
     map fallback and no Front/central RMin substitution.
   - Center panel headed 'Indices (in 8 mm zone)': ISV, IVA, KI, CKI, IHA, IHD,
     TKC, KISA and signed I-S. Read each directly from its own labeled box.
     Do not calculate, reverse-calculate, infer, or source these indices elsewhere.
2. 4 MAPS REFRACTIVE only, lower-left labeled numerical box:
   - central_pachy_um = Pupil Center pachymetry identified by + marker.
   - pachy_thinnest_um = Thinnest Location pachymetry identified by circle marker.
   - Kmax_D = K Max (Front).
   - corneal_diameter_mm = HWTW.
   No color-map, coordinate, other screen, or derived substitute is permitted.
3. BELIN/AMBROSIO BAD DISPLAY only:
   - central numerical box: F.Ele.Th and B.Ele.Th.
   - Progression Index box: PPI Min, Avg, Max and ARTmax.
   - bottom BAD-D strip: Df, Db, Dp, Dt, Da and final D (BAD_D).
   Never reconstruct any of these from maps, CTSP/PTI graphs, neighboring values,
   formulas, or another Pentacam display.
For every locked field: if its canonical labeled value cannot be read confidently,
return null/UNREADABLE. There is NO fallback, NO cross-screen substitution, NO
calculation, NO reverse calculation, and NO conservative merge from a different
source. Duplicate appearances elsewhere are not sources.
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
    if field in SHOW2_FIELDS:
        return SHOW2
    if field in FOURMAPS_FIELDS:
        return FOURMAPS
    if field in BAD_FIELDS:
        return BAD
    return None


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
            if field == "topometric_RMin":
                continue
            family = _required_family(field)
            # Locked fields never have a map fallback, including posterior Rmin.
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


def install(core: Any, targeted_reread: Any) -> None:
    if getattr(core, "_canonical_pentacam_source_lock_installed", False):
        return

    # Make both extraction passes obey the same binding owner-defined source contract.
    if SOURCE_LOCK_PROMPT not in core.PROMPT:
        core.PROMPT += SOURCE_LOCK_PROMPT
    if SOURCE_LOCK_PROMPT not in targeted_reread.REREAD_PROMPT:
        targeted_reread.REREAD_PROMPT += SOURCE_LOCK_PROMPT

    prior_merge = core.merge_extractions

    def merge_source_locked(results):
        cleaned = [_strip_noncanonical(result) for result in results]
        merged = prior_merge(cleaned)
        for eye in merged.get("eyes") or []:
            fallback = set(eye.get("map_fallback_numeric_fields") or [])
            illegal = fallback & (LOCKED_FIELDS - {"topometric_RMin"})
            if illegal:
                for field in illegal:
                    eye[field] = None
                eye["map_fallback_numeric_fields"] = sorted(fallback - illegal)
                eye["missing_or_unreadable"] = sorted(set(
                    list(eye.get("missing_or_unreadable") or []) + list(illegal)
                ))
        return merged

    core.merge_extractions = merge_source_locked
    core._canonical_pentacam_source_lock_installed = True
