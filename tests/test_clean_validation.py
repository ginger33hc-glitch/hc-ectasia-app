from clean_engine.validation import ValidationInput, validate_decision_inputs


def valid(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK",
        prior_refractive_surgery=False, ablation_um=60, flap_um=100,
        preop_kmean_d=43, manifest_mrse_d=-3, intended_mrse_d=-3,
        intended_sphere_d=-3, intended_cylinder_magnitude_d=0,
        laser_platform="Alcon EX500",
    )
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


def test_procedure_critical_inputs_are_required():
    for field in (
        "preop_kmean_d", "intended_mrse_d",
        "intended_sphere_d", "intended_cylinder_magnitude_d", "laser_platform",
    ):
        assert field in validate_decision_inputs(valid(**{field: None}))
    assert "ablation_um" in validate_decision_inputs(valid(
        ablation_um=None, intended_sphere_d=2, intended_mrse_d=2,
    ))
    assert "manifest_mrse_d" in validate_decision_inputs(valid(manifest_mrse_d=None))
    assert validate_decision_inputs(valid(flap_um=None)) == ()
    assert "flap_um" in validate_decision_inputs(valid(flap_um=95))


def test_prior_surgery_status_must_be_explicitly_virgin_at_validation_boundary():
    assert validate_decision_inputs(valid(prior_refractive_surgery=None)) == ("prior_refractive_surgery",)


def test_numeric_domains_and_intended_mrse_consistency_fail_closed():
    assert "age_years" in validate_decision_inputs(valid(age_years=130))
    assert "pachy_thinnest_um" in validate_decision_inputs(valid(pachy_thinnest_um=float("nan")))
    assert "intended_cylinder_magnitude_d" in validate_decision_inputs(valid(intended_cylinder_magnitude_d=-1))
    assert "intended_mrse_consistency" in validate_decision_inputs(valid(intended_mrse_d=-2))
