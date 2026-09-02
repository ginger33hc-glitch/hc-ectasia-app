"""Single registry for Pentacam fields used by reread and surgeon completion.

Extraction schemas remain in their owning adapters, while canonical field names
and user-facing completion labels live here.  No clinical threshold or score is
defined in this module.
"""

TARGET_FIELDS = (
    "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmax_D",
    "topographic_astig_D", "topographic_steep_axis_deg", "posterior_Kmean_D",
    "corneal_diameter_mm", "pachy_thinnest_um", "central_pachy_um", "F_Ele_Th_um", "B_Ele_Th_um", "BAD_D", "Df", "Db",
    "Dp", "Dt", "Da", "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um",
    "ISV", "IVA", "KI", "CKI", "IHD", "I_S", "KISA", "IHA",
    "Rmin_mm", "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "Kmean_D",
    "total_RMS_um", "spherical_aberration_um",
)

# Legacy K1/K2/Km source contract remains unchanged.
CORNEA_FRONT_KERATOMETRY_SOURCE = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
CORNEA_FRONT_KERATOMETRY_FIELDS = frozenset({
    "K1_D",
    "K1_axis_deg",
    "K2_D",
    "K2_axis_deg",
    "Kmean_D",
})
KERATOMETRY_SOURCE_VALUES = (
    CORNEA_FRONT_KERATOMETRY_SOURCE,
    "OTHER_PENTACAM_SOURCE",
    "UNREADABLE",
    "NOT_SHOWN",
)

# PS3-specific source groups are descriptive only. They must not change the
# established keratometry-source gate above.
PS3_CORNEA_FRONT_FIELDS = frozenset({"topographic_astig_D", "topographic_steep_axis_deg"})
PS3_CORNEA_BACK_FIELDS = frozenset({"posterior_Kmean_D"})
PS3_TOPOGRAPHIC_INDEX_FIELDS = frozenset({"I_S", "KISA"})
PS3_BAD_THINNEST_FIELDS = frozenset({"F_Ele_Th_um", "B_Ele_Th_um"})
PS3_BAD_PROGRESSION_FIELDS = frozenset({"PPI_avg", "ARTmax_um"})

# Preserve reconciliation semantics for all established fields. Only newly
# introduced PS3 fields with a single authoritative printed source are added.
EXCLUSIVE_LABELED_BOX_FIELDS = frozenset({
    *CORNEA_FRONT_KERATOMETRY_FIELDS,
    "Kmax_D",
    "ARTmax_um",
    "pachy_thinnest_um",
    "central_pachy_um",
    "B_Ele_Th_um",
    "topographic_astig_D",
    "topographic_steep_axis_deg",
    "posterior_Kmean_D",
    "F_Ele_Th_um",
})

COMPLETION_NUMERIC_FIELDS = {
    "pachy_thinnest_um": "Thinnest pachymetry (µm)",
    "BAD_D": "Final BAD-D",
    "Df": "BAD Df",
    "Db": "BAD Db",
    "Dp": "BAD Dp",
    "Dt": "BAD Dt",
    "Da": "BAD Da",
    "F_Ele_Th_um": "F. Ele.Th (µm; BAD Display labeled box)",
    "B_Ele_Th_um": "B. Ele.Th (µm; BAD Display labeled box)",
    "ARTmax_um": "ARTmax (µm)",
    "PPI_min": "PPI minimum",
    "PPI_avg": "PPI average",
    "PPI_max": "PPI maximum",
    "K1_D": "K1 (D)",
    "K2_D": "K2 (D; not Kmax)",
    "Kmean_D": "Anterior Kmean/Km (D; Cornea Front)",
    "posterior_Kmean_D": "Posterior Kmean/Km (D; Cornea Back)",
    "topographic_astig_D": "Topographic Astig. (D; Cornea Front)",
    "topographic_steep_axis_deg": "Topographic Axis (steep) (degrees; Cornea Front)",
    "Kmax_D": "Kmax (D)",
    "KISA": "KISA (%)",
    "srax_deg": "SRAX (degrees)",
    "inferior_opposite_steepening_D": "Inferior-opposite steepening (D)",
    "Rmin_mm": "Rmin (mm)",
    "I_S": "Signed I-S (D; not ISV/IVA)",
}


def completion_label(field: str) -> str:
    """Return the canonical surgeon-completion label for a supported field."""
    return COMPLETION_NUMERIC_FIELDS[field]
