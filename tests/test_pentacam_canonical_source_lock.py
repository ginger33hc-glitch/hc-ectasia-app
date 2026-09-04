from pentacam_canonical_source_lock import CANONICAL_FIELD_SOURCES, derivation_is_allowed
from pentacam_canonical_source_enforcement import (
    BAD, FOURMAPS, SHOW2, _required_family, _strip_noncanonical,
)


def eye(screen, **values):
    base = {
        "eye": "OD", "screen_types": [screen],
        "table_verified_numeric_fields": list(values),
        "map_fallback_numeric_fields": [], "missing_or_unreadable": [],
    }
    base.update(values)
    return base


def payload(screen, **values):
    return {
        "document_context": {"document_type": "PENTACAM_TOPOGRAPHY"},
        "eyes": [eye(screen, **values)],
    }


def test_all_owner_locked_fields_forbid_derivation():
    assert CANONICAL_FIELD_SOURCES
    assert all(not derivation_is_allowed(field) for field in CANONICAL_FIELD_SOURCES)


def test_show2_indices_are_show2_only():
    for field in ("ISV", "IVA", "KI", "CKI", "IHA", "IHD", "TKC", "KISA", "I_S", "topometric_RMin"):
        assert _required_family(field) == SHOW2


def test_four_maps_lower_left_fields_are_four_maps_only():
    for field in ("central_pachy_um", "pachy_thinnest_um", "Kmax_D", "corneal_diameter_mm"):
        assert _required_family(field) == FOURMAPS


def test_bad_fields_are_bad_display_only():
    for field in ("F_Ele_Th_um", "B_Ele_Th_um", "PPI_min", "PPI_avg", "PPI_max", "ARTmax_um", "Df", "Db", "Dp", "Dt", "Da", "BAD_D"):
        assert _required_family(field) == BAD


def test_wrong_screen_locked_value_is_deleted_not_reconciled():
    result = payload("BAD_DISPLAY", Kmax_D=49.7, I_S=1.2)
    cleaned = _strip_noncanonical(result)
    od = cleaned["eyes"][0]
    assert od["Kmax_D"] is None
    assert od["I_S"] is None
    assert "Kmax_D" in od["missing_or_unreadable"]
    assert "I_S" in od["missing_or_unreadable"]


def test_rmin_map_fallback_is_cancelled():
    result = payload("SHOW_2_EXAMS_TOPOMETRIC", Rmin_mm=5.33)
    result["eyes"][0]["map_fallback_numeric_fields"] = ["Rmin_mm"]
    cleaned = _strip_noncanonical(result)
    assert "Rmin_mm" not in cleaned["eyes"][0]["map_fallback_numeric_fields"]


def test_canonical_screen_keeps_direct_value():
    result = payload("SHOW_2_EXAMS_TOPOMETRIC", I_S=-0.18, ISV=34)
    cleaned = _strip_noncanonical(result)
    assert cleaned["eyes"][0]["I_S"] == -0.18
    assert cleaned["eyes"][0]["ISV"] == 34
