"""Equivalence tests between locked v0.7.43 runtime and the Phase 2 clean policy."""
import canonical_engine
from clean_engine import policy

legacy = canonical_engine.core


def test_age_equivalence_at_boundaries_and_neighbors():
    for age in (None, 17, 18, 18.999, 19, 20, 20.999, 21, 30, 80):
        assert policy.age_points(age) == legacy.age_points(age)


def test_pachymetry_equivalence_at_boundaries_and_neighbors():
    for pachy in (None, 479.999, 480, 480.001, 481, 499, 499.999, 500, 510, 510.001, 511, 600):
        assert policy.lasik_pachymetry_points(pachy) == legacy.lasik_pachy_points(pachy)


def test_final_bad_d_equivalence_at_boundaries_and_neighbors():
    for value in (None, 0, 1.5999, 1.6, 1.6001, 2.6, 2.9999, 3.0, 4.0):
        assert policy.final_bad_d_classification(value) == legacy.bad_classification(value, final=True)


def test_topography_equivalence():
    for morphology in (
        "NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA",
        "ABNORMAL_ECTATIC", "UNCERTAIN", "UNREADABLE"
    ):
        assert policy.randleman_topography_points(morphology) == legacy.lasik_topography_points(morphology)


def test_rsb_equivalence_at_all_score_boundaries():
    for rsb in (None, 200, 239.999, 240, 259.999, 260, 279.999, 280, 299.999, 300, 400):
        assert policy.lasik_rsb_points(rsb) == legacy.lasik_rsb_points(rsb)


def test_clean_constants_equal_locked_runtime_constants():
    assert policy.POLICY.prk_epithelium_um == legacy.PRK_EPITHELIUM_UM
    assert policy.POLICY.corneal_effect_per_intended_mrse_d == legacy.CORNEAL_EFFECT_PER_INTENDED_MRSE_D
    assert policy.POLICY.final_kmean_min_d == legacy.FINAL_KMEAN_MIN_D
    assert policy.POLICY.final_kmean_max_d == legacy.FINAL_KMEAN_MAX_D
