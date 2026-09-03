import erss_auto_read_policy as policy


def test_resolved_erss_does_not_require_retired_morphology_prompt():
    result = {
        "randleman_erss": {"topography_category": "ASYMMETRIC_BOWTIE", "missing_erss_inputs": []},
        "missing": ["topography category", "NICE: central_pachy_um"],
    }
    policy._clean_missing(result)
    assert result["missing"] == ["NICE: central_pachy_um"]


def test_nice_never_owns_srax_or_abt():
    result = {
        "missing": ["NICE: SRAX", "NICE: asymmetric bow-tie", "NICE: B_Ele_Th_um"]
    }
    policy._clean_missing(result)
    assert result["missing"] == ["NICE: B_Ele_Th_um"]


def test_unresolved_erss_preserves_explicit_front_map_srax_confirmation():
    result = {
        "randleman_erss": {
            "topography_category": "UNCERTAIN",
            "missing_erss_inputs": ["topography", "morphology"],
        },
        "missing": [
            "topography category",
            "morphology confirmation",
            "Signed I-S (D) required",
            "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
        ],
    }
    policy._clean_missing(result)
    assert result["missing"] == [
        "Signed I-S (D) required",
        "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
    ]
    assert result["randleman_erss"]["missing_erss_inputs"] == []
