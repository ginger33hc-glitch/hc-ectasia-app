"""Canonical contact-lens washout boundary locks."""

from canonical_readiness import evaluate_precore_readiness


def _evaluate(modifiers):
    return evaluate_precore_readiness(
        age_years=30,
        eye_plans={"OD": {"prior": "no", "procedure": "LASIK"}},
        patient_modifiers=modifiers,
    )


def test_soft_lens_nine_days_blocks_before_clinical_core():
    result = _evaluate({"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 9})
    assert result["ready"] is False
    assert result["contact_lens_washout"]["required_days"] == 10
    assert result["contact_lens_washout"]["remaining_days"] == 1


def test_soft_lens_ten_full_days_clears_washout_gate():
    result = _evaluate({"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 10})
    assert result["contact_lens_washout"] is None
    assert result["ready"] is True


def test_rigid_lens_twenty_days_blocks_before_clinical_core():
    result = _evaluate({"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 20})
    assert result["ready"] is False
    assert result["contact_lens_washout"]["required_days"] == 21
    assert result["contact_lens_washout"]["remaining_days"] == 1


def test_rigid_lens_twenty_one_full_days_clears_washout_gate():
    result = _evaluate({"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 21})
    assert result["contact_lens_washout"] is None
    assert result["ready"] is True


def test_contact_lens_days_must_be_documented_when_lens_is_used():
    result = _evaluate({"contact_lens_type": "SOFT"})
    assert result["ready"] is False
    assert result["contact_lens_washout"]["form_id"] == "contact_lens_days"


def test_none_lens_type_needs_no_days():
    result = _evaluate({"contact_lens_type": "NONE"})
    assert result["contact_lens_washout"] is None
    assert result["ready"] is True
