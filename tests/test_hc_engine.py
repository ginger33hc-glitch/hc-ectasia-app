import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from fastapi.testclient import TestClient


def normal_eye(eye="OD", pachy=560, morphology="NORMAL_SYMMETRIC"):
    return {
        "eye": eye,
        "screen_types": ["4 Maps", "BAD Display"],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
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
        "PPI_max": 1.1,
        "ARTmax_um": 500,
        "ISV": 20,
        "IVA": 0.1,
        "KI": 1.0,
        "CKI": 1.0,
        "IHD": 0.01,
        "I_S": 0.5,
        "KISA": 10,
        "morphology": morphology,
        "morphology_evidence": ["Visible symmetric bowtie"],
        "asymmetric_bow_tie": "NO",
        "srax": "NO",
        "srax_deg": 0,
        "posterior_pattern": "REASSURING",
    }


def plan(procedure="PRK", sphere=-3.0, cylinder=0.0, ablation=60, flap=None):
    return {
        "prior": "no",
        "procedure": procedure,
        "sphere_D": sphere,
        "cylinder_magnitude_D": cylinder,
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


MODIFIERS = {
    "eye_rubbing": "no",
    "family_history": "no",
    "inter_eye_asymmetry": "no",
    "assessed_eyes": ["OD"],
}


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
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
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

    def test_ablation_estimate_is_limited_to_ex500_at_6_mm(self):
        eligible = plan(ablation=None)
        ineligible = dict(eligible, laser_platform="Other platform")
        eligible_result = app.assess_eye(normal_eye(), eligible, 35, MODIFIERS)
        ineligible_result = app.assess_eye(normal_eye(), ineligible, 35, MODIFIERS)
        self.assertEqual(eligible_result["values"]["max_ablation_um"], 36.0)
        self.assertIsNone(ineligible_result["values"]["max_ablation_um"])
        self.assertEqual(ineligible_result["status"], "DATA INSUFFICIENT")


class TestScoringAndCompleteness(unittest.TestCase):
    def test_reassuring_prk_can_pass(self):
        result = app.assess_eye(normal_eye(), plan(), 35, MODIFIERS)
        self.assertEqual(result["score"]["total"], 0)
        self.assertEqual(result["status"], "PASS")

    def test_lasik_erss_moderate_means_stop_defer(self):
        eye = normal_eye(morphology="ASYMMETRIC_BOWTIE")
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


class TestApiIntegration(unittest.TestCase):
    def test_analyze_endpoint_accepts_eye_specific_payload(self):
        extraction = {"eyes": [normal_eye()], "global_warnings": []}
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
                    "eye_plans": json.dumps({"OD": plan()}),
                    "patient_modifiers": json.dumps(MODIFIERS),
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"]["status"], "PASS")
        self.assertEqual(payload["decision"]["eyes"][0]["eye"], "OD")


if __name__ == "__main__":
    unittest.main()
