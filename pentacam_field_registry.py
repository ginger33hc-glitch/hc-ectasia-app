"""Single registry for Pentacam fields used by extraction and completion.

Extraction schemas remain in their owning adapters, while canonical field names
and user-facing completion labels live here. No clinical threshold or score is
defined in this module.
"""

from pentacam_canonical_source_lock import CANONICAL_FIELD_SOURCES

TARGET_FIELDS = tuple(CANONICAL_FIELD_SOURCES)

# Optional descriptive values may be retained when their own printed label and
# value are immediately readable during the primary pass. They never trigger a
# targeted reread, surgeon completion, warning, report requirement or decision.
PASSIVE_INFORMATIONAL_FIELDS = (
    "thinnest_x_mm", "thinnest_y_mm", "corneal_volume_mm3", "RMS_HOA_um",
    "vertical_coma_um", "total_RMS_um", "spherical_aberration_um",
)

EXTRACTION_NUMERIC_FIELDS = TARGET_FIELDS + PASSIVE_INFORMATIONAL_FIELDS

CORNEA_FRONT_KERATOMETRY_SOURCE = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
CORNEA_FRONT_KERATOMETRY_FIELDS = frozenset({"K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D"})
KERATOMETRY_SOURCE_VALUES = (
    CORNEA_FRONT_KERATOMETRY_SOURCE, "OTHER_PENTACAM_SOURCE", "UNREADABLE", "NOT_SHOWN",
)

COMPLETION_NUMERIC_FIELDS = {
    "pachy_thinnest_um": "Thinnest pachymetry (µm)",
    "central_pachy_um": "Pupil Center (+) pachymetry (µm; 4 Maps Refractive)",
    "BAD_D": "Final BAD-D",
    "Df": "BAD Df", "Db": "BAD Db", "Dp": "BAD Dp", "Dt": "BAD Dt", "Da": "BAD Da",
    "ARTmax_um": "ARTmax (µm)", "PPI_min": "PPI minimum", "PPI_avg": "PPI average", "PPI_max": "PPI maximum",
    "K1_D": "K1 (D)", "K2_D": "K2 (D; not Kmax)", "Kmean_D": "Preoperative Kmean (D)",
    "Kmax_D": "Kmax (D)", "srax_deg": "SRAX (degrees)",
    "Rmin_mm": "Cornea Back Rmin (mm)", "topometric_RMin": "Topometric RMin (8 mm indices)",
    "I_S": "Signed I-S (D; not ISV/IVA)", "TKC": "TKC (Show 2 Exams center indices)",
    "topographic_astig_D": "Topographic Astig. (D; Cornea Front)",
    "topographic_steep_axis_deg": "Topographic Axis (steep) (degrees; Cornea Front)",
    "ml7_bad_k1_d": "ML7 K1 (D; BAD Display upper-middle K1 box)",
    "ml7_bad_k2_d": "ML7 K2 (D; BAD Display upper-middle K2 box)",
    "bad_flat_axis_deg": "PS3 BAD Axis (degrees; upper-middle box beside K1; flat meridian)",
    "posterior_Kmean_D": "Posterior Km (D; Cornea Back)",
    "F_Ele_Th_um": "F. Ele.Th (µm; BAD Display labeled box)",
    "B_Ele_Th_um": "B. Ele.Th (µm; BAD Display labeled box)",
}


def completion_label(field: str) -> str:
    return COMPLETION_NUMERIC_FIELDS[field]
