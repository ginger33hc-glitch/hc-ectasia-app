import asyncio
import base64
import json
import mimetypes
import os
from contextlib import asynccontextmanager
from io import BytesIO
from threading import RLock
from time import monotonic
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

import pentacam_targeted_reread
import geometric_srax_policy

from clinical_disposition import combine_status as combine_clinical_status
from pentacam_canonical_source_lock import (
    CANONICAL_FIELD_SOURCES, LOCKED_FIELDS, canonical_source_id,
)
from pentacam_field_registry import (
    CORNEA_FRONT_KERATOMETRY_FIELDS,
    CORNEA_FRONT_KERATOMETRY_SOURCE,
    EXCLUSIVE_LABELED_BOX_FIELDS,
    KERATOMETRY_SOURCE_VALUES,
)
from pentacam_quality_policy import is_quality_only_issue, warnings_for_extracted
from reports import build_docx, build_pdf


@asynccontextmanager
async def canonical_runtime_lifespan(application: FastAPI):
    """Refuse to serve the uncomposed legacy core as a clinical runtime."""
    if not getattr(application.state, "cerai_canonical_runtime_ready", False):
        raise RuntimeError(
            "Unsupported CER-AI startup target. Use python start.py or canonical_engine:app; "
            "the uncomposed app:app target is not a clinical runtime."
        )
    yield


app = FastAPI(
    title="CER-AI — Cornea Ectasia Risk Assessment Intelligence v0.7.71",
    lifespan=canonical_runtime_lifespan,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
client: Optional[OpenAI] = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")
VALIDATED_MODEL = "gpt-5.6-terra"

# A mobile browser can lose the HTTP connection after the upload while the
# assessment is still running. Keep a short-lived, user-scoped task registry so
# a transparent retry waits for the original work instead of running the same
# clinical extraction twice.
ANALYSIS_REQUEST_TTL_SECONDS = 10 * 60
_analysis_request_lock = RLock()
_analysis_request_tasks: Dict[tuple[str, str], tuple[float, asyncio.Task]] = {}

EYES = ("OD", "OS")
PRK_EPITHELIUM_UM = 50
CORNEAL_EFFECT_PER_INTENDED_MRSE_D = 0.8
FINAL_KMEAN_MIN_D = 36.0
FINAL_KMEAN_MAX_D = 48.0
MORPHOLOGY = (
    "NORMAL_SYMMETRIC",
    "ASYMMETRIC_BOWTIE",
    "INFERIOR_STEEPENING_SRA",
    "ABNORMAL_ECTATIC",
    "UNCERTAIN",
)
TABLE_NUMERIC_FIELDS = (
    "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmax_D", "corneal_diameter_mm",
    "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp",
    "Dt", "Da", "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um", "ISV", "IVA", "KI",
    "CKI", "IHD", "I_S", "KISA", "IHA", "Rmin_mm", "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "Kmean_D",
    "total_RMS_um", "spherical_aberration_um",
    "central_pachy_um", "B_Ele_Th_um", "F_Ele_Th_um", "posterior_Kmean_D",
    "topographic_astig_D", "topographic_steep_axis_deg", "topometric_RMin", "TKC",
)
MAP_FALLBACK_NUMERIC_FIELDS = (
    # Only explicitly marked elevation-at-thinnest values remain permitted local-map fallbacks.
    # Locked printed outputs such as Rmin, K values, BAD, PPI, ARTmax, and topometric indices
    # must be read from their exact canonical labeled source or left unreadable.
    "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um",
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_context": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "document_type": {
                    "type": "string",
                    "enum": ["PENTACAM_TOPOGRAPHY", "TREATMENT_CARD", "OTHER", "UNKNOWN"],
                },
                "patient_id": {"type": ["string", "null"]},
                "patient_last_name": {"type": ["string", "null"]},
                "patient_first_name": {"type": ["string", "null"]},
                "patient_name": {"type": ["string", "null"]},
                "patient_name_source": {
                    "type": "string",
                    "enum": [
                        "PENTACAM_FIRST_LAST_NAME_FIELDS", "OTHER_LABELED_PATIENT_NAME",
                        "UNREADABLE", "NOT_SHOWN",
                    ],
                },
                "patient_age_years": {"type": ["integer", "null"]},
                "exam_date": {"type": ["string", "null"]},
                "exam_time": {"type": ["string", "null"]},
                "laterality": {"type": "string", "enum": ["OD", "OS", "BOTH", "UNKNOWN"]},
                "pentacam_qs": {
                    "type": "string",
                    "enum": ["OK", "NOT_OK", "UNREADABLE", "NOT_SHOWN", "NOT_APPLICABLE"],
                },
                "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "document_type", "patient_id", "patient_last_name", "patient_first_name",
                "patient_name", "patient_name_source", "patient_age_years", "exam_date",
                "exam_time", "laterality", "pentacam_qs", "missing_or_unreadable",
            ],
        },
        "eyes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "screen_types": {"type": "array", "items": {"type": "string"}},
                    "quality": {"type": "string", "enum": ["ADEQUATE", "LIMITED", "INADEQUATE"]},
                    "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
                    "table_verified_numeric_fields": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(TABLE_NUMERIC_FIELDS)},
                    },
                    "map_fallback_numeric_fields": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(MAP_FALLBACK_NUMERIC_FIELDS)},
                    },
                    "keratometry_source": {
                        "type": "string",
                        "enum": list(KERATOMETRY_SOURCE_VALUES),
                    },
                    "K1_D": {"type": ["number", "null"]},
                    "K1_axis_deg": {"type": ["number", "null"]},
                    "K2_D": {"type": ["number", "null"]},
                    "K2_axis_deg": {"type": ["number", "null"]},
                    "Kmax_D": {"type": ["number", "null"]},
                    "central_pachy_um": {"type": ["number", "null"]},
                    "B_Ele_Th_um": {"type": ["number", "null"]},
                    "F_Ele_Th_um": {"type": ["number", "null"]},
                    "posterior_Kmean_D": {"type": ["number", "null"]},
                    "topographic_astig_D": {"type": ["number", "null"]},
                    "topographic_steep_axis_deg": {"type": ["number", "null"]},
                    "topometric_RMin": {"type": ["number", "null"]},
                    "TKC": {"type": ["number", "null"]},
                    "corneal_diameter_mm": {"type": ["number", "null"]},
                    "pachy_thinnest_um": {"type": ["number", "null"]},
                    "BAD_D": {"type": ["number", "null"]},
                    "Df": {"type": ["number", "null"]},
                    "Db": {"type": ["number", "null"]},
                    "Dp": {"type": ["number", "null"]},
                    "Dt": {"type": ["number", "null"]},
                    "Da": {"type": ["number", "null"]},
                    "PPI_avg": {"type": ["number", "null"]},
                    "PPI_min": {"type": ["number", "null"]},
                    "PPI_max": {"type": ["number", "null"]},
                    "ARTmax_um": {"type": ["number", "null"]},
                    "ISV": {"type": ["number", "null"]},
                    "IVA": {"type": ["number", "null"]},
                    "KI": {"type": ["number", "null"]},
                    "CKI": {"type": ["number", "null"]},
                    "IHD": {"type": ["number", "null"]},
                    "I_S": {"type": ["number", "null"]},
                    "KISA": {"type": ["number", "null"]},
                    "IHA": {"type": ["number", "null"]},
                    "Rmin_mm": {"type": ["number", "null"]},
                    "anterior_elevation_thinnest_um": {"type": ["number", "null"]},
                    "posterior_elevation_thinnest_um": {"type": ["number", "null"]},
                    "thinnest_x_mm": {"type": ["number", "null"]},
                    "thinnest_y_mm": {"type": ["number", "null"]},
                    "corneal_volume_mm3": {"type": ["number", "null"]},
                    "RMS_HOA_um": {"type": ["number", "null"]},
                    "vertical_coma_um": {"type": ["number", "null"]},
                    "Kmean_D": {"type": ["number", "null"]},
                    "total_RMS_um": {"type": ["number", "null"]},
                    "spherical_aberration_um": {"type": ["number", "null"]},
                    "morphology": {"type": "string", "enum": list(MORPHOLOGY)},
                    "morphology_evidence": {"type": "array", "items": {"type": "string"}},
                    "asymmetric_bow_tie": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax_deg": {"type": ["number", "null"]},
                    "inferior_opposite_steepening_D": {"type": ["number", "null"]},
                    "anterior_pattern": {
                        "type": "string",
                        "enum": ["REASSURING", "BORDERLINE", "ABNORMAL", "UNREADABLE"],
                    },
                    "posterior_pattern": {
                        "type": "string",
                        "enum": ["REASSURING", "BORDERLINE", "ABNORMAL", "UNREADABLE"],
                    },
                },
                "required": [
                    "eye", "screen_types", "quality", "missing_or_unreadable",
                    "table_verified_numeric_fields", "map_fallback_numeric_fields", "keratometry_source",
                    "K1_D", "K1_axis_deg",
                    "K2_D", "K2_axis_deg", "Kmax_D", "corneal_diameter_mm", "pachy_thinnest_um",
                    "BAD_D", "Df", "Db", "Dp", "Dt", "Da",
                    "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um", "ISV", "IVA", "KI", "CKI", "IHD",
                    "I_S", "KISA", "IHA", "Rmin_mm", "anterior_elevation_thinnest_um",
                    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
                    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "Kmean_D",
                    "total_RMS_um", "spherical_aberration_um",
                    "central_pachy_um", "B_Ele_Th_um", "F_Ele_Th_um", "posterior_Kmean_D",
                    "topographic_astig_D", "topographic_steep_axis_deg", "topometric_RMin", "TKC",
                    "morphology",
                    "morphology_evidence", "asymmetric_bow_tie", "srax", "srax_deg",
                    "inferior_opposite_steepening_D",
                    "anterior_pattern", "posterior_pattern",
                ],
            },
        },
        "treatment_corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "source_document": {
                        "type": "string",
                        "enum": ["EXCIMER_LASER_FOLLOW_UP_CARD", "OTHER", "UNKNOWN"],
                    },
                    "source_label": {
                        "type": "string",
                        "enum": ["DUZELTME_MIKTARI", "OTHER", "UNREADABLE"],
                    },
                    "sphere_D": {"type": ["number", "null"]},
                    "cylinder_D": {"type": ["number", "null"]},
                    "axis_deg": {"type": ["number", "null"]},
                    "sphere_cylinder_status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE"],
                    },
                    "axis_status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE"],
                    },
                    "raw_text": {"type": ["string", "null"]},
                    "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "eye", "source_document", "source_label", "sphere_D", "cylinder_D",
                    "axis_deg", "sphere_cylinder_status", "axis_status", "raw_text",
                    "missing_or_unreadable",
                ],
            },
        },
        "global_warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["document_context", "eyes", "treatment_corrections", "global_warnings"],
}

_CANONICAL_SOURCE_ID_PROPERTIES = {
    field: {"type": ["string", "null"], "enum": [source_id, None]}
    for field, (source_id, _label) in CANONICAL_FIELD_SOURCES.items()
}
_eye_schema = SCHEMA["properties"]["eyes"]["items"]
_eye_schema["properties"]["canonical_source_ids"] = {
    "type": "object",
    "additionalProperties": False,
    "properties": _CANONICAL_SOURCE_ID_PROPERTIES,
    "required": list(CANONICAL_FIELD_SOURCES),
}
if "canonical_source_ids" not in _eye_schema["required"]:
    _eye_schema["required"].append("canonical_source_ids")

PROMPT = """You are a strict data-extraction component for preoperative corneal-refractive-surgery images.
The image may be a Pentacam/topography screen, an Excimer Laser Follow-up Card (Excimer Laser Takip
Karti), or another clinical document. Extract only values visibly supported by the supplied image.
Never guess an unreadable or absent
number. Identify OD/OS and screen type. Return null for unreadable/absent numeric values and list
them in missing_or_unreadable.

DOCUMENT IDENTITY AND ACQUISITION RULE:
For every PENTACAM_TOPOGRAPHY image, read the patient name ONLY from the patient-demographics fields
explicitly labeled "Last Name" and "First Name". Read the text directly opposite each label. Put those
exact strings in patient_last_name and patient_first_name, and combine them as "First Name Last Name"
in patient_name. Set patient_name_source=PENTACAM_FIRST_LAST_NAME_FIELDS. Never use a physician,
surgeon, operator, examiner, clinic, hospital, account, login, header, footer, or another person's name
as the patient name. If either labeled Pentacam field or its value is absent or unreadable, return null
for that component and list it in missing_or_unreadable; never substitute text from another box. If
neither name component is readable, patient_name must be null and patient_name_source must be
UNREADABLE or NOT_SHOWN. On a non-Pentacam clinical document, use only an explicitly labeled patient-
name field, set the two name components to null when they are not separately labeled, and use
patient_name_source=OTHER_LABELED_PATIENT_NAME, UNREADABLE, or NOT_SHOWN as applicable.

Transcribe the patient ID, explicitly printed patient age in completed years, exam date, exam time,
laterality, and document type exactly when visible. Transcribe patient_id only from an
explicitly labeled patient-ID field in the patient-demographics box (for example ID, Patient ID, or
Pat.-ID). Never use an examination number, measurement number, scan number, accession number,
page/report number, device serial number, date, time, or another unlabeled number as patient_id.
If the patient-ID label or its value is not clearly readable, return patient_id=null. Use null/UNKNOWN
when other identity fields are absent or unreadable. Patient age is one patient-level value shared by
OD and OS: on every Pentacam source, inspect the top patient-demographics/header area for the explicitly
printed Age field, but return it only when the label and completed-year integer are both unambiguous.
Do not extract or return date of birth. Never calculate age from another field and never
infer that two images belong to the same patient merely because their laterality matches. For a Pentacam image, transcribe
the device quality specification only when the literal QS status is visible. Use OK only for an
explicitly visible acceptable/OK QS. Use NOT_OK for a visible non-OK status, UNREADABLE when the QS
area is present but cannot be read, and NOT_SHOWN when no QS field is visible. Treatment cards and
non-Pentacam documents use NOT_APPLICABLE.

PENTACAM NUMERIC-SOURCE RULE — this rule has priority over map interpretation:
First inspect the labeled parameter panels, side tables, summary tables, and the labeled numeric
boxes around the edge of the Pentacam display. Every numeric output in TABLE_NUMERIC_FIELDS must be
copied preferentially from its own explicitly labeled printed field. Add the exact output-field name to
table_verified_numeric_fields only when that labeled field is visible and the value was transcribed
from it. The list must exactly match the non-null table-derived numeric outputs.

I-S SOURCE LOCK: transcribe I_S only from the explicitly labeled "IS:" or "I-S:" field, preferentially
from the Pentacam Topometric/Keratoconus panel headed "Indices (in 8 mm zone)". Preserve its printed
sign. Never substitute ISV, IVA, IHD, IHA, KISA, Q-value, a color, or a curvature-map spot for I_S.
If the IS label, sign, digits, or eye laterality is uncertain, return I_S=null; never calculate I-S.

If and only if the corresponding side/summary-table field is absent, obscured, or unreadable, a local
map number may be used as a second-priority fallback when it directly represents the same named
measurement and that field is allowed by MAP_FALLBACK_NUMERIC_FIELDS. Record it in
map_fallback_numeric_fields and not in table_verified_numeric_fields. The marker/location and map
type must make the identity unambiguous. This fallback is limited to the explicitly marked anterior/posterior elevation
at that same thinnest point. Rmin is never a map fallback. A generic curvature-map spot is not Kmax
or Rmin. If the identity or location is uncertain, return null.

EXCLUSIVE LABELED-BOX SOURCE LOCK:
- K1_D, K1_axis_deg, K2_D, K2_axis_deg, and Kmean_D have exactly one accepted source:
  the upper parameter panel explicitly headed "Cornea Front" for the corresponding eye on a
  screen whose visible title is "Show 2 Exams Topometric". Set keratometry_source to
  SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT only when both that screen title and the Cornea Front panel
  heading are visible. In that panel, Kmean_D is the value printed in the Km row; never calculate
  it from K1 and K2. On every other Pentacam page or panel, return all five fields as null, do not
  add them to table_verified_numeric_fields, and set keratometry_source to OTHER_PENTACAM_SOURCE,
  UNREADABLE, or NOT_SHOWN. Never use Cornea Back, True Net Power, Total Corneal Refractive Power,
  another map/display, a color-map number, Kmax, or another K/Km-like field for these outputs.
- Rmin_mm: exactly one accepted source: "Show 2 Exams Topometric" -> panel headed "Cornea Back" -> printed Rmin row. Never use Cornea Front Rmin, the center topometric RMin index, Four Maps, a map spot, or any calculated value.
- central_pachy_um: use only 4 Maps Refractive lower-left Pupil Center (+) pachymetry.
- B_Ele_Th_um and F_Ele_Th_um: use only the BAD Display central labeled B.Ele.Th/F.Ele.Th boxes.
- posterior_Kmean_D: use only Show 2 Exams Topometric -> Cornea Back -> printed Km.
- topographic_astig_D and topographic_steep_axis_deg: use only Show 2 Exams Topometric -> Cornea Front.
- topometric_RMin and TKC: use only Show 2 Exams Topometric center Indices (in 8 mm zone).
- Kmax_D: use only the numeric value in the explicitly printed "KMax"/"Kmax" row.
- ARTmax_um: use only the numeric value in the explicitly printed "ARTmax" row beneath the
  Progression Index panel.
- pachy_thinnest_um: use only the pachymetry value in the circle-marked printed
  "Thinnest Locat." row. Never use Pachy Vertex N., Pupil Center, or a thickness-map number.
These are single authoritative labeled-box readings. Never compare them with a map value,
neighboring number, calculated value, or another Pentacam screen to create a conflict. If the
authoritative row/panel is unreadable, return null for that field.

Never substitute a generic map spot value, color-scale value, axis label, neighboring parameter,
calculated value, average, or visual estimate for K1, K2, their axes, horizontal white-to-white
(HWTW), Kmax,
Rmin, BAD-D/components, PPI, ARTmax, topometric
indices, coordinates, corneal volume, HOA, or coma. Those summary/calculated fields must remain null
when their own labeled table value is unreadable. A labeled BAD-display center/bottom numeric box
counts as a printed parameter field; an unlabeled number inside the map does not. The table source
always overrides a local-map fallback when both are visible.

ERSS VISUAL MORPHOLOGY DISABLED:
General ERSS/Randleman visual morphology classification is disabled. Do not visually score asymmetric
bow-tie, inferior steepening, keratoconus pattern, forme-fruste pattern, PMD pattern, or any other ERSS
morphology category.

ERSS SRAX SOURCE LOCK — MODEL ESTIMATION DISABLED:
SRAX is measured outside the extraction model by CER-AI's deterministic geometric image-analysis
engine using only the Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.
Do not visually estimate SRAX, return a numeric srax_deg from map appearance, or derive SRAX from
KISA, Kmax, I-S, astigmatism tables, K1/K2/global Axis, BAD values, elevation, pachymetry, or any surrogate.
For every image handled by this model, return srax=UNCERTAIN and srax_deg=null. The deterministic
geometry layer may replace those values only when the correct Front map and both hemimeridian axes
are resolved with adequate confidence. General morphology outputs remain morphology=UNCERTAIN,
morphology_evidence=[], asymmetric_bow_tie=UNCERTAIN, and inferior_opposite_steepening_D=null.
Anterior/posterior tomography pattern fields remain separate non-ERSS review inputs.

BELIN/AMBROSIO BAD DISPLAY SOURCE LOCK:
BAD_D, Df, Db, Dp, Dt, and Da may be transcribed ONLY from the explicitly labeled bottom BAD-D
component strip on a visible Belin/Ambrosio Display for the same eye. Preserve every printed sign
exactly. Never derive or reconstruct Df from anterior elevation, Db from B.Ele.Th/posterior elevation,
Dp from PPI, Dt from thinnest pachymetry, Da from ARTmax, or Final D from the component values. Never
substitute a color, map spot, neighboring value, or another screen/eye. If the label, sign, digits, or
laterality is unreadable, return null for that field. Final BAD-D remains the printed overall BAD signal.

For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled
"Duzeltme Miktari" (including Turkish characters). Do not substitute values from "Subjektif
Refraksiyon" or any other row. Map SAG/right to OD and SOL/left to OS. Transcribe sphere, signed
cylinder, and axis exactly as written. sphere_cylinder_status may be CONFIDENT only when the sphere
and cylinder digits and signs are unambiguous. If either is ambiguous, set both numeric fields to
null and use UNCERTAIN or UNREADABLE while preserving visible characters in raw_text. Axis ambiguity
does not require discarding an otherwise confident sphere/cylinder pair; report it separately in
axis_status and set axis_deg to null when uncertain. Never transpose cylinder notation and never
infer the laser platform, optical zone, procedure, or ablation depth from the card. For a card-only
image with no corneal tomography/topography data, return an empty eyes array. For a tomography-only
image with no treatment card, return an empty treatment_corrections array. Downstream, a confident
Duzeltme Miktari is treated as both preoperative manifest refraction and intended correction unless
the clinician separately enters or otherwise explicitly identifies a different value for either role."""


_CANONICAL_SOURCE_PROMPT = "\n".join(
    f"- {field}: source_id={source_id}; printed label={label}"
    for field, (source_id, label) in CANONICAL_FIELD_SOURCES.items()
)
PROMPT += (
    "\n\nCANONICAL EXACT-SOURCE PROVENANCE — REQUIRED FOR EVERY LOCKED FIELD:\n"
    "Return canonical_source_ids for every locked field. Use the exact source_id listed below only when "
    "that field was transcribed from that exact screen/panel/box. Otherwise return null for both the "
    "field source id and, if no canonical reading exists, the field value. Never assign a canonical "
    "source id to a wrong-screen or inferred value.\n"
    + _CANONICAL_SOURCE_PROMPT
)


def data_url(raw: bytes, filename: str) -> str:
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def openai_client() -> OpenAI:
    global client
    if MODEL != VALIDATED_MODEL and os.getenv("ALLOW_UNVALIDATED_MODEL") != "1":
        raise RuntimeError(
            f"OPENAI_MODEL={MODEL!r} is not the validated extraction configuration. "
            "Set ALLOW_UNVALIDATED_MODEL=1 only for non-clinical validation testing."
        )
    if client is None:
        client = OpenAI()
    return client


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def tri(value: Any) -> str:
    return value if value in ("yes", "no", "unknown") else "unknown"


def combine_status(current: str, new: str) -> str:
    return combine_clinical_status(current, new)


def _transpose_axis(axis: Optional[float]) -> Optional[float]:
    """Rotate a plus-cylinder axis into its equivalent minus-cylinder axis."""
    if not is_number(axis):
        return None
    rotated = (float(axis) + 90.0) % 180.0
    return 180.0 if abs(rotated) < 1e-9 else rotated


def normalize_signed_refraction_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve entered notation and provide one canonical minus-cylinder plan to the engine.

    Legacy/API plans that already provide ``*_cylinder_magnitude_D`` remain supported. The
    browser sends the explicit entered fields, so a positive cylinder is transposed rather than
    silently converted to an absolute magnitude.
    """
    normalized = dict(plan or {})
    warnings = list(normalized.get("correction_warnings", []))
    entered_axis = normalized.get("entered_axis_deg")
    if entered_axis is None and any(
        normalized.get(field) is not None
        for field in ("manifest_entered_sphere_D", "manifest_cylinder_signed_D",
                      "intended_entered_sphere_D", "intended_cylinder_signed_D")
    ):
        entered_axis = normalized.get("correction_axis_deg")
    if entered_axis is not None:
        normalized["entered_axis_deg"] = entered_axis

    for role in ("manifest", "intended"):
        entered_sphere_field = f"{role}_entered_sphere_D"
        signed_cylinder_field = f"{role}_cylinder_signed_D"
        sphere_field = f"{role}_sphere_D"
        magnitude_field = f"{role}_cylinder_magnitude_D"
        entered_sphere = normalized.get(entered_sphere_field)
        signed_cylinder = normalized.get(signed_cylinder_field)
        raw_supplied = entered_sphere is not None or signed_cylinder is not None
        if not raw_supplied:
            continue
        if not is_number(entered_sphere) or not is_number(signed_cylinder):
            normalized[sphere_field] = None
            normalized[magnitude_field] = None
            continue

        entered_sphere = float(entered_sphere)
        signed_cylinder = float(signed_cylinder)
        plus_cylinder = signed_cylinder > 0
        normalized[sphere_field] = entered_sphere + signed_cylinder if plus_cylinder else entered_sphere
        normalized[magnitude_field] = abs(signed_cylinder)
        normalized_axis = _transpose_axis(entered_axis) if plus_cylinder else entered_axis
        normalized[f"{role}_normalized_axis_deg"] = normalized_axis
        if role == "intended":
            normalized["correction_axis_deg"] = normalized_axis
        if plus_cylinder:
            note = (
                f"{role.capitalize()} plus-cylinder notation was transposed for calculation: "
                f"{entered_sphere:+.2f} {signed_cylinder:+.2f} D"
                + (f" x {float(entered_axis):.0f}°" if is_number(entered_axis) else " (axis unavailable)")
                + f" -> {normalized[sphere_field]:+.2f} {-normalized[magnitude_field]:+.2f} D"
                + (f" x {float(normalized_axis):.0f}°." if is_number(normalized_axis) else ".")
            )
            warnings.append(note)

    normalized["correction_warnings"] = list(dict.fromkeys(warnings))
    return normalized


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    """Return decision-blocking input errors; invalid values are never used in calculations."""
    errors: List[str] = []
    numeric_ranges = {
        "manifest_sphere_D": (-30, 20),
        "manifest_cylinder_magnitude_D": (0, 15),
        "intended_sphere_D": (-30, 20),
        "intended_cylinder_magnitude_D": (0, 15),
        "manifest_entered_sphere_D": (-30, 20),
        "manifest_cylinder_signed_D": (-15, 15),
        "intended_entered_sphere_D": (-30, 20),
        "intended_cylinder_signed_D": (-15, 15),
        "entered_axis_deg": (0, 180),
        "correction_axis_deg": (0, 180),
        "ablation_um": (0, 400),
    }
    for field, (low, high) in numeric_ranges.items():
        value = plan.get(field)
        if value is not None and (not is_number(value) or not low <= float(value) <= high):
            errors.append(f"invalid {field}: expected {low} to {high}")
    if plan.get("flap_um") is not None and plan.get("flap_um") not in (90, 100, 110, 120):
        errors.append("invalid flap_um: CER-AI options are 90, 100, 110, or 120 µm")
    if plan.get("optical_zone_mm") is not None and plan.get("optical_zone_mm") not in (6.0, 6.5, 7.0):
        errors.append("invalid optical_zone_mm: CER-AI options are 6.0, 6.5, or 7.0 mm")
    if plan.get("transition_zone_mm") is not None and plan.get("transition_zone_mm") not in (8.0, 8.5, 9.0):
        errors.append("invalid transition_zone_mm: CER-AI options are 8.0, 8.5, or 9.0 mm")
    return errors


def bad_classification(value: Optional[float], final: bool = False) -> str:
    if not is_number(value):
        return "UNAVAILABLE"
    if final:
        if value <= 1.6:
            return "NORMAL"
        if value < 2.6:
            return "SUSPICIOUS"
        return "ABNORMAL"
    if value < 1.6:
        return "NORMAL"
    if value < 2.6:
        return "SUSPICIOUS"
    return "ABNORMAL"


def lasik_topography_points(morphology: str) -> Optional[int]:
    return {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }.get(morphology)


def scoring_morphology(eye: Dict[str, Any]) -> Dict[str, Any]:
    """Apply published ERSS Placido definitions without declaring disease from one index."""
    reported_category = eye.get("morphology", "UNCERTAIN")
    category = reported_category
    evidence = list(eye.get("morphology_evidence", []))
    i_s = eye.get("I_S")
    srax_deg = eye.get("srax_deg")
    inferior_opposite = eye.get("inferior_opposite_steepening_D")
    srax_supported = is_number(srax_deg) and srax_deg >= 20
    inferior_supported = (
        is_number(inferior_opposite)
        and inferior_opposite >= 1.0
        and is_number(i_s)
        and i_s < 1.4
    )
    asymmetric_supported = (
        is_number(inferior_opposite)
        and 0.5 < inferior_opposite < 1.0
        and not srax_supported
    )
    if reported_category == "ABNORMAL_ECTATIC":
        category = "ABNORMAL_ECTATIC"
    elif is_number(i_s) and i_s >= 1.4:
        category = "ABNORMAL_ECTATIC"
        evidence.append("Published Placido-era ERSS abnormal-pattern criterion: I-S >=1.4 D.")
    elif srax_supported or inferior_supported:
        category = "INFERIOR_STEEPENING_SRA"
        if srax_supported:
            evidence.append("Published ERSS SRA/SRAX category supported: SRA/SRAX >=20 degrees.")
        if inferior_supported:
            evidence.append(
                "Published ERSS inferior-steepening category supported: >=1.0 D versus the opposite "
                "region with I-S <1.4 D."
            )
    elif reported_category == "INFERIOR_STEEPENING_SRA" or eye.get("srax") == "YES":
        category = "UNCERTAIN"
        evidence.append(
            "SRAX/inferior-steepening label not scored: neither SRA/SRAX >=20 degrees nor the "
            ">=1.0 D inferior-opposite criterion with I-S <1.4 D was documented."
        )
    elif reported_category == "ASYMMETRIC_BOWTIE" or eye.get("asymmetric_bow_tie") == "YES":
        if asymmetric_supported:
            category = "ASYMMETRIC_BOWTIE"
            evidence.append(
                "Published ERSS asymmetric-bowtie category supported: >0.5 D and <1.0 D "
                "versus the region 180 degrees opposite, without SRA."
            )
        else:
            category = "UNCERTAIN"
            evidence.append(
                "Asymmetric-bowtie label not scored: the required >0.5 D and <1.0 D "
                "opposite-region difference without SRA was not documented."
            )
    return {"category": category, "evidence": list(dict.fromkeys(evidence))}


def lasik_rsb_points(rsb: Optional[float]) -> Optional[int]:
    if not is_number(rsb):
        return None
    if rsb < 240:
        return 4
    if rsb < 260:
        return 3
    if rsb < 280:
        return 2
    if rsb < 300:
        return 1
    return 0


def age_points(age: Optional[int]) -> Optional[int]:
    if not is_number(age) or age < 18:
        return None
    if age <= 21:
        return 3
    if age <= 25:
        return 2
    if age <= 29:
        return 1
    return 0


def lasik_pachy_points(pachy: Optional[float]) -> Optional[int]:
    if not is_number(pachy):
        return None
    # The printed ERSS table leaves 450 µm unstated and places 510 µm on
    # conflicting/overlapping boundaries. Do not silently adjudicate either.
    if pachy in (450, 510):
        return None
    if pachy < 450:
        return 4
    if pachy <= 480:
        return 3
    if pachy <= 510:
        return 2
    return 0


def lasik_mrse_points(mrse: Optional[float]) -> Optional[int]:
    if not is_number(mrse):
        return None
    if mrse < -14:
        return 4
    if mrse < -12:
        return 3
    if mrse < -10:
        return 2
    if mrse < -8:
        return 1
    return 0


def prk_morphology_points(morphology: str) -> Optional[int]:
    return {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 5,
        # A numeric Placido abnormal-pattern criterion yields high concern but
        # is not, by itself, relabeled as a definite-disease override.
        "ABNORMAL_ECTATIC": 5,
    }.get(morphology)


def prk_pachy_points(pachy: Optional[float]) -> Optional[int]:
    if not is_number(pachy):
        return None
    if pachy <= 450:
        return 4
    if pachy <= 480:
        return 3
    if pachy <= 510:
        return 2
    return 0


def score_category(procedure: str, score: int) -> str:
    if procedure == "LASIK":
        if score <= 2:
            return "LOW"
        if score == 3:
            return "MODERATE"
        return "HIGH"
    if score <= 1:
        return "LOWER_FLAGGED_BURDEN"
    if score <= 3:
        return "CAUTION"
    return "HIGH_CONCERN"


def tomography_review(eye: Dict[str, Any]) -> Dict[str, Any]:
    bad = {"BAD_D": bad_classification(eye.get("BAD_D"), final=True)}
    for key in ("Df", "Db", "Dp", "Dt", "Da"):
        bad[key] = bad_classification(eye.get(key))

    flags: List[str] = []
    if is_number(eye.get("ARTmax_um")) and eye["ARTmax_um"] <= 424:
        flags.append("ARTmax <=424 µm: cross-sectional subclinical-KC concern flag.")
    if is_number(eye.get("pachy_thinnest_um")) and eye["pachy_thinnest_um"] <= 544:
        flags.append("Thinnest pachymetry <=544 µm: cross-sectional phenotype flag, not an exclusion cutoff.")
    if is_number(eye.get("Dt")) and eye["Dt"] >= -0.165:
        flags.append("BAD-Dt >=-0.165: cross-sectional subclinical-KC concern flag.")
    if is_number(eye.get("Da")) and eye["Da"] >= 0.585:
        flags.append("BAD-Da >=0.585: cross-sectional subclinical-KC concern flag.")

    display_values = list(bad.values())
    map_patterns = (eye.get("anterior_pattern"), eye.get("posterior_pattern"))
    if "ABNORMAL" in display_values or "ABNORMAL" in map_patterns:
        status = "ABNORMAL"
    elif "SUSPICIOUS" in display_values or "BORDERLINE" in map_patterns:
        status = "SUSPICIOUS"
    elif "UNAVAILABLE" in display_values or "UNREADABLE" in map_patterns:
        status = "INCOMPLETE"
    elif flags:
        status = "CONCERN FLAGS"
    else:
        status = "REASSURING"

    return {
        "status": status,
        "BAD_display": bad,
        "cross_sectional_flags": flags,
        "evidence_note": (
            "BAD and ARTmax/TP/Dt/Da thresholds are adjunctive diagnostic/review signals; "
            "they are not independently validated predictors of post-refractive ectasia."
        ),
    }


def estimate_ablation(plan: Dict[str, Any], warnings: List[str]) -> Optional[float]:
    ablation = plan.get("ablation_um")
    if is_number(ablation) and 0 <= float(ablation) <= 400:
        return float(ablation)
    if ablation is not None:
        return None
    sphere = plan.get("intended_sphere_D")
    cylinder = plan.get("intended_cylinder_magnitude_D")
    optical_zone = plan.get("optical_zone_mm")
    platform = str(plan.get("laser_platform") or "").lower().replace(" ", "")
    is_ex500 = "alcon" in platform and "ex500" in platform
    ablation_rate = {6.0: 12.0, 6.5: 15.0, 7.0: 16.33}.get(optical_zone) if is_ex500 else None
    if is_number(sphere) and sphere > 0:
        warnings.append(
            "The CER-AI linear EX500 ablation estimate is not applied to a hyperopic or mixed-meridian plan; "
            "enter the actual laser-plan maximum ablation."
        )
        return None
    if is_number(sphere) and is_number(cylinder) and ablation_rate is not None:
        warnings.append(
            f"Maximum ablation estimated with the CER-AI Alcon EX500, {optical_zone:.1f}-mm-zone, "
            f"{ablation_rate:g} µm/D convention; "
            "actual laser-plan maximum is preferred."
        )
        return (abs(float(sphere)) + abs(float(cylinder))) * ablation_rate
    if is_number(sphere) and is_number(cylinder):
        warnings.append(
            "The CER-AI ablation estimate was not applied because an Alcon EX500 with a 6.0-mm, "
            "6.5-mm, or 7.0-mm optical zone was not explicitly documented."
        )
    return None


def refractive_pattern(sphere: Any, cylinder_magnitude: Any) -> Dict[str, Any]:
    """Classify a correction from its two principal meridians in minus-cylinder notation."""
    if not is_number(sphere) or not is_number(cylinder_magnitude):
        return {"category": "UNAVAILABLE", "principal_meridians_D": [None, None]}
    meridian_1 = float(sphere)
    meridian_2 = float(sphere) - float(cylinder_magnitude)
    eps = 1e-9
    if abs(meridian_1) <= eps:
        meridian_1 = 0.0
    if abs(meridian_2) <= eps:
        meridian_2 = 0.0
    if meridian_1 > 0 and meridian_2 > 0:
        category = "HYPEROPIC"
    elif meridian_1 > 0 and meridian_2 < 0:
        category = "MIXED_ASTIGMATISM"
    elif meridian_1 < 0 and meridian_2 < 0:
        category = "MYOPIC"
    elif meridian_1 > 0 and meridian_2 == 0:
        category = "SIMPLE_HYPEROPIC_ASTIGMATISM"
    elif meridian_1 == 0 and meridian_2 < 0:
        category = "SIMPLE_MYOPIC_ASTIGMATISM"
    elif meridian_1 == 0 and meridian_2 == 0:
        category = "PLANO"
    else:
        category = "UNCLASSIFIED"
    return {"category": category, "principal_meridians_D": [meridian_1, meridian_2]}


def required_tomography_missing(eye: Dict[str, Any]) -> List[str]:
    required = (
        "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"
    )
    missing = [key for key in required if not is_number(eye.get(key))]
    derived = scoring_morphology(eye)["category"]
    if derived not in MORPHOLOGY or derived == "UNCERTAIN":
        missing.append("classifiable topographic morphology")
    if eye.get("posterior_pattern") in (None, "UNREADABLE"):
        missing.append("readable posterior pattern")
    if eye.get("anterior_pattern") in (None, "UNREADABLE"):
        missing.append("readable anterior pattern")
    plausible_ranges = {
        "pachy_thinnest_um": (300, 800), "K1_D": (20, 80), "K2_D": (20, 80),
        "K1_axis_deg": (0, 180), "K2_axis_deg": (0, 180), "Kmax_D": (20, 90),
        "corneal_diameter_mm": (8, 16), "ARTmax_um": (1, 1000), "PPI_min": (0.01, 10),
        "PPI_avg": (0.01, 10), "PPI_max": (0.01, 10), "Rmin_mm": (3, 15),
        "thinnest_x_mm": (-10, 10), "thinnest_y_mm": (-10, 10),
        "anterior_elevation_thinnest_um": (-300, 300),
        "posterior_elevation_thinnest_um": (-300, 300),
    }
    for field, (low, high) in plausible_ranges.items():
        value = eye.get(field)
        if value is not None and (not is_number(value) or not low <= float(value) <= high):
            missing.append(f"plausible {field} ({low} to {high})")
    ppi_min, ppi_avg, ppi_max = eye.get("PPI_min"), eye.get("PPI_avg"), eye.get("PPI_max")
    if all(is_number(value) for value in (ppi_min, ppi_avg, ppi_max)) and not (
        float(ppi_min) <= float(ppi_avg) <= float(ppi_max)
    ):
        missing.append("internally consistent PPI minimum/average/maximum")
    # Defensive compatibility filter: legacy/cached extraction payloads may still contain
    # conflicts for descriptive, non-decision fields. They must never prohibit PASS.
    non_decision_conflict_fields = {
        "K1_D", "K2_D", "thinnest_x_mm", "thinnest_y_mm", "morphology_confidence"
    }
    for conflict in eye.get("data_conflicts", []):
        conflict_field = str(conflict).split(":", 1)[0].strip()
        if conflict_field in non_decision_conflict_fields:
            continue
        missing.append(f"unresolved multi-image conflict: {conflict}")
    return missing





def merge_extractions(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "eyes": [], "treatment_corrections": [], "global_warnings": [], "identity_warnings": [],
        "document_contexts": [], "critical_input_issues": [], "extraction_models": [],
    }
    by_eye: Dict[str, Dict[str, Any]] = {}
    conservative = {
        "BAD_D": "max", "Df": "max", "Db": "max",
        "Dp": "max", "Dt": "max", "Da": "max", "PPI_max": "max",
        "PPI_avg": "max", "PPI_min": "max", "ISV": "max", "IVA": "max",
        "KI": "max", "CKI": "max", "IHD": "max", "I_S": "max", "KISA": "max",
        "IHA": "max", "Rmin_mm": "min", "anterior_elevation_thinnest_um": "max",
        "posterior_elevation_thinnest_um": "max", "RMS_HOA_um": "max", "vertical_coma_um": "max",
        "srax_deg": "max", "inferior_opposite_steepening_D": "max",
    }
    morphology_rank = {
        "UNCERTAIN": 0, "NORMAL_SYMMETRIC": 1, "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 3, "ABNORMAL_ECTATIC": 4,
    }
    quality_rank = {"INADEQUATE": 0, "LIMITED": 1, "ADEQUATE": 2}
    posterior_rank = {"UNREADABLE": 0, "REASSURING": 1, "BORDERLINE": 2, "ABNORMAL": 3}
    numeric_tolerance = {
        "K1_D": 0.25, "K2_D": 0.25,
        "K1_axis_deg": 2.0, "K2_axis_deg": 2.0, "corneal_diameter_mm": 0.10,
    }
    # Descriptive values that do not drive a CER-AI decision must never become unresolved conflicts
    # that prohibit PASS. Across overlapping Pentacam screens, preserve source priority
    # (labeled table over permitted map fallback); at equal priority retain the first reading.
    non_decision_conflict_fields = {
        "thinnest_x_mm", "thinnest_y_mm", "morphology_confidence"
    }
    planning_conflict_fields = {"K1_axis_deg", "K2_axis_deg", "corneal_diameter_mm"}

    def normalized_eye(raw_eye: Dict[str, Any]) -> Dict[str, Any]:
        eye = dict(raw_eye)
        verified = eye.get("table_verified_numeric_fields")
        if isinstance(verified, list):
            verified_set = set(verified)
            if eye.get("keratometry_source") != CORNEA_FRONT_KERATOMETRY_SOURCE:
                missing = list(eye.get("missing_or_unreadable", []))
                for field in CORNEA_FRONT_KERATOMETRY_FIELDS:
                    missing.append(field)
                    eye[field] = None
                verified_set -= CORNEA_FRONT_KERATOMETRY_FIELDS
                eye["missing_or_unreadable"] = list(dict.fromkeys(missing))
            fallback_set = set(eye.get("map_fallback_numeric_fields", []))
            fallback_set &= set(MAP_FALLBACK_NUMERIC_FIELDS)
            fallback_set -= verified_set  # A readable labeled table value always has priority.
            missing = list(eye.get("missing_or_unreadable", []))
            source_ids = eye.get("canonical_source_ids")
            source_ids = source_ids if isinstance(source_ids, dict) else {}
            for field in LOCKED_FIELDS:
                if eye.get(field) is None:
                    continue
                if source_ids.get(field) != canonical_source_id(field):
                    eye[field] = None
                    verified_set.discard(field)
                    fallback_set.discard(field)
                    missing.append(field)
            for field in TABLE_NUMERIC_FIELDS:
                if eye.get(field) is not None and field not in verified_set and field not in fallback_set:
                    eye[field] = None
                    missing.append(field)
            eye["missing_or_unreadable"] = list(dict.fromkeys(missing))
            eye["table_verified_numeric_fields"] = sorted(verified_set)
            eye["map_fallback_numeric_fields"] = sorted(fallback_set)
        derived = scoring_morphology(eye)["category"]
        eye["scoring_morphology"] = derived
        if eye.get("morphology") in ("ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA") and derived == "UNCERTAIN":
            eye["morphology"] = "UNCERTAIN"
        if eye.get("asymmetric_bow_tie") == "YES" and derived != "ASYMMETRIC_BOWTIE":
            eye["asymmetric_bow_tie"] = "UNCERTAIN"
        if eye.get("srax") == "YES" and derived != "INFERIOR_STEEPENING_SRA":
            eye["srax"] = "UNCERTAIN"
        return eye

    for result in results:
        if result.get("extraction_model"):
            merged["extraction_models"].append(result["extraction_model"])
        context = result.get("document_context")
        if isinstance(context, dict):
            context = dict(context)
            context["extracted_eyes"] = sorted({
                eye.get("eye") for eye in result.get("eyes", [])
                if isinstance(eye, dict) and eye.get("eye") in EYES
            })
            merged["document_contexts"].append(context)
            if context.get("document_type") == "PENTACAM_TOPOGRAPHY" and not (
                context.get("patient_first_name") and context.get("patient_last_name")
            ):
                missing_name_fields = [
                    label for field, label in (
                        ("patient_last_name", "Last Name"), ("patient_first_name", "First Name")
                    ) if not context.get(field)
                ]
                merged["identity_warnings"].append(
                    "PATIENT NAME NOT VERIFIED: Pentacam "
                    f"{', '.join(missing_name_fields)} field(s) could not be read in "
                    f"{context.get('source_filename', 'an uploaded source')}. Surgeon confirmation is required."
                )
            if context.get("document_type") in ("UNKNOWN", "OTHER"):
                merged["critical_input_issues"].append(
                    f"Unclassified uploaded source: {context.get('source_filename', 'unknown file')}."
                )
            if context.get("document_type") in ("PENTACAM_TOPOGRAPHY", "TREATMENT_CARD") and not (
                context.get("patient_id") or context.get("patient_name")
            ):
                merged["identity_warnings"].append(
                    "PATIENT IDENTITY NOT VERIFIED: patient name/ID is not visible or readable in "
                    f"{context.get('source_filename', 'an uploaded source')}. Surgeon confirmation is required."
                )
            if not result.get("eyes") and not result.get("treatment_corrections"):
                merged["critical_input_issues"].append(
                    f"Uploaded source yielded no usable eye or treatment data: {context.get('source_filename', 'unknown file')}."
                )
        merged["global_warnings"].extend(result.get("global_warnings", []))
        merged["treatment_corrections"].extend(
            item for item in result.get("treatment_corrections", []) if isinstance(item, dict)
        )
        for raw_eye in result.get("eyes", []):
            source_eye = dict(raw_eye)
            if isinstance(context, dict) and context.get("document_type") == "PENTACAM_TOPOGRAPHY":
                # QS belongs to the acquisition/document, not to an independently inferred eye
                # value. Keep one canonical transfer path even for imported/legacy extractions.
                source_eye["_pentacam_qs"] = context.get("pentacam_qs", "NOT_SHOWN")
            eye = normalized_eye(source_eye)
            eye_id = eye.get("eye", "UNKNOWN")
            source_filename = eye.get("_source_filename")
            eye["source_files"] = [source_filename] if source_filename else []
            eye["quality_by_source"] = {source_filename: eye.get("quality")} if source_filename else {}
            eye["pentacam_qs"] = eye.get("_pentacam_qs", eye.get("pentacam_qs", "NOT_SHOWN"))
            eye["field_provenance"] = {}
            if source_filename:
                for field in eye.get("table_verified_numeric_fields", []):
                    if eye.get(field) is not None:
                        targeted = list((eye.get("targeted_reread_evidence") or {}).get(field) or [])
                        source = (
                            (eye.get("canonical_source_ids") or {}).get(field)
                            or (
                                CORNEA_FRONT_KERATOMETRY_SOURCE
                                if field in CORNEA_FRONT_KERATOMETRY_FIELDS
                                else "LABELED_TABLE"
                            )
                        )
                        eye["field_provenance"][field] = targeted or [
                            {"file": source_filename, "source": source}
                        ]
                for field in eye.get("map_fallback_numeric_fields", []):
                    if eye.get(field) is not None:
                        eye["field_provenance"][field] = [{"file": source_filename, "source": "PERMITTED_MAP_FALLBACK"}]
                for field in ("morphology", "anterior_pattern", "posterior_pattern", "asymmetric_bow_tie", "srax"):
                    if eye.get(field) is not None:
                        eye["field_provenance"][field] = [{"file": source_filename, "source": "VISUAL_CLASSIFICATION"}]
            if eye_id not in by_eye:
                by_eye[eye_id] = dict(eye)
                continue
            target = by_eye[eye_id]
            target.setdefault("data_conflicts", [])
            target_table_sources = set(target.get("table_verified_numeric_fields", []))
            target_map_sources = set(target.get("map_fallback_numeric_fields", []))
            incoming_table_sources = set(eye.get("table_verified_numeric_fields", []))
            incoming_map_sources = set(eye.get("map_fallback_numeric_fields", []))
            target["screen_types"] = sorted(set(target.get("screen_types", []) + eye.get("screen_types", [])))
            target["source_files"] = sorted(set(target.get("source_files", []) + eye.get("source_files", [])))
            target.setdefault("quality_by_source", {}).update(eye.get("quality_by_source", {}))
            target.setdefault("field_provenance", {})
            target.setdefault("canonical_source_ids", {})
            for field, source_id in (eye.get("canonical_source_ids") or {}).items():
                if source_id:
                    target["canonical_source_ids"][field] = source_id
            for field, records in eye.get("field_provenance", {}).items():
                if (
                    field in EXCLUSIVE_LABELED_BOX_FIELDS
                    and field in target_table_sources
                    and target.get(field) is not None
                ):
                    continue
                combined_records = target["field_provenance"].setdefault(field, []) + records
                target["field_provenance"][field] = [
                    dict(item) for item in {
                        json.dumps(record, sort_keys=True): record for record in combined_records
                    }.values()
                ]
            target["table_verified_numeric_fields"] = sorted(
                set(target.get("table_verified_numeric_fields", []))
                | set(eye.get("table_verified_numeric_fields", []))
            )
            target["map_fallback_numeric_fields"] = sorted(
                (
                    set(target.get("map_fallback_numeric_fields", []))
                    | set(eye.get("map_fallback_numeric_fields", []))
                )
                - set(target["table_verified_numeric_fields"])
            )
            if eye.get("keratometry_source") == CORNEA_FRONT_KERATOMETRY_SOURCE:
                target["keratometry_source"] = CORNEA_FRONT_KERATOMETRY_SOURCE
            elif not target.get("keratometry_source"):
                target["keratometry_source"] = eye.get("keratometry_source")
            target["morphology_evidence"] = list(
                dict.fromkeys(target.get("morphology_evidence", []) + eye.get("morphology_evidence", []))
            )
            target.setdefault("targeted_reread_evidence", {})
            for field, records in (eye.get("targeted_reread_evidence") or {}).items():
                combined = target["targeted_reread_evidence"].setdefault(field, []) + list(records or [])
                target["targeted_reread_evidence"][field] = [
                    dict(item) for item in {
                        json.dumps(record, sort_keys=True): record for record in combined
                    }.values()
                ]
            target.setdefault("targeted_unreadable_regions", {})
            for field, region in (eye.get("targeted_unreadable_regions") or {}).items():
                target["targeted_unreadable_regions"].setdefault(field, dict(region))
            target.setdefault("unreadable_source_regions", {})
            for field, region in (eye.get("unreadable_source_regions") or {}).items():
                target["unreadable_source_regions"].setdefault(field, dict(region))
            if quality_rank.get(eye.get("quality"), 0) > quality_rank.get(target.get("quality"), 0):
                target["quality"] = eye.get("quality")
            # Image quality is one canonical gate, not a synthetic multi-image value conflict.
            # An ancillary/overlapping limited page must not poison an otherwise adequate
            # same-eye source. If no adequate source exists, required_tomography_missing blocks
            # readiness through the eye's final quality value.
            target["data_conflicts"] = [
                conflict for conflict in target.get("data_conflicts", [])
                if conflict != "source image quality: limited/inadequate decision source"
            ]
            qs_values = {target.get("pentacam_qs"), eye.get("pentacam_qs")}
            if "NOT_OK" in qs_values:
                target["pentacam_qs"] = "NOT_OK"
            elif "OK" in qs_values:
                target["pentacam_qs"] = "OK"

            for key, value in eye.items():
                if key in (
                    "eye", "screen_types", "quality", "missing_or_unreadable",
                    "table_verified_numeric_fields", "map_fallback_numeric_fields",
                    "keratometry_source",
                    "morphology_evidence", "source_files", "quality_by_source", "_source_filename",
                    "_pentacam_qs", "pentacam_qs", "scoring_morphology", "field_provenance",
                    "planning_data_issues", "targeted_reread_evidence",
                    "canonical_source_ids", "targeted_unreadable_regions",
                    "unreadable_source_regions",
                ):
                    continue
                old = target.get(key)
                if old is None and value is not None:
                    target[key] = value
                    continue
                if value is None or old == value:
                    continue

                if (
                    key in EXCLUSIVE_LABELED_BOX_FIELDS
                    and key in target_table_sources
                    and key in incoming_table_sources
                ):
                    # This field is owned by its explicitly labeled Pentacam box. Retain the
                    # first valid same-eye box transcription; duplicate screens are not a
                    # consensus source and must not manufacture a conflict.
                    continue

                if key in TABLE_NUMERIC_FIELDS:
                    if key in incoming_table_sources and key in target_map_sources and key not in target_table_sources:
                        target[key] = value
                        continue
                    if key in target_table_sources and key in incoming_map_sources:
                        continue
                    if key in target_map_sources and key in incoming_map_sources:
                        # Same-parameter local readings are a lower-priority substitute for one
                        # unreadable edge box. Preserve the safety-limiting value but do not label
                        # this permitted fallback-source merge as an unresolved clinical conflict.
                        if key in conservative and is_number(old) and is_number(value):
                            target[key] = min(old, value) if conservative[key] == "min" else max(old, value)
                        merged["global_warnings"].append(
                            f"Multiple permitted local-map {key} readings for {eye_id}; "
                            "a conservative value was retained without creating an unresolved conflict."
                        )
                        continue

                # Missing/uncertain information on a page that lacks the relevant map is not
                # contradictory evidence against a readable observation on another page.
                if key == "morphology":
                    if old == "UNCERTAIN" and value != "UNCERTAIN":
                        target[key] = value
                        continue
                    if value == "UNCERTAIN":
                        continue
                elif key in ("anterior_pattern", "posterior_pattern"):
                    if old == "UNREADABLE" and value != "UNREADABLE":
                        target[key] = value
                        continue
                    if value == "UNREADABLE":
                        continue
                elif key in ("asymmetric_bow_tie", "srax"):
                    if old == "UNCERTAIN" and value != "UNCERTAIN":
                        target[key] = value
                        continue
                    if value == "UNCERTAIN":
                        continue

                if (
                    key in numeric_tolerance
                    and is_number(old)
                    and is_number(value)
                    and abs(float(old) - float(value)) <= numeric_tolerance[key]
                ):
                    continue

                if key in planning_conflict_fields:
                    target[key] = None
                    target.setdefault("planning_data_issues", []).append(
                        f"Conflicting {key} values ({old} vs {value}); microkeratome planning will not use this field."
                    )
                    continue

                if key in non_decision_conflict_fields:
                    continue

                target["data_conflicts"].append(f"{key}: {old} vs {value}")
                if key in conservative and is_number(old) and is_number(value):
                    target[key] = min(old, value) if conservative[key] == "min" else max(old, value)
                    merged["global_warnings"].append(
                        f"Conflicting {key} values for {eye_id}; conservative limiting value retained."
                    )
                elif key == "morphology":
                    target[key] = max((old, value), key=lambda item: morphology_rank.get(item, 0))
                    merged["global_warnings"].append(
                        f"Conflicting morphology classifications for {eye_id}; more concerning visible category retained."
                    )
                elif key == "posterior_pattern":
                    target[key] = max((old, value), key=lambda item: posterior_rank.get(item, 0))
                elif key == "anterior_pattern":
                    target[key] = max((old, value), key=lambda item: posterior_rank.get(item, 0))
                elif key in ("asymmetric_bow_tie", "srax"):
                    if "YES" in (old, value):
                        target[key] = "YES"
                    elif "UNCERTAIN" in (old, value):
                        target[key] = "UNCERTAIN"
                    else:
                        target[key] = "NO"
                elif old != value:
                    merged["global_warnings"].append(
                        f"Conflicting {key} values for {eye_id}: {old} vs {value}; first value retained."
                    )

    for eye in by_eye.values():
        # Remove any legacy/non-decision entries defensively before returning the payload.
        eye["data_conflicts"] = sorted(
            conflict for conflict in set(eye.get("data_conflicts", []))
            if str(conflict).split(":", 1)[0].strip() not in non_decision_conflict_fields
        )
        eye["missing_or_unreadable"] = sorted(
            set(key for key in eye.get("missing_or_unreadable", []) if eye.get(key) is None)
        )

    merged["eyes"] = list(by_eye.values())
    unique_corrections: List[Dict[str, Any]] = []
    seen_corrections = set()
    for correction in merged["treatment_corrections"]:
        key = json.dumps(correction, sort_keys=True, ensure_ascii=False)
        if key not in seen_corrections:
            seen_corrections.add(key)
            unique_corrections.append(correction)
    merged["treatment_corrections"] = unique_corrections
    pentacam_contexts = [
        c for c in merged["document_contexts"] if c.get("document_type") == "PENTACAM_TOPOGRAPHY"
    ]
    ids = {
        str(c.get("patient_id")).strip().casefold()
        for c in pentacam_contexts if c.get("patient_id")
    }
    normalized_names = [
        " ".join(str(c.get("patient_name") or "").casefold().split())
        for c in pentacam_contexts
    ]
    names = {name for name in normalized_names if name}
    pentacam_dates = {
        str(c.get("exam_date")).strip() for c in pentacam_contexts if c.get("exam_date")
    }
    pentacam_ages = {
        int(c["patient_age_years"]) for c in pentacam_contexts
        if is_number(c.get("patient_age_years"))
    }
    shared_readable_name = (
        bool(normalized_names)
        and all(normalized_names)
        and all(c.get("patient_first_name") and c.get("patient_last_name") for c in pentacam_contexts)
        and len(set(normalized_names)) == 1
    )
    age_is_consistent = len(pentacam_ages) <= 1
    identity_corroborated_by_name_and_age = (
        shared_readable_name and age_is_consistent and len(pentacam_ages) == 1
    )

    identity_readings = "; ".join(
        f"{c.get('source_filename', 'unknown file')}: {c.get('patient_name') or 'unreadable'}"
        for c in pentacam_contexts
    )
    if len(names) > 1:
        merged["identity_warnings"].append(
            "PATIENT IDENTITY NOT VERIFIED: different patient names were read from the Pentacam "
            f"First Name / Last Name fields ({identity_readings}). Surgeon confirmation is required."
        )
    if len(pentacam_ages) > 1:
        merged["patient_age_conflict_values"] = sorted(pentacam_ages)
        merged["global_warnings"].append(
            "Different printed patient ages were transcribed across Pentacam sources; "
            "no image-derived age was used and one surgeon-confirmed patient age is required."
        )
    elif len(pentacam_ages) == 1:
        merged["derived_age_years"] = next(iter(pentacam_ages))
    if len(ids) > 1:
        if identity_corroborated_by_name_and_age:
            merged["identity_warnings"].append(
                "PATIENT IDENTITY REQUIRES CONFIRMATION: different patient-ID strings were read, "
                "although the Pentacam First Name / Last Name fields and printed age agree."
            )
        else:
            merged["identity_warnings"].append(
                "PATIENT IDENTITY NOT VERIFIED: conflicting patient IDs were read across Pentacam sources. Surgeon confirmation is required."
            )
    if len(pentacam_dates) > 1:
        merged["critical_input_issues"].append("Conflicting Pentacam examination dates across uploaded sources.")

    assessed_eyes = {
        eye for context in pentacam_contexts for eye in context.get("extracted_eyes", [])
        if eye in EYES
    }
    if assessed_eyes == set(EYES):
        relevant_contexts = [
            context for context in pentacam_contexts
            if set(context.get("extracted_eyes", [])) & set(EYES)
        ]
        normalized_ids = [str(c.get("patient_id") or "").strip().casefold() for c in relevant_contexts]
        normalized_names = [
            " ".join(str(c.get("patient_name") or "").casefold().split()) for c in relevant_contexts
        ]
        verified_by_id = bool(normalized_ids) and all(normalized_ids) and len(set(normalized_ids)) == 1
        verified_by_name = (
            bool(normalized_names)
            and all(normalized_names)
            and all(c.get("patient_first_name") and c.get("patient_last_name") for c in relevant_contexts)
            and len(set(normalized_names)) == 1
        )
        if not (verified_by_id or verified_by_name):
            merged["identity_warnings"].append(
                "PATIENT IDENTITY NOT VERIFIED: OD and OS Pentacam sources could not be confirmed "
                f"as the same patient ({identity_readings}). Surgeon confirmation is required."
            )
    merged["global_warnings"] = sorted(set(merged["global_warnings"]))
    merged["identity_warnings"] = sorted(set(merged["identity_warnings"]))
    merged["critical_input_issues"] = sorted(set(merged["critical_input_issues"]))
    merged["extraction_models"] = sorted(set(merged["extraction_models"]))
    return merged


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        "static/sw.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )


@app.post("/report/pdf")
def report_pdf(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    from assessment_workflow import export_payload
    payload = export_payload(payload)
    content = build_pdf(payload)
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="CER-AI_Report.pdf"'},
    )


@app.post("/report/word")
def report_word(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    from assessment_workflow import export_payload
    payload = export_payload(payload)
    content = build_docx(payload)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="CER-AI_Report.docx"'},
    )


def normalize_document_context_identity(context: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce Pentacam name provenance; never accept a name copied from another box."""
    context = dict(context)
    if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
        return context
    first_name = str(context.get("patient_first_name") or "").strip() or None
    last_name = str(context.get("patient_last_name") or "").strip() or None
    context["patient_first_name"] = first_name
    context["patient_last_name"] = last_name
    context["patient_name"] = " ".join(
        component for component in (first_name, last_name) if component
    ) or None
    context["patient_name_source"] = (
        "PENTACAM_FIRST_LAST_NAME_FIELDS"
        if first_name or last_name
        else context.get("patient_name_source", "UNREADABLE")
    )
    return context


def extract_one_image(raw: bytes, filename: str) -> Dict[str, Any]:
    """Run one independent image extraction outside the async server event loop."""
    content = [
        {"type": "input_text", "text": PROMPT},
        {
            "type": "input_image",
            "image_url": data_url(raw, filename),
            "detail": "original",
        },
    ]
    response = openai_client().responses.create(
        model=MODEL,
        store=False,
        reasoning={"effort": "low"},
        input=[{"role": "user", "content": content}],
        text={
            "format": {
                "type": "json_schema", "name": "hc_preoperative_image_extraction",
                "strict": True, "schema": SCHEMA,
            }
        },
    )
    output_text = response.output_text
    print(
        "OPENAI DEBUG:", "status=", getattr(response, "status", None),
        "incomplete_details=", getattr(response, "incomplete_details", None),
        "output_length=", len(output_text or ""), flush=True,
    )
    if not output_text or not output_text.strip():
        raise RuntimeError(
            "OpenAI returned empty output_text. "
            f"status={getattr(response, 'status', None)}, "
            f"incomplete_details={getattr(response, 'incomplete_details', None)}"
        )
    try:
        result = json.loads(output_text)
        result["extraction_model"] = MODEL
        context = normalize_document_context_identity(result.get("document_context", {}))
        context["source_filename"] = filename
        result["document_context"] = context
        for eye in result.get("eyes", []):
            eye["_source_filename"] = filename
            eye["_pentacam_qs"] = context.get("pentacam_qs", "NOT_SHOWN")
        result = pentacam_targeted_reread.enrich_extraction(
            sys.modules[__name__], result, raw, filename
        )
        result = geometric_srax_policy.enrich_extraction(result, raw, filename)
        return result
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI output was not valid JSON: {exc}") from exc


def _analysis_request_key(request_id: Optional[str]) -> Optional[tuple[str, str]]:
    if not request_id:
        return None
    try:
        normalized = str(UUID(str(request_id)))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(400, "Invalid assessment request identifier.") from exc

    from user_access import current_principal

    principal = current_principal()
    actor = principal.user_id if principal is not None else "access-key-session"
    return actor, normalized


def _cached_analysis_task(key: tuple[str, str]) -> Optional[asyncio.Task]:
    now = monotonic()
    with _analysis_request_lock:
        expired = [
            item_key
            for item_key, (created, _task) in _analysis_request_tasks.items()
            if now - created > ANALYSIS_REQUEST_TTL_SECONDS
        ]
        for item_key in expired:
            _analysis_request_tasks.pop(item_key, None)
        record = _analysis_request_tasks.get(key)
        return record[1] if record else None


async def _run_image_assessment(
    image_payloads: list[tuple[bytes, str]],
    age: Optional[int],
    plans: Dict[str, Any],
    modifiers: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    from operational_security import admit_analysis, analysis_slot

    admit_analysis()

    # Every image remains an independent extraction. Bounded concurrency prevents the total
    # request time from becoming the sum of all upstream calls and keeps FastAPI responsive.
    concurrency = max(1, min(int(os.getenv("IMAGE_EXTRACTION_CONCURRENCY", "3")), 4))
    semaphore = asyncio.Semaphore(concurrency)

    async def extract_bounded(raw: bytes, filename: str) -> Dict[str, Any]:
        async with semaphore:
            return await asyncio.to_thread(extract_one_image, raw, filename)

    try:
        async with analysis_slot():
            extraction_results = await asyncio.gather(
                *(extract_bounded(raw, filename) for raw, filename in image_payloads)
            )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"IMAGE EXTRACTION ERROR: {type(exc).__name__}: {exc}", flush=True)
        raise HTTPException(
            502,
            "Image extraction service failed before the CER-AI assessment. Please retry once.",
        ) from exc

    from assessment_workflow import begin
    import sys
    extracted = merge_extractions(extraction_results)
    return begin(
        sys.modules[__name__], extracted, age, plans, modifiers, metadata,
        source_images=image_payloads,
    )


async def _await_analysis_task(
    task: asyncio.Task,
    key: Optional[tuple[str, str]],
) -> Dict[str, Any]:
    try:
        # The extraction must survive a mobile client disconnect so that the
        # retry can recover its result using the same request identifier.
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        raise
    except Exception:
        if key is not None and task.done():
            with _analysis_request_lock:
                record = _analysis_request_tasks.get(key)
                if record and record[1] is task:
                    _analysis_request_tasks.pop(key, None)
        raise


@app.post("/analyze")
async def analyze(
    images: List[UploadFile] = File(...),
    age: Optional[int] = Form(None),
    eye_plans: str = Form("{}"),
    patient_modifiers: str = Form("{}"),
    patient_metadata: str = Form("{}"),
    assessment_request_id: Optional[str] = Form(None),
):
    if not images:
        raise HTTPException(400, "No images supplied.")
    try:
        plans = json.loads(eye_plans)
        modifiers = json.loads(patient_modifiers)
        metadata = json.loads(patient_metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid structured clinical input: {exc}") from exc
    if not isinstance(plans, dict) or not isinstance(modifiers, dict) or not isinstance(metadata, dict):
        raise HTTPException(400, "eye_plans, patient_modifiers, and patient_metadata must be JSON objects.")

    from operational_security import read_uploads

    request_key = _analysis_request_key(assessment_request_id)
    if request_key is not None:
        existing = _cached_analysis_task(request_key)
        if existing is not None:
            return await _await_analysis_task(existing, request_key)

    image_payloads = await read_uploads(images)
    task = None
    if request_key is not None:
        with _analysis_request_lock:
            record = _analysis_request_tasks.get(request_key)
            if record is not None:
                task = record[1]
            else:
                task = asyncio.create_task(
                    _run_image_assessment(image_payloads, age, plans, modifiers, metadata)
                )
                _analysis_request_tasks[request_key] = (monotonic(), task)
    if task is None:
        task = asyncio.create_task(
            _run_image_assessment(image_payloads, age, plans, modifiers, metadata)
        )
    return await _await_analysis_task(task, request_key)
