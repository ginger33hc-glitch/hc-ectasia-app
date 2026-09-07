import ps3_extraction_policy as ps3_extract


def _base_merged():
    return {
        "document_context": {},
        "eyes": [{
            "eye": "OD",
            "table_verified_numeric_fields": [],
            "data_conflicts": [
                "posterior_elevation_thinnest_um: 7 vs 12",
                "anterior_elevation_thinnest_um: 3 vs 6",
            ],
            "field_provenance": {},
        }],
        "critical_input_issues": [],
        "global_warnings": [],
    }


def test_f_and_b_ele_th_are_owned_only_by_bad_display():
    previous = ps3_extract._previous_merge_extractions
    ps3_extract._previous_merge_extractions = lambda results: _base_merged()
    try:
        results = [
            {
                "document_context": {"document_type": "PENTACAM_TOPOGRAPHY"},
                "eyes": [{
                    "eye": "OD",
                    "screen_types": ["FOUR_MAPS_REFRACTIVE"],
                    "F_Ele_Th_um": 99,
                    "table_verified_numeric_fields": ["F_Ele_Th_um"],
                }],
                "nice_readings": [],
            },
            {
                "document_context": {"document_type": "PENTACAM_TOPOGRAPHY"},
                "eyes": [{
                    "eye": "OD",
                    "screen_types": ["BELIN_AMBROSIO_DISPLAY"],
                    "F_Ele_Th_um": 7,
                    "table_verified_numeric_fields": ["F_Ele_Th_um"],
                }],
                "nice_readings": [{
                    "eye": "OD",
                    "B_Ele_Th_um": 12,
                    "b_ele_th_status": "CONFIDENT",
                    "b_ele_th_landmark": "B_ELE_TH_LABELED_BOX",
                    "b_ele_th_page": "BAD_DISPLAY",
                }],
            },
        ]
        merged = ps3_extract.merge_extractions_with_new_fields(results)
        eye = merged["eyes"][0]
        assert eye["F_Ele_Th_um"] == 7
        assert eye["B_Ele_Th_um"] == 12
        assert not any("posterior_elevation_thinnest_um" in x for x in eye["data_conflicts"])
        assert not any("anterior_elevation_thinnest_um" in x for x in eye["data_conflicts"])
    finally:
        ps3_extract._previous_merge_extractions = previous
