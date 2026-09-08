import exam_date_reconciliation_policy as policy


CONFLICT = "Conflicting Pentacam examination dates across uploaded sources."


def extraction(date_value, screen_type=None, eye="OD"):
    result = {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "exam_date": date_value,
        },
        "eyes": [],
    }
    if screen_type:
        result["eyes"] = [{"eye": eye, "screen_types": [screen_type]}]
    return result


def four_maps(date_value, eye="OD"):
    return extraction(date_value, "FOUR_MAPS_REFRACTIVE", eye=eye)


def test_same_calendar_date_different_unambiguous_formats_is_consistent():
    assert policy.dates_are_semantically_consistent([
        four_maps("2026-09-02", "OD"),
        four_maps("02.09.2026", "OS"),
    ])


def test_same_calendar_date_with_ambiguous_slash_format_is_consistent_only_by_common_date():
    assert policy.dates_are_semantically_consistent([
        four_maps("2026-09-02", "OD"),
        four_maps("09/02/2026", "OS"),
    ])


def test_true_different_four_maps_dates_remain_conflicting():
    assert not policy.dates_are_semantically_consistent([
        four_maps("2026-09-02", "OD"),
        four_maps("2026-09-03", "OS"),
    ])


def test_unparseable_four_maps_date_never_suppresses_conflict():
    assert not policy.dates_are_semantically_consistent([
        four_maps("2026-09-02", "OD"),
        four_maps("Sept 2 2026?", "OS"),
    ])


def test_show_2_exams_topometric_date_is_ignored_completely():
    assert not policy.authoritative_exam_date_conflict([
        four_maps("2026-09-02", "OD"),
        extraction("2026-09-03", "SHOW_2_EXAMS_TOPOMETRIC", eye="OD"),
    ])


def test_bad_display_date_is_ignored_completely():
    assert not policy.authoritative_exam_date_conflict([
        four_maps("2026-09-02", "OD"),
        extraction("2026-09-03", "BAD_DISPLAY", eye="OD"),
    ])


def test_other_pentacam_dates_do_not_hide_true_four_maps_conflict():
    assert policy.authoritative_exam_date_conflict([
        four_maps("2026-09-02", "OD"),
        four_maps("2026-09-03", "OS"),
        extraction("2026-09-02", "BAD_DISPLAY", eye="OD"),
        extraction("2026-09-02", "SHOW_2_EXAMS_TOPOMETRIC", eye="OS"),
    ])


def test_authoritative_check_ignores_non_four_maps_dates_and_preserves_inputs():
    inputs = [
        four_maps("2026-09-02", "OD"),
        extraction("03.09.2026", "BAD_DISPLAY", eye="OD"),
    ]
    assert not policy.authoritative_exam_date_conflict(inputs)
    assert [item["document_context"]["exam_date"] for item in inputs] == [
        "2026-09-02", "03.09.2026"
    ]


def test_authoritative_check_keeps_true_four_maps_exam_date_conflict():
    inputs = [
        four_maps("2026-09-02", "OD"),
        four_maps("2026-09-03", "OS"),
    ]
    assert policy.authoritative_exam_date_conflict(inputs)


def test_exam_date_module_exposes_no_install_time_merge_wrapper():
    assert not hasattr(policy, "install")
    assert not hasattr(policy, "merge_extractions_with_exam_date_reconciliation")
    assert not hasattr(policy, "reconcile_merged_exam_date_conflict")
