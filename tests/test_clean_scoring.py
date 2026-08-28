from clean_engine.scoring import ScoringInput, calculate_scores


def test_lasik_scoring_keeps_all_five_erss_components():
    lasik, prk = calculate_scores(ScoringInput(
        procedure="LASIK", age_years=18, pachy_thinnest_um=500,
        morphology="ASYMMETRIC_BOWTIE", intended_mrse_d=-9,
        lasik_rsb_um=270, prk_pta_percent=None,
    ))
    assert (lasik.age_points, lasik.pachymetry_points, lasik.topography_points, lasik.rsb_points, lasik.mrse_points) == (3, 1, 1, 2, 1)
    assert lasik.erss_total == 8
    assert prk.total is None


def test_prk_scoring_remains_separate_from_lasik_erss():
    lasik, prk = calculate_scores(ScoringInput(
        procedure="PRK", age_years=30, pachy_thinnest_um=520,
        morphology="ASYMMETRIC_BOWTIE", intended_mrse_d=-3,
        lasik_rsb_um=350, prk_pta_percent=30,
    ))
    assert lasik.erss_total is None
    assert lasik.rsb_points is None
    assert lasik.mrse_points is None
    assert prk.total == 2
    assert prk.category == "NO_SCORE_ESCALATION"


def test_prk_score_three_and_four_boundaries_use_shared_policy():
    _, score3 = calculate_scores(ScoringInput("PRK", 18, 520, "NORMAL_SYMMETRIC", -3, None, 30))
    _, score5 = calculate_scores(ScoringInput("PRK", 30, 520, "INFERIOR_STEEPENING_SRA", -3, None, 30))
    assert score3.total == 3 and score3.category == "CAUTION"
    assert score5.total == 5 and score5.category == "HIGH_CONCERN"


def test_prk_pta_evidence_gap_is_part_of_prk_score_result_only():
    lasik, prk = calculate_scores(ScoringInput("PRK", 30, 520, "NORMAL_SYMMETRIC", -3, None, 35.280001))
    assert lasik.erss_total is None
    assert prk.pta_evidence_gap is True


def test_unavailable_component_fails_closed_without_fabricating_total():
    lasik, _ = calculate_scores(ScoringInput("LASIK", None, 520, "NORMAL_SYMMETRIC", -3, 350, None))
    assert lasik.age_points is None
    assert lasik.erss_total is None
