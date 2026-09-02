"""Regression locks for the Ridvan Ozay false OS defer case."""
import hc_final_decision_policy as policy


def test_labeled_i_s_minus_013_overrides_false_asymmetric_bow_tie():
    eye = {
        "I_S": -0.13,
        "table_verified_numeric_fields": ["I_S"],
        "morphology": "ASYMMETRIC_BOWTIE",
        "asymmetric_bow_tie": "YES",
        "srax": "NO",
        "srax_deg": None,
        "inferior_opposite_steepening_D": None,
        "morphology_evidence": ["visual false positive"],
    }
    corrected = policy._apply_locked_i_s_normal_band(eye)
    assert corrected["morphology"] == "NORMAL_SYMMETRIC"
    assert corrected["asymmetric_bow_tie"] == "NO"
    assert eye["morphology"] == "ASYMMETRIC_BOWTIE"  # input is not mutated


def test_i_s_normal_band_boundaries_are_inclusive():
    for value in (-0.50, 0.0, 0.50):
        corrected = policy._apply_locked_i_s_normal_band({
            "I_S": value,
            "table_verified_numeric_fields": ["I_S"],
            "morphology": "ASYMMETRIC_BOWTIE",
            "asymmetric_bow_tie": "YES",
            "srax": "NO",
            "morphology_evidence": [],
        })
        assert corrected["morphology"] == "NORMAL_SYMMETRIC"


def test_unverified_i_s_does_not_override_morphology():
    corrected = policy._apply_locked_i_s_normal_band({
        "I_S": -0.13,
        "table_verified_numeric_fields": [],
        "morphology": "ASYMMETRIC_BOWTIE",
        "asymmetric_bow_tie": "YES",
        "srax": "NO",
        "morphology_evidence": [],
    })
    assert corrected["morphology"] == "ASYMMETRIC_BOWTIE"


def test_prk_caution_without_hard_stop_is_recognized_as_non_defer():
    result = {
        "values": {"procedure": "PRK"},
        "score": {"total": 2, "category": "CAUTION"},
        "hard_stops": [],
        "status": "STOP-DEFER",
    }
    assert policy._prk_caution_was_auto_deferred(result)


def test_prk_caution_never_masks_independent_hard_stop():
    result = {
        "values": {"procedure": "PRK"},
        "score": {"total": 2, "category": "CAUTION"},
        "hard_stops": ["independent hard stop"],
        "status": "STOP-DEFER",
    }
    assert not policy._prk_caution_was_auto_deferred(result)
