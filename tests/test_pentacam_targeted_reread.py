"""Current targeted-reread regression surface after the 2026-09-04 Pentacam source lock.

The historical module is preserved unchanged for traceability. Two tests that treated a generic
PACHYMETRY screen as an accepted source for pupil-center/thinnest pachymetry are superseded by the
owner-defined FOUR MAPS REFRACTIVE lower-left labeled-box rule and are replaced below.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Compose the canonical runtime before loading the historical targeted-reread tests so the test
# surface exercises the same source enforcement used in production.
import canonical_engine  # noqa: F401

_LEGACY_PATH = Path(__file__).with_name("legacy_pentacam_targeted_reread_tests.py")
_SPEC = importlib.util.spec_from_file_location("cerai_legacy_pentacam_targeted_reread_tests", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load historical Pentacam targeted-reread regression module")
_legacy = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _legacy
_SPEC.loader.exec_module(_legacy)

_RETIRED = {
    "test_pupil_center_reread_feeds_nice_and_unreadable_region_reaches_form",
    "test_circle_marked_thinnest_location_is_retained_as_labeled_row",
}
for _name in _RETIRED:
    if not hasattr(_legacy, _name):
        raise RuntimeError(f"Retired targeted-reread test missing: {_name}")
    delattr(_legacy, _name)

for _name, _value in vars(_legacy).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

# Explicit bindings keep static analysis deterministic while the historical test surface is
# re-exported dynamically above.
pentacam_result = _legacy.pentacam_result
reading = _legacy.reading
targeted = _legacy.targeted
Core = _legacy.Core
assessment_workflow = _legacy.assessment_workflow


def test_pupil_center_reread_uses_four_maps_lower_left_source_and_feeds_nice():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    requested = {"OD": ["central_pachy_um"]}
    confident = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "central_pachy_um", 548, "Pupil Center +", tile="LOWER_LEFT",
            source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, result, confident, requested, "od.png")
    assert result["nice_readings"][-1]["central_pachy_um"] == 548
    assert result["nice_readings"][-1]["central_status"] == "CONFIDENT"
    assert result["nice_readings"][-1]["central_landmark"] == "PUPIL_CENTER_PLUS"
    assert result["eyes"][0]["central_pachy_um"] is None

    unreadable = pentacam_result()
    unreadable["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "central_pachy_um", None, "Pupil Center +", status="UNREADABLE",
            tile="LOWER_LEFT", source_box=[100, 200, 650, 480],
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(Core, unreadable, reread, requested, "od.png")
    item = assessment_workflow._request("OD", "NICE: central_pachy_um", unreadable)
    assert item["source_region"] is True
    assert item["form_id"] == "od_nice_central"


def test_circle_marked_thinnest_location_is_retained_only_from_four_maps_lower_left():
    result = pentacam_result()
    result["eyes"][0]["screen_types"] = ["FOUR_MAPS_REFRACTIVE"]
    reread = {
        "screen_family": "FOUR_MAPS_REFRACTIVE",
        "readings": [reading(
            "pachy_thinnest_um", 501, "Thinnest Locat.", tile="LOWER_LEFT",
        )],
        "warnings": [],
    }
    targeted.apply_targeted_readings(
        Core, result, reread, {"OD": ["pachy_thinnest_um"]}, "od.png"
    )
    eye = result["eyes"][0]
    assert eye["pachy_thinnest_um"] == 501
    assert "pachy_thinnest_um" in eye["table_verified_numeric_fields"]
    assert "pachy_thinnest_um" not in eye.get("map_fallback_numeric_fields", [])


PENTACAM_SOURCE_LOCK_RETIRED_TARGETED_TESTS = tuple(sorted(_RETIRED))
del _name, _value
