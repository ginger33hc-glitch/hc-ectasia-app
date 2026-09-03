"""Regression tests for numeric-only Randleman/ERSS topography handling."""
import unittest

import canonical_engine

core = canonical_engine.core


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
