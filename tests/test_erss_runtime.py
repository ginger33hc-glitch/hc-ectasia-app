"""Regression tests for numeric-only Randleman/ERSS topography handling."""
import unittest

import canonical_engine

core = canonical_engine.core


def eye(role_visible, morphology, source):
    """Backward-compatible extraction fixture used by reconciliation tests.

    Visual morphology fields remain in the schema for compatibility only and do
    not participate in current ERSS scoring.
    """
    return {
        "eye": "OD",
        "screen_types": [source],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": [],
        "map_fallback_numeric_fields": [],
        "keratometry_source": "NOT_SHOWN",
        "K1_D": None,
        "K1_axis_deg": None,
        "K2_D": None,
        "K2_axis_deg": None,
        "Kmax_D": None,
        "pachy_thinnest_um": None,
        "BAD_D": None,
        "Df": None,
        "Db": None,
        "Dp": None,
        "Dt": None,
        "Da": None,
        "PPI_avg": None,
        "PPI_min": None,
        "PPI_max": None,
        "ARTmax_um": None,
        "ISV": None,
        "IVA": None,
        "KI": None,
        "CKI": None,
        "IHD": None,
        "I_S": None,
        "KISA": None,
        "IHA": None,
        "Rmin_mm": None,
        "corneal_diameter_mm": None,
        "anterior_elevation_thinnest_um": None,
        "posterior_elevation_thinnest_um": None,
        "thinnest_x_mm": None,
        "thinnest_y_mm": None,
        "corneal_volume_mm3": None,
        "RMS_HOA_um": None,
        "vertical_coma_um": None,
        "Kmean_D": None,
        "total_RMS_um": None,
        "spherical_aberration_um": None,
        "topographic_astig_D": None,
        "morphology": morphology,
        "morphology_confidence": "HIGH" if role_visible else "UNREADABLE",
        "morphology_evidence": [source],
        "asymmetric_bow_tie": "YES" if morphology == "ASYMMETRIC_BOWTIE" else "NO",
        "srax": "YES" if morphology == "INFERIOR_STEEPENING_SRA" else "NO",
        "srax_deg": None,
        "inferior_opposite_steepening_D": None,
        "anterior_pattern": "UNREADABLE",
        "posterior_pattern": "UNREADABLE",
        "_source_filename": source,
        "_pentacam_qs": "OK",
    }


def result(e, filename):
    return {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "patient_id": "1",
            "patient_last_name": "X",
            "patient_first_name": "Y",
            "patient_name": "Y X",
            "patient_name_source": "PENTACAM_FIRST_LAST_NAME_FIELDS",
            "patient_age_years": 30,
            "exam_date": "2026-08-27",
            "exam_time": "10:00",
            "laterality": "OD",
            "pentacam_qs": "OK",
            "missing_or_unreadable": [],
            "source_filename": filename,
        },
        "eyes": [e],
        "treatment_corrections": [],
        "laser_plans": [],
        "global_warnings": [],
    }


def numeric_eye(i_s=None, kisa=None, kmax=None, astig=None):
    verified = []
    values = {
        "I_S": i_s,
        "KISA": kisa,
        "Kmax_D": kmax,
        "topographic_astig_D": astig,
    }
    for key, value in values.items():
        if value is not None:
            verified.append(key)
    return {
        **values,
        "I_S_status": "CONFIDENT" if i_s is not None else "NOT_SHOWN",
        "table_verified_numeric_fields": verified,
        "data_conflicts": [],
        "field_provenance": {key: [{"source": "TEST"}] for key in verified},
        "_erss_i_s_gate_required": True,
        # Deliberately alarming visual fields: numeric policy must ignore them.
        "morphology": "ABNORMAL_ECTATIC",
        "morphology_confidence": "HIGH",
        "morphology_evidence": ["visual morphology must be ignored"],
        "asymmetric_bow_tie": "YES",
        "srax": "YES",
        "srax_deg": 45.0,
        "inferior_opposite_steepening_D": 3.0,
    }


class TestERSSCanonicalEngine(unittest.TestCase):
    def test_runtime_invariants(self):
        self.assertTrue(canonical_engine.runtime_invariants())

    def test_i_s_normal_band_scores_zero_despite_visual_abnormal_label(self):
        scored = core.scoring_morphology(numeric_eye(i_s=0.0, kisa=1.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "NORMAL_SYMMETRIC")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 0)

    def test_i_s_positive_abt_scores_one(self):
        scored = core.scoring_morphology(numeric_eye(i_s=0.8, kisa=1.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "ASYMMETRIC_BOWTIE")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 1)

    def test_negative_i_s_has_no_lower_boundary_for_abt(self):
        scored = core.scoring_morphology(numeric_eye(i_s=-5.0, kisa=1.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "ASYMMETRIC_BOWTIE")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 1)

    def test_i_s_inferior_steepening_band_scores_three(self):
        scored = core.scoring_morphology(numeric_eye(i_s=1.2, kisa=1.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "INFERIOR_STEEPENING_SRA")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 3)

    def test_i_s_at_1_40_is_abnormal_four_point_category(self):
        scored = core.scoring_morphology(numeric_eye(i_s=1.40, kisa=1.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "ABNORMAL_ECTATIC")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 4)

    def test_original_randleman_srax_at_20_or_above_scores_three(self):
        scored = core.scoring_morphology(numeric_eye(i_s=0.5, kisa=10.0, kmax=47.0, astig=1.0))
        self.assertGreaterEqual(scored["derived_srax_deg"], 20.0)
        self.assertEqual(scored["category"], "INFERIOR_STEEPENING_SRA")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 3)

    def test_higher_numeric_category_wins_without_addition(self):
        scored = core.scoring_morphology(numeric_eye(i_s=0.8, kisa=10.0, kmax=47.0, astig=1.0))
        self.assertEqual(scored["category"], "INFERIOR_STEEPENING_SRA")
        self.assertEqual(core.lasik_topography_points(scored["category"]), 3)

    def test_visual_category_without_signed_i_s_is_not_scored(self):
        scored = core.scoring_morphology(numeric_eye())
        self.assertEqual(scored["category"], "UNCERTAIN")
        self.assertEqual(scored["category_source"], "UNRESOLVED_NUMERIC_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
