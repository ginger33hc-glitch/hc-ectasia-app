"""Phase 2 equivalence for pre-assessment contact-lens readiness."""

import assessment_workflow
from clinical_core.readiness import (
    RIGID_CONTACT_LENS_WASHOUT_DAYS,
    SOFT_CONTACT_LENS_WASHOUT_DAYS,
    contact_lens_washout,
)


def test_readiness_constants_match_server_workflow():
    assert SOFT_CONTACT_LENS_WASHOUT_DAYS == assessment_workflow.SOFT_CONTACT_LENS_WASHOUT_DAYS == 10
    assert RIGID_CONTACT_LENS_WASHOUT_DAYS == assessment_workflow.RIGID_CONTACT_LENS_WASHOUT_DAYS == 21


def test_contact_lens_gate_matches_server_workflow_cases():
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
        assert contact_lens_washout(modifiers) == assessment_workflow._contact_lens_washout(modifiers)


def test_readiness_import_does_not_mutate_runtime():
    before = assessment_workflow._contact_lens_washout
    import clinical_core.readiness  # noqa: F401
    assert assessment_workflow._contact_lens_washout is before
