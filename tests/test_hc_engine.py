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
        "morphology": morphology,
        "morphology_evidence": ["Visible symmetric bowtie"],
        "asymmetric_bow_tie": "NO",
        "srax": "NO",
        "srax_deg": 0,
        "anterior_pattern": "REASSURING",
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
        self.assertEqual(result["status"], "PASS")
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

    def test_noncritical_numeric_conflict_is_unresolved_and_prohibits_pass(self):
        first = normal_eye()
        second = normal_eye()
        second["K1_D"] = 42.25
        merged = app.merge_extractions(
            [{"eyes": [first], "global_warnings": []}, {"eyes": [second], "global_warnings": []}]
        )
        result = app.assess_eye(merged["eyes"][0], plan(), 35, MODIFIERS)
        self.assertEqual(result["status"], "DATA INSUFFICIENT")
        self.assertTrue(any("K1_D" in item for item in result["missing"]))

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
        self.assertEqual(effective["OD"]["sphere_D"], -4.5)
        self.assertEqual(effective["OD"]["cylinder_magnitude_D"], 3.5)
        self.assertEqual(effective["OD"]["correction_axis_deg"], 170.0)
        self.assertIn("Duzeltme Miktari", effective["OD"]["correction_source"])
        result = app.assess_eye(normal_eye(), effective["OD"], 35, MODIFIERS)
        self.assertEqual(result["values"]["max_ablation_um"], 120.0)

    def test_manual_pair_wins_when_card_differs(self):
        extracted = {"treatment_corrections": [card_correction()]}
        effective = app.apply_extracted_corrections(extracted, {"OD": plan(sphere=-2, cylinder=1)})
        self.assertEqual(effective["OD"]["sphere_D"], -2)
        self.assertEqual(effective["OD"]["cylinder_magnitude_D"], 1)
        self.assertNotIn("correction_source", effective["OD"])
        self.assertTrue(any("manual correction differs" in item for item in effective["OD"]["correction_warnings"]))

    def test_partial_manual_pair_is_never_mixed_with_card(self):
        partial = plan(sphere=-2, cylinder=None)
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [card_correction()]}, {"OD": partial}
        )
        self.assertEqual(effective["OD"]["sphere_D"], -2)
        self.assertIsNone(effective["OD"]["cylinder_magnitude_D"])
        self.assertTrue(any("partial manual correction" in item for item in effective["OD"]["correction_warnings"]))

    def test_uncertain_axis_keeps_confident_sphere_and_cylinder_only(self):
        correction = card_correction(axis=None, axis_status="UNCERTAIN")
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [correction]},
            {"OD": plan(sphere=None, cylinder=None)},
        )
        self.assertEqual(effective["OD"]["sphere_D"], -4.5)
        self.assertEqual(effective["OD"]["cylinder_magnitude_D"], 3.5)
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
        self.assertIsNone(uncertain_result["OD"]["sphere_D"])
        self.assertIsNone(conflict_result["OD"]["sphere_D"])
        self.assertTrue(any("Conflicting" in item for item in conflict_result["OD"]["correction_warnings"]))

    def test_plus_cylinder_is_not_transposed_or_auto_filled(self):
        plus = card_correction(cylinder=3.5)
        effective = app.apply_extracted_corrections(
            {"treatment_corrections": [plus]},
            {"OD": plan(sphere=None, cylinder=None)},
        )
        self.assertIsNone(effective["OD"]["sphere_D"])
        self.assertIsNone(effective["OD"]["cylinder_magnitude_D"])
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
        self.assertEqual(payload["decision"]["status"], "PASS")
        self.assertEqual(payload["decision"]["eyes"][0]["eye"], "OD")
        self.assertEqual(payload["effective_eye_plans"]["OD"]["sphere_D"], -4.5)
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

    def test_manifest_and_html_use_cache_busted_v4_png_icons(self):
        static_dir = Path(__file__).resolve().parents[1] / "static"
        manifest = json.loads((static_dir / "manifest.webmanifest").read_text())
        self.assertEqual({icon["src"] for icon in manifest["icons"]}, {
            "/static/icons/icon-192.png?v=4",
            "/static/icons/icon-512.png?v=4",
            "/static/icons/icon-maskable-512.png?v=4",
        })
        html = (static_dir / "index.html").read_text()
        self.assertIn('/static/manifest.webmanifest?v=4', html)
        self.assertIn('/static/icons/favicon-32.png?v=4', html)
        self.assertIn('/static/icons/apple-touch-icon.png?v=4', html)
        self.assertNotIn('/static/icons/icon-source.svg', html)


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
