"""Canonical pre-assessment contact-lens readiness ownership locks."""

import canonical_readiness
from clinical_core.readiness import (
    RIGID_CONTACT_LENS_WASHOUT_DAYS,
    SOFT_CONTACT_LENS_WASHOUT_DAYS,
    contact_lens_washout,
)


def test_readiness_constants_have_one_clinical_owner():
    assert SOFT_CONTACT_LENS_WASHOUT_DAYS == 10
    assert RIGID_CONTACT_LENS_WASHOUT_DAYS == 21
    assert not hasattr(canonical_readiness, "SOFT_CONTACT_LENS_WASHOUT_DAYS")
    assert not hasattr(canonical_readiness, "RIGID_CONTACT_LENS_WASHOUT_DAYS")


def test_precore_readiness_uses_clinical_core_contact_lens_policy_cases():
    cases = [
        {"contact_lens_type": "NONE", "contact_lens_discontinuation_days": None},
        {"contact_lens_type": "UNKNOWN", "contact_lens_discontinuation_days": None},
        {"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": None},
        {"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 9},
        {"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 10},
        {"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 20},
        {"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 21},
        {"contact_lens_type": "RIGID", "contact_lens_discontinuation_days": 20.5},
    ]
    for modifiers in cases:
        result = canonical_readiness.evaluate_precore_readiness(
            age_years=30,
            eye_plans={"OD": {"prior": "no", "procedure": "LASIK"}},
            patient_modifiers=modifiers,
        )
        assert result["contact_lens_washout"] == contact_lens_washout(modifiers)


def test_importing_readiness_does_not_mutate_workflow_runtime():
    import assessment_workflow
    before = assessment_workflow._respond
    import clinical_core.readiness  # noqa: F401
    assert assessment_workflow._respond is before
