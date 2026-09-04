"""Regression locks for retired general morphology and source-locked SRAX readiness."""

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
                "values": {"procedure": "LASIK"},
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
                    "rows": {"topography": None, "RSB": 0, "age": 0, "pachymetry": 0, "MRSE": 0},
                    "total": None,
                    "missing_erss_inputs": ["topography", "morphology"],
                },
            }
        ],
    }


def test_unresolved_erss_removes_retired_morphology_but_preserves_srax_i_s_and_score_block(monkeypatch):
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
        "Randleman/ERSS score incomplete: topography",
    ]
    assert eye["randleman_erss"]["missing_erss_inputs"] == ["topography"]
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


def test_complete_lasik_erss_is_not_blocked():
    result = {
        "values": {"procedure": "LASIK"},
        "missing": [],
        "randleman_erss": {
            "rows": {"topography": 3, "RSB": 0, "age": 0, "pachymetry": 0, "MRSE": 0},
            "total": 3,
            "missing_erss_inputs": [],
        },
    }
    policy._clean_missing(result)
    assert result["missing"] == []
    assert result["randleman_erss"]["missing_erss_inputs"] == []
