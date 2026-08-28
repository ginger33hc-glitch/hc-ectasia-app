from clean_engine.validation import ValidationInput, validate_decision_inputs


def valid(**changes):
    values = dict(age_years=30, pachy_thinnest_um=520, bad_d=1.0, morphology="NORMAL_SYMMETRIC", procedure="LASIK")
    values.update(changes)
    return ValidationInput(**values)


def test_complete_lasik_and_prk_inputs_validate_cleanly():
    assert validate_decision_inputs(valid()) == ()
    assert validate_decision_inputs(valid(procedure="prk")) == ()


def test_missing_principal_inputs_are_reported_in_stable_order():
    out = validate_decision_inputs(valid(age_years=None, pachy_thinnest_um=None, bad_d=None))
    assert out == ("age_years", "pachy_thinnest_um", "bad_d")


def test_uncertain_or_unreadable_morphology_is_not_silently_normal():
    assert validate_decision_inputs(valid(morphology="UNCERTAIN")) == ("morphology",)
    assert validate_decision_inputs(valid(morphology="UNREADABLE")) == ("morphology",)


def test_unknown_or_blank_procedure_is_not_accepted():
    assert validate_decision_inputs(valid(procedure="SMILE")) == ("procedure",)
    assert validate_decision_inputs(valid(procedure="")) == ("procedure",)


def test_multiple_validation_failures_are_composed_deterministically():
    out = validate_decision_inputs(valid(age_years=None, bad_d=None, morphology="UNCERTAIN", procedure="SMILE"))
    assert out == ("age_years", "bad_d", "morphology", "procedure")
