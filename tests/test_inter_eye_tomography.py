from inter_eye_tomography import assess_inter_eye_tomography
import inter_eye_tomography_policy as policy_layer


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


def test_manual_modifier_is_neutralized_and_status_is_unchanged(monkeypatch):
    captured = {}

    def upstream(extracted, age, eye_plans, modifiers, patient_metadata=None):
        captured.update(modifiers)
        return {
            "status": "PASS WITH CAUTION",
            "eyes": [
                {"eye": "OD", "status": "PASS WITH CAUTION", "tomography_review": {"cross_sectional_flags": []}},
                {"eye": "OS", "status": "PASS WITH CAUTION", "tomography_review": {"cross_sectional_flags": []}},
            ],
        }

    monkeypatch.setattr(policy_layer, "_previous_hc_engine", upstream)
    extracted = {"eyes": [eye("OD"), eye("OS", bad=2.0)]}
    out = policy_layer.hc_engine_with_inter_eye_tomography(
        extracted,
        30,
        {},
        {"inter_eye_asymmetry": "yes"},
        {},
    )
    assert captured["inter_eye_asymmetry"] == "no"
    assert out["status"] == "PASS WITH CAUTION"
    assert out["inter_eye_tomography_concern"]["status"] == "POSITIVE"
    assert all(result["status"] == "PASS WITH CAUTION" for result in out["eyes"])
    assert all(
        any("Inter-eye tomography concern: POSITIVE" in flag for flag in result["tomography_review"]["cross_sectional_flags"])
        for result in out["eyes"]
    )
