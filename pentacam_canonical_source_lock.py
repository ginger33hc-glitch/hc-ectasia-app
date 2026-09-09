"""Single authoritative CER-AI Pentacam source registry.

Every locked clinical field is read directly from one defined Pentacam location.
Extraction, reread, provenance, reconciliation, readiness and reporting must query
this registry rather than maintain their own field/source lists.
"""

POLICY_VERSION = "2026-09-09-ML7-FOUR-MAPS"
NO_FALLBACK = True
NO_DERIVATION = True

SHOW2 = "SHOW_2_EXAMS_TOPOMETRIC"
FOURMAPS = "FOUR_MAPS_REFRACTIVE"
BAD = "BAD_DISPLAY"


def is_four_maps_eye(eye):
    """Recognize the Four Maps source family for extraction consumers."""
    for screen_type in eye.get("screen_types") or []:
        text = str(screen_type).upper().replace("_", " ")
        if "4 MAP" in text or "FOUR MAP" in text or "4MAP" in text:
            return True
    return False

SHOW_2_CORNEA_FRONT = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT"
SHOW_2_CORNEA_BACK = "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK"
SHOW_2_INDICES = "SHOW_2_EXAMS_TOPOMETRIC_CENTER_INDICES_8MM"
FOUR_MAPS_LOWER_LEFT = "FOUR_MAPS_REFRACTIVE_LOWER_LEFT_LABELED_BOX"
FOUR_MAPS_ANTERIOR_SAGITTAL = "FOUR_MAPS_REFRACTIVE_ANTERIOR_SAGITTAL_CURVATURE"
BAD_CENTER = "BELIN_AMBROSIO_CENTER_NUMERIC_BOX"
BAD_ELEVATION_ROW = "BELIN_AMBROSIO_LOWER_ELEVATION_LABEL_VALUE_ROW"
BAD_PPI = "BELIN_AMBROSIO_PROGRESSION_INDEX_BOX"
BAD_STRIP = "BELIN_AMBROSIO_BOTTOM_BAD_D_STRIP"

CANONICAL_SOURCE_REGIONS = {
    SHOW_2_CORNEA_FRONT: ("Show 2 Exams – Topometric", "Cornea Front"),
    SHOW_2_CORNEA_BACK: ("Show 2 Exams – Topometric", "Cornea Back"),
    SHOW_2_INDICES: ("Show 2 Exams – Topometric", "center — Indices (in 8 mm zone)"),
    FOUR_MAPS_LOWER_LEFT: ("4 Maps Refractive", "lower-left labeled numerical box"),
    FOUR_MAPS_ANTERIOR_SAGITTAL: (
        "4 Maps Refractive",
        "Anterior Sagittal Curvature (Front) — labeled K1/K2 values",
    ),
    BAD_CENTER: ("Belin/Ambrósio Display", "central numeric box"),
    BAD_ELEVATION_ROW: (
        "Belin/Ambrósio Display",
        "central results table — elevation label/value row immediately above Progression Index",
    ),
    BAD_PPI: ("Belin/Ambrósio Display", "Progression Index section"),
    BAD_STRIP: ("Belin/Ambrósio Display", "bottom BAD-D strip"),
}

CANONICAL_FIELD_SOURCES = {
    # Show 2 Exams -> Cornea Front.
    "K1_D": (SHOW_2_CORNEA_FRONT, "K1"),
    "K1_axis_deg": (SHOW_2_CORNEA_FRONT, "K1 axis"),
    "K2_D": (SHOW_2_CORNEA_FRONT, "K2"),
    "K2_axis_deg": (SHOW_2_CORNEA_FRONT, "K2 axis"),
    "Kmean_D": (SHOW_2_CORNEA_FRONT, "Km"),
    "topographic_astig_D": (SHOW_2_CORNEA_FRONT, "Astig"),
    "topographic_steep_axis_deg": (SHOW_2_CORNEA_FRONT, "Astig/steep axis"),

    "ml7_k1_d": (FOUR_MAPS_ANTERIOR_SAGITTAL, "K1 (ML7 planning only)"),
    "ml7_k2_d": (FOUR_MAPS_ANTERIOR_SAGITTAL, "K2 (ML7 planning only)"),

    # PS3 prescription-axis comparison only; independent of steep-axis and SRAX sources.
    "bad_flat_axis_deg": (BAD_CENTER, "Axis (upper middle, beside K1; flat meridian)"),

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

    # Belin/Ambrosio BAD -> elevation row immediately above Progression Index.
    "F_Ele_Th_um": (BAD_ELEVATION_ROW, "F.Ele.Th — adjacent signed µm value"),
    "B_Ele_Th_um": (BAD_ELEVATION_ROW, "B.Ele.Th — adjacent signed µm value"),

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


def canonical_source_region(field: str):
    """Return the registry-owned user-facing screen and exact source box."""
    source = canonical_source_id(field)
    region = CANONICAL_SOURCE_REGIONS.get(source)
    if region is None:
        return None
    screen, box = region
    label = canonical_label(field)
    return {"screen": screen, "box": f"{box} → {label}" if label else box}


def source_family(field: str):
    source = canonical_source_id(field)
    if source in {SHOW_2_CORNEA_FRONT, SHOW_2_CORNEA_BACK, SHOW_2_INDICES}:
        return SHOW2
    if source in {FOUR_MAPS_LOWER_LEFT, FOUR_MAPS_ANTERIOR_SAGITTAL}:
        return FOURMAPS
    if source in {BAD_CENTER, BAD_ELEVATION_ROW, BAD_PPI, BAD_STRIP}:
        return BAD
    return None


def source_is_allowed(field: str, source: str) -> bool:
    required = canonical_source_id(field)
    return required is None or source == required


def derivation_is_allowed(field: str) -> bool:
    """Locked fields are display-read only; derivation/reverse calculation is forbidden."""
    return field not in LOCKED_FIELDS
