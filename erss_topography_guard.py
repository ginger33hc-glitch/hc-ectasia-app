"""Structured provenance guard for Randleman/ERSS anterior-topography scoring.

ERSS morphology is derived only from the ANTERIOR CURVATURE panel. On the standard Pentacam
4 Maps Refractive display this is the UPPER-LEFT panel labelled Axial/Sagittal Curvature (Front).
The upper-right Elevation (Front), lower-left Corneal Thickness, and lower-right Elevation (Back)
are different data sources and cannot generate ERSS anterior-topography points.
"""
import extraction_guard
core=extraction_guard.core
_original_merge=core.merge_extractions

eye_schema=core.SCHEMA["properties"]["eyes"]["items"]
eye_props=eye_schema["properties"]
eye_props["anterior_curvature_map_visible"]={"type":"string","enum":["YES","NO","UNCERTAIN"]}
eye_props["anterior_curvature_map_type"]={"type":"string","enum":["AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE","NONE","UNCERTAIN"]}
eye_props["anterior_curvature_map_location"]={"type":"string","enum":["UPPER_LEFT","OTHER","NONE","UNCERTAIN"]}
for field in ("anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"):
    if field not in eye_schema["required"]: eye_schema["required"].append(field)

core.PROMPT += r"""

PENTACAM 4 MAPS REFRACTIVE — FIXED MAP IDENTITY RULE (MANDATORY):
When the supplied image is an OCULUS Pentacam "4 Maps Refractive" display, identify the four panels
by their printed panel labels and positions. Do not treat the four maps as interchangeable.

UPPER LEFT: "Axial / Sagittal Curvature (Front)" = ANTERIOR CORNEAL CURVATURE MAP.
Set anterior_curvature_map_visible=YES,
anterior_curvature_map_type=AXIAL_SAGITTAL_FRONT, and
anterior_curvature_map_location=UPPER_LEFT. This is the ONLY panel on this standard four-map page
that may be used for Randleman/ERSS anterior-topography morphology scoring.

UPPER RIGHT: "Elevation (Front)" = ANTERIOR ELEVATION MAP. It is NOT an anterior curvature map and
must NEVER be used to assign Randleman morphology, asymmetric bow-tie, inferior steepening, SRA/SRAX,
or ERSS anterior-topography points.

LOWER LEFT: "Corneal Thickness" = PACHYMETRY/CORNEAL-THICKNESS MAP. It is NOT a curvature map and
must NEVER generate Randleman topography points.

LOWER RIGHT: "Elevation (Back)" = POSTERIOR ELEVATION MAP. It is NOT a curvature map and must NEVER
generate Randleman topography points.

On a 4 Maps Refractive page, inspect the UPPER-LEFT Axial/Sagittal Curvature (Front) panel directly
for morphology. Do not report "no curvature/topography map visible" when that labelled upper-left
panel is visibly present. BAD-D, BAD components, elevation colors/values, and pachymetry must not
influence the Randleman topography category.

For other Pentacam layouts, set anterior_curvature_map_visible=YES only when a panel is explicitly
an anterior/front curvature/topography map; set its type and location accordingly. If a page contains
only BAD/Belin-Ambrosio, elevation, or pachymetry information, use NO/NONE/NONE. Use UNCERTAIN only
when image quality truly prevents identifying the map.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
def _qualifies(eye):
    return eye.get("anterior_curvature_map_visible")=="YES" and eye.get("anterior_curvature_map_type") in QUALIFYING

def merge_extractions_with_erss_source_guard(results):
    guarded=[]
    for result in results:
        copied=dict(result); eyes=[]
        for raw in result.get("eyes",[]):
            eye=dict(raw)
            if not _qualifies(eye):
                eye["morphology"]="UNCERTAIN"; eye["asymmetric_bow_tie"]="UNCERTAIN"; eye["srax"]="UNCERTAIN"
                eye["srax_deg"]=None; eye["inferior_opposite_steepening_D"]=None
                eye["morphology_evidence"]=["ERSS morphology excluded from this source because no verified anterior/front curvature panel is present."]
            eyes.append(eye)
        copied["eyes"]=eyes; guarded.append(copied)
    merged=_original_merge(guarded)
    for eye in merged.get("eyes",[]):
        eye_name=eye.get("eye"); sources=[]; morphs=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_name and _qualifies(src):
                    record={"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology")}
                    sources.append(record)
                    if src.get("morphology") not in (None,"UNCERTAIN"): morphs.append(src.get("morphology"))
        provenance=eye.setdefault("field_provenance",{}); provenance["erss_topography"]=sources; eye["erss_topography_sources"]=sources
        if not sources:
            eye["morphology"]="UNCERTAIN"; eye["scoring_morphology"]="UNCERTAIN"; eye["asymmetric_bow_tie"]="UNCERTAIN"; eye["srax"]="UNCERTAIN"; eye["srax_deg"]=None; eye["inferior_opposite_steepening_D"]=None
            eye.setdefault("morphology_evidence",[]).append("Randleman/ERSS topography unavailable: no verified anterior/front curvature map source.")
        elif not morphs:
            eye["morphology"]="UNCERTAIN"; eye["scoring_morphology"]="UNCERTAIN"
            eye.setdefault("morphology_evidence",[]).append("Anterior/front curvature map verified, but morphology could not be classified reliably.")
        else:
            labels=[]
            for s in sources:
                labels.append(f"{s.get('file') or 'uploaded image'} [{s.get('map_type')}, {s.get('map_location')}]")
            eye.setdefault("morphology_evidence",[]).append("Randleman/ERSS morphology derived only from verified anterior curvature source: "+", ".join(labels)+".")
        eye["morphology_evidence"]=list(dict.fromkeys(eye.get("morphology_evidence",[])))
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard
