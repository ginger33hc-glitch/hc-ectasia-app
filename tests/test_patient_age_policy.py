import pytest
from patient_age_policy import apply_surgeon_age_precedence, resolve_patient_age


def source(birth, exam, printed=None, screen="FOUR_MAPS_REFRACTIVE"):
    return {"document_context": {"document_type": "PENTACAM_TOPOGRAPHY",
            "patient_date_of_birth": birth, "exam_date": exam, "patient_age_years": printed},
            "eyes": [{"eye": "OD", "screen_types": [screen]}]}


@pytest.mark.parametrize("exam, expected", [("2026-03-14", 20), ("2026-03-15", 21), ("2026-03-16", 21)])
def test_completed_years_at_exam_birthday_boundary(exam, expected):
    assert resolve_patient_age([source("2005-03-15", exam)])["age_years"] == expected


def test_ambiguous_date_allowed_only_if_age_is_unambiguous():
    assert resolve_patient_age([source("03/07/2002", "20/08/2026")])["age_years"] == 24
    assert resolve_patient_age([source("03/07/2002", "2026-05-01")])["age_years"] is None


@pytest.mark.parametrize("sources", [
    [source("2005-03-15", "2026-08-20", 22)],
    [source("2005-03-15", "2026-08-20"), source("2005-03-16", "2026-08-20")],
    [source("2005-02-30", "2026-08-20")],
    [source("2027-03-15", "2026-08-20")],
    [source("2005-03-15", None)],
    [source("2005-03-15", "2026-08-20", screen="BAD")],
])
def test_unresolved_dates_do_not_supply_age(sources):
    assert resolve_patient_age(sources)["age_years"] is None


def test_merge_exposes_calculated_age_and_retains_raw_dates():
    from app import merge_extractions
    result = merge_extractions([source("2005-03-15", "2026-08-20")])
    assert result["derived_age_years"] == 21
    assert result["patient_age_resolution"]["source"] == "DOB_AT_EXAM"
    assert result["document_contexts"][0]["patient_date_of_birth"] == "2005-03-15"


def test_surgeon_entered_age_overrides_derived_conflict_without_erasing_source_audit():
    warning = "Printed and/or calculated patient ages conflict; enter surgeon-confirmed age."
    extracted = {
        "patient_age_resolution": {
            "age_years": None, "candidate_ages": [31, 32], "warning": warning,
            "source": "DOB_AT_EXAM", "date_evidence": [{"file": "od.png"}],
        },
        "patient_age_conflict_values": [31, 32],
        "global_warnings": [warning, "another warning"],
    }
    resolved = apply_surgeon_age_precedence(extracted, 33)
    assert resolved["resolved_age_years"] == 33
    assert resolved["surgeon_confirmed_age_years"] == 33
    assert resolved["age_source"] == "SURGEON_CONFIRMED"
    assert "patient_age_conflict_values" not in resolved
    assert resolved["global_warnings"] == ["another warning"]
    assert resolved["patient_age_resolution"]["candidate_ages"] == [31, 32]
    assert "patient_age_conflict_values" in extracted
