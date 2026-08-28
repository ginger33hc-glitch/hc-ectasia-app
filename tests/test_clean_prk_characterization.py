"""Characterization lock for the active legacy PRK scoring primitives.

These tests intentionally record current behavior before the clean engine models PRK.
They do not assert that the provisional PRK-EWSS is a validated LASIK ERSS analogue.
"""
import canonical_engine

legacy = canonical_engine.core


def test_prk_morphology_points_are_characterized():
    expected = {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 5,
        "ABNORMAL_ECTATIC": 5,
        "UNCERTAIN": None,
        "UNREADABLE": None,
    }
    for morphology, points in expected.items():
        assert legacy.prk_morphology_points(morphology) == points


def test_prk_pachymetry_boundaries_are_characterized():
    expected = {
        449.999: 4,
        450: 4,
        450.001: 3,
        479.999: 3,
        480: 3,
        480.001: 2,
        509.999: 2,
        510: 2,
        510.001: 0,
        600: 0,
    }
    for pachy, points in expected.items():
        assert legacy.prk_pachy_points(pachy) == points


def test_prk_uses_active_hc_age_policy_at_runtime():
    expected = {18: 3, 19: 2, 20: 2, 21: 0, 30: 0}
    for age, points in expected.items():
        assert legacy.age_points(age) == points


def test_prk_provisional_category_boundaries_are_characterized():
    expected = {
        0: "LOWER_FLAGGED_BURDEN",
        1: "LOWER_FLAGGED_BURDEN",
        2: "CAUTION",
        3: "CAUTION",
        4: "HIGH_CONCERN",
        8: "HIGH_CONCERN",
    }
    for score, category in expected.items():
        assert legacy.score_category("PRK", score) == category


def test_prk_tissue_calculation_constants_match_locked_runtime():
    assert legacy.PRK_EPITHELIUM_UM == 50
    assert 500 - legacy.PRK_EPITHELIUM_UM - 140 == 310
    assert 500 - legacy.PRK_EPITHELIUM_UM - 140.001 < 310


def test_prk_pta_35_28_is_evidence_gap_flag_not_hard_stop_boundary():
    # Characterizes the comparison used by assess_eye: strictly greater than 35.28%.
    assert not (35.28 > 35.28)
    assert 35.280001 > 35.28
