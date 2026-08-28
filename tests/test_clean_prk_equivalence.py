"""Old-vs-clean PRK component equivalence plus explicit HC decision override."""
import canonical_engine

from clean_engine import prk

legacy = canonical_engine.core


def test_prk_morphology_equivalence():
    for morphology in (
        "NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA",
        "ABNORMAL_ECTATIC", "UNCERTAIN", "UNREADABLE",
    ):
        assert prk.prk_morphology_points(morphology) == legacy.prk_morphology_points(morphology)


def test_prk_pachymetry_equivalence_at_boundaries_and_neighbors():
    for pachy in (None, 449.999, 450, 450.001, 479.999, 480, 480.001, 509.999, 510, 510.001, 600):
        assert prk.prk_pachymetry_points(pachy) == legacy.prk_pachy_points(pachy)


def test_prk_decision_category_uses_unified_hc_boundary():
    expected = {
        0: "NO_SCORE_ESCALATION",
        1: "NO_SCORE_ESCALATION",
        2: "NO_SCORE_ESCALATION",
        3: "CAUTION",
        4: "HIGH_CONCERN",
        5: "HIGH_CONCERN",
    }
    for score, category in expected.items():
        assert prk.prk_score_category(score) == category


def test_prk_total_uses_same_runtime_components():
    cases = [
        (30, 520, "NORMAL_SYMMETRIC"),
        (20, 500, "NORMAL_SYMMETRIC"),
        (30, 520, "ASYMMETRIC_BOWTIE"),
        (18, 480, "ASYMMETRIC_BOWTIE"),
        (30, 520, "INFERIOR_STEEPENING_SRA"),
    ]
    for age, pachy, morphology in cases:
        expected = legacy.age_points(age) + legacy.prk_pachy_points(pachy) + legacy.prk_morphology_points(morphology)
        assert prk.prk_score_total(age, pachy, morphology) == expected


def test_prk_total_fails_closed_when_component_unavailable():
    assert prk.prk_score_total(None, 520, "NORMAL_SYMMETRIC") is None
    assert prk.prk_score_total(30, None, "NORMAL_SYMMETRIC") is None
    assert prk.prk_score_total(30, 520, "UNCERTAIN") is None


def test_prk_pta_evidence_gap_boundary_is_strictly_greater_than_35_28():
    assert prk.prk_pta_evidence_gap(None) is False
    assert prk.prk_pta_evidence_gap(35.279999) is False
    assert prk.prk_pta_evidence_gap(35.28) is False
    assert prk.prk_pta_evidence_gap(35.280001) is True
