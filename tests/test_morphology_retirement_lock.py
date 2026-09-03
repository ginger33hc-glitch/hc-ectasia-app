"""Regression lock: retired morphology stays retired while SRAX confirmation remains active."""

import erss_auto_read_policy as policy


def _legacy_decision():
    return {
        "critical_input_issues": [
            "OD extraction validation: unresolved morphology",
            "OS Signed I-S (D) is unreadable",
            "OD SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
        ],
        "eyes": [
            {
                "eye": "OD",
                "missing": [
                    "Randleman topography category",
                    "morphology confirmation required",
                    "asymmetric bow-tie confirmation",
                    "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
                    "inferior steepening morphology",
                    "readable anterior pattern",
                    "readable posterior pattern",
                    "Signed I-S (D) required",
                ],
                "randleman_erss": {
                    "topography_category": "UNCERTAIN",
                    "missing_erss_inputs": ["topography", "morphology"],
                },
            }
        ],
    }


def test_unresolved_erss_removes_retired_morphology_but_preserves_srax_and_i_s(monkeypatch):
    monkeypatch.setattr(
        policy,
        "_previous_hc_engine",
        lambda *args, **kwargs: _legacy_decision(),
    )

    decision = policy.hc_engine_with_erss_auto_read({}, 30, {}, {}, {})
    eye = decision["eyes"][0]

    assert eye["missing"] == [
        "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
        "Signed I-S (D) required",
    ]
    assert eye["randleman_erss"]["missing_erss_inputs"] == []
    assert decision["critical_input_issues"] == [
        "OS Signed I-S (D) is unreadable",
        "OD SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
    ]


def test_retired_terms_are_removed_while_signed_i_s_and_srax_are_preserved():
    result = {
        "missing": [
            "morphology",
            "Randleman topography category",
            "topographic category",
            "asymmetric bow tie",
            "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
            "inferior steepening morphology",
            "readable anterior pattern",
            "readable posterior pattern",
            "Signed I-S (D) required",
        ]
    }
    policy._clean_missing(result)
    assert result["missing"] == [
        "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
        "Signed I-S (D) required",
    ]
