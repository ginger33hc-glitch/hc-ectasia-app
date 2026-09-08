import inspect
from pathlib import Path

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
    result = evaluate_eligibility(_plan(), _modifiers())
    assert result.missing == ()
    assert _statuses(result) == {"clinical_eligibility": PASS}


def test_instability_or_progression_is_stop_defer():
    unstable = evaluate_eligibility(_plan(stable="no"), _modifiers())
    progression = evaluate_eligibility(_plan(progression="yes"), _modifiers())
    assert _statuses(unstable)["refractive_stability"] == STOP_DEFER
    assert _statuses(progression)["refractive_stability"] == STOP_DEFER


def test_documented_eligibility_cautions_remain_cautions():
    result = evaluate_eligibility(
        _plan(cdva_below_20_20="yes"),
        _modifiers(
            eye_rubbing="yes",
            family_history="yes",
            drug_usage="yes",
            dry_eye="yes",
            systemic_disease="yes",
        ),
    )
    statuses = _statuses(result)
    assert statuses["unexplained_cdva"] == CAUTION
    assert statuses["eye_rubbing_or_ocular_trauma"] == CAUTION
    assert statuses["family_history_keratoconus"] == CAUTION
    assert statuses["relevant_medication"] == CAUTION
    assert statuses["dry_eye"] == CAUTION
    assert statuses["systemic_disease"] == CAUTION


def test_pregnancy_or_nursing_is_stop_defer():
    result = evaluate_eligibility(_plan(), _modifiers(pregnancy_nursing="yes"))
    assert _statuses(result)["pregnancy_nursing"] == STOP_DEFER


def test_collagen_connective_tissue_disease_is_stop_defer():
    result = evaluate_eligibility(_plan(), _modifiers(collagen_tissue_disease="yes"))
    assert _statuses(result)["collagen_tissue_disease"] == STOP_DEFER


def test_eye_rubbing_and_family_history_are_cautions_and_reported_as_modifiers():
    result = evaluate_eligibility(
        _plan(),
        _modifiers(eye_rubbing="yes", family_history="yes"),
    )
    assert _statuses(result) == {
        "eye_rubbing_or_ocular_trauma": CAUTION,
        "family_history_keratoconus": CAUTION,
    }
    assert len(result.notes) == 2


def test_missing_required_documentation_is_incomplete():
    modifiers = _modifiers()
    modifiers["dry_eye"] = "unknown"
    result = evaluate_eligibility(_plan(), modifiers)
    assert "dry_eye" in result.missing
    assert _statuses(result)["clinical_eligibility"] == ASSESSMENT_INCOMPLETE


def test_removed_inter_eye_modifier_is_ignored_by_eligibility():
    result = evaluate_eligibility(_plan(), _modifiers(inter_eye_asymmetry="yes"))
    assert result.missing == ()
    assert _statuses(result) == {"clinical_eligibility": PASS}


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
        "inter_eye_asymmetry",
        "enhancement_anticipated",
    ):
        assert token not in source


def test_removed_duplicate_and_unused_controls_are_absent_from_ui():
    html = (Path(__file__).parents[1] / "static" / "index.html").read_text()
    assert 'value="inter_eye_asymmetry"' not in html
    assert "enhancement_anticipated" not in html
    assert "Enhancement anticipated?" not in html
