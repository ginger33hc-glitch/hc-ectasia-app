"""Regression tests against the approved recovery ERSS architecture."""
import unittest
import canonical_engine

core=canonical_engine.core

def eye(role_visible,morphology,source):
    return {"eye":"OD","screen_types":[source],"quality":"ADEQUATE","missing_or_unreadable":[],"table_verified_numeric_fields":[],"map_fallback_numeric_fields":[],"K1_D":None,"K2_D":None,"Kmax_D":None,"pachy_thinnest_um":None,"BAD_D":None,"Df":None,"Db":None,"Dp":None,"Dt":None,"Da":None,"PPI_avg":None,"PPI_min":None,"PPI_max":None,"ARTmax_um":None,"ISV":None,"IVA":None,"KI":None,"CKI":None,"IHD":None,"I_S":None,"KISA":None,"IHA":None,"Rmin_mm":None,"anterior_elevation_thinnest_um":None,"posterior_elevation_thinnest_um":None,"thinnest_x_mm":None,"thinnest_y_mm":None,"corneal_volume_mm3":None,"RMS_HOA_um":None,"vertical_coma_um":None,"Kmean_D":None,"total_RMS_um":None,"spherical_aberration_um":None,"morphology":morphology,"morphology_confidence":"HIGH" if role_visible else "UNREADABLE","morphology_evidence":[source],"asymmetric_bow_tie":"YES" if morphology=="ASYMMETRIC_BOWTIE" else "NO","srax":"YES" if morphology=="INFERIOR_STEEPENING_SRA" else "NO","srax_deg":None,"srax_source":None,"inferior_opposite_steepening_D":None,"anterior_pattern":"UNREADABLE","posterior_pattern":"UNREADABLE","anterior_curvature_map_visible":"YES" if role_visible else "NO","anterior_curvature_map_type":"AXIAL_SAGITTAL_FRONT" if role_visible else "NONE","anterior_curvature_map_location":"UPPER_LEFT" if role_visible else "NONE","_source_filename":source,"_pentacam_qs":"OK"}

def result(e,filename):
    return {"document_context":{"document_type":"PENTACAM_TOPOGRAPHY","patient_id":"1","patient_last_name":"X","patient_first_name":"Y","patient_name":"Y X","patient_name_source":"PENTACAM_FIRST_LAST_NAME_FIELDS","patient_age_years":30,"exam_date":"2026-08-27","exam_time":"10:00","laterality":"OD","pentacam_qs":"OK","missing_or_unreadable":[],"source_filename":filename},"eyes":[e],"treatment_corrections":[],"laser_plans":[],"global_warnings":[]}

def resolve_srax(maps,degrees):
    maps["srax_deg"]=degrees;maps["srax_source"]="AXIAL_SAGITTAL_CURVATURE_FRONT";maps["srax"]="YES" if degrees>20 else "NO"

class TestERSSCanonicalEngine(unittest.TestCase):
    def test_runtime_invariants(self): self.assertTrue(canonical_engine.runtime_invariants())
    def test_bad_no_does_not_override_4maps_yes(self):
        bad=eye(False,"UNCERTAIN","bad.jpg");maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        od=core.merge_extractions([result(bad,"bad.jpg"),result(maps,"4maps.jpg")])["eyes"][0]
        self.assertEqual((od["anterior_curvature_map_visible"],od["anterior_curvature_map_type"],od["anterior_curvature_map_location"]),("YES","AXIAL_SAGITTAL_FRONT","UPPER_LEFT"));self.assertTrue(od["erss_topography_sources"])
    def test_map_role_fields_never_become_conflicts(self):
        merged=core.merge_extractions([result(eye(False,"UNCERTAIN","bad.jpg"),"bad.jpg"),result(eye(True,"NORMAL_SYMMETRIC","4maps.jpg"),"4maps.jpg")])
        self.assertFalse(any("anterior_curvature_map" in str(x) for x in merged["eyes"][0].get("data_conflicts",[])))
    def test_unreadable_and_high_morphology_confidence_are_complementary_sources(self):
        bad=eye(False,"UNCERTAIN","bad.jpg");maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        merged=core.merge_extractions([result(bad,"bad.jpg"),result(maps,"4maps.jpg")]);od=merged["eyes"][0]
        self.assertEqual(od["morphology_confidence"],"HIGH")
        self.assertFalse(any("morphology_confidence" in str(x) for x in od.get("data_conflicts",[])))
    def test_signed_i_s_abt_reaches_randleman_points_when_srax_resolved_negative(self):
        maps=eye(True,"ASYMMETRIC_BOWTIE","4maps.jpg");maps["I_S"]=0.75;maps["table_verified_numeric_fields"]=["I_S"];resolve_srax(maps,10)
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True;scored=core.scoring_morphology(od)
        self.assertEqual(scored["category"],"ASYMMETRIC_BOWTIE");self.assertEqual(core.lasik_topography_points(scored["category"]),1)
    def test_srax_strictly_greater_than_20_reaches_three_points(self):
        maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["I_S"]=0.5;maps["table_verified_numeric_fields"]=["I_S"];resolve_srax(maps,20.1)
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True;scored=core.scoring_morphology(od)
        self.assertEqual(scored["category"],"INFERIOR_STEEPENING_SRA");self.assertEqual(core.lasik_topography_points(scored["category"]),3)
    def test_srax_exactly_20_is_not_positive(self):
        maps=eye(True,"INFERIOR_STEEPENING_SRA","4maps.jpg");maps["I_S"]=0.5;maps["table_verified_numeric_fields"]=["I_S"];resolve_srax(maps,20.0)
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True
        self.assertEqual(core.scoring_morphology(od)["category"],"NORMAL_SYMMETRIC")
    def test_visual_category_without_i_s_is_not_scored(self):
        maps=eye(True,"ASYMMETRIC_BOWTIE","4maps.jpg");resolve_srax(maps,10)
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True
        self.assertEqual(core.scoring_morphology(od)["category"],"UNCERTAIN")
    def test_unresolved_srax_is_not_silently_normal(self):
        maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["I_S"]=0.0;maps["table_verified_numeric_fields"]=["I_S"]
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True
        self.assertEqual(core.scoring_morphology(od)["category"],"UNCERTAIN")
    def test_negative_i_s_below_minus_half_is_abt_without_lower_limit(self):
        maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["I_S"]=-2.0;maps["table_verified_numeric_fields"]=["I_S"];resolve_srax(maps,5)
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0];od["_erss_i_s_gate_required"]=True
        self.assertEqual(core.scoring_morphology(od)["category"],"ASYMMETRIC_BOWTIE")
    def test_conflicting_dedicated_morphologies_do_not_create_generic_merge_conflicts(self):
        a=eye(True,"NORMAL_SYMMETRIC","a.jpg");b=eye(True,"ASYMMETRIC_BOWTIE","b.jpg");a["erss_source_read"]=b["erss_source_read"]="DEDICATED_CURVATURE_PASS";od=core.merge_extractions([result(a,"a.jpg"),result(b,"b.jpg")])["eyes"][0]
        self.assertFalse(any(str(conflict).split(":",1)[0] in {"morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D"} for conflict in od.get("data_conflicts",[])))

if __name__=="__main__": unittest.main()
