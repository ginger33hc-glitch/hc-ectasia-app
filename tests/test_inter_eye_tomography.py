from inter_eye_tomography import assess_inter_eye_tomography


def eye(eye_id, bad=1.0, morphology="NORMAL_SYMMETRIC", anterior="REASSURING", posterior="REASSURING"):
    return {
        "eye": eye_id,
        "BAD_D": bad,
        "morphology": morphology,
        "anterior_pattern": anterior,
        "posterior_pattern": posterior,
    }


def test_bilateral_reassuring_is_non_scored_negative():
    out = assess_inter_eye_tomography([eye("OD"), eye("OS")])
    assert out["status"] == "NO MAJOR INTER-EYE DISCORDANCE DETECTED"
    assert out["scored"] is False
    assert out["decision_effect"] == "NONE"


def test_final_bad_category_discordance_is_positive():
    out = assess_inter_eye_tomography([eye("OD", bad=1.2), eye("OS", bad=2.1)])
    assert out["status"] == "POSITIVE"
    assert any("Final BAD-D" in item for item in out["major_discordances"])


def test_final_bad_2_60_boundary_is_abnormal_for_inter_eye_context():
    out = assess_inter_eye_tomography([eye("OD", bad=2.5999), eye("OS", bad=2.6)])
    assert out["status"] == "POSITIVE"
    assert "OD SUSPICIOUS vs OS ABNORMAL" in out["major_discordances"][0]


def test_morphology_normal_vs_inferior_steepening_is_positive():
    out = assess_inter_eye_tomography([
        eye("OD"),
        eye("OS", morphology="INFERIOR_STEEPENING_SRA"),
    ])
    assert out["status"] == "POSITIVE"
    assert any("Anterior morphology" in item for item in out["major_discordances"])


def test_pattern_reassuring_vs_borderline_is_positive():
    out = assess_inter_eye_tomography([
        eye("OD"),
        eye("OS", posterior="BORDERLINE"),
    ])
    assert out["status"] == "POSITIVE"
    assert any("Posterior Pattern" in item for item in out["major_discordances"])


def test_missing_required_domain_cannot_be_called_negative():
    os_eye = eye("OS")
    os_eye["BAD_D"] = None
    out = assess_inter_eye_tomography([eye("OD"), os_eye])
    assert out["status"] == "NOT ASSESSABLE"
    assert "Final BAD-D" in out["unavailable_domains"]


def test_missing_fellow_eye_is_not_assessable():
    out = assess_inter_eye_tomography([eye("OD")])
    assert out["status"] == "NOT ASSESSABLE"
