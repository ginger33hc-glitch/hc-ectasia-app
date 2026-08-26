import json
import struct
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader


def normal_eye(eye="OD", pachy=560, morphology="NORMAL_SYMMETRIC"):
    return {
        "eye": eye,
        "screen_types": ["4 Maps", "BAD Display"],
        "quality": "ADEQUATE",
        "pentacam_qs": "OK",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": list(app.TABLE_NUMERIC_FIELDS),
        "map_fallback_numeric_fields": [],
        "K1_D": 42.0,
        "K2_D": 43.0,
        "Kmax_D": 44.0,
        "pachy_thinnest_um": pachy,
        "BAD_D": 1.0,
        "Df": 1.0,
        "Db": 1.0,
        "Dp": 1.0,
        "Dt": -0.5,
        "Da": 0.2,
        "PPI_avg": 0.9,
        "PPI_min": 0.7,
        "PPI_max": 1.1,
        "ARTmax_um": 500,
        "ISV": 20,
        "IVA": 0.1,
        "KI": 1.0,
        "CKI": 1.0,
        "IHD": 0.01,
        "I_S": 0.5,
        "KISA": 10,
        "IHA": 2.0,
        "Rmin_mm": 7.6,
        "anterior_elevation_thinnest_um": 2.0,
        "posterior_elevation_thinnest_um": 4.0,
        "thinnest_x_mm": 0.2,
        "thinnest_y_mm": -0.3,
        "corneal_volume_mm3": 60.0,
        "RMS_HOA_um": 0.2,
        "vertical_coma_um": 0.05,
        "Kmean_D": 42.5,
        "total_RMS_um": 0.3,
        "spherical_aberration_um": 0.1,
        "morphology": morphology,
        "morphology_evidence": ["Visible symmetric bowtie"],
        "asymmetric_bow_tie": "NO",
        "srax": "NO",
        "srax_deg": 0,
        "inferior_opposite_steepening_D": 0,
        "anterior_pattern": "REASSURING",
        "posterior_pattern": "REASSURING",
    }


def plan(procedure="PRK", sphere=-3.0, cylinder=0.0, ablation=60, flap=None):
    return {
        "prior": "no",
        "procedure": procedure,
        "manifest_sphere_D": sphere,
        "manifest_cylinder_magnitude_D": cylinder,
        "intended_sphere_D": sphere,
        "intended_cylinder_magnitude_D": cylinder,
        "ablation_um": ablation,
        "flap_um": flap,
        "laser_platform": "Alcon EX500",
        "optical_zone_mm": 6.0,
        "transition_zone_mm": None,
        "transition_zone_not_applicable": "yes",
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
        "enhancement_anticipated": "no",
    }


def card_correction(
    eye="OD", sphere=-4.5, cylinder=-3.5, axis=170,
    sphere_cylinder_status="CONFIDENT", axis_status="CONFIDENT",
):
    return {
        "eye": eye,
        "source_document": "EXCIMER_LASER_FOLLOW_UP_CARD",
        "source_label": "DUZELTME_MIKTARI",
        "sphere_D": sphere,
        "cylinder_D": cylinder,
        "axis_deg": axis,
        "sphere_cylinder_status": sphere_cylinder_status,
        "axis_status": axis_status,
        "raw_text": f"{sphere} ({cylinder} x {axis})",
        "missing_or_unreadable": [],
    }


MODIFIERS = {
    "eye_rubbing": "no",
    "family_history": "no",
    "inter_eye_asymmetry": "no",
    "pregnancy_nursing": "no",
    "collagen_tissue_disease": "no",
    "drug_usage": "no",
    "dry_eye": "no",
    "systemic_disease": "no",
    "contact_lens_type": "NONE",
    "contact_lens_discontinuation_days": None,
    "assessed_eyes": ["OD"],
}


def document_context(patient_id="HC-1", dob="2000-01-01", exam_date="2026-08-25", qs="OK"):
    return {
        "document_type": "PENTACAM_TOPOGRAPHY", "patient_id": patient_id,
        "patient_name": "Test Patient", "date_of_birth": dob, "exam_date": exam_date,
        "exam_time": "10:00", "laterality": "BOTH", "pentacam_qs": qs,
        "missing_or_unreadable": [], "source_filename": "pentacam.png",
    }


class TestSafetyGates(unittest.TestCase):
    def test_prior_surgery_short_circuits_virgin_engine_even_if_thin(self):
        prior_plan = plan()
        prior_plan["prior"] = "yes"
        result = app.assess_eye(normal_eye(pachy=430), prior_plan, 35, MODIFIERS)
        self.assertEqual(result["status"], "POST-REFRACTIVE PATHWAY REQUIRED")
        self.assertEqual(result["score"]["rows"], {})
        self.assertEqual(result["hard_stops"], [])

    def test_hc_sphere_hard_stops_and_exact_boundaries(self):
        minus_11 = app.assess_eye(normal_eye(), plan(sphere=-11), 35, MODIFIERS)
        minus_10 = app.assess_eye(normal_eye(), plan(sphere=-10), 35, MODIFIERS)
        plus_7 = app.assess_eye(normal_eye(), plan(sphere=7), 35, MODIFIERS)
        plus_6 = app.assess_eye(normal_eye(), plan(sphere=6), 35, MODIFIERS)
        self.assertTrue(any("<−10.00" in item for item in minus_11["hard_stops"]))
        self.assertFalse(any("<−10.00" in item for item in minus_10["hard_stops"]))
        self.assertTrue(any(">+6.00" in item for item in plus_7["hard_stops"]))
        self.assertFalse(any(">+6.00" in item for item in plus_6["hard_stops"]))

    def test_manifest_refraction_not_intended_plan_drives_lasik_mrse(self):
        p = plan("LASIK", sphere=-9, cylinder=2, ablation=70, flap=100)
        p["manifest_sphere_D"] = -1
        p["manifest_cylinder_magnitude_D"] = 0
        result = app.assess_eye(normal_eye(), p, 35, MODIFIERS)
        self.assertEqual(result["values"]["MRSE_D"], -1)
        self.assertEqual(result["score"]["rows"]["MRSE"], 0)

    def test_negative_ablation_is_rejected_and_not_used(self):
        result = app.assess_eye(normal_eye(), plan(ablation=-50), 35, MODIFIERS)
        self.assertIsNone(result["values"]["max_ablation_um"])
        self.assertIsNone(result["values"]["PRK_RST_um"])
        self.assertNotEqual(result["status"], "PASS")

    def test_i_s_merge_does_not_create_definite_disease_override(self):
        eye = normal_eye()
        eye["I_S"] = 1.4
        merged = app.merge_extractions([{"eyes": [eye], "treatment_corrections": [], "global_warnings": []}])
        self.assertEqual(merged["eyes"][0]["morphology"], "NORMAL_SYMMETRIC")
        result = app.assess_eye(merged["eyes"][0], plan("LASIK", ablation=60, flap=100), 35, MODIFIERS)
        self.assertEqual(result["topography_classification"]["scoring_category"], "ABNORMAL_ECTATIC")
        self.assertFalse(any("Definite KC" in item for item in result["hard_stops"]))

    def test_single_eye_never_yields_overall_pass(self):
        extracted = {"eyes": [normal_eye("OD")], "global_warnings": []}
        result = app.hc_engine(extracted, 35, {"OD": plan()}, MODIFIERS)
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
        self.assertTrue(any("Both OD and OS" in item for item in result["critical_input_issues"]))

    def test_identity_date_conflicts_and_non_ok_qs_are_global_blockers(self):
        first = {"document_context": document_context("A", qs="OK"), "eyes": [normal_eye("OD")], "treatment_corrections": [], "global_warnings": []}
        second_context = document_context("B", exam_date="2026-08-26", qs="NOT_OK")
        second_context["source_filename"] = "other.png"
        second = {"document_context": second_context, "eyes": [normal_eye("OS")], "treatment_corrections": [], "global_warnings": []}
        merged = app.merge_extractions([first, second])
        self.assertTrue(any("Conflicting patient IDs" in item for item in merged["critical_input_issues"]))
        self.assertTrue(any("Conflicting Pentacam" in item for item in merged["critical_input_issues"]))
        self.assertTrue(any("non-OK QS" in item for item in merged["critical_input_issues"]))

    def test_clinical_eligibility_modifier_blocks_pass_without_score_points(self):
        modifiers = dict(MODIFIERS, pregnancy_nursing="yes")
        result = app.assess_eye(normal_eye(), plan(), 35, modifiers)
        self.assertEqual(result["status"], "CAUTION — STOP/DEFER")
        self.assertEqual(result["score"]["total"], 0)


class TestBoundaries(unittest.TestCase):
    def test_bad_display_boundaries(self):
        self.assertEqual(app.bad_classification(1.6, final=True), "NORMAL")
        self.assertEqual(app.bad_classification(1.6001, final=True), "SUSPICIOUS")
        self.assertEqual(app.bad_classification(3.0, final=True), "ABNORMAL")
        self.assertEqual(app.bad_classification(1.6), "SUSPICIOUS")
        self.assertEqual(app.bad_classification(2.6), "ABNORMAL")

    def test_prk_cct_480_not_hard_stop_but_scores_caution(self):
        result = app.assess_eye(normal_eye(pachy=480), plan(ablation=120), 35, MODIFIERS)
        self.assertEqual(result["values"]["PRK_RST_um"], 310)
        self.assertEqual(result["score"]["total"], 3)
        self.assertEqual(result["status"], "CAUTION — STOP/DEFER")
        self.assertEqual(result["hard_stops"], [])

    def test_prk_cct_479_is_hard_stop_even_with_other_missing_data(self):
        eye = normal_eye(pachy=479)
        eye["BAD_D"] = None
        result = app.assess_eye(eye, plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "DO NOT PROCEED")
        self.assertTrue(any("<480" in item for item in result["hard_stops"]))
        self.assertIn("BAD_D", result["missing"])

    def test_prk_rst_310_allowed_by_structural_rule(self):
        result = app.assess_eye(normal_eye(pachy=520), plan(ablation=160), 35, MODIFIERS)
        self.assertEqual(result["values"]["PRK_epithelium_um"], 50)
        self.assertEqual(result["values"]["PRK_RST_um"], 310)
        self.assertFalse(any("RST" in item for item in result["hard_stops"]))

    def test_prk_rst_below_310_is_hard_stop(self):
        result = app.assess_eye(normal_eye(pachy=520), plan(ablation=161), 35, MODIFIERS)
        self.assertEqual(result["status"], "DO NOT PROCEED")
        self.assertTrue(any("RST <310" in item for item in result["hard_stops"]))

    def test_lasik_rsb_300_allowed_and_299_stopped(self):
        allowed = app.assess_eye(
            normal_eye(pachy=520), plan("LASIK", ablation=120, flap=100), 35, MODIFIERS
        )
        stopped = app.assess_eye(
            normal_eye(pachy=520), plan("LASIK", ablation=121, flap=100), 35, MODIFIERS
        )
        self.assertEqual(allowed["values"]["LASIK_RSB_um"], 300)
        self.assertFalse(any("RSB <300" in item for item in allowed["hard_stops"]))
        self.assertEqual(stopped["values"]["LASIK_RSB_um"], 299)
        self.assertTrue(any("RSB <300" in item for item in stopped["hard_stops"]))

    def test_lasik_exact_510_boundary_is_not_silently_scored(self):
        result = app.assess_eye(
            normal_eye(pachy=510), plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertIsNone(result["score"]["rows"]["pachymetry"])
        self.assertNotEqual(result["status"], "PASS")
        self.assertTrue(any("510" in item for item in result["missing"]))

    def test_i_s_1_4_uses_published_erss_abnormal_pattern_without_disease_override(self):
        eye = normal_eye()
        eye["I_S"] = 1.4
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "ABNORMAL_ECTATIC")
        self.assertEqual(result["score"]["rows"]["topography"], 4)
        self.assertEqual(result["status"], "DO NOT PROCEED")
        self.assertFalse(any("Definite KC" in item for item in result["hard_stops"]))

    def test_srax_20_degrees_uses_published_erss_sra_category(self):
        eye = normal_eye()
        eye["srax"] = "UNCERTAIN"
        eye["srax_deg"] = 20
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "INFERIOR_STEEPENING_SRA")
        self.assertEqual(result["score"]["rows"]["topography"], 3)
        self.assertEqual(result["status"], "CAUTION — STOP/DEFER")

    def test_minimal_axis_deviation_is_not_scored_as_srax(self):
        eye = normal_eye()
        eye["morphology"] = "INFERIOR_STEEPENING_SRA"
        eye["srax"] = "YES"
        eye["srax_deg"] = 5
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "UNCERTAIN")
        self.assertIsNone(result["score"]["rows"]["topography"])
        self.assertNotEqual(result["status"], "PASS")

    def test_srax_below_20_degrees_is_not_scored(self):
        eye = normal_eye()
        eye["morphology"] = "INFERIOR_STEEPENING_SRA"
        eye["srax"] = "YES"
        eye["srax_deg"] = 19.9
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "UNCERTAIN")
        self.assertNotEqual(result["status"], "PASS")

    def test_unquantified_visual_srax_label_is_not_scored(self):
        eye = normal_eye()
        eye["morphology"] = "INFERIOR_STEEPENING_SRA"
        eye["srax"] = "YES"
        eye["srax_deg"] = None
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "UNCERTAIN")
        self.assertNotEqual(result["status"], "PASS")

    def test_quantified_inferior_steepening_alternative_uses_published_category(self):
        eye = normal_eye()
        eye["morphology"] = "UNCERTAIN"
        eye["I_S"] = 1.3
        eye["inferior_opposite_steepening_D"] = 1.0
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "INFERIOR_STEEPENING_SRA")
        self.assertEqual(result["score"]["rows"]["topography"], 3)

    def test_definite_ectatic_morphology_is_not_downgraded_by_srax_fields(self):
        eye = normal_eye(morphology="ABNORMAL_ECTATIC")
        eye["srax"] = "YES"
        eye["srax_deg"] = 5
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-3, ablation=100, flap=100), 35, MODIFIERS
        )
        self.assertEqual(result["topography_classification"]["scoring_category"], "ABNORMAL_ECTATIC")
        self.assertEqual(result["status"], "DO NOT PROCEED")

    def test_ablation_estimate_uses_zone_specific_ex500_conventions(self):
        zone_6 = plan(ablation=None)
        zone_65 = dict(zone_6, optical_zone_mm=6.5)
        zone_7 = dict(zone_6, optical_zone_mm=7.0)
        other_platform = dict(zone_65, laser_platform="Other platform")

        zone_6_result = app.assess_eye(normal_eye(), zone_6, 35, MODIFIERS)
        zone_65_result = app.assess_eye(normal_eye(), zone_65, 35, MODIFIERS)
        zone_7_result = app.assess_eye(normal_eye(), zone_7, 35, MODIFIERS)
        other_platform_result = app.assess_eye(normal_eye(), other_platform, 35, MODIFIERS)

        self.assertEqual(zone_6_result["values"]["max_ablation_um"], 36.0)
        self.assertEqual(zone_65_result["values"]["max_ablation_um"], 45.0)
        self.assertAlmostEqual(zone_7_result["values"]["max_ablation_um"], 48.99)
        self.assertIn("15 µm/D", zone_65_result["warnings"][0])
        self.assertIn("16.33 µm/D", zone_7_result["warnings"][0])
        self.assertIsNone(other_platform_result["values"]["max_ablation_um"])
        self.assertEqual(other_platform_result["status"], "DATA INSUFFICIENT")

    def test_hyperopic_plan_requires_actual_ablation_and_review(self):
        estimated = app.assess_eye(normal_eye(), plan(sphere=2.0, cylinder=0.0, ablation=None), 35, MODIFIERS)
        actual = app.assess_eye(normal_eye(), plan(sphere=2.0, cylinder=0.0, ablation=40), 35, MODIFIERS)
        self.assertIsNone(estimated["values"]["max_ablation_um"])
        self.assertNotEqual(estimated["status"], "PASS")
        self.assertEqual(actual["status"], "REVIEW — NOT CLEARED")
        self.assertFalse(any("treatment cutoff" in item for item in actual["hard_stops"]))


class TestScoringAndCompleteness(unittest.TestCase):
    def test_extraction_contract_prioritizes_labeled_pentacam_numeric_fields(self):
        eye_schema = app.SCHEMA["properties"]["eyes"]["items"]
        self.assertIn("table_verified_numeric_fields", eye_schema["required"])
        self.assertIn("map_fallback_numeric_fields", eye_schema["required"])
        self.assertIn("PENTACAM NUMERIC-SOURCE RULE", app.PROMPT)
        self.assertIn("Never substitute a map spot value", app.PROMPT)
        self.assertIn("Only the categorical fields", app.PROMPT)

    def test_reassuring_prk_can_pass(self):
        result = app.assess_eye(normal_eye(), plan(), 35, MODIFIERS)
        self.assertEqual(result["score"]["total"], 0)
        self.assertEqual(result["status"], "PASS")

    def test_lasik_erss_moderate_means_stop_defer(self):
        eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
        eye["asymmetric_bow_tie"] = "YES"
        eye["inferior_opposite_steepening_D"] = 0.7
        result = app.assess_eye(
            eye, plan("LASIK", sphere=-8.5, cylinder=1.0, ablation=100, flap=100), 28, MODIFIERS
        )
        self.assertEqual(result["score"]["total"], 3)
        self.assertEqual(result["status"], "CAUTION — STOP/DEFER")
        self.assertIn("at least 6 months", result["action"])

    def test_missing_critical_tomography_prohibits_pass(self):
        eye = normal_eye()
        eye["ARTmax_um"] = None
        result = app.assess_eye(eye, plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
        self.assertIn("ARTmax_um", result["missing"])

    def test_prk_pta_outside_cohort_envelope_is_labeled_not_recast_as_validated_cutoff(self):
        result = app.assess_eye(normal_eye(pachy=560), plan(ablation=150), 35, MODIFIERS)
        self.assertGreater(result["values"]["PRK_PTA_percent"], 35.28)
        self.assertTrue(any("evidence-gap" in item for item in result["surgical_load_flags"]))
        self.assertEqual(result["status"], "REVIEW — NOT CLEARED")

    def test_concordant_cross_sectional_tomography_flags_prohibit_pass(self):
        eye = normal_eye(pachy=530)
        eye.update(ARTmax_um=400, Dt=-0.10, Da=0.70)
        result = app.assess_eye(eye, plan(), 35, MODIFIERS)
        self.assertEqual(result["tomography_review"]["status"], "CONCERN FLAGS")
        self.assertEqual(len(result["tomography_review"]["cross_sectional_flags"]), 4)
        self.assertEqual(result["status"], "REVIEW — NOT CLEARED")

    def test_limited_image_quality_prohibits_pass(self):
        eye = normal_eye()
        eye["quality"] = "LIMITED"
        result = app.assess_eye(eye, plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
        self.assertIn("adequate-quality tomography/topography", result["missing"])

    def test_unreadable_anterior_map_prohibits_pass(self):
        eye = normal_eye()
        eye["anterior_pattern"] = "UNREADABLE"
        result = app.assess_eye(eye, plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
        self.assertIn("readable anterior pattern", result["missing"])

    def test_added_patient_modifiers_are_reported_without_invented_score_weights(self):
        modifiers = dict(
            MODIFIERS,
            pregnancy_nursing="yes",
            collagen_tissue_disease="yes",
            drug_usage="yes",
        )
        result = app.assess_eye(normal_eye(), plan(), 35, modifiers)
        self.assertEqual(result["status"], "CAUTION — STOP/DEFER")
        self.assertTrue(any("Pregnancy or nursing" in item for item in result["clinical_modifiers"]))
        self.assertTrue(any("Collagen/connective-tissue" in item for item in result["clinical_modifiers"]))
        self.assertTrue(any("medication/drug" in item for item in result["clinical_modifiers"]))

    def test_conflicting_i_s_values_use_concerning_value_and_prohibit_pass(self):
        first = normal_eye()
        second = normal_eye()
        first["I_S"] = 0.5
        second["I_S"] = 1.6
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        self.assertEqual(merged["eyes"][0]["I_S"], 1.6)
        self.assertTrue(any(item.startswith("I_S:") for item in merged["eyes"][0]["data_conflicts"]))
        result = app.assess_eye(merged["eyes"][0], plan(), 35, MODIFIERS)
        self.assertNotEqual(result["status"], "PASS")

    def test_minor_keratometry_ocr_variation_is_not_an_unresolved_conflict(self):
        first = normal_eye()
        second = normal_eye()
        first["K2_D"] = 46.8
        second["K2_D"] = 46.6
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        self.assertEqual(merged["eyes"][0]["K2_D"], 46.8)
        self.assertFalse(any("K2_D" in item for item in merged["eyes"][0]["data_conflicts"]))
        result = app.assess_eye(merged["eyes"][0], plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "PASS")

    def test_unverified_map_spot_number_is_not_accepted_as_a_table_parameter(self):
        eye = normal_eye()
        eye["K2_D"] = 46.6
        eye["table_verified_numeric_fields"].remove("K2_D")
        merged = app.merge_extractions([{"eyes": [eye], "global_warnings": []}])
        extracted = merged["eyes"][0]
        self.assertIsNone(extracted["K2_D"])
        self.assertIn("K2_D", extracted["missing_or_unreadable"])
        self.assertEqual(extracted["morphology"], "NORMAL_SYMMETRIC")

    def test_labeled_side_table_number_is_retained(self):
        eye = normal_eye()
        eye["K2_D"] = 46.8
        merged = app.merge_extractions([{"eyes": [eye], "global_warnings": []}])
        self.assertEqual(merged["eyes"][0]["K2_D"], 46.8)

    def test_same_measurement_local_map_fallback_is_accepted_when_table_is_unreadable(self):
        eye = normal_eye(pachy=566)
        eye["table_verified_numeric_fields"].remove("pachy_thinnest_um")
        eye["map_fallback_numeric_fields"] = ["pachy_thinnest_um"]
        merged = app.merge_extractions([{"eyes": [eye], "global_warnings": []}])
        extracted = merged["eyes"][0]
        self.assertEqual(extracted["pachy_thinnest_um"], 566)
        self.assertEqual(extracted["map_fallback_numeric_fields"], ["pachy_thinnest_um"])

    def test_map_spot_cannot_substitute_for_k2_even_when_model_labels_it_as_fallback(self):
        eye = normal_eye()
        eye["K2_D"] = 46.6
        eye["table_verified_numeric_fields"].remove("K2_D")
        eye["map_fallback_numeric_fields"] = ["K2_D"]
        merged = app.merge_extractions([{"eyes": [eye], "global_warnings": []}])
        extracted = merged["eyes"][0]
        self.assertIsNone(extracted["K2_D"])
        self.assertNotIn("K2_D", extracted["map_fallback_numeric_fields"])

    def test_later_labeled_table_value_overrides_earlier_local_map_fallback_without_conflict(self):
        map_eye = normal_eye(pachy=565)
        map_eye["table_verified_numeric_fields"].remove("pachy_thinnest_um")
        map_eye["map_fallback_numeric_fields"] = ["pachy_thinnest_um"]
        table_eye = normal_eye(pachy=566)
        merged = app.merge_extractions(
            [{"eyes": [map_eye], "global_warnings": []}, {"eyes": [table_eye], "global_warnings": []}]
        )
        extracted = merged["eyes"][0]
        self.assertEqual(extracted["pachy_thinnest_um"], 566)
        self.assertNotIn("pachy_thinnest_um", extracted["map_fallback_numeric_fields"])
        self.assertFalse(any("pachy_thinnest_um" in item for item in extracted["data_conflicts"]))

    def test_table_verified_field_lists_are_unioned_without_conflict(self):
        first = normal_eye()
        second = normal_eye()
        first["table_verified_numeric_fields"] = ["K1_D"]
        second["table_verified_numeric_fields"] = ["K2_D"]
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        eye = merged["eyes"][0]
        self.assertEqual(eye["table_verified_numeric_fields"], ["K1_D", "K2_D"])
        self.assertEqual(eye["K1_D"], 42.0)
        self.assertEqual(eye["K2_D"], 43.0)
        self.assertFalse(any("table_verified" in item for item in eye["data_conflicts"]))

    def test_material_keratometry_difference_remains_a_conflict(self):
        first = normal_eye()
        second = normal_eye()
        second["K2_D"] = 43.3
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        self.assertTrue(any("K2_D" in item for item in merged["eyes"][0]["data_conflicts"]))

    def test_uncertain_or_unreadable_page_does_not_conflict_with_readable_page(self):
        readable = normal_eye()
        limited = normal_eye()
        limited.update(
            morphology="UNCERTAIN",
            asymmetric_bow_tie="UNCERTAIN",
            srax="UNCERTAIN",
            anterior_pattern="UNREADABLE",
            posterior_pattern="UNREADABLE",
        )
        merged = app.merge_extractions(
            [{"eyes": [readable], "global_warnings": []}, {"eyes": [limited], "global_warnings": []}]
        )
        eye = merged["eyes"][0]
        self.assertEqual(eye["morphology"], "NORMAL_SYMMETRIC")
        self.assertEqual(eye["posterior_pattern"], "REASSURING")
        self.assertEqual(eye["data_conflicts"], [])

    def test_unsupported_asymmetric_bowtie_label_does_not_override_supported_normal_map(self):
        normal = normal_eye()
        unsupported = normal_eye(morphology="ASYMMETRIC_BOWTIE")
        unsupported["asymmetric_bow_tie"] = "YES"
        unsupported["inferior_opposite_steepening_D"] = None
        merged = app.merge_extractions(
            [{"eyes": [normal], "global_warnings": []}, {"eyes": [unsupported], "global_warnings": []}]
        )
        eye = merged["eyes"][0]
        self.assertEqual(eye["morphology"], "NORMAL_SYMMETRIC")
        self.assertFalse(any("morphology" in item for item in eye["data_conflicts"]))

    def test_bilateral_engine_keeps_eyes_separate_and_overall_is_worst(self):
        extracted = {"eyes": [normal_eye("OD", 560), normal_eye("OS", 479)], "global_warnings": []}
        modifiers = dict(MODIFIERS, assessed_eyes=["OD", "OS"])
        decision = app.hc_engine(
            extracted, 35, {"OD": plan(), "OS": plan()}, modifiers
        )
        self.assertEqual([r["eye"] for r in decision["eyes"]], ["OD", "OS"])
        self.assertEqual(decision["eyes"][0]["status"], "PASS")
        self.assertEqual(decision["eyes"][1]["status"], "DO NOT PROCEED")
        self.assertEqual(decision["status"], "DO NOT PROCEED")

    def test_merge_clears_missing_when_later_image_supplies_value(self):
        first = normal_eye()
        first["BAD_D"] = None
        first["missing_or_unreadable"] = ["BAD_D"]
        second = normal_eye()
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        self.assertEqual(merged["eyes"][0]["BAD_D"], 1.0)
        self.assertNotIn("BAD_D", merged["eyes"][0]["missing_or_unreadable"])


class TestTreatmentCardTransfer(unittest.TestCase):
    def test_confident_card_fills_empty_plan_and_drives_zone_specific_ablation(self):
        extracted = {
            "eyes": [normal_eye()],
            "treatment_corrections": [card_correction()],
            "global_warnings": [],
        }
        empty = plan(sphere=None, cylinder=None, ablation=None)
        empty["optical_zone_mm"] = 6.5
        effective = app.apply_extracted_corrections(extracted, {"OD": empty})
        self.assertEqual(effective["OD"]["intended_sphere_D"], -4.5)
        self.assertEqual(effective["OD"]["intended_cylinder_magnitude_D"], 3.5)
        self.assertEqual(effective["OD"]["correction_axis_deg"], 170.0)
        self.assertIn("Duzeltme Miktari", effective["OD"]["correction_source"])
        result = app.assess_eye(normal_eye(), effective["OD"], 35, MODIFIERS)
        self.assertEqual(result["values"]["max_ablation_um"], 120.0)

    def test_manual_pair_wins_when_card_differs(self):
        extracted = {"treatment_corrections": [card_correction()]}
        effective = app.apply_extracted_corrections(extracted, {"OD": plan(sphere=-2, cylinder=1)})
        self.assertEqual(effective["OD"]["intended_sphere_D"], -2)
        self.assertEqual(effective["OD"]["intended_cylinder_magnitude_D"], 1)
        self.assertNotIn("correction_source", effective["OD"])
        self.assertTrue(any("manual correction differs" in item for item in effective["OD"]["correction_warnings"]))

    def test_partial_manual_pair_is_never_mixed_with_card(self):
        partial = plan(sphere=-2, cylinder=None)
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [card_correction()]}, {"OD": partial}
        )
        self.assertEqual(effective["OD"]["intended_sphere_D"], -2)
        self.assertIsNone(effective["OD"]["intended_cylinder_magnitude_D"])
        self.assertTrue(any("partial manual correction" in item for item in effective["OD"]["correction_warnings"]))

    def test_uncertain_axis_keeps_confident_sphere_and_cylinder_only(self):
        correction = card_correction(axis=None, axis_status="UNCERTAIN")
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [correction]},
            {"OD": plan(sphere=None, cylinder=None)},
        )
        self.assertEqual(effective["OD"]["intended_sphere_D"], -4.5)
        self.assertEqual(effective["OD"]["intended_cylinder_magnitude_D"], 3.5)
        self.assertNotIn("correction_axis_deg", effective["OD"])
        self.assertTrue(any("axis was not confidently readable" in item for item in effective["OD"]["correction_warnings"]))

    def test_uncertain_or_conflicting_values_do_not_auto_fill(self):
        uncertain = card_correction(
            sphere=None, cylinder=None, sphere_cylinder_status="UNCERTAIN"
        )
        conflicting = card_correction(sphere=-3.5, cylinder=-3.0, axis=3)
        empty = plan(sphere=None, cylinder=None)
        uncertain_result = app.apply_extracted_corrections(
            {"treatment_corrections": [uncertain]}, {"OD": empty}
        )
        conflict_result = app.apply_extracted_corrections(
            {"treatment_corrections": [card_correction(), conflicting]}, {"OD": empty}
        )
        self.assertIsNone(uncertain_result["OD"]["intended_sphere_D"])
        self.assertIsNone(conflict_result["OD"]["intended_sphere_D"])
        self.assertTrue(any("Conflicting" in item for item in conflict_result["OD"]["correction_warnings"]))

    def test_plus_cylinder_is_not_transposed_or_auto_filled(self):
        plus = card_correction(cylinder=3.5)
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [plus]},
            {"OD": plan(sphere=None, cylinder=None)},
        )
        self.assertIsNone(effective["OD"]["intended_sphere_D"])
        self.assertIsNone(effective["OD"]["intended_cylinder_magnitude_D"])
        self.assertTrue(any("plus-cylinder" in item for item in effective["OD"]["correction_warnings"]))

    def test_unknown_eye_from_card_image_is_not_assessed(self):
        unknown = normal_eye("UNKNOWN")
        extracted = {
            "eyes": [normal_eye(), unknown],
            "treatment_corrections": [card_correction()],
            "global_warnings": [],
        }
        effective = app.apply_extracted_corrections(
            extracted, {"OD": plan(sphere=None, cylinder=None)}
        )
        decision = app.hc_engine(extracted, 35, effective, MODIFIERS)
        self.assertEqual([eye["eye"] for eye in decision["eyes"]], ["OD"])

    def test_merge_keeps_and_deduplicates_card_readings(self):
        correction = card_correction()
        merged = app.merge_extractions([
            {"eyes": [normal_eye()], "treatment_corrections": [correction], "global_warnings": []},
            {"eyes": [], "treatment_corrections": [correction], "global_warnings": []},
        ])
        self.assertEqual(merged["treatment_corrections"], [correction])


class TestApiIntegration(unittest.TestCase):
    def test_analyze_endpoint_accepts_eye_specific_payload(self):
        extraction = {
            "eyes": [normal_eye()],
            "treatment_corrections": [card_correction()],
            "global_warnings": [],
        }
        fake_response = SimpleNamespace(
            output_text=json.dumps(extraction), status="completed", incomplete_details=None
        )
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(create=lambda **kwargs: fake_response)
        )
        client = TestClient(app.app)
        with patch.object(app, "openai_client", return_value=fake_client):
            response = client.post(
                "/analyze",
                files={"images": ("od.png", b"synthetic-image-bytes", "image/png")},
                data={
                    "age": "35",
                    "eye_plans": json.dumps({"OD": plan(sphere=None, cylinder=None, ablation=None)}),
                    "patient_modifiers": json.dumps(MODIFIERS),
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"]["status"], "DATA INSUFFICIENT")
        self.assertTrue(any("Both OD and OS" in item for item in payload["decision"]["critical_input_issues"]))
        self.assertEqual(payload["decision"]["eyes"][0]["eye"], "OD")
        self.assertEqual(payload["effective_eye_plans"]["OD"]["intended_sphere_D"], -4.5)
        self.assertEqual(payload["decision"]["eyes"][0]["values"]["correction_axis_deg"], 170.0)

    def test_professional_pdf_and_word_exports_are_valid(self):
        extracted = {"eyes": [normal_eye()], "global_warnings": []}
        decision = app.hc_engine(extracted, 35, {"OD": plan()}, MODIFIERS)
        payload = {
            "patient": {
                "name": "Test Patient", "id": "HC-001", "age": 35,
                "reviewer": "Test Reviewer", "report_date": "2026-08-25",
            },
            "decision": decision,
            "extracted": extracted,
        }
        client = TestClient(app.app)
        pdf = client.post("/report/pdf", json=payload)
        word = client.post("/report/word", json=payload)
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertGreaterEqual(len(PdfReader(BytesIO(pdf.content)).pages), 1)
        self.assertEqual(word.status_code, 200)
        self.assertIn("wordprocessingml.document", word.headers["content-type"])
        document = Document(BytesIO(word.content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("HC PREOPERATIVE ECTASIA RISK ASSESSMENT", text)
        self.assertIn("PASS", text)


class TestPwaIcons(unittest.TestCase):
    def test_icon_files_are_real_pngs_with_declared_dimensions(self):
        expected = {
            "icon-192.png": (192, 192),
            "icon-512.png": (512, 512),
            "icon-maskable-512.png": (512, 512),
        }
        icon_dir = Path(__file__).resolve().parents[1] / "static" / "icons"
        for filename, dimensions in expected.items():
            raw = (icon_dir / filename).read_bytes()
            self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(raw[12:16], b"IHDR")
            self.assertEqual(struct.unpack(">II", raw[16:24]), dimensions)

    def test_manifest_and_html_use_cache_busted_png_assets(self):
        static_dir = Path(__file__).resolve().parents[1] / "static"
        manifest = json.loads((static_dir / "manifest.webmanifest").read_text())
        self.assertEqual({icon["src"] for icon in manifest["icons"]}, {
            "/static/icons/icon-192.png?v=4",
            "/static/icons/icon-512.png?v=4",
            "/static/icons/icon-maskable-512.png?v=4",
        })
        html = (static_dir / "index.html").read_text()
        self.assertIn('/static/manifest.webmanifest?v=5', html)
        self.assertIn('/static/icons/favicon-32.png?v=4', html)
        self.assertIn('/static/icons/apple-touch-icon.png?v=4', html)
        self.assertNotIn('/static/icons/icon-source.svg', html)


class TestPwaShareTarget(unittest.TestCase):
    def test_manifest_accepts_one_or_multiple_shared_images(self):
        static_dir = Path(__file__).resolve().parents[1] / "static"
        manifest = json.loads((static_dir / "manifest.webmanifest").read_text())
        target = manifest["share_target"]
        self.assertEqual(target["action"], "/share-target")
        self.assertEqual(target["method"], "POST")
        self.assertEqual(target["enctype"], "multipart/form-data")
        self.assertEqual(target["params"]["files"], [{"name": "images", "accept": ["image/*"]}])

    def test_root_scoped_service_worker_is_served_without_caching(self):
        response = TestClient(app.app).get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/javascript", response.headers["content-type"])
        self.assertEqual(response.headers["service-worker-allowed"], "/")
        self.assertEqual(response.headers["cache-control"], "no-cache, no-store, must-revalidate")
        self.assertIn('url.pathname===SHARE_PATH', response.text)

    def test_frontend_loads_shared_files_into_existing_analyze_request(self):
        static_dir = Path(__file__).resolve().parents[1] / "static"
        html = (static_dir / "index.html").read_text()
        self.assertIn('id="imageInput" name="images"', html)
        self.assertIn('params.get("share_token")', html)
        self.assertIn('images.forEach(file=>fd.append("images",file,file.name))', html)
        self.assertIn('navigator.serviceWorker.register("/sw.js",{scope:"/"})', html)


class TestAnalyzeLoadingStateUi(unittest.TestCase):
    def test_loading_message_paints_before_network_request_and_validation_is_visible(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertIn('<form id="f" novalidate>', html)
        self.assertIn('id="analysisProgress"', html)
        self.assertIn('role="status" aria-live="polite"', html)
        self.assertIn('analyzeBtn.textContent="Analyzing images... Please wait"', html)
        self.assertIn('showFormMessage("Analyzing images... Please wait.")', html)
        self.assertIn("await allowLoadingStateToPaint()", html)
        self.assertLess(html.index("await allowLoadingStateToPaint()"), html.index('fetch("/analyze"'))
        self.assertIn("f.reportValidity()", html)
        self.assertIn('showFormMessage(`Analysis failed:', html)


class TestPatientModifierUi(unittest.TestCase):
    def test_single_dropdown_contains_all_multi_select_modifier_options(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertEqual(html.count('id="modifierDropdown"'), 1)
        for value in (
            "eye_rubbing", "family_history", "inter_eye_asymmetry",
            "pregnancy_nursing", "collagen_tissue_disease", "drug_usage",
        ):
            self.assertIn(f'name="patient_modifier" value="{value}"', html)
        self.assertNotIn('id="eye_rubbing"', html)
        self.assertNotIn('id="family_history"', html)
        self.assertNotIn('id="inter_eye_asymmetry"', html)
        self.assertIn('value="none" data-exclusive="true"', html)
        self.assertIn('value="unknown" data-exclusive="true"', html)

    def test_none_closes_dropdown_but_regular_multi_select_items_do_not(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertIn('if(input.checked&&input.value==="none")modifierDropdown.open=false;', html)
        self.assertNotIn('if(input.checked)modifierDropdown.open=false;', html)


class TestFixedLaserPlatformUi(unittest.TestCase):
    def test_each_eye_keeps_a_read_only_alcon_ex500_box(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertIn(
            'id="${eye}_platform" type="text" value="Alcon EX500" readonly aria-readonly="true"',
            html,
        )
        self.assertIn('laser_platform:"Alcon EX500"', html)
        self.assertNotIn('placeholder="e.g., Alcon EX500"', html)


class TestLasikFlapDropdownUi(unittest.TestCase):
    def test_flap_field_is_a_dropdown_with_only_hc_options(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        expected = (
            '<select id="${eye}_flap"><option value="">Select</option>'
            '<option value="90">90 µm</option><option value="100">100 µm</option>'
            '<option value="110">110 µm</option><option value="120">120 µm</option></select>'
        )
        self.assertIn(expected, html)
        self.assertNotIn('id="${eye}_flap" type="number"', html)


class TestFixedPrkEpitheliumUi(unittest.TestCase):
    def test_each_eye_has_a_read_only_50_micron_prk_epithelium_box(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertIn(
            'id="${eye}_epithelium" type="text" value="50" readonly aria-readonly="true"',
            html,
        )
        self.assertIn("epithelium_um:50", html)


class TestZoneDropdownUi(unittest.TestCase):
    def test_zone_fields_use_only_the_requested_dropdown_options(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        optical = (
            '<select id="${eye}_optical"><option value="">Select</option>'
            '<option value="6.0">6.0 mm</option><option value="6.5">6.5 mm</option>'
            '<option value="7.0">7.0 mm</option></select>'
        )
        transition = (
            '<select id="${eye}_transition"><option value="">Select</option>'
            '<option value="8.0">8.0 mm</option><option value="8.5">8.5 mm</option>'
            '<option value="9.0">9.0 mm</option></select>'
        )
        self.assertIn(optical, html)
        self.assertIn(transition, html)
        self.assertNotIn('id="${eye}_transition_na"', html)
        self.assertIn('transition_zone_not_applicable:"no"', html)


class TestPriorSurgeryDefaultUi(unittest.TestCase):
    def test_prior_surgery_defaults_to_no_and_yes_remains_selectable(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        expected = (
            '<select id="${eye}_prior"><option value="no" selected>No</option>'
            '<option value="yes">Yes</option><option value="unknown">Unknown</option></select>'
        )
        self.assertIn(expected, html)


class TestClinicalEligibilityGroupUi(unittest.TestCase):
    def test_four_eye_specific_clinical_controls_share_one_collapsible_box(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        self.assertIn(
            'id="${eye}_clinical" class="clinical-select-group">\n'
            '    <summary>Clinical eligibility and stability</summary>',
            html,
        )
        group_start = html.index('id="${eye}_clinical"')
        group_end = html.index('</details>`;', group_start)
        group = html[group_start:group_end]
        for field in ("stable", "progression", "cdva", "enhancement"):
            self.assertEqual(group.count(f'id="${{eye}}_{field}"'), 1)
        self.assertIn(
            'id="${eye}_stable"><option value="yes" selected>Yes</option>'
            '<option value="no">No</option><option value="unknown">Unknown</option>',
            group,
        )
        for field in ("progression", "cdva", "enhancement"):
            self.assertIn(
                f'id="${{eye}}_{field}"><option value="no" selected>No</option>'
                '<option value="yes">Yes</option><option value="unknown">Unknown</option>',
                group,
            )


class TestLiabilityNoticeUi(unittest.TestCase):
    def test_top_input_box_contains_the_red_surgeon_liability_notice(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
        notice = (
            '<p class="liability-notice">Final decision and liability always rests on the surgeon, '
            'this app is only an aid tool.</p>'
        )
        self.assertIn(notice, html)
        self.assertIn('.liability-notice{color:#a31212;', html)


if __name__ == "__main__":
    unittest.main()
