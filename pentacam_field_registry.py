"""Single registry for Pentacam fields used by extraction and completion.

Extraction schemas remain in their owning adapters, while canonical field names
and user-facing completion labels live here. No clinical threshold or score is
defined in this module.
"""

from pentacam_canonical_source_lock import CANONICAL_FIELD_SOURCES

# These are the only Pentacam values whose absence can prevent the canonical
# clinical decision/report from being completed. They retain the existing
# five-attempt targeted-reread policy.
DECISION_REQUIRED_FIELDS = (
    "K2_D", "Kmean_D", "posterior_Kmean_D", "I_S",
    "central_pachy_um", "pachy_thinnest_um",
    "F_Ele_Th_um", "B_Ele_Th_um", "PPI_avg", "BAD_D",
)

# Context displayed in the canonical BAD section is important for surgeon
# review even though Final BAD-D remains the only BAD disposition signal.
# Give missing values one focused reread, without turning them into completion
# blockers or independent clinical scores.
REPORT_CONTEXT_REREAD_FIELDS = (
    "PPI_min", "PPI_max", "ARTmax_um", "Df", "Db", "Dp", "Dt", "Da",
)

# These values are not decision inputs.  They are requested from the surgeon
# only after a favorable LASIK assessment when ML7 ring planning needs them.
# They must not cause automatic image rereads before the clinical decision.
CONDITIONAL_REPORT_FIELDS = (
    "K1_D", "corneal_diameter_mm",
)

# Retain these canonical values when their printed label/value is clear on the
# initial pass. If absent or unreadable, bypass them without reread, completion
# request, warning, or report block. This includes the non-scoring Topometric
# indices requested for one primary-pass attempt.
INITIAL_PASS_ONLY_CANONICAL_FIELDS = tuple(
    field for field in CANONICAL_FIELD_SOURCES
    if field not in (
        set(DECISION_REQUIRED_FIELDS)
        | set(REPORT_CONTEXT_REREAD_FIELDS)
        | set(CONDITIONAL_REPORT_FIELDS)
    )
)

assert set(DECISION_REQUIRED_FIELDS).isdisjoint(CONDITIONAL_REPORT_FIELDS)
assert set(REPORT_CONTEXT_REREAD_FIELDS).isdisjoint(DECISION_REQUIRED_FIELDS)
assert (
    set(DECISION_REQUIRED_FIELDS)
    | set(REPORT_CONTEXT_REREAD_FIELDS)
    | set(CONDITIONAL_REPORT_FIELDS)
    | set(INITIAL_PASS_ONLY_CANONICAL_FIELDS)
) == set(CANONICAL_FIELD_SOURCES)

TARGET_FIELDS = DECISION_REQUIRED_FIELDS + REPORT_CONTEXT_REREAD_FIELDS

# Optional descriptive values may be retained when their own printed label and
# value are immediately readable during the primary pass. They never trigger a
# targeted reread, surgeon completion, warning, report requirement or decision.
PASSIVE_INFORMATIONAL_FIELDS = (
    "thinnest_x_mm", "thinnest_y_mm", "corneal_volume_mm3", "RMS_HOA_um",
    "vertical_coma_um", "total_RMS_um", "spherical_aberration_um",
)

NON_MANDATORY_EXTRACTION_FIELDS = (
    CONDITIONAL_REPORT_FIELDS
    + REPORT_CONTEXT_REREAD_FIELDS
    + INITIAL_PASS_ONLY_CANONICAL_FIELDS
    + PASSIVE_INFORMATIONAL_FIELDS
)

# The strict extraction schema still exposes every field so an immediately
# readable optional value can be retained.  "Required" here is a JSON-shape
# constraint (nullable), not a clinical requirement.
EXTRACTION_NUMERIC_FIELDS = tuple(CANONICAL_FIELD_SOURCES) + PASSIVE_INFORMATIONAL_FIELDS

CORNEA_FRONT_KERATOMETRY_SOURCE = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
CORNEA_FRONT_KERATOMETRY_FIELDS = frozenset({"K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D"})
KERATOMETRY_SOURCE_VALUES = (
    CORNEA_FRONT_KERATOMETRY_SOURCE, "OTHER_PENTACAM_SOURCE", "UNREADABLE", "NOT_SHOWN",
)

COMPLETION_NUMERIC_FIELDS = {
    "pachy_thinnest_um": "Thinnest pachymetry (µm)",
    "central_pachy_um": "Pupil Center (+) pachymetry (µm; 4 Maps Refractive)",
    "BAD_D": "Final BAD-D",
    "PPI_avg": "PPI average",
    "K1_D": "K1 (D)", "K2_D": "K2 (D; not Kmax)", "Kmean_D": "Preoperative Kmean (D)",
    "corneal_diameter_mm": "HWTW (mm; 4 Maps Refractive lower-left labeled box)",
    "I_S": "Signed I-S (D; not ISV/IVA)",
    "posterior_Kmean_D": "Posterior Km (D; Cornea Back)",
    "F_Ele_Th_um": "F. Ele.Th (µm; BAD Display labeled box)",
    "B_Ele_Th_um": "B. Ele.Th (µm; BAD Display labeled box)",
}

assert set(COMPLETION_NUMERIC_FIELDS) == (
    set(DECISION_REQUIRED_FIELDS) | set(CONDITIONAL_REPORT_FIELDS)
)


def completion_label(field: str) -> str:
    return COMPLETION_NUMERIC_FIELDS[field]
