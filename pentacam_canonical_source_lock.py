"""Single authoritative CER-AI Pentacam source registry.

Every locked clinical field is read directly from one defined Pentacam location.
Extraction, reread, provenance, reconciliation, readiness and reporting must query
this registry rather than maintain their own field/source lists.
"""

POLICY_VERSION = "2026-09-07"
NO_FALLBACK = True
NO_DERIVATION = True

SHOW2 = "SHOW_2_EXAMS_TOPOMETRIC"
FOURMAPS = "FOUR_MAPS_REFRACTIVE"
BAD = "BAD_DISPLAY"

SHOW_2_CORNEA_FRONT = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
SHOW_2_CORNEA_BACK = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK"
SHOW_2_INDICES = "SHOW_2_EXAMS_TOPOMETRIC_CENTER_INDICES_8MM"
FOUR_MAPS_LOWER_LEFT = "FOUR_MAPS_REFRACTIVE_LOWER_LEFT_LABELED_BOX"
BAD_CENTER = "BELIN_AMBROSIO_CENTER_NUMERIC_BOX"
BAD_PPI = "BELIN_AMBROSIO_PROGRESSION_INDEX_BOX"
BAD_STRIP = "BELIN_AMBROSIO_BOTTOM_BAD_D_STRIP"

CANONICAL_FIELD_SOURCES = {
    # Show 2 Exams -> Cornea Front.
    "K1_D": (SHOW_2_CORNEA_FRONT, "K1"),
    "K1_axis_deg": (SHOW_2_CORNEA_FRONT, "K1 axis"),
    "K2_D": (SHOW_2_CORNEA_FRONT, "K2"),
    "K2_axis_deg": (SHOW_2_CORNEA_FRONT, "K2 axis"),
    "Kmean_D": (SHOW_2_CORNEA_FRONT, "Km"),
    "topographic_astig_D": (SHOW_2_CORNEA_FRONT, "Astig"),
    "topographic_steep_axis_deg": (SHOW_2_CORNEA_FRONT, "Astig/steep axis"),

    # Show 2 Exams -> Cornea Back.
    "Rmin_mm": (SHOW_2_CORNEA_BACK, "Rmin"),
    "posterior_Kmean_D": (SHOW_2_CORNEA_BACK, "Km"),

    # Show 2 Exams center -> Indices (in 8 mm zone).
    "ISV": (SHOW_2_INDICES, "ISV"),
    "IVA": (SHOW_2_INDICES, "IVA"),
    "KI": (SHOW_2_INDICES, "KI"),
    "CKI": (SHOW_2_INDICES, "CKI"),
    "IHA": (SHOW_2_INDICES, "IHA"),
    "IHD": (SHOW_2_INDICES, "IHD"),
    "topometric_RMin": (SHOW_2_INDICES, "RMin"),
    "TKC": (SHOW_2_INDICES, "TKC"),
    "KISA": (SHOW_2_INDICES, "KISA"),
    "I_S": (SHOW_2_INDICES, "I-S"),

    # 4 Maps Refractive -> lower-left labeled numerical box.
    "central_pachy_um": (FOUR_MAPS_LOWER_LEFT, "Pupil Center (+) pachymetry"),
    "pachy_thinnest_um": (FOUR_MAPS_LOWER_LEFT, "Thinnest Location (circle) pachymetry"),
    "Kmax_D": (FOUR_MAPS_LOWER_LEFT, "K Max (Front)"),
    "corneal_diameter_mm": (FOUR_MAPS_LOWER_LEFT, "HWTW"),

    # Belin/Ambrosio BAD -> central labeled box.
    "F_Ele_Th_um": (BAD_CENTER, "F.Ele.Th"),
    "B_Ele_Th_um": (BAD_CENTER, "B.Ele.Th"),

    # Belin/Ambrosio BAD -> Progression Index box.
    "PPI_min": (BAD_PPI, "Min"),
    "PPI_avg": (BAD_PPI, "Avg"),
    "PPI_max": (BAD_PPI, "Max"),
    "ARTmax_um": (BAD_PPI, "ARTmax"),

    # Belin/Ambrosio BAD -> bottom D strip.
    "Df": (BAD_STRIP, "Df"),
    "Db": (BAD_STRIP, "Db"),
    "Dp": (BAD_STRIP, "Dp"),
    "Dt": (BAD_STRIP, "Dt"),
    "Da": (BAD_STRIP, "Da"),
    "BAD_D": (BAD_STRIP, "D"),
}

LOCKED_FIELDS = frozenset(CANONICAL_FIELD_SOURCES)


def canonical_source(field: str):
    return CANONICAL_FIELD_SOURCES.get(field)


def canonical_source_id(field: str):
    spec = canonical_source(field)
    return spec[0] if spec else None


def canonical_label(field: str):
    spec = canonical_source(field)
    return spec[1] if spec else None


def source_family(field: str):
    source = canonical_source_id(field)
    if source in {SHOW_2_CORNEA_FRONT, SHOW_2_CORNEA_BACK, SHOW_2_INDICES}:
        return SHOW2
    if source == FOUR_MAPS_LOWER_LEFT:
        return FOURMAPS
    if source in {BAD_CENTER, BAD_PPI, BAD_STRIP}:
        return BAD
    return None


def source_is_allowed(field: str, source: str) -> bool:
    required = canonical_source_id(field)
    return required is None or source == required


def derivation_is_allowed(field: str) -> bool:
    """Locked fields are display-read only; derivation/reverse calculation is forbidden."""
    return field not in LOCKED_FIELDS
