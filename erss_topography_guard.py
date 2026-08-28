"""Randleman/ERSS source guard: ERSS topography is independent of Pentacam BAD."""
import extraction_guard
core=extraction_guard.core
_original_merge=core.merge_extractions

eye_schema=core.SCHEMA["properties"]["eyes"]["items"]
eye_props=eye_schema["properties"]
eye_props["anterior_curvature_map_visible"]={"type":"string","enum":["YES","NO","UNCERTAIN"]}
eye_props["anterior_curvature_map_type"]={"type":"string","enum":["AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE","NONE","UNCERTAIN"]}
eye_props["anterior_curvature_map_location"]={"type":"string","enum":["UPPER_LEFT","OTHER","NONE","UNCERTAIN"]}
for f in ("anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"):
    if f not in eye_schema["required"]: eye_schema["required"].append(f)

core.PROMPT += r"""

MANDATORY RANDLEMAN / ERSS SOURCE ISOLATION:
Randleman/ERSS anterior-topography scoring and Pentacam BAD analysis are TWO INDEPENDENT PATHWAYS.
Never require, request, search for, or infer a BAD/Belin-Ambrosio map in order to perform Randleman/ERSS topography scoring.
Never use BAD-D, Df, Db, Dp, Dt, Da, ARTmax, PPI, anterior elevation, posterior elevation, pachymetry maps,
or any BAD-display color/pattern to determine the Randleman anterior-topography category.
Missing BAD fields MUST NOT make the Randleman topography source unavailable and MUST NOT change its score.
Conversely, a BAD display is not an anterior curvature source and can never supply a Randleman topography score.

The ONLY image source for the Randleman topography component is a visible ANTERIOR CORNEAL CURVATURE/TOPOGRAPHY map.
On OCULUS Pentacam 4 Maps Refractive, the UPPER-LEFT panel labelled "Axial / Sagittal Curvature (Front)"
is such a source. If visible, set anterior_curvature_map_visible=YES,
anterior_curvature_map_type=AXIAL_SAGITTAL_FRONT, anterior_curvature_map_location=UPPER_LEFT and assess
Randleman morphology/SRA-SRAX from that panel only.
The upper-right Elevation (Front), lower-left Corneal Thickness, lower-right Elevation (Back), and any
Belin/Ambrosio BAD display are NOT Randleman topography sources.

Across multiple uploaded images, source availability is existential: one verified anterior-curvature map
is sufficient for the Randleman topography pathway. NO/NONE from BAD, elevation, pachymetry, or topometric
screens must never override a verified curvature-map YES.
If the curvature map is visible but the published morphology criteria cannot be supported, keep the source
as verified and return morphology=UNCERTAIN. Do not relabel the source as absent and do not ask for BAD.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
ROLE_FIELDS={"anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"}
BAD_FIELDS={"BAD_D","Df","Db","Dp","Dt","Da","ARTmax_um","PPI_min","PPI_avg","PPI_max","anterior_elevation_thinnest_um","posterior_elevation_thinnest_um"}
def _qualifies(e): return e.get("anterior_curvature_map_visible")=="YES" and e.get("anterior_curvature_map_type") in QUALIFYING

def merge_extractions_with_erss_source_guard(results):
    guarded=[]
    for result in results:
        copied=dict(result); copied_eyes=[]
        for raw in result.get("eyes",[]):
            e=dict(raw)
            if not _qualifies(e):
                e["morphology"]="UNCERTAIN"; e["asymmetric_bow_tie"]="UNCERTAIN"; e["srax"]="UNCERTAIN"
                e["srax_deg"]=None; e["inferior_opposite_steepening_D"]=None
            copied_eyes.append(e)
        copied["eyes"]=copied_eyes; guarded.append(copied)

    merge_input=[]
    for result in guarded:
        r=dict(result); eyes=[]
        for src in result.get("eyes",[]):
            e=dict(src)
            for f in ROLE_FIELDS: e.pop(f,None)
            eyes.append(e)
        r["eyes"]=eyes; merge_input.append(r)
    merged=_original_merge(merge_input)

    for eye in merged.get("eyes",[]):
        eye_id=eye.get("eye"); sources=[]; source_eyes=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_id and _qualifies(src):
                    sources.append({"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology")})
                    source_eyes.append(src)
        eye["erss_topography_sources"]=sources
        eye.setdefault("field_provenance",{})["erss_topography"]=sources
        eye["erss_bad_dependency"]=False
        if sources:
            eye["anterior_curvature_map_visible"]="YES"
            # Prefer a source that actually yielded a supported morphology category.
            best=next((s for s in source_eyes if s.get("morphology") not in (None,"UNCERTAIN")),source_eyes[0])
            eye["anterior_curvature_map_type"]=best.get("anterior_curvature_map_type")
            eye["anterior_curvature_map_location"]=best.get("anterior_curvature_map_location")
            eye["morphology"]=best.get("morphology","UNCERTAIN")
            eye["asymmetric_bow_tie"]=best.get("asymmetric_bow_tie","UNCERTAIN")
            eye["srax"]=best.get("srax","UNCERTAIN")
            eye["srax_deg"]=best.get("srax_deg")
            eye["inferior_opposite_steepening_D"]=best.get("inferior_opposite_steepening_D")
            evidence=[x for x in (best.get("morphology_evidence") or []) if "BAD" not in str(x).upper() and "BELIN" not in str(x).upper()]
            evidence.append("Randleman/ERSS source verified from anterior curvature/topography only; BAD data are not part of this topography score.")
            eye["morphology_evidence"]=list(dict.fromkeys(evidence))
            eye["data_conflicts"]=[c for c in eye.get("data_conflicts",[]) if str(c).split(":",1)[0].strip() not in ROLE_FIELDS]
        else:
            eye["anterior_curvature_map_visible"]="NO"; eye["anterior_curvature_map_type"]="NONE"; eye["anterior_curvature_map_location"]="NONE"
            eye["morphology"]="UNCERTAIN"; eye["asymmetric_bow_tie"]="UNCERTAIN"; eye["srax"]="UNCERTAIN"; eye["srax_deg"]=None; eye["inferior_opposite_steepening_D"]=None
            eye["morphology_evidence"]=["Randleman/ERSS topography unavailable: no verified anterior curvature/topography source in the uploaded image set. BAD data are irrelevant to this determination."]
        eye["morphology_evidence"]=list(dict.fromkeys(eye.get("morphology_evidence",[])))
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard
