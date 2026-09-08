import pytest
from patient_age_policy import resolve_patient_age


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
