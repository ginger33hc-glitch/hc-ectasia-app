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


def test_browser_form_carries_only_numeric_i_s_confirmation_for_erss():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert '${eye}_surgeon_i_s' in html
    assert 'surgeon_I_S_D:numberOrNull' in html


def test_missing_i_s_requires_numeric_confirmation_and_never_visual_category():
    eye = normal_eye()
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["randleman_erss"]["rows"]["topography"] is None
    assert result["randleman_erss"]["total"] is None
    assert result["erss_topography_evidence"]["needs_surgeon_I_S"] is True
    assert "needs_surgeon_category" not in result["erss_topography_evidence"]
    assert "PASS" not in result["status"]


def test_high_confidence_visual_map_cannot_complete_erss_without_i_s():
    eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
    eye.update({
        "I_S": None,
        "morphology_confidence": "HIGH",
        "anterior_curvature_map_visible": "YES",
        "erss_source_read": "DEDICATED_CURVATURE_PASS",
        "inferior_opposite_steepening_D": 1.2,
        "srax": "YES",
        "srax_deg": 30.0,
    })
    eye["table_verified_numeric_fields"].remove("I_S")
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["randleman_erss"]["rows"]["topography"] is None
    assert result["erss_topography_evidence"]["validated_category"] == "UNCERTAIN"
    assert result["erss_topography_evidence"]["category_source"] == "UNRESOLVED_NUMERIC_EVIDENCE"


def test_lasik_i_s_gate_does_not_change_the_separate_prk_pathway():
    eye = normal_eye()
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    result = core.assess_eye(
        eye,
        plan("PRK", sphere=-3.0, cylinder=0.0, ablation=60, flap=None),
        30,
        MODIFIERS,
    )
    assert "erss_topography_evidence" not in result
    assert not any("I-S value for Randleman" in str(item) for item in result.get("missing") or [])


def test_conflicting_i_s_is_not_resolved_by_scoring_the_maximum():
    eye = normal_eye()
    eye["data_conflicts"] = ["I_S: 0.50 vs 1.50"]
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["I_S_status"] == "CONFLICT"
    assert result["randleman_erss"]["rows"]["topography"] is None
    assert result["randleman_erss"]["total"] is None


def test_canonical_i_s_normal_band_ignores_visual_abnormal_fields():
    eye = normal_eye(morphology="ABNORMAL_ECTATIC")
    eye.update({
        "I_S": 0.5,
        "inferior_opposite_steepening_D": 2.0,
        "asymmetric_bow_tie": "YES",
        "srax": "YES",
        "srax_deg": 40.0,
    })
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "NORMAL_SYMMETRIC"
    assert result["erss_topography_evidence"]["category_source"] == "CANONICAL_SIGNED_I_S"
    assert result["randleman_erss"]["rows"]["topography"] == 0


def test_manual_i_s_confirmation_survives_effective_plan_normalization():
    p = lasik_plan()
    p.update({"surgeon_I_S_D": -0.61})
    effective = core.apply_extracted_corrections({"treatment_corrections": []}, {"OD": p, "OS": {}})
    assert effective["OD"]["surgeon_I_S_D"] == -0.61


def test_canonical_i_s_abt_band_is_not_upgraded_by_legacy_visual_srax_fields():
    eye = normal_eye(morphology="ABNORMAL_ECTATIC")
    eye.update({
        "I_S": 0.8,
        "inferior_opposite_steepening_D": 2.0,
        "srax_deg": 40.0,
        "asymmetric_bow_tie": "YES",
        "srax": "YES",
        "erss_source_read": "DEDICATED_CURVATURE_PASS",
        "KISA": 1.0,
        "Kmax_D": 47.0,
        "topographic_astig_D": 1.0,
    })
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "ASYMMETRIC_BOWTIE"
    assert result["erss_topography_evidence"]["category_source"] == "CANONICAL_SIGNED_I_S"
    assert result["randleman_erss"]["rows"]["topography"] == 1


def test_surgeon_i_s_confirmation_enters_existing_scorer_without_new_point_path():
    eye = normal_eye(morphology="ABNORMAL_ECTATIC")
    eye["I_S"] = None
    eye["table_verified_numeric_fields"].remove("I_S")
    p = lasik_plan()
    p.update({"surgeon_I_S_D": -0.61})
    result = core.assess_eye(eye, p, 30, MODIFIERS)
    assert result["erss_topography_evidence"]["I_S_source"] == "SURGEON_ENTRY"
    assert result["erss_topography_evidence"]["validated_category"] == "ASYMMETRIC_BOWTIE"
    assert result["randleman_erss"]["rows"]["topography"] == 1


def test_i_s_at_abnormal_threshold_uses_one_four_point_category():
    eye = normal_eye(morphology="NORMAL_SYMMETRIC")
    eye["I_S"] = 1.4
    result = core.assess_eye(eye, lasik_plan(), 30, MODIFIERS)
    assert result["erss_topography_evidence"]["validated_category"] == "ABNORMAL_ECTATIC"
    assert result["randleman_erss"]["rows"]["topography"] == 4


def test_all_five_lasik_erss_parameter_boundaries_are_locked():
    assert [core.lasik_rsb_points(x) for x in (239.999, 240, 260, 280, 300)] == [4, 3, 2, 1, 0]
    assert [core.age_points(x) for x in (18, 19, 20, 21, 30)] == [3, 2, 2, 0, 0]
    assert [core.lasik_pachy_points(x) for x in (479.999, 480, 499.999, 500, 509.999, 510)] == [None, 2, 2, 1, 1, 0]
    assert [core.lasik_mrse_points(x) for x in (-14.001, -14, -12, -10, -8)] == [4, 3, 2, 1, 0]
    assert [core.lasik_topography_points(x) for x in (
        "NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA", "ABNORMAL_ECTATIC"
    )] == [0, 1, 3, 4]


def test_complete_erss_rows_use_manifest_mrse_and_planned_rsb():
    eye = normal_eye(pachy=520, morphology="ABNORMAL_ECTATIC")
    eye.update({
        "I_S": 0.0,
        "KISA": 1.0,
        "Kmax_D": 47.0,
        "topographic_astig_D": 1.0,
    })
    p = lasik_plan()
    p.update({
        "manifest_sphere_D": -9.0,
        "manifest_cylinder_magnitude_D": 2.0,
        "manifest_normalized_axis_deg": 180,
        "flap_um": 100,
        "ablation_um": 140,
    })
    result = core.assess_eye(eye, p, 20, MODIFIERS)
    erss = result["randleman_erss"]
    assert result["values"]["MRSE_D"] == -10.0
    assert result["lasik_planning_sequence"][0]["LASIK_RSB_um"] == 280.0
    assert result["values"]["LASIK_RSB_um"] == 384.0
    assert erss["rows"] == {"topography": 0, "RSB": 0, "age": 2, "pachymetry": 0, "MRSE": 1}
    assert erss["total"] == 3
    assert erss["bad_dependency"] is False
