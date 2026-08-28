"""Equivalence tests between locked v0.7.43 runtime and the Phase 2 clean policy."""
import canonical_engine
from clean_engine import policy
from clean_engine import prk
from clean_engine.decision import DecisionInput, decide

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


def test_mrse_equivalence_at_all_score_boundaries():
    for mrse in (None, -16, -14.001, -14, -13.999, -12.001, -12, -11.999, -10.001, -10, -9.999, -8.001, -8, -7.999, 0, 4):
        assert policy.lasik_mrse_points(mrse) == legacy.lasik_mrse_points(mrse)


def test_clean_erss_total_uses_all_five_randleman_components():
    age = 18
    pachy = 500
    morphology = "ASYMMETRIC_BOWTIE"
    rsb = 270
    mrse = -9
    expected = (
        legacy.age_points(age)
        + legacy.lasik_pachy_points(pachy)
        + legacy.lasik_topography_points(morphology)
        + legacy.lasik_rsb_points(rsb)
        + legacy.lasik_mrse_points(mrse)
    )
    assert policy.lasik_erss_total(age, pachy, morphology, rsb, mrse) == expected


def test_clean_constants_equal_locked_runtime_constants():
    assert policy.POLICY.prk_epithelium_um == legacy.PRK_EPITHELIUM_UM
    assert policy.POLICY.corneal_effect_per_intended_mrse_d == legacy.CORNEAL_EFFECT_PER_INTENDED_MRSE_D
    assert policy.POLICY.final_kmean_min_d == legacy.FINAL_KMEAN_MIN_D
    assert policy.POLICY.final_kmean_max_d == legacy.FINAL_KMEAN_MAX_D


def test_unified_score_policy_has_one_locked_2_3_4_boundary():
    assert policy.POLICY.score_defer == 3
    assert policy.POLICY.score_stop == 4
    expected = {
        0: "NO_SCORE_ESCALATION",
        1: "NO_SCORE_ESCALATION",
        2: "NO_SCORE_ESCALATION",
        3: "DEFER",
        4: "STOP",
        5: "STOP",
    }
    for score, band in expected.items():
        assert policy.score_decision_band(score) == band


def test_prk_category_consumes_shared_score_policy():
    expected = {
        2: "NO_SCORE_ESCALATION",
        3: "CAUTION",
        4: "HIGH_CONCERN",
    }
    for score, category in expected.items():
        assert prk.prk_score_category(score) == category
        assert policy.score_decision_band(score) in {
            "NO_SCORE_ESCALATION", "DEFER", "STOP"
        }


def test_lasik_decision_consumes_shared_defer_boundary():
    assert decide(DecisionInput("PASS", "NORMAL", 2)).status == "PASS WITH CAUTION"
    assert decide(DecisionInput("PASS", "NORMAL", 3)).status == "CAUTION — DEFER"
    # Score >=4 is converted to an independent hard stop by the clean engine;
    # the pure decision layer still preserves the shared score escalation semantics.
    assert decide(DecisionInput("PASS", "NORMAL", 4)).status == "CAUTION — DEFER"
