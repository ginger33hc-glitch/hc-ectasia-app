"""Structured provenance guard for Randleman/ERSS anterior-topography scoring.

The extraction contract explicitly identifies whether an anterior curvature map is visible and its
map type. ERSS topography is permitted only from that structured source role. BAD/Belin-Ambrosio/
elevation-only pages cannot create or validate Randleman morphology points.
"""
import extraction_guard

core = extraction_guard.core
_original_merge = core.merge_extractions

# Extend the structured extraction contract at runtime before any extraction request is made.
eye_schema = core.SCHEMA["properties"]["eyes"]["items"]
eye_props = eye_schema["properties"]
eye_props["anterior_curvature_map_visible"] = {
    "type": "string", "enum": ["YES", "NO", "UNCERTAIN"]
}
eye_props["anterior_curvature_map_type"] = {
    "type": "string",
    "enum": ["AXIAL", "SAGITTAL", "TANGENTIAL", "PLACIDO", "OTHER_CURVATURE", "NONE", "UNCERTAIN"],
}
for field in ("anterior_curvature_map_visible", "anterior_curvature_map_type"):
    if field not in eye_schema["required"]:
        eye_schema["required"].append(field)

core.PROMPT += r"""

MANDATORY ANTERIOR-CURVATURE SOURCE CLASSIFICATION FOR RANDLEMAN/ERSS:
For every returned eye on every image, independently inspect the image itself for a true anterior
corneal curvature/topography map. Do NOT decide this from the screen title alone and do NOT rely on
the free-text screen_types value.

Set anterior_curvature_map_visible=YES when a visible anterior corneal curvature/topography map is
present, including an anterior axial, sagittal, tangential, Placido-style, or equivalent Pentacam
anterior curvature map even when the surrounding Pentacam page has another product/layout name
(such as a multi-map or refractive display). Set anterior_curvature_map_type to AXIAL, SAGITTAL,
TANGENTIAL, PLACIDO, or OTHER_CURVATURE as visually appropriate.

Set anterior_curvature_map_visible=NO and anterior_curvature_map_type=NONE only when the image clearly
contains no anterior curvature/topography map. A BAD/Belin-Ambrosio display, pachymetric progression
map, or elevation map by itself is NOT an anterior curvature map. If image quality prevents a reliable
determination, use UNCERTAIN/UNCERTAIN.

Randleman morphology, asymmetric_bow_tie, srax, srax_deg, and inferior_opposite_steepening_D may be
classified only from the same image when anterior_curvature_map_visible=YES. Never infer these from
BAD-D, Df/Db/Dp/Dt/Da, elevation, pachymetry, or other BAD-display information. When the curvature map
is visible, inspect that map directly and do not mark morphology UNCERTAIN merely because another map
on the same page is BAD/elevation/pachymetry. Record the visible curvature-map basis in
morphology_evidence.
"""


def _qualifies(eye):
    return (
        eye.get("anterior_curvature_map_visible") == "YES"
        and eye.get("anterior_curvature_map_type")
        in {"AXIAL", "SAGITTAL", "TANGENTIAL", "PLACIDO", "OTHER_CURVATURE"}
    )


def merge_extractions_with_erss_source_guard(results):
    guarded = []
    # Strip ERSS visual fields only from images explicitly not qualifying. The decision is now
    # based on structured visual provenance, never on keyword matching of screen_types.
    for result in results:
        copied = dict(result)
        eyes = []
        for raw in result.get("eyes", []):
            eye = dict(raw)
            if not _qualifies(eye):
                eye["morphology"] = "UNCERTAIN"
                eye["asymmetric_bow_tie"] = "UNCERTAIN"
                eye["srax"] = "UNCERTAIN"
                eye["srax_deg"] = None
                eye["inferior_opposite_steepening_D"] = None
                eye["morphology_evidence"] = [
                    "Randleman/ERSS topography not derived from this image: no explicitly verified anterior curvature map on this source."
                ]
            eyes.append(eye)
        copied["eyes"] = eyes
        guarded.append(copied)

    merged = _original_merge(guarded)
    for eye in merged.get("eyes", []):
        eye_name = eye.get("eye")
        qualifying_sources = []
        qualifying_morphologies = []
        for result in guarded:
            filename = (result.get("document_context") or {}).get("source_filename")
            for source_eye in result.get("eyes", []):
                if source_eye.get("eye") == eye_name and _qualifies(source_eye):
                    qualifying_sources.append({
                        "file": filename,
                        "map_type": source_eye.get("anterior_curvature_map_type"),
                        "morphology": source_eye.get("morphology"),
                    })
                    if source_eye.get("morphology") not in (None, "UNCERTAIN"):
                        qualifying_morphologies.append(source_eye.get("morphology"))

        provenance = eye.setdefault("field_provenance", {})
        provenance["erss_topography"] = qualifying_sources
        eye["erss_topography_sources"] = qualifying_sources

        if not qualifying_sources:
            eye["morphology"] = "UNCERTAIN"
            eye["scoring_morphology"] = "UNCERTAIN"
            eye["asymmetric_bow_tie"] = "UNCERTAIN"
            eye["srax"] = "UNCERTAIN"
            eye["srax_deg"] = None
            eye["inferior_opposite_steepening_D"] = None
            eye.setdefault("morphology_evidence", []).append(
                "Randleman/ERSS topography unavailable: no image was explicitly verified as containing an anterior curvature map."
            )
        elif not qualifying_morphologies:
            eye["morphology"] = "UNCERTAIN"
            eye["scoring_morphology"] = "UNCERTAIN"
            eye.setdefault("morphology_evidence", []).append(
                "Anterior curvature map verified, but its Randleman morphology could not be classified reliably."
            )
        else:
            # The normal merge already applies conservative morphology conflict handling. Make
            # provenance explicit so the report/audit can show where the ERSS topography came from.
            source_names = [x.get("file") or "uploaded image" for x in qualifying_sources]
            eye.setdefault("morphology_evidence", []).append(
                "Randleman/ERSS anterior-topography evidence accepted only from verified curvature-map source(s): "
                + ", ".join(source_names)
                + "."
            )
        eye["morphology_evidence"] = list(dict.fromkeys(eye.get("morphology_evidence", [])))
    return merged


core.merge_extractions = merge_extractions_with_erss_source_guard
