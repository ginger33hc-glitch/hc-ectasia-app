"""End-to-end equivalence matrix for behavior that can be compared safely.

This complements primitive equivalence tests. Intentional HC policy overrides are
kept out of this matrix and remain locked by their dedicated clean tests.
"""
import canonical_engine
import clean_engine

legacy = canonical_engine.core


def clean_case(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK", ablation_um=60,
        flap_um=100, preop_kmean_d=44, intended_mrse_d=-3,
        intended_sphere_d=-3, intended_cylinder_magnitude_d=1,
        laser_platform="Alcon EX500",
    )
    values.update(changes)
    return clean_engine.assess(clean_engine.EyeInput(**values))


def test_clean_lasik_score_components_match_canonical_primitives_across_matrix():
    cases = (
        (18, 500, "NORMAL_SYMMETRIC", 340, -3),
        (19, 505, "ASYMMETRIC_BOWTIE", 270, -9),
        (21, 511, "INFERIOR_STEEPENING_SRA", 300, -8),
        (30, 520, "NORMAL_SYMMETRIC", 360, 2),
    )
    for age, pachy, morphology, expected_rsb, mrse in cases:
        flap = 100
        ablation = pachy - flap - expected_rsb
        out = clean_case(
            age_years=age, pachy_thinnest_um=pachy, morphology=morphology,
            flap_um=flap, ablation_um=ablation, intended_mrse_d=mrse,
            intended_sphere_d=max(-10, min(6, mrse)), preop_kmean_d=44,
        )
        expected = (
            legacy.age_points(age),
            legacy.lasik_pachy_points(pachy),
            legacy.lasik_topography_points(morphology),
            legacy.lasik_rsb_points(expected_rsb),
            legacy.lasik_mrse_points(mrse),
        )
        actual = (
            out.scores.age_points, out.scores.pachymetry_points,
            out.scores.topography_points, out.scores.rsb_points,
            out.scores.mrse_points,
        )
        assert actual == expected
        assert out.scores.erss_total == sum(expected)


def test_clean_bad_d_classification_matches_canonical_across_final_boundaries():
    for bad_d in (1.0, 1.6, 1.6001, 2.99, 3.0, 4.0):
        out = clean_case(bad_d=bad_d)
        assert out.bad_d_status == legacy.bad_classification(bad_d, final=True)


def test_clean_surgical_outputs_match_locked_canonical_formulas():
    lasik = clean_case(pachy_thinnest_um=520, flap_um=100, ablation_um=60, preop_kmean_d=44, intended_mrse_d=-3)
    assert lasik.calculations.lasik_rsb_um == 520 - 100 - 60
    assert lasik.calculations.lasik_pta_percent == 100 * (100 + 60) / 520
    assert lasik.calculations.final_kmean_d == 44 + legacy.CORNEAL_EFFECT_PER_INTENDED_MRSE_D * -3

    prk = clean_case(procedure="PRK", flap_um=None, pachy_thinnest_um=520, ablation_um=60)
    assert prk.calculations.prk_rst_um == 520 - legacy.PRK_EPITHELIUM_UM - 60
    assert prk.calculations.prk_pta_percent == 100 * (legacy.PRK_EPITHELIUM_UM + 60) / 520


def test_clean_final_lasik_status_matches_locked_principal_hierarchy_for_comparable_cases():
    expected = (
        ({}, "PASS WITH CAUTION"),
        ({"age_years": 18}, "CAUTION — DEFER"),
        ({"bad_d": 3.0}, "DO NOT PROCEED"),
        ({"bad_d": None}, "DATA INSUFFICIENT"),
    )
    for changes, status in expected:
        assert clean_case(**changes).status == status
