import canonical_engine

core = canonical_engine.core


def _scored_category(i_s):
    eye = {
        "I_S": i_s,
        "I_S_status": "CONFIDENT",
        "table_verified_numeric_fields": ["I_S"],
        "data_conflicts": [],
        "morphology_evidence": [],
        "morphology": "UNCERTAIN",
        "morphology_confidence": "UNREADABLE",
        "anterior_curvature_map_visible": "NO",
        "_erss_i_s_gate_required": True,
        "KISA": None,
        "Kmax_D": None,
        "topographic_astig_D": None,
    }
    return core.scoring_morphology(eye)["category"]


def test_negative_half_is_normal_boundary():
    assert _scored_category(-0.50) == "NORMAL_SYMMETRIC"


def test_just_below_negative_half_is_abt():
    assert _scored_category(-0.5001) == "ASYMMETRIC_BOWTIE"


def test_negative_one_point_one_four_is_abt():
    assert _scored_category(-1.14) == "ASYMMETRIC_BOWTIE"


def test_far_negative_i_s_has_no_lower_limit_for_abt():
    assert _scored_category(-5.0) == "ASYMMETRIC_BOWTIE"
