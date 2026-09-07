import inspect

from clinical_core.disposition import ASSESSMENT_INCOMPLETE, CAUTION, PASS, STOP_DEFER
from clinical_eligibility import evaluate_eligibility


def _plan(**overrides):
    values = {
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers(**overrides):
    values = {
        "eye_rubbing": "no",
        "family_history": "no",
        "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }
    values.update(overrides)
    return values


def _statuses(result):
    return {finding.key: finding.status for finding in result.findings}


def test_complete_reassuring_eligibility_emits_pass_finding():
    result = evaluate_eligibility(_plan(), _modifiers(), bilateral=True)
    assert result.missing == ()
    assert _statuses(result) == {"clinical_eligibility": PASS}


def test_instability_or_progression_is_stop_defer():
    unstable = evaluate_eligibility(_plan(stable="no"), _modifiers(), bilateral=False)
    progression = evaluate_eligibility(_plan(progression="yes"), _modifiers(), bilateral=False)
    assert _statuses(unstable)["refractive_stability"] == STOP_DEFER
    assert _statuses(progression)["refractive_stability"] == STOP_DEFER


def test_documented_eligibility_cautions_remain_cautions():
    result = evaluate_eligibility(
        _plan(cdva_below_20_20="yes"),
        _modifiers(
            inter_eye_asymmetry="yes",
            collagen_tissue_disease="yes",
            drug_usage="yes",
            dry_eye="yes",
            systemic_disease="yes",
        ),
        bilateral=True,
    )
    statuses = _statuses(result)
    assert statuses["unexplained_cdva"] == CAUTION
    assert statuses["clinical_inter_eye_asymmetry"] == CAUTION
    assert statuses["collagen_tissue_disease"] == CAUTION
    assert statuses["relevant_medication"] == CAUTION
    assert statuses["dry_eye"] == CAUTION
    assert statuses["systemic_disease"] == CAUTION


def test_pregnancy_or_nursing_is_stop_defer():
    result = evaluate_eligibility(_plan(), _modifiers(pregnancy_nursing="yes"), bilateral=False)
    assert _statuses(result)["pregnancy_nursing"] == STOP_DEFER


def test_eye_rubbing_and_family_history_are_notes_not_independent_risk_points():
    result = evaluate_eligibility(
        _plan(),
        _modifiers(eye_rubbing="yes", family_history="yes"),
        bilateral=False,
    )
    assert _statuses(result) == {"clinical_eligibility": PASS}
    assert len(result.notes) == 2


def test_missing_required_documentation_is_incomplete():
    modifiers = _modifiers()
    modifiers["dry_eye"] = "unknown"
    result = evaluate_eligibility(_plan(), modifiers, bilateral=False)
    assert "dry_eye" in result.missing
    assert _statuses(result)["clinical_eligibility"] == ASSESSMENT_INCOMPLETE


def test_inter_eye_documentation_is_required_only_for_bilateral_case():
    modifiers = _modifiers(inter_eye_asymmetry="unknown")
    unilateral = evaluate_eligibility(_plan(), modifiers, bilateral=False)
    bilateral = evaluate_eligibility(_plan(), modifiers, bilateral=True)
    assert "marked_inter_eye_asymmetry" not in unilateral.missing
    assert "marked_inter_eye_asymmetry" in bilateral.missing


def test_eligibility_module_has_no_tomography_or_scoring_logic():
    import clinical_eligibility as module
    source = inspect.getsource(module)
    for token in (
        "BAD_D",
        "ARTmax",
        "I_S",
        "Kmax",
        "pachy_thinnest_um",
        "score_nice",
        "evaluate_ps3",
        "evaluate_normalized_case",
        "finalize_disposition",
    ):
        assert token not in source
