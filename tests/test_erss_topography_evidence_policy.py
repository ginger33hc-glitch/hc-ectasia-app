import canonical_engine as runtime
from pathlib import Path

from test_hc_engine import MODIFIERS, normal_eye, plan


core = runtime.core


def lasik_plan():
    return plan("LASIK", sphere=-3.0, cylinder=0.0, ablation=60, flap=100)


def test_evidence_module_does_not_replace_or_duplicate_point_mapper():
    assert core.lasik_topography_points.__module__ == "app"
    assert core.lasik_topography_points("ASYMMETRIC_BOWTIE") == 1
    assert core.lasik_topography_points("INFERIOR_STEEPENING_SRA") == 3


def test_dedicated_schema_and_browser_form_carry_i_s_confirmation():
    import erss_topography_guard as guard

    assert "I_S" in guard.ERSS_SCHEMA["required"]
    assert "PENTACAM_TOPOMETRIC_KC" in guard.ERSS_SCHEMA["properties"]["display_type"]["enum"]
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert '${eye}_surgeon_i_s' in html
    assert 'surgeon_I_S_D:numberOrNull' in html
    assert 'surgeon_topography_category:value' in html


def test_missing_i_s_blocks_topography_row_and_erss_total():
    eye = normal_eye()
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["randleman_erss"]["rows"]["topography"] is None
    assert result["randleman_erss"]["total"] is None
    assert result["erss_topography_evidence"]["needs_surgeon_I_S"] is True
    assert "PASS" not in result["status"]


def test_lasik_i_s_gate_does_not_change_the_separate_prk_pathway():
    eye = normal_eye()
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    result = core.assess_eye(eye, plan("PRK", sphere=-3.0, cylinder=0.0, ablation=60, flap=None), 30, MODIFIERS)
    assert "erss_topography_evidence" not in result
    assert not any("I-S value for Randleman" in str(item) for item in result.get("missing") or [])


def test_conflicting_i_s_is_not_resolved_by_scoring_the_maximum():
    eye = normal_eye()
    eye["data_conflicts"] = ["I_S: 0.50 vs 1.50"]
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["I_S_status"] == "CONFLICT"
    assert result["randleman_erss"]["rows"]["topography"] is None
    assert result["randleman_erss"]["total"] is None


def test_dedicated_and_general_same_image_i_s_conflict_requires_confirmation(monkeypatch):
    import erss_topography_guard as guard
    from test_erss_runtime import eye as extracted_eye, result as extraction_result

    source_eye = extracted_eye(True, "NORMAL_SYMMETRIC", "topometric.jpg")
    source_eye["I_S"] = 0.5
    source_eye["table_verified_numeric_fields"] = ["I_S"]
    general = extraction_result(source_eye, "topometric.jpg")
    monkeypatch.setattr(guard, "_original_extract_one_image", lambda raw, filename: general)
    monkeypatch.setattr(guard, "_erss_second_pass", lambda raw, filename: {
        "display_type": "PENTACAM_TOPOMETRIC_KC",
        "eye": "OD",
        "I_S": 0.75,
        "I_S_status": "CONFIDENT",
    })
    extracted = guard.extract_one_image_with_erss(b"image", "topometric.jpg")
    assert extracted["eyes"][0]["I_S"] is None
    assert "I_S" not in extracted["eyes"][0]["table_verified_numeric_fields"]
    assert any(str(item).startswith("I_S:") for item in extracted["eyes"][0]["data_conflicts"])


def test_lower_surgeon_category_does_not_downgrade_stronger_validated_abt_evidence():
    eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
    eye.update({"I_S": 0.5, "inferior_opposite_steepening_D": 0.75, "asymmetric_bow_tie": "YES"})
    p = lasik_plan()
    p["surgeon_topography_category"] = "NORMAL_SYMMETRIC"
    result = core.assess_eye(eye, p, 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "ASYMMETRIC_BOWTIE"
    assert result["randleman_erss"]["rows"]["topography"] == 1


def test_manual_confirmation_survives_existing_effective_plan_normalization():
    p = lasik_plan()
    p.update({"surgeon_I_S_D": -0.61, "surgeon_topography_category": "NORMAL_SYMMETRIC"})
    effective = core.apply_extracted_corrections({"treatment_corrections": []}, {"OD": p, "OS": {}})
    assert effective["OD"]["surgeon_I_S_D"] == -0.61
    assert effective["OD"]["surgeon_topography_category"] == "NORMAL_SYMMETRIC"


def test_inferior_steepening_takes_one_three_point_category_not_abt_plus_three():
    eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
    eye.update({
        "I_S": 0.8,
        "inferior_opposite_steepening_D": 1.0,
        "srax_deg": 20.0,
        "asymmetric_bow_tie": "YES",
        "srax": "YES",
        "erss_source_read": "DEDICATED_CURVATURE_PASS",
    })
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "INFERIOR_STEEPENING_SRA"
    assert result["randleman_erss"]["rows"]["topography"] == 3


def test_surgeon_confirmation_enters_existing_scorer_without_new_point_path():
    eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    p = lasik_plan()
    p.update({"surgeon_I_S_D": -0.61, "surgeon_topography_category": "ASYMMETRIC_BOWTIE"})
    result = core.assess_eye(eye, p, 30, MODIFIERS)
    assert result["erss_topography_evidence"]["I_S_source"] == "SURGEON_ENTRY"
    assert result["erss_topography_evidence"]["validated_category"] == "ASYMMETRIC_BOWTIE"
    assert result["randleman_erss"]["rows"]["topography"] == 1


def test_i_s_at_abnormal_threshold_uses_one_four_point_category():
    eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
    eye["I_S"] = 1.4
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "ABNORMAL_ECTATIC"
    assert result["randleman_erss"]["rows"]["topography"] == 4
