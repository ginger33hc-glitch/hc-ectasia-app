from types import SimpleNamespace

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
    merged = {"critical_input_issues": [CONFLICT]}
    result = policy.reconcile_merged_exam_date_conflict(merged, [
        four_maps("2026-09-02", "OD"),
        extraction("2026-09-03", "SHOW_2_EXAMS_TOPOMETRIC", eye="OD"),
    ])
    assert result["critical_input_issues"] == []


def test_bad_display_date_is_ignored_completely():
    merged = {"critical_input_issues": [CONFLICT]}
    result = policy.reconcile_merged_exam_date_conflict(merged, [
        four_maps("2026-09-02", "OD"),
        extraction("2026-09-03", "BAD_DISPLAY", eye="OD"),
    ])
    assert result["critical_input_issues"] == []


def test_other_pentacam_dates_do_not_hide_true_four_maps_conflict():
    merged = {"critical_input_issues": [CONFLICT]}
    result = policy.reconcile_merged_exam_date_conflict(merged, [
        four_maps("2026-09-02", "OD"),
        four_maps("2026-09-03", "OS"),
        extraction("2026-09-02", "BAD_DISPLAY", eye="OD"),
        extraction("2026-09-02", "SHOW_2_EXAMS_TOPOMETRIC", eye="OS"),
    ])
    assert result["critical_input_issues"] == [CONFLICT]


def test_wrapper_removes_false_conflict_from_non_four_maps_sources_and_preserves_raw_dates():
    core = SimpleNamespace()

    def base_merge(extractions):
        return {
            "critical_input_issues": [CONFLICT, "another issue"],
            "source_dates": [item["document_context"]["exam_date"] for item in extractions],
        }

    core.merge_extractions = base_merge
    policy._previous_merge_extractions = None
    policy.install(core)
    inputs = [
        four_maps("2026-09-02", "OD"),
        extraction("03.09.2026", "BAD_DISPLAY", eye="OD"),
    ]
    merged = core.merge_extractions(inputs)
    assert merged["critical_input_issues"] == ["another issue"]
    assert merged["source_dates"] == ["2026-09-02", "03.09.2026"]


def test_wrapper_keeps_true_four_maps_exam_date_conflict():
    def base_merge(extractions):
        return {"critical_input_issues": [CONFLICT]}

    policy._previous_merge_extractions = base_merge
    merged = policy.merge_extractions_with_exam_date_reconciliation([
        four_maps("2026-09-02", "OD"),
        four_maps("2026-09-03", "OS"),
    ])
    assert merged["critical_input_issues"] == [CONFLICT]
