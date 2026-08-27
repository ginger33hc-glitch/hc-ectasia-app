"""Strict source guard for Randleman/ERSS anterior-topography scoring.

ERSS topography is permitted only when the contributing extraction came from a visible
curvature/topography map. BAD/Belin-Ambrosio/elevation-only pages cannot create or validate
Randleman morphology points.
"""
import extraction_guard

core = extraction_guard.core
_original_merge = core.merge_extractions

CURVATURE_TOKENS = ("CURV", "TOPO", "AXIAL", "SAGITTAL", "TANGENTIAL", "PLACIDO")
BAD_ONLY_TOKENS = ("BAD", "BELIN", "AMBROSIO", "ELEVATION")

def _has_curvature(screen_types):
    text = " ".join(str(x).upper() for x in (screen_types or []))
    return any(token in text for token in CURVATURE_TOKENS)

def merge_extractions_with_erss_source_guard(results):
    # Strip ERSS visual classifications from source pages that do not themselves show a
    # curvature/topography map. This is done before the normal multi-image merge so a BAD page
    # cannot seed NORMAL_SYMMETRIC (0 points) or any other ERSS morphology category.
    guarded=[]
    for result in results:
        copied=dict(result)
        eyes=[]
        for raw in result.get("eyes", []):
            eye=dict(raw)
            screens=eye.get("screen_types") or []
            if not _has_curvature(screens):
                eye["morphology"]="UNCERTAIN"
                eye["asymmetric_bow_tie"]="UNCERTAIN"
                eye["srax"]="UNCERTAIN"
                eye["srax_deg"]=None
                eye["inferior_opposite_steepening_D"]=None
                eye["morphology_evidence"]=[
                    "Randleman/ERSS anterior-topography score not derived from this source: no qualifying curvature/topography map is visible."
                ]
            eyes.append(eye)
        copied["eyes"]=eyes
        guarded.append(copied)
    merged=_original_merge(guarded)
    for eye in merged.get("eyes", []):
        provenance=eye.setdefault("field_provenance", {})
        morphology_records=provenance.get("morphology", [])
        # Retain only provenance from actual curvature/topography sources. The merge already
        # discarded UNCERTAIN pages as contradictory evidence; this flag makes the score source explicit.
        qualifying=[]
        for record in morphology_records:
            filename=record.get("file") if isinstance(record,dict) else None
            for result in guarded:
                context=result.get("document_context") or {}
                if filename and context.get("source_filename")==filename:
                    for source_eye in result.get("eyes",[]):
                        if source_eye.get("eye")==eye.get("eye") and _has_curvature(source_eye.get("screen_types")):
                            qualifying.append(record)
                            break
        provenance["erss_topography"] = qualifying
        if not qualifying:
            eye["morphology"]="UNCERTAIN"
            eye["scoring_morphology"]="UNCERTAIN"
            eye["asymmetric_bow_tie"]="UNCERTAIN"
            eye["srax"]="UNCERTAIN"
            eye["srax_deg"]=None
            eye["inferior_opposite_steepening_D"]=None
            eye.setdefault("morphology_evidence",[]).append(
                "Randleman/ERSS topography points unavailable: no qualifying anterior curvature/topography image supplied. BAD-D/elevation displays are not valid substitutes."
            )
        else:
            eye.setdefault("morphology_evidence",[]).append(
                "Randleman/ERSS anterior-topography classification derived only from qualifying curvature/topography image evidence."
            )
        eye["morphology_evidence"]=list(dict.fromkeys(eye.get("morphology_evidence",[])))
    return merged

core.merge_extractions = merge_extractions_with_erss_source_guard
