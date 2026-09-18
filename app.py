import asyncio
import base64
import json
import mimetypes
import os
import sys
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

import mandatory_source_set_policy
from exam_date_reconciliation_policy import (
    EXAM_DATE_CONFLICT_ISSUE,
    FOUR_MAPS_EXAM_DATE_SOURCE,
    _is_four_maps_refractive,
    authoritative_exam_date_conflict,
    possible_calendar_dates,
    promote_consistent_targeted_exam_dates,
)
from patient_age_policy import resolve_patient_age
from pentacam_canonical_source_lock import (
    is_four_maps_eye, source_family as canonical_source_family,
    LOCKED_FIELDS, canonical_source_id,
)
from pentacam_field_registry import (
    CORNEA_FRONT_KERATOMETRY_FIELDS,
    CORNEA_FRONT_KERATOMETRY_SOURCE,
    EXTRACTION_NUMERIC_FIELDS,
    INITIAL_PASS_ONLY_CANONICAL_FIELDS,
    NON_MANDATORY_EXTRACTION_FIELDS,
    PASSIVE_INFORMATIONAL_FIELDS,
)
from reports import ReportContractError, build_conclusion_pdf, build_docx, build_pdf


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
    title="CER-AI — Corneal Ectasia Risk Assessment Intelligence v2.0",
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

# One canonical extraction contract with source-specific eye variants.  The
# model chooses the page family visible in the image and emits only fields that
# belong to that family's registered source boxes.  Downstream receives the
# same normalized flat eye dictionary after ``normalized_eye`` fills absent
# fields with nulls and reconstructs registry-owned provenance.
SOURCE_SPECIFIC_EYE_FIELDS = {
    "FOUR_MAPS_REFRACTIVE": (
        "central_pachy_um", "pachy_thinnest_um", "Kmax_D", "corneal_diameter_mm",
    ),
    "BAD_DISPLAY": (
        "F_Ele_Th_um", "B_Ele_Th_um", "PPI_avg", "BAD_D", "bad_flat_axis_deg",
    ),
    "SHOW_2_EXAMS_TOPOMETRIC": (
        "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D",
        "posterior_Kmean_D", "topographic_astig_D",
        "topographic_steep_axis_deg", "I_S",
    ),
    "OTHER": (),
}


def _source_specific_eye_schema(family: str) -> Dict[str, Any]:
    fields = SOURCE_SPECIFIC_EYE_FIELDS[family]
    keratometry_values = (
        [CORNEA_FRONT_KERATOMETRY_SOURCE, "UNREADABLE", "NOT_SHOWN"]
        if family == "SHOW_2_EXAMS_TOPOMETRIC"
        else ["OTHER_PENTACAM_SOURCE", "UNREADABLE", "NOT_SHOWN"]
    )
    properties: Dict[str, Any] = {
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "source_family": {"type": "string", "enum": [family]},
        "screen_types": {"type": "array", "items": {"type": "string"}},
        "quality": {"type": "string", "enum": ["ADEQUATE", "LIMITED", "INADEQUATE"]},
        "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
        "table_verified_numeric_fields": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": list(fields) or ["NO_NUMERIC_FIELDS"],
            },
        },
        "keratometry_source": {"type": "string", "enum": keratometry_values},
    }
    properties.update({field: {"type": ["number", "null"]} for field in fields})
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


SOURCE_SPECIFIC_EYE_SCHEMAS = [
    _source_specific_eye_schema(family) for family in SOURCE_SPECIFIC_EYE_FIELDS
]

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
                "patient_date_of_birth": {"type": ["string", "null"]},
                "exam_date": {"type": ["string", "null"]},
                "exam_date_source": {
                    "type": "string",
                    "enum": [FOUR_MAPS_EXAM_DATE_SOURCE, "UNREADABLE", "NOT_SHOWN"],
                },
                "exam_time": {"type": ["string", "null"]},
                "laterality": {"type": "string", "enum": ["OD", "OS", "BOTH", "UNKNOWN"]},
                "pentacam_qs": {
                    "type": "string",
                    "enum": ["OK", "NOT_OK", "UNREADABLE", "NOT_SHOWN", "NOT_APPLICABLE"],
                },
                "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "document_type", "patient_last_name", "patient_first_name",
                "patient_name", "patient_name_source", "patient_age_years", "patient_date_of_birth", "exam_date",
                "exam_date_source",
                "exam_time", "laterality", "pentacam_qs", "missing_or_unreadable",
            ],
        },
        "eyes": {
            "type": "array",
            "items": {"anyOf": SOURCE_SPECIFIC_EYE_SCHEMAS},
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

# Canonical EX500 extraction schema; no import-time extension layer.
SCHEMA["properties"]["document_context"]["properties"]["document_type"]["enum"].append("ALCON_EX500_PLANNING")
SCHEMA["properties"]["laser_plans"] = {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
    "properties": {
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "platform": {"type": "string", "enum": ["ALCON_WAVELIGHT_EX500", "UNKNOWN"]},
        "max_ablation_um": {"type": ["number", "null"]},
        "max_ablation_status": {"type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]},
        "profile_max_ablation_um": {"type": ["number", "null"]},
        "profile_max_status": {"type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]},
        "optical_zone_mm": {"type": ["number", "null"]},
        "ablation_zone_mm": {"type": ["number", "null"]},
        "flap_thickness_um": {"type": ["number", "null"]},
        "raw_max_ablation_text": {"type": ["string", "null"]},
        "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "eye", "platform", "max_ablation_um", "max_ablation_status",
        "profile_max_ablation_um", "profile_max_status", "optical_zone_mm",
        "ablation_zone_mm", "flap_thickness_um", "raw_max_ablation_text",
        "missing_or_unreadable",
    ],
}}
SCHEMA["required"].append("laser_plans")

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

Transcribe the explicitly printed patient age in completed years, exam time,
laterality, and document type exactly when visible. The examination date is source-locked: on a
4 Maps Refractive page, transcribe exam_date ONLY from the upper-left patient-information field
explicitly labeled "Exam Date" and from the value directly attached to that label. Ignore Date of
Birth, examination time, print/report/export dates, dates elsewhere on the page, and dates in any
other format or box. On BAD Display, Show 2 Exams Topometric, treatment cards, and every non-4-Maps
page, return exam_date=null and exam_date_source=NOT_SHOWN even if another date is visible. On a
4 Maps page, set exam_date_source=FOUR_MAPS_REFRACTIVE_UPPER_LEFT_EXAM_DATE only when the explicit
"Exam Date" label and its attached complete value are visible; otherwise return exam_date=null with
exam_date_source=UNREADABLE or NOT_SHOWN. Do not inspect or transcribe patient ID, record number,
examination number, measurement number, scan number, or accession number. Patient name is the sole
patient-identity field used by CER-AI. Use null/UNKNOWN when other identity fields are absent or
unreadable. Patient age is one patient-level value shared by
OD and OS: on every Pentacam source, inspect the top patient-demographics/header area for the explicitly
printed Age field, but return it only when the label and completed-year integer are both unambiguous.
On 4 Maps Refractive, transcribe the labeled Date of Birth exactly into patient_date_of_birth,
preserving the printed date format. Return null if absent or unreadable. The canonical engine
calculates completed years from this date and the examination date. Never perform date arithmetic
in the image extraction or place calculated age in patient_age_years. Never
infer that two images belong to the same patient merely because their laterality matches. For a Pentacam image, transcribe
the device quality specification only when the literal QS status is visible. Use OK only for an
explicitly visible acceptable/OK QS. Use NOT_OK for a visible non-OK status, UNREADABLE when the QS
area is present but cannot be read, and NOT_SHOWN when no QS field is visible. Treatment cards and
non-Pentacam documents use NOT_APPLICABLE.

CANONICAL SOURCE-SPECIFIC OUTPUT CONTRACT:
For each Pentacam eye item, first classify only the visible page as FOUR_MAPS_REFRACTIVE,
BAD_DISPLAY, SHOW_2_EXAMS_TOPOMETRIC, or OTHER in source_family. Return only the numeric properties
present in that source_family's schema variant. Never emit or search for a field belonging to another
page family. Add a field to table_verified_numeric_fields only when its own printed label and value
were transcribed from the exact box defined below. The list must exactly match the non-null numeric
outputs. Null is required when the authoritative label, sign, digits, units, or laterality are unclear.
No numeric map fallback, cross-page comparison, calculation, or derivation is permitted.

- FOUR_MAPS_REFRACTIVE: central_pachy_um, pachy_thinnest_um, Kmax_D, corneal_diameter_mm only.
- BAD_DISPLAY: F_Ele_Th_um, B_Ele_Th_um, PPI_avg, BAD_D, bad_flat_axis_deg only.
- SHOW_2_EXAMS_TOPOMETRIC: K1_D, K1_axis_deg, K2_D, K2_axis_deg, Kmean_D,
  posterior_Kmean_D, topographic_astig_D, topographic_steep_axis_deg, and I_S only.
- OTHER: no eye numeric fields.

Only K2_D, Kmean_D, posterior_Kmean_D, I_S, central_pachy_um, pachy_thinnest_um, F_Ele_Th_um,
B_Ele_Th_um, PPI_avg, and BAD_D are decision-required Pentacam fields. K1_D and
corneal_diameter_mm are conditional later LASIK-planning inputs. Kmax_D and the displayed axes or
astigmatism values are retained only when immediately clear from their exact labeled boxes; their
absence never triggers a targeted reread or blocks the clinical report.

I-S SOURCE LOCK: transcribe I_S only from the explicitly labeled "IS:" or "I-S:" field in
Show 2 Exams Topometric center "Indices (in 8 mm zone)". Preserve its printed sign. Never substitute
ISV, IVA, IHD, IHA, KISA, Q-value, a color, or a curvature-map spot for I_S.
If the IS label, sign, digits, or eye laterality is uncertain, return I_S=null; never calculate I-S.

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
- central_pachy_um: use only 4 Maps Refractive lower-left Pupil Center (+) pachymetry.
- F_Ele_Th_um: on the Belin/Ambrósio BAD Display, first locate the literal F.Ele.Th label in the
  central results table's elevation row immediately above the Progression Index section, then
  transcribe only the signed integer in the immediately adjacent value box. This is front/anterior elevation at the
  thinnest corneal point in µm. Never use K1, K2, Axis, an elevation map, or an unlabeled number.
- B_Ele_Th_um: on that same row immediately above Progression Index, first locate the literal B.Ele.Th label,
  then transcribe only the signed integer in its immediately adjacent value box. This is back/posterior
  elevation at the thinnest corneal point in µm. Never use K1, K2, Axis, an elevation map, or an
  unlabeled number.
- posterior_Kmean_D: use only Show 2 Exams Topometric -> Cornea Back -> printed Km.
- topographic_astig_D and topographic_steep_axis_deg: use only Show 2 Exams Topometric -> Cornea Front.
- ML7 planning reuses the canonical K1_D and K2_D values above. Do not create or request a second
  ML7-specific K1/K2 pair. HWTW remains in the 4 Maps Refractive lower-left HWTW box.
- bad_flat_axis_deg: for PS3 prescription-axis comparison ONLY, read the Axis box beside K1 in the BAD Display upper-middle numeric area. Never substitute the steep axis or derive a rotated value. Preserve all other axis sources and SRAX geometry.
- Kmax_D: use only the numeric value in the explicitly printed "KMax"/"Kmax" row.
- pachy_thinnest_um: use only the pachymetry value in the circle-marked printed
  "Thinnest Locat." row. Never use Pachy Vertex N., Pupil Center, or a thickness-map number.
These are single authoritative labeled-box readings. Never compare them with a map value,
neighboring number, calculated value, or another Pentacam screen to create a conflict. If the
authoritative row/panel is unreadable, return null for that field.

Never substitute a generic map spot, color-scale value, neighboring parameter, calculation, average,
or visual estimate for an output field. A labeled BAD-display center/bottom numeric box counts as a
printed parameter field; an unlabeled number inside a map does not.

ERSS VISUAL MORPHOLOGY DISABLED:
General ERSS/Randleman visual morphology classification is disabled. Do not visually score asymmetric
bow-tie, inferior steepening, keratoconus pattern, forme-fruste pattern, PMD pattern, or any other ERSS
morphology category.

ERSS SRAX SOURCE LOCK — MODEL ESTIMATION DISABLED:
SRAX is measured outside the extraction model by CER-AI's deterministic geometric image-analysis
engine using only the Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.
Do not visually estimate or return SRAX, and do not derive it from Kmax, I-S, astigmatism tables,
K1/K2/global Axis, BAD values, elevation, pachymetry, or any surrogate. SRAX is absent from this
model's schema; the deterministic geometry layer owns it exclusively.
BELIN/AMBROSIO BAD DISPLAY SOURCE LOCK:
BAD_D may be transcribed ONLY from the explicitly labeled final D value in the bottom BAD-D strip on
a visible Belin/Ambrosio Display for the same eye. Preserve every printed sign exactly. Never derive or
reconstruct Final D from component values and never return the component values. Never substitute a
color, map spot, neighboring value, or another screen/eye.

For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled
"Duzeltme Miktari" (including Turkish characters). Do not substitute values from "Subjektif
Refraksiyon" or any other row. Map SAG/right to OD and SOL/left to OS. Transcribe sphere, signed
cylinder, and axis exactly as written. Never convert absent cylinder or axis notation into zero.
When the row contains only one signed refractive value, return that value as sphere and keep
cylinder_D and axis_deg null. Any absent, obscured, cropped, ambiguous, or unreadable cylinder region
must remain null and UNCERTAIN or UNREADABLE. Otherwise, sphere_cylinder_status may be CONFIDENT only
when the sphere and cylinder digits and signs
are unambiguous. If either is ambiguous, set both numeric fields to null and use UNCERTAIN or
UNREADABLE while preserving visible characters in raw_text. Axis ambiguity does not require
discarding an otherwise confident nonzero sphere/cylinder pair; report it separately in axis_status
and set axis_deg to null when uncertain. Never transpose cylinder notation and never
infer the laser platform, optical zone, procedure, or ablation depth from the card. For a card-only
image with no corneal tomography/topography data, return an empty eyes array. For a tomography-only
image with no treatment card, return an empty treatment_corrections array. Downstream, a confident
Duzeltme Miktari is treated as both preoperative manifest refraction and intended correction unless
the clinician separately enters or otherwise explicitly identifies a different value for either role."""


PROMPT += (
    "\n\nCANONICAL PROVENANCE:\n"
    "Do not return source identifiers. CER-AI reconstructs provenance deterministically from "
    "source_family, table_verified_numeric_fields, and its single canonical field-source registry."
)
PROMPT += "\n" + mandatory_source_set_policy.BAD_DISPLAY_RECOGNITION_PROMPT

# Canonical EX500 transcription rule; no later prompt mutation.
PROMPT += """

ALCON WAVELIGHT EX500 PLANNING-SCREEN RULE:
An uploaded image may be an Alcon WaveLight EX500 treatment-planning screen. When the platform is visibly identifiable as WaveLight/EX500 and the screen shows treatment planning details, set DOCUMENT_TYPE=ALCON_EX500_PLANNING and return one laser_plans entry for the visibly identified eye. Use OD/right and OS/left exactly as displayed; never infer laterality.
The authoritative ablation field is the explicitly printed treatment-details value labeled "Maximal Ablation" or "Max. Ablation". Transcribe that number in micrometres into max_ablation_um only when the label, digits, unit/context, and eye are unambiguous; then set max_ablation_status to CONFIDENT. Preserve the visible label/value in raw_max_ablation_text. Do not calculate this value from sphere/cylinder, optical zone, colour scale, map geometry, residual stroma, or any other field. Do not estimate it visually.
The ablation-profile panel may separately print a value such as "max 109 µm". Transcribe it into profile_max_ablation_um only when unambiguous. This is a cross-check, not a substitute for an unreadable treatment-details Maximal/Max. Ablation field. If both printed values are confident and differ, preserve both values; downstream logic will treat the discrepancy as a conflict rather than choosing either one. The treatment-details Maximal/Max. Ablation value has source priority when the two agree.
Also transcribe explicitly printed Optical Zone, Ablation Zone, and Flap Thickness when readable, but never use them to reconstruct a missing maximum ablation. For an EX500 planning-only image, return an empty eyes array and an empty treatment_corrections array. For a non-EX500 image, return an empty laser_plans array. Pentacam QS is NOT_APPLICABLE on an EX500 planning screen.
"""


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

def normalized_eye(raw_eye: Dict[str, Any]) -> Dict[str, Any]:
    eye = dict(raw_eye)
    declared_family = eye.get("source_family")
    verified = eye.get("table_verified_numeric_fields")
    verified_set = set(verified) if isinstance(verified, list) else set()
    if declared_family in SOURCE_SPECIFIC_EYE_FIELDS:
        allowed_fields = set(SOURCE_SPECIFIC_EYE_FIELDS[declared_family])
        verified_set &= allowed_fields
        for field in EXTRACTION_NUMERIC_FIELDS:
            if field not in allowed_fields:
                eye[field] = None
        eye["canonical_source_ids"] = {
            field: (
                canonical_source_id(field)
                if field in verified_set and canonical_source_family(field) == declared_family
                else None
            )
            for field in LOCKED_FIELDS
        }
        eye["table_verified_numeric_fields"] = sorted(verified_set)
    for field in EXTRACTION_NUMERIC_FIELDS:
        eye.setdefault(field, None)
    eye.setdefault("canonical_source_ids", {})
    eye.setdefault("srax", None)
    eye.setdefault("srax_deg", None)
    # UNCERTAIN means no SRAX observation on this source, not a measured
    # disagreement with the Front-map geometry from another page.
    if eye.get("srax") == "UNCERTAIN":
        eye["srax"] = None
    eye.pop("targeted_unreadable_regions", None)
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
        missing = list(eye.get("missing_or_unreadable", []))
        source_ids = eye.get("canonical_source_ids")
        source_ids = source_ids if isinstance(source_ids, dict) else {}
        for field in LOCKED_FIELDS:
            if eye.get(field) is None:
                continue
            if source_ids.get(field) != canonical_source_id(field):
                eye[field] = None
                verified_set.discard(field)
                missing.append(field)
        for field in EXTRACTION_NUMERIC_FIELDS:
            if eye.get(field) is not None and field not in verified_set:
                eye[field] = None
                if field not in NON_MANDATORY_EXTRACTION_FIELDS:
                    missing.append(field)
        eye["missing_or_unreadable"] = [
            field for field in dict.fromkeys(missing)
            if field not in NON_MANDATORY_EXTRACTION_FIELDS
        ]
        eye["table_verified_numeric_fields"] = sorted(verified_set)
    return eye


def merge_extractions(
    results: List[Dict[str, Any]],
    surgeon_authority: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "eyes": [], "treatment_corrections": [], "laser_plans": [], "global_warnings": [], "identity_warnings": [],
        "document_contexts": [], "critical_input_issues": [], "extraction_models": [],
    }
    authoritative_patient = (surgeon_authority or {}).get("patient") or set()
    by_eye: Dict[str, Dict[str, Any]] = {}
    quality_rank = {"INADEQUATE": 0, "LIMITED": 1, "ADEQUATE": 2}
    # Descriptive values that do not drive a CER-AI decision must never become unresolved conflicts
    # that prohibit PASS. Canonical numeric disagreements are never tolerance-reconciled.
    non_decision_conflict_fields = (
        set(PASSIVE_INFORMATIONAL_FIELDS)
        | set(INITIAL_PASS_ONLY_CANONICAL_FIELDS)
        | {"morphology_confidence"}
    )
    planning_conflict_fields = {"K1_D", "corneal_diameter_mm"}


    for result in results:
        if result.get("extraction_model"):
            merged["extraction_models"].append(result["extraction_model"])
        context = result.get("document_context")
        if isinstance(context, dict):
            context = dict(context)
            passive_unreadable_card = (
                context.get("optional_treatment_card_status") == "UNREADABLE"
            )
            context["extracted_eyes"] = sorted({
                eye.get("eye") for eye in result.get("eyes", [])
                if isinstance(eye, dict) and eye.get("eye") in EYES
            })
            context["four_maps_eyes"] = sorted({
                eye.get("eye") for eye in result.get("eyes", [])
                if isinstance(eye, dict) and eye.get("eye") in EYES
                and is_four_maps_eye(eye)
            })
            merged["document_contexts"].append(context)
            if (
                "name" not in authoritative_patient
                and context.get("document_type") == "PENTACAM_TOPOGRAPHY"
                and not (
                context.get("patient_first_name") and context.get("patient_last_name")
                )
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
            if context.get("document_type") in ("UNKNOWN", "OTHER") and not passive_unreadable_card:
                merged["critical_input_issues"].append(
                    f"Unclassified uploaded source: {context.get('source_filename', 'unknown file')}."
                )
            if (
                "name" not in authoritative_patient
                and context.get("document_type") in ("PENTACAM_TOPOGRAPHY", "TREATMENT_CARD")
                and not context.get("patient_name")
            ):
                merged["identity_warnings"].append(
                    "PATIENT NAME NOT VERIFIED: patient name is not visible or readable in "
                    f"{context.get('source_filename', 'an uploaded source')}. Surgeon confirmation is required."
                )
            if (
                not result.get("eyes")
                and not result.get("treatment_corrections")
                and not result.get("laser_plans")
                and not passive_unreadable_card
            ):
                merged["critical_input_issues"].append(
                    f"Uploaded source yielded no usable eye or treatment data: {context.get('source_filename', 'unknown file')}."
                )
            if passive_unreadable_card:
                merged["global_warnings"].append(
                    "Optional treatment card was unreadable; surgeon-entered manifest and intended refraction were used."
                )
        merged["global_warnings"].extend(result.get("global_warnings", []))
        merged["treatment_corrections"].extend(
            item for item in result.get("treatment_corrections", []) if isinstance(item, dict)
        )
        for item in result.get("laser_plans", []):
            if isinstance(item, dict):
                copied = dict(item)
                copied["source_filename"] = (context or {}).get("source_filename") if isinstance(context, dict) else None
                merged["laser_plans"].append(copied)
        for raw_eye in result.get("eyes", []):
            source_eye = dict(raw_eye)
            if isinstance(context, dict) and context.get("document_type") == "PENTACAM_TOPOGRAPHY":
                # QS belongs to the acquisition/document, not to an independently inferred eye
                # value. Keep one canonical transfer path even for imported/legacy extractions.
                source_eye["_pentacam_qs"] = context.get("pentacam_qs", "NOT_SHOWN")
            eye = normalized_eye(source_eye)
            eye.pop("source_family", None)
            eye_id = eye.get("eye", "UNKNOWN")
            source_filename = eye.get("_source_filename")
            eye["source_files"] = [source_filename] if source_filename else []
            eye["quality_by_source"] = {source_filename: eye.get("quality")} if source_filename else {}
            eye["pentacam_qs"] = eye.get("_pentacam_qs", eye.get("pentacam_qs", "NOT_SHOWN"))
            eye["field_provenance"] = {
                field: list((source_eye.get("field_provenance") or {}).get(field) or [])
                for field in ("srax", "srax_deg")
                if (source_eye.get("field_provenance") or {}).get(field)
            }
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
            if eye_id not in by_eye:
                by_eye[eye_id] = dict(eye)
                continue
            target = by_eye[eye_id]
            target.setdefault("data_conflicts", [])
            target["data_conflicts"].extend(
                conflict for conflict in (eye.get("data_conflicts") or [])
                if conflict not in target["data_conflicts"]
            )
            target["screen_types"] = sorted(set(target.get("screen_types", []) + eye.get("screen_types", [])))
            target["source_files"] = sorted(set(target.get("source_files", []) + eye.get("source_files", [])))
            target.setdefault("quality_by_source", {}).update(eye.get("quality_by_source", {}))
            target.setdefault("field_provenance", {})
            target.setdefault("canonical_source_ids", {})
            for field, source_id in (eye.get("canonical_source_ids") or {}).items():
                if source_id:
                    target["canonical_source_ids"][field] = source_id
            for field, records in eye.get("field_provenance", {}).items():
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
            if eye.get("keratometry_source") == CORNEA_FRONT_KERATOMETRY_SOURCE:
                target["keratometry_source"] = CORNEA_FRONT_KERATOMETRY_SOURCE
            elif not target.get("keratometry_source"):
                target["keratometry_source"] = eye.get("keratometry_source")
            target.setdefault("targeted_reread_evidence", {})
            for field, records in (eye.get("targeted_reread_evidence") or {}).items():
                combined = target["targeted_reread_evidence"].setdefault(field, []) + list(records or [])
                target["targeted_reread_evidence"][field] = [
                    dict(item) for item in {
                        json.dumps(record, sort_keys=True): record for record in combined
                    }.values()
                ]
            target.setdefault("threshold_elevation_verification_evidence", {})
            target["threshold_elevation_verification_evidence"].update(
                eye.get("threshold_elevation_verification_evidence") or {}
            )
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
                    "table_verified_numeric_fields",
                    "keratometry_source",
                    "source_files", "quality_by_source", "_source_filename",
                    "_pentacam_qs", "pentacam_qs", "scoring_morphology", "field_provenance",
                    "planning_data_issues", "targeted_reread_evidence",
                    "threshold_elevation_verification_evidence",
                    "canonical_source_ids", "unreadable_source_regions", "data_conflicts",
                ):
                    continue
                # Once a field conflicts, no later duplicate may silently refill it.
                existing_unresolved_conflict = any(
                    str(item).split(":", 1)[0].strip() == key
                    for item in target.get("data_conflicts", [])
                )
                if existing_unresolved_conflict:
                    continue
                old = target.get(key)
                if old is None and value is not None:
                    target[key] = value
                    continue
                if value is None or old == value:
                    continue
                if key in LOCKED_FIELDS:
                    target["data_conflicts"].append(f"{key}: {old} vs {value}")
                    target[key] = None
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
                target[key] = None
                merged["global_warnings"].append(
                    f"Conflicting {key} values for {eye_id}: {old} vs {value}; "
                    "value left unresolved for surgeon confirmation."
                )

    for eye in by_eye.values():
        # Remove any legacy/non-decision entries defensively before returning the payload.
        eye["data_conflicts"] = sorted(
            conflict for conflict in set(eye.get("data_conflicts", []))
            if str(conflict).split(":", 1)[0].strip() not in non_decision_conflict_fields
        )
        eye["missing_or_unreadable"] = sorted(
            set(
                key for key in eye.get("missing_or_unreadable", [])
                if eye.get(key) is None and key not in NON_MANDATORY_EXTRACTION_FIELDS
            )
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
    normalized_names = [
        " ".join(str(c.get("patient_name") or "").casefold().split())
        for c in pentacam_contexts
    ]
    names = {name for name in normalized_names if name}
    age_resolution = resolve_patient_age(results)
    merged["patient_age_resolution"] = age_resolution
    pentacam_ages = set(age_resolution["candidate_ages"])
    identity_readings = "; ".join(
        f"{c.get('source_filename', 'unknown file')}: {c.get('patient_name') or 'unreadable'}"
        for c in pentacam_contexts
    )
    if len(names) > 1 and "name" not in authoritative_patient:
        merged["identity_warnings"].append(
            "PATIENT IDENTITY NOT VERIFIED: different patient names were read from the Pentacam "
            f"First Name / Last Name fields ({identity_readings}). Surgeon confirmation is required."
        )
    if age_resolution["warning"]:
        merged["patient_age_conflict_values"] = sorted(pentacam_ages)
        merged["global_warnings"].append(
            age_resolution["warning"]
        )
    elif age_resolution["age_years"] is not None:
        merged["derived_age_years"] = age_resolution["age_years"]
    if authoritative_exam_date_conflict(results):
        merged["critical_input_issues"].append(EXAM_DATE_CONFLICT_ISSUE)

    assessed_eyes = {
        eye for context in pentacam_contexts for eye in context.get("extracted_eyes", [])
        if eye in EYES
    }
    if assessed_eyes == set(EYES) and "name" not in authoritative_patient:
        relevant_contexts = [
            context for context in pentacam_contexts
            if set(context.get("extracted_eyes", [])) & set(EYES)
        ]
        normalized_names = [
            " ".join(str(c.get("patient_name") or "").casefold().split()) for c in relevant_contexts
        ]
        verified_by_name = (
            bool(normalized_names)
            and all(normalized_names)
            and all(c.get("patient_first_name") and c.get("patient_last_name") for c in relevant_contexts)
            and len(set(normalized_names)) == 1
        )
        if not verified_by_name:
            merged["identity_warnings"].append(
                "PATIENT IDENTITY NOT VERIFIED: OD and OS Pentacam sources could not be confirmed "
                f"as the same patient ({identity_readings}). Surgeon confirmation is required."
            )
    merged["global_warnings"] = sorted(set(merged["global_warnings"]))
    merged["identity_warnings"] = sorted(set(merged["identity_warnings"]))
    merged["critical_input_issues"] = sorted(set(merged["critical_input_issues"]))
    merged["extraction_models"] = sorted(set(merged["extraction_models"]))
    if authoritative_patient:
        merged["surgeon_authoritative_patient_fields"] = sorted(authoritative_patient)

    # One explicit post-merge extraction audit; this helper never owns or replaces merge_extractions.
    from extraction_guard import apply_extraction_validation
    return apply_extraction_validation(merged)


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
    try:
        content = build_pdf(payload)
    except ReportContractError as exc:
        raise HTTPException(409, f"Complete canonical report unavailable: {exc}") from exc
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="CER-AI_Report.pdf"'},
    )


@app.post("/report/word")
def report_word(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    from assessment_workflow import export_payload
    payload = export_payload(payload)
    try:
        content = build_docx(payload)
    except ReportContractError as exc:
        raise HTTPException(409, f"Complete canonical report unavailable: {exc}") from exc
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="CER-AI_Report.docx"'},
    )


@app.post("/report/conclusion/pdf")
def report_conclusion_pdf(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    from assessment_workflow import export_payload
    payload = export_payload(payload)
    try:
        content = build_conclusion_pdf(payload)
    except ReportContractError as exc:
        raise HTTPException(409, f"Complete canonical report unavailable: {exc}") from exc
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="CER-AI_Conclusion.pdf"'},
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


def enforce_exam_date_source_lock(
    result: Dict[str, Any], context: Dict[str, Any],
) -> Dict[str, Any]:
    """Accept only the labeled upper-left Four Maps Exam Date field."""
    context = dict(context)
    valid = (
        _is_four_maps_refractive(result)
        and context.get("exam_date_source") == FOUR_MAPS_EXAM_DATE_SOURCE
        and bool(possible_calendar_dates(context.get("exam_date")))
    )
    if not valid:
        context["exam_date"] = None
        context["exam_date_source"] = (
            "UNREADABLE"
            if _is_four_maps_refractive(result)
            and context.get("exam_date_source") == "UNREADABLE"
            else "NOT_SHOWN"
        )
        context["missing_or_unreadable"] = [
            item for item in context.get("missing_or_unreadable") or []
            if item != "exam_date"
        ]
    return context


def surgeon_image_authority(
    age: Optional[int], plans: Dict[str, Any], metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Describe pre-assessment surgeon values that image reading must not challenge."""
    patient = set()
    if str(metadata.get("name") or "").strip():
        patient.add("name")
    if age is not None:
        patient.add("age")
    eyes = {
        eye: {"I_S"} if isinstance(plan, dict) and plan.get("surgeon_I_S_D") is not None else set()
        for eye, plan in plans.items() if eye in EYES
    }
    return {"patient": patient, "eyes": eyes}


def surgeon_authority_prompt(authority: Dict[str, Any]) -> str:
    """Generate explicit no-read instructions for already authoritative inputs."""
    rules = []
    patient = authority.get("patient") or set()
    if "name" in patient:
        rules.append(
            "Patient name was entered by the surgeon. Do not inspect or transcribe any image name; "
            "return patient_first_name, patient_last_name, and patient_name as null, "
            "patient_name_source=NOT_SHOWN, and do not list them as missing."
        )
    if "age" in patient:
        rules.append(
            "Patient age was entered by the surgeon. Do not inspect or transcribe image age or date "
            "of birth; return patient_age_years=null and patient_date_of_birth=null and do not list "
            "either as missing."
        )
    for eye, fields in sorted((authority.get("eyes") or {}).items()):
        if "I_S" in fields:
            rules.append(
                f"{eye} I-S was entered by the surgeon. Do not inspect or transcribe {eye} I_S; "
                "return it as null, omit it from table_verified_numeric_fields, and do not list it as missing."
            )
    if not rules:
        return ""
    return (
        "\n\nSURGEON-AUTHORITATIVE PRE-ASSESSMENT INPUTS:\n"
        "The following values are final inputs, not facts to confirm against images. "
        "Follow each no-read instruction exactly.\n- " + "\n- ".join(rules)
    )


def apply_surgeon_image_authority(
    result: Dict[str, Any], authority: Dict[str, Any],
) -> Dict[str, Any]:
    """Enforce no-read fields even if a model returned them despite the prompt."""
    patient = authority.get("patient") or set()
    context = result.get("document_context") or {}
    missing = list(context.get("missing_or_unreadable") or [])
    if "name" in patient:
        for key in ("patient_first_name", "patient_last_name", "patient_name"):
            context[key] = None
            missing = [item for item in missing if item != key]
        context["patient_name_source"] = "NOT_SHOWN"
    if "age" in patient:
        context["patient_age_years"] = None
        context["patient_date_of_birth"] = None
        missing = [
            item for item in missing
            if item not in {"patient_age_years", "patient_date_of_birth"}
        ]
    context["missing_or_unreadable"] = missing
    result["document_context"] = context

    for eye in result.get("eyes") or []:
        excluded = (authority.get("eyes") or {}).get(eye.get("eye"), set())
        for field in excluded:
            eye[field] = None
            eye["table_verified_numeric_fields"] = [
                item for item in eye.get("table_verified_numeric_fields") or [] if item != field
            ]
            if isinstance(eye.get("canonical_source_ids"), dict):
                eye["canonical_source_ids"][field] = None
            eye["missing_or_unreadable"] = [
                item for item in eye.get("missing_or_unreadable") or [] if item != field
            ]
    return result


def extract_one_image(
    raw: bytes, filename: str, surgeon_authority: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run one independent image extraction outside the async server event loop."""
    surgeon_authority = surgeon_authority or {}
    content = [
        {
            "type": "input_text",
            "text": PROMPT + surgeon_authority_prompt(surgeon_authority or {}),
        },
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
        result = apply_surgeon_image_authority(result, surgeon_authority or {})
        context = normalize_document_context_identity(result.get("document_context", {}))
        context = enforce_exam_date_source_lock(result, context)
        context["source_filename"] = filename
        result["document_context"] = context
        for eye in result.get("eyes", []):
            eye["_source_filename"] = filename
            eye["_pentacam_qs"] = context.get("pentacam_qs", "NOT_SHOWN")
        # Primary transcription ends here. The case-level source-set gate runs
        # before any targeted reread or geometric SRAX processing.
        result["eyes"] = [normalized_eye(eye) for eye in result.get("eyes", [])]
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


def primary_extraction_concurrency(image_count: int) -> int:
    """Start the five mandatory source reads together, with a bounded override."""
    configured = int(os.getenv("IMAGE_EXTRACTION_CONCURRENCY", "5"))
    return max(1, min(configured, 5, max(1, image_count)))


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
    concurrency = primary_extraction_concurrency(len(image_payloads))
    semaphore = asyncio.Semaphore(concurrency)
    assessment_started = monotonic()
    automation_deadline = pentacam_targeted_reread.assessment_automation_deadline(
        assessment_started
    )
    surgeon_authority = surgeon_image_authority(age, plans, metadata)

    async def extract_bounded(
        image_number: int, raw: bytes, filename: str,
    ) -> Dict[str, Any]:
        async with semaphore:
            image_started = monotonic()
            result = await asyncio.to_thread(
                extract_one_image, raw, filename, surgeon_authority
            )
            source_set = mandatory_source_set_policy.classify_source_set([result])
            source_roles = [
                item["label"] for item in source_set["required_sources"]
                if item["present"]
            ]
            if not source_roles:
                optional_card = source_set["optional_treatment_card"]
                source_roles = [
                    "Excimer laser treatment card"
                    if optional_card["present"] else "Unclassified source"
                ]
            print(
                "ASSESSMENT TIMING:",
                "stage=primary_image",
                f"image={image_number}",
                f"duration_ms={round((monotonic() - image_started) * 1000)}",
                f"source_role={json.dumps(source_roles, separators=(',', ':'))}",
                flush=True,
            )
            return result

    try:
        async with analysis_slot():
            extraction_results = await asyncio.gather(
                *(
                    extract_bounded(image_number, raw, filename)
                    for image_number, (raw, filename) in enumerate(image_payloads, start=1)
                )
            )
            print(
                "ASSESSMENT TIMING:",
                f"stage=primary_extraction duration_ms={round((monotonic() - assessment_started) * 1000)}",
                f"images={len(image_payloads)}",
                flush=True,
            )
            # Page identity from the primary read is the single source-set authority.
            # Stop here if one of the five mandatory sources is absent; no targeted
            # reread, SRAX measurement, merge, clinical score, or report may start.
            mandatory_source_set = mandatory_source_set_policy.validate_preassessment_requirements(
                extraction_results, plans
            )
            exam_date_reread_required = authoritative_exam_date_conflict(extraction_results)

            async def enrich_bounded(
                result: Dict[str, Any], raw: bytes, filename: str,
            ) -> Dict[str, Any]:
                async with semaphore:
                    reread = await asyncio.to_thread(
                        pentacam_targeted_reread.enrich_extraction,
                        sys.modules[__name__], result, raw, filename,
                        exam_date_requested=(
                            exam_date_reread_required and _is_four_maps_refractive(result)
                        ),
                        seek_patient_age=age is None,
                        excluded_fields_by_eye=surgeon_authority["eyes"],
                        deadline_monotonic=automation_deadline,
                    )
                    reread = await asyncio.to_thread(
                        pentacam_targeted_reread.verify_threshold_level_bad_elevations,
                        sys.modules[__name__], reread, raw, filename,
                        deadline_monotonic=automation_deadline,
                    )
                    return await asyncio.to_thread(
                        geometric_srax_policy.enrich_extraction, reread, raw, filename,
                    )

            extraction_results = await asyncio.gather(*(
                enrich_bounded(result, raw, filename)
                for result, (raw, filename) in zip(extraction_results, image_payloads)
            ))
            print(
                "ASSESSMENT TIMING:",
                f"stage=targeted_enrichment cumulative_ms={round((monotonic() - assessment_started) * 1000)}",
                flush=True,
            )
            if exam_date_reread_required:
                promote_consistent_targeted_exam_dates(extraction_results)

            print(
                "ASSESSMENT TIMING:",
                f"stage=automatic_extraction_complete cumulative_ms={round((monotonic() - assessment_started) * 1000)}",
                f"budget_ms={round(pentacam_targeted_reread.assessment_automation_budget_seconds() * 1000)}",
                flush=True,
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
    extracted = merge_extractions(extraction_results, surgeon_authority)
    extracted["mandatory_source_set"] = mandatory_source_set
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

    mandatory_source_set_policy.validate_upload_count(len(images))

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
