"""Single registry for Pentacam fields used by reread and surgeon completion.

Extraction schemas remain in their owning adapters, while canonical field names
and user-facing completion labels live here.  No clinical threshold or score is
defined in this module.
"""

TARGET_FIELDS = (
    "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmax_D",
    "corneal_diameter_mm", "pachy_thinnest_um", "central_pachy_um", "B_Ele_Th_um", "BAD_D", "Df", "Db",
    "Dp", "Dt", "Da", "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um",
    "ISV", "IVA", "KI", "CKI", "IHD", "I_S", "KISA", "IHA",
    "Rmin_mm", "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "Kmean_D",
    "total_RMS_um", "spherical_aberration_um",
)

# These values have one authoritative printed Pentacam box/row. They are not
# cross-image consensus fields and must never be reconstructed from a map or a
# neighboring value. The first valid same-eye labeled-box transcription is retained.
EXCLUSIVE_LABELED_BOX_FIELDS = frozenset({
    "Kmax_D",
    "ARTmax_um",
    "pachy_thinnest_um",
    "central_pachy_um",
    "B_Ele_Th_um",
})

COMPLETION_NUMERIC_FIELDS = {
    "pachy_thinnest_um": "Thinnest pachymetry (µm)",
    "BAD_D": "Final BAD-D",
    "Df": "BAD Df",
    "Db": "BAD Db",
    "Dp": "BAD Dp",
    "Dt": "BAD Dt",
    "Da": "BAD Da",
    "ARTmax_um": "ARTmax (µm)",
    "PPI_min": "PPI minimum",
    "PPI_avg": "PPI average",
    "PPI_max": "PPI maximum",
    "K1_D": "K1 (D)",
    "K2_D": "K2 (D; not Kmax)",
    "Kmean_D": "Preoperative Kmean (D)",
    "Kmax_D": "Kmax (D)",
    "srax_deg": "SRAX (degrees)",
    "inferior_opposite_steepening_D": "Inferior-opposite steepening (D)",
    "Rmin_mm": "Rmin (mm)",
    "I_S": "Signed I-S (D; not ISV/IVA)",
}


def completion_label(field: str) -> str:
    """Return the canonical surgeon-completion label for a supported field."""
    return COMPLETION_NUMERIC_FIELDS[field]
