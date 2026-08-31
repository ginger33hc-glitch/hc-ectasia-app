import types
import erss_auto_read_policy as policy


def test_resolved_erss_does_not_require_morphology_prompt():
    result = {
        "randleman_erss": {"topography_category": "ASYMMETRIC_BOWTIE", "missing_erss_inputs": []},
        "missing": ["topography category", "NICE: central_pachy_um"],
    }
    policy._clean_missing(result)
    assert "NICE: central_pachy_um" in result["missing"]
    assert policy._is_unresolved_erss(result) is False


def test_nice_never_owns_srax_or_abt():
    result = {
        "missing": ["NICE: SRAX", "NICE: asymmetric bow-tie", "NICE: posterior_pupil_max_um"]
    }
    policy._clean_missing(result)
    assert result["missing"] == ["NICE: posterior_pupil_max_um"]


def test_unresolved_erss_remains_reviewable():
    result = {
        "randleman_erss": {"topography_category": "UNCERTAIN", "missing_erss_inputs": ["topography"]},
        "missing": ["topography category"],
    }
    assert policy._is_unresolved_erss(result) is True
