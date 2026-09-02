from types import SimpleNamespace

import ps3_extraction_policy
import ps3_runtime_policy


def _combine(current, new):
    rank = {"PASS": 0, "CAUTION": 1, "DATA INSUFFICIENT": 2, "STOP-DEFER": 3}
    return new if rank.get(new, 0) > rank.get(current, 0) else current


def _eye(name="OD", km=47.0, ppi=1.1):
    return {
        "eye": name,
        "Kmean_D": km,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "pachy_thinnest_um": 520 if name == "OD" else 525,
        "topographic_astig_D": 1.0,
        "topographic_steep_axis_deg": 0.0,
        "Kmax_D": 47.0,
        "I_S": 0.4,
        "KISA": 5.0,
        "PPI_avg": ppi,
        "F_Ele_Th_um": 2.0 if name == "OD" else 3.0,
        "B_Ele_Th_um": 5.0 if name == "OD" else 8.0,
    }


def _plan(procedure="PRK"):
    return {
        "prior": "no",
        "procedure": procedure,
        "manifest_cylinder_magnitude_D": 1.0,
        "entered_axis_deg": 0.0,
    }


def _base_engine(extracted, age, eye_plans, modifiers, metadata=None):
    return {
        "status": "PASS",
        "eyes": [
            {
                "eye": eye["eye"],
                "status": "PASS",
                "hard_stops": [],
                "reasons": [],
                "warnings": [],
                "action": "Proceed",
            }
            for eye in extracted["eyes"]
        ],
    }


def test_extraction_install_adds_only_ps3_transcription_fields_and_is_idempotent():
    eye_schema = {
        "properties": {
            "table_verified_numeric_fields": {"items": {"enum": ["Kmax_D"]}},
        },
        "required": ["eye"],
    }
    core = SimpleNamespace(
        SCHEMA={"properties": {"eyes": {"items": eye_schema}}},
        TABLE_NUMERIC_FIELDS=("Kmax_D",),
        PROMPT="base",
    )
    original_table_fields = core.TABLE_NUMERIC_FIELDS
    ps3_extraction_policy.install(core)
    ps3_extraction_policy.install(core)

    for field in ("topographic_astig_D", "topographic_steep_axis_deg", "posterior_Kmean_D", "F_Ele_Th_um"):
        assert field in eye_schema["properties"]
        assert eye_schema["required"].count(field) == 1
        assert eye_schema["properties"]["table_verified_numeric_fields"]["items"]["enum"].count(field) == 1
    assert core.TABLE_NUMERIC_FIELDS == original_table_fields
    assert core.PROMPT.count("PS3 ADDITIONAL LABELED-BOX READINGS") == 1
    for canonical in ("Kmax_D", "I_S", "KISA", "pachy_thinnest_um", "B_Ele_Th_um", "PPI_avg", "ARTmax_um"):
        assert f"- {canonical}:" not in core.PROMPT
    assert "Read ONLY the four new fields" in core.PROMPT


def test_ps3_runtime_keeps_single_moderate_prk_allowed_without_rewriting_upstream_scores():
    core = SimpleNamespace(hc_engine=_base_engine, combine_status=_combine)
    ps3_runtime_policy.install(core)
    extracted = {"eyes": [_eye("OD", km=48.0), _eye("OS")]}
    decision = core.hc_engine(extracted, 35, {"OD": _plan("PRK"), "OS": _plan("PRK")}, {})

    od = decision["eyes"][0]
    assert od["ps3"]["moderate_count"] == 1
    assert od["ps3"]["high_count"] == 0
    assert od["ps3"]["disposition"]["prk"] == "ALLOWED"
    assert od["ps3"]["disposition"]["lasik"] == "DEFER"
    assert od["status"] == "PASS"
    assert od["hard_stops"] == []
    assert any(reason.startswith("PS3:") for reason in od["reasons"])
    assert len([warning for warning in od["warnings"] if warning.startswith("PS3 surgeon review required:")]) == 3


def test_ps3_runtime_single_moderate_defers_lasik_only():
    core = SimpleNamespace(hc_engine=_base_engine, combine_status=_combine)
    ps3_runtime_policy.install(core)
    extracted = {"eyes": [_eye("OD", km=48.0), _eye("OS")]}
    decision = core.hc_engine(extracted, 35, {"OD": _plan("LASIK"), "OS": _plan("PRK")}, {})

    od = decision["eyes"][0]
    assert od["status"] == "STOP-DEFER"
    assert any("PS3 DEFER for selected LASIK" in reason for reason in od["hard_stops"])
    assert decision["status"] == "STOP-DEFER"


def test_two_moderates_defer_selected_prk():
    core = SimpleNamespace(hc_engine=_base_engine, combine_status=_combine)
    ps3_runtime_policy.install(core)
    extracted = {"eyes": [_eye("OD", km=48.0, ppi=1.21), _eye("OS")]}
    decision = core.hc_engine(extracted, 35, {"OD": _plan("PRK"), "OS": _plan("PRK")}, {})
    assert decision["eyes"][0]["status"] == "STOP-DEFER"


def test_f_ele_th_and_b_ele_th_are_not_reused_as_main_ps3_elevation_thresholds():
    core = SimpleNamespace(hc_engine=_base_engine, combine_status=_combine)
    ps3_runtime_policy.install(core)
    od = _eye("OD")
    os = _eye("OS")
    od["F_Ele_Th_um"] = 50
    od["B_Ele_Th_um"] = 50
    os["F_Ele_Th_um"] = 50
    os["B_Ele_Th_um"] = 50
    decision = core.hc_engine({"eyes": [od, os]}, 35, {"OD": _plan(), "OS": _plan()}, {})
    elevation = next(f for f in decision["eyes"][0]["ps3"]["findings"] if f["key"] == "elevation")
    assert elevation["status"] == "NOT_EVALUATED"


def test_runtime_marks_three_unread_morphology_domains_for_surgeon_review():
    core = SimpleNamespace(hc_engine=_base_engine, combine_status=_combine)
    ps3_runtime_policy.install(core)
    decision = core.hc_engine(
        {"eyes": [_eye("OD"), _eye("OS")]},
        35,
        {"OD": _plan(), "OS": _plan()},
        {},
    )
    notes = decision["eyes"][0]["ps3"]["review_notes"]
    assert len(notes) == 3
    assert all("surgeon review required" in note.lower() for note in notes)
