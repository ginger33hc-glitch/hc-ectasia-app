"""Regression tests for the production runtime patch chain, not bare app.py."""
import unittest
import pachymetry_policy
import bootstrap

core=bootstrap.core

def eye(role_visible,morphology,source):
    return {"eye":"OD","screen_types":[source],"quality":"ADEQUATE","missing_or_unreadable":[],"table_verified_numeric_fields":[],"map_fallback_numeric_fields":[],"K1_D":None,"K2_D":None,"Kmax_D":None,"pachy_thinnest_um":None,"BAD_D":None,"Df":None,"Db":None,"Dp":None,"Dt":None,"Da":None,"PPI_avg":None,"PPI_min":None,"PPI_max":None,"ARTmax_um":None,"ISV":None,"IVA":None,"KI":None,"CKI":None,"IHD":None,"I_S":None,"KISA":None,"IHA":None,"Rmin_mm":None,"anterior_elevation_thinnest_um":None,"posterior_elevation_thinnest_um":None,"thinnest_x_mm":None,"thinnest_y_mm":None,"corneal_volume_mm3":None,"RMS_HOA_um":None,"vertical_coma_um":None,"Kmean_D":None,"total_RMS_um":None,"spherical_aberration_um":None,"morphology":morphology,"morphology_evidence":[source],"asymmetric_bow_tie":"YES" if morphology=="ASYMMETRIC_BOWTIE" else "NO","srax":"YES" if morphology=="INFERIOR_STEEPENING_SRA" else "NO","srax_deg":None,"inferior_opposite_steepening_D":None,"anterior_pattern":"UNREADABLE","posterior_pattern":"UNREADABLE","anterior_curvature_map_visible":"YES" if role_visible else "NO","anterior_curvature_map_type":"AXIAL_SAGITTAL_FRONT" if role_visible else "NONE","anterior_curvature_map_location":"UPPER_LEFT" if role_visible else "NONE","_source_filename":source,"_pentacam_qs":"OK"}

def result(e,filename):
    return {"document_context":{"document_type":"PENTACAM_TOPOGRAPHY","patient_id":"1","patient_last_name":"X","patient_first_name":"Y","patient_name":"Y X","patient_name_source":"PENTACAM_FIRST_LAST_NAME_FIELDS","patient_age_years":30,"exam_date":"2026-08-27","exam_time":"10:00","laterality":"OD","pentacam_qs":"OK","missing_or_unreadable":[],"source_filename":filename},"eyes":[e],"treatment_corrections":[],"laser_plans":[],"global_warnings":[]}

class TestERSSProductionChain(unittest.TestCase):
    def test_bad_no_does_not_override_4maps_yes(self):
        bad=eye(False,"UNCERTAIN","bad.jpg");maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg");maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        od=core.merge_extractions([result(bad,"bad.jpg"),result(maps,"4maps.jpg")])["eyes"][0]
        self.assertEqual((od["anterior_curvature_map_visible"],od["anterior_curvature_map_type"],od["anterior_curvature_map_location"]),("YES","AXIAL_SAGITTAL_FRONT","UPPER_LEFT"));self.assertTrue(od["erss_topography_sources"])

    def test_map_role_fields_never_become_conflicts(self):
        merged=core.merge_extractions([result(eye(False,"UNCERTAIN","bad.jpg"),"bad.jpg"),result(eye(True,"NORMAL_SYMMETRIC","4maps.jpg"),"4maps.jpg")])
        self.assertFalse(any("anterior_curvature_map" in str(x) for x in merged["eyes"][0].get("data_conflicts",[])))

    def test_dedicated_asymmetric_category_reaches_randleman_points(self):
        maps=eye(True,"ASYMMETRIC_BOWTIE","4maps.jpg");maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0]
        scored=core.scoring_morphology(od)
        self.assertEqual(scored["category"],"ASYMMETRIC_BOWTIE");self.assertEqual(core.lasik_topography_points(scored["category"]),1)

    def test_dedicated_srax_category_reaches_randleman_points(self):
        maps=eye(True,"INFERIOR_STEEPENING_SRA","4maps.jpg");maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        od=core.merge_extractions([result(maps,"4maps.jpg")])["eyes"][0]
        scored=core.scoring_morphology(od)
        self.assertEqual(scored["category"],"INFERIOR_STEEPENING_SRA");self.assertEqual(core.lasik_topography_points(scored["category"]),3)

    def test_conflicting_dedicated_morphologies_become_uncertain(self):
        a=eye(True,"NORMAL_SYMMETRIC","a.jpg");b=eye(True,"ASYMMETRIC_BOWTIE","b.jpg");a["erss_source_read"]=b["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        od=core.merge_extractions([result(a,"a.jpg"),result(b,"b.jpg")])["eyes"][0]
        self.assertEqual(od["morphology"],"UNCERTAIN")

if __name__=="__main__": unittest.main()
