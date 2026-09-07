import inspect

from canonical_readiness import POST_REFRACTIVE, VIRGIN, evaluate_precore_readiness


def _plan(**overrides):
    values = {"prior": "no", "procedure": "LASIK"}
    values.update(overrides)
    return values


def test_reassuring_precore_readiness_allows_virgin_case():
    result = evaluate_precore_readiness(
        age_years=35,
        eye_plans={"OD": _plan(), "OS": _plan(procedure="PRK")},
        patient_modifiers={"contact_lens_type": "NONE"},
    )
    assert result["ready"] is True
    assert result["blockers"] == []
    assert result["pathways"] == {"OD": VIRGIN, "OS": VIRGIN}


def test_contact_lens_gate_blocks_before_core():
    result = evaluate_precore_readiness(
        age_years=35,
        eye_plans={"OD": _plan()},
        patient_modifiers={"contact_lens_type": "SOFT", "contact_lens_discontinuation_days": 9},
    )
    assert result["ready"] is False
    assert result["contact_lens_washout"]["required_days"] == 10
    assert any(item["key"] == "contact_lens_discontinuation_days" for item in result["blockers"])


def test_post_refractive_eye_routes_outside_virgin_core_without_requiring_procedure():
    result = evaluate_precore_readiness(
        age_years=35,
        eye_plans={"OD": _plan(prior="PRK", procedure=None)},
        patient_modifiers={"contact_lens_type": "NONE"},
    )
    assert result["ready"] is True
    assert result["pathways"]["OD"] == POST_REFRACTIVE


def test_unknown_prior_or_unsupported_virgin_procedure_blocks():
    unknown = evaluate_precore_readiness(
        age_years=35,
        eye_plans={"OD": _plan(prior="unknown")},
        patient_modifiers={"contact_lens_type": "NONE"},
    )
    unsupported = evaluate_precore_readiness(
        age_years=35,
        eye_plans={"OD": _plan(procedure="OTHER")},
        patient_modifiers={"contact_lens_type": "NONE"},
    )
    assert any(item["key"] == "prior" for item in unknown["blockers"])
    assert any(item["key"] == "procedure" for item in unsupported["blockers"])


def test_age_must_be_supported_adult_whole_number():
    for age in (None, 17, 120.5, 121):
        result = evaluate_precore_readiness(
            age_years=age,
            eye_plans={"OD": _plan()},
            patient_modifiers={"contact_lens_type": "NONE"},
        )
        assert result["ready"] is False
        assert any(item["key"] == "age" for item in result["blockers"])


def test_precore_readiness_has_no_tomography_or_scoring_dependency_table():
    import canonical_readiness as module
    source = inspect.getsource(module)
    for token in (
        "ARTmax",
        "BAD_D",
        "Df",
        "Db",
        "Dp",
        "Dt",
        "Da",
        "I_S",
        "Kmax",
        "evaluate_normalized_case",
        "score_nice",
        "evaluate_ps3",
    ):
        assert token not in source
