from types import SimpleNamespace

import rmin_front_source_policy as policy


def core():
    return SimpleNamespace(
        is_number=lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        MAP_FALLBACK_NUMERIC_FIELDS=("Rmin_mm", "posterior_elevation_thinnest_um"),
        PROMPT="BASE",
    )


def source_result(screen_type, rmin=6.34):
    return {
        "document_context": {"document_type": "PENTACAM_TOPOGRAPHY"},
        "eyes": [{
            "eye": "OS",
            "screen_types": [screen_type],
            "Rmin_mm": rmin,
            "table_verified_numeric_fields": ["Rmin_mm"],
            "map_fallback_numeric_fields": ["Rmin_mm"],
            "field_provenance": {"Rmin_mm": [{"source": "OLD"}]},
        }],
    }


def test_non_four_maps_rmin_is_cleared_and_never_reused():
    c = core()
    targeted = SimpleNamespace(targeted_reread=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    wrapped = policy.make_extractor(c, lambda raw, filename: source_result("SHOW_2_EXAMS_TOPOMETRIC"), targeted)
    result = wrapped(b"x", "show2.png")
    eye = result["eyes"][0]
    assert eye["Rmin_mm"] is None
    assert "Rmin_mm" not in eye["table_verified_numeric_fields"]
    assert "Rmin_mm" not in eye["map_fallback_numeric_fields"]


def test_four_maps_accepts_only_cornea_front_rmin():
    c = core()
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [
            {"eye": "OS", "field": "Rmin_mm", "value": 6.81, "status": "CONFIDENT",
             "printed_label": "Rmin:", "group_label": "Cornea Front", "source_tile": "UPPER_LEFT"},
            {"eye": "OS", "field": "Rmin_mm", "value": 6.34, "status": "CONFIDENT",
             "printed_label": "Rmin:", "group_label": "Cornea Back", "source_tile": "UPPER_LEFT"},
        ],
    }
    targeted = SimpleNamespace(targeted_reread=lambda *args, **kwargs: reread)
    wrapped = policy.make_extractor(c, lambda raw, filename: source_result("FOUR_MAPS_REFRACTIVE"), targeted)
    result = wrapped(b"x", "fourmaps.png")
    eye = result["eyes"][0]
    assert eye["Rmin_mm"] == 6.81
    assert eye["field_provenance"]["Rmin_mm"][0]["source"] == "FOUR_MAPS_REFRACTIVE_CORNEA_FRONT"


def test_cornea_back_only_rmin_is_rejected():
    c = core()
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [
            {"eye": "OS", "field": "Rmin_mm", "value": 6.34, "status": "CONFIDENT",
             "printed_label": "Rmin:", "group_label": "Cornea Back", "source_tile": "UPPER_LEFT"},
        ],
    }
    targeted = SimpleNamespace(targeted_reread=lambda *args, **kwargs: reread)
    wrapped = policy.make_extractor(c, lambda raw, filename: source_result("FOUR_MAPS_REFRACTIVE"), targeted)
    result = wrapped(b"x", "fourmaps.png")
    assert result["eyes"][0]["Rmin_mm"] is None


def test_install_removes_rmin_map_fallback_and_appends_source_lock():
    c = core()
    c.extract_one_image = lambda raw, filename: source_result("OTHER_PENTACAM")
    targeted = SimpleNamespace(targeted_reread=lambda *args, **kwargs: {})
    policy._previous_extract_one_image = None
    policy.extract_one_image_with_front_rmin = None
    policy.install(c, targeted)
    assert "Rmin_mm" not in c.MAP_FALLBACK_NUMERIC_FIELDS
    assert "CER-AI RMIN SOURCE LOCK" in c.PROMPT
    assert c._cerai_rmin_front_source_installed is True
