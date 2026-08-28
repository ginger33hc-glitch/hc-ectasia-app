"""Regression tests for the production runtime patch chain, not bare app.py."""
import unittest
import pachymetry_policy  # loads the same chain used by start.py
import bootstrap

core=bootstrap.core


def eye(role_visible, morphology, source):
    return {
        "eye":"OD","screen_types":[source],"quality":"ADEQUATE","missing_or_unreadable":[],
        "table_verified_numeric_fields":[],"map_fallback_numeric_fields":[],
        "K1_D":None,"K2_D":None,"Kmax_D":None,"pachy_thinnest_um":None,"BAD_D":None,"Df":None,"Db":None,"Dp":None,"Dt":None,"Da":None,
        "PPI_avg":None,"PPI_min":None,"PPI_max":None,"ARTmax_um":None,"ISV":None,"IVA":None,"KI":None,"CKI":None,"IHD":None,"I_S":None,"KISA":None,"IHA":None,"Rmin_mm":None,
        "anterior_elevation_thinnest_um":None,"posterior_elevation_thinnest_um":None,"thinnest_x_mm":None,"thinnest_y_mm":None,"corneal_volume_mm3":None,"RMS_HOA_um":None,"vertical_coma_um":None,"Kmean_D":None,"total_RMS_um":None,"spherical_aberration_um":None,
        "morphology":morphology,"morphology_evidence":[source],"asymmetric_bow_tie":"NO","srax":"NO","srax_deg":0 if role_visible else None,"inferior_opposite_steepening_D":0 if role_visible else None,
        "anterior_pattern":"UNREADABLE","posterior_pattern":"UNREADABLE",
        "anterior_curvature_map_visible":"YES" if role_visible else "NO",
        "anterior_curvature_map_type":"AXIAL_SAGITTAL_FRONT" if role_visible else "NONE",
        "anterior_curvature_map_location":"UPPER_LEFT" if role_visible else "NONE",
        "_source_filename":source,"_pentacam_qs":"OK",
    }

def result(e,filename):
    return {"document_context":{"document_type":"PENTACAM_TOPOGRAPHY","patient_id":"1","patient_last_name":"X","patient_first_name":"Y","patient_name":"Y X","patient_name_source":"PENTACAM_FIRST_LAST_NAME_FIELDS","patient_age_years":30,"exam_date":"2026-08-27","exam_time":"10:00","laterality":"OD","pentacam_qs":"OK","missing_or_unreadable":[],"source_filename":filename},"eyes":[e],"treatment_corrections":[],"laser_plans":[],"global_warnings":[]}

class TestERSSProductionChain(unittest.TestCase):
    def test_bad_no_does_not_override_4maps_yes(self):
        bad=eye(False,"UNCERTAIN","bad.jpg")
        maps=eye(True,"NORMAL_SYMMETRIC","4maps.jpg")
        maps["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        merged=core.merge_extractions([result(bad,"bad.jpg"),result(maps,"4maps.jpg")])
        od=merged["eyes"][0]
        self.assertEqual(od["anterior_curvature_map_visible"],"YES")
        self.assertEqual(od["anterior_curvature_map_type"],"AXIAL_SAGITTAL_FRONT")
        self.assertEqual(od["anterior_curvature_map_location"],"UPPER_LEFT")
        self.assertTrue(od["erss_topography_sources"])

    def test_map_role_fields_never_become_conflicts(self):
        merged=core.merge_extractions([result(eye(False,"UNCERTAIN","bad.jpg"),"bad.jpg"),result(eye(True,"NORMAL_SYMMETRIC","4maps.jpg"),"4maps.jpg")])
        conflicts=merged["eyes"][0].get("data_conflicts",[])
        self.assertFalse(any("anterior_curvature_map" in str(x) for x in conflicts))

if __name__=="__main__": unittest.main()
