from types import SimpleNamespace

import microkeratome_report_policy as policy


def fake_reports():
    def original_rows(eye, locale="en"):
        return [("Assessment gate", "PASS"), ("Vacuum ring", "8.5 mm")]

    return SimpleNamespace(
        _microkeratome_rows=original_rows,
        translate_text=lambda value, locale: value,
    )


def planning():
    return {
        "applicable": True,
        "assessment_gate": "PASS",
        "vacuum_ring_mm": 8.5,
        "warnings": ["stale planning warning"],
        "notes": ["stale planning note"],
        "source": "MED-LOGICS ML7 Rev. 22 active Turkish reference + CER-AI hinge amendment",
    }


def eye(status="PASS", procedure="LASIK"):
    return {
        "status": status,
        "values": {"procedure": procedure},
        "microkeratome_planning": planning(),
    }


def test_final_stop_defer_replaces_intermediate_ml7_pass_with_not_applicable():
    reports = fake_reports()
    policy.install(reports)
    result_eye = eye(status="STOP-DEFER")

    rows = reports._microkeratome_rows(result_eye)

    assert rows[0] == ("Assessment gate", "NOT APPLICABLE — LASIK not eligible by CER-AI")
    assert all(value == "Not applicable" for _, value in rows[1:-1])
    assert result_eye["microkeratome_planning"]["warnings"] == []
    assert result_eye["microkeratome_planning"]["notes"] == []


def test_final_pass_lasik_preserves_original_ml7_rows():
    reports = fake_reports()
    policy.install(reports)

    assert reports._microkeratome_rows(eye(status="PASS")) == [
        ("Assessment gate", "PASS"),
        ("Vacuum ring", "8.5 mm"),
    ]


def test_final_caution_lasik_preserves_original_ml7_rows():
    reports = fake_reports()
    policy.install(reports)

    assert reports._microkeratome_rows(eye(status="CAUTION"))[0] == ("Assessment gate", "PASS")


def test_non_lasik_final_procedure_cannot_show_ml7_pass():
    reports = fake_reports()
    policy.install(reports)

    rows = reports._microkeratome_rows(eye(status="PASS", procedure="PRK"))
    assert rows[0][1] == "NOT APPLICABLE — LASIK not eligible by CER-AI"


def test_no_stored_ml7_record_does_not_create_report_section():
    reports = fake_reports()
    policy.install(reports)

    assert reports._microkeratome_rows({"status": "STOP-DEFER", "values": {"procedure": "LASIK"}}) == []
