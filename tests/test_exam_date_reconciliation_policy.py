from types import SimpleNamespace

import exam_date_reconciliation_policy as policy


CONFLICT = "Conflicting Pentacam examination dates across uploaded sources."


def extraction(date_value, screen_type=None):
    result = {
        "document_context": {
            "document_type": "PENTACAM_TOPOGRAPHY",
            "exam_date": date_value,
        },
        "eyes": [],
    }
    if screen_type:
        result["eyes"] = [{"eye": "OD", "screen_types": [screen_type]}]
    return result


def test_same_calendar_date_different_unambiguous_formats_is_consistent():
    assert policy.dates_are_semantically_consistent([
        extraction("2026-09-02"),
        extraction("02.09.2026"),
        extraction("2026/09/02"),
    ])


def test_same_calendar_date_with_ambiguous_slash_format_is_consistent_only_by_common_date():
    assert policy.dates_are_semantically_consistent([
        extraction("2026-09-02"),
        extraction("09/02/2026"),
    ])


def test_true_different_calendar_dates_remain_conflicting():
    assert not policy.dates_are_semantically_consistent([
        extraction("2026-09-02"),
        extraction("2026-09-03"),
    ])


def test_unparseable_date_never_suppresses_conflict():
    assert not policy.dates_are_semantically_consistent([
        extraction("2026-09-02"),
        extraction("Sept 2 2026?"),
    ])


def test_show_2_exams_topometric_date_is_ignored_completely():
    merged = {"critical_input_issues": [CONFLICT]}
    result = policy.reconcile_merged_exam_date_conflict(merged, [
        extraction("2026-09-02", "FOUR_MAPS_REFRACTIVE"),
        extraction("2026-09-03", "SHOW_2_EXAMS_TOPOMETRIC"),
    ])
    assert result["critical_input_issues"] == []


def test_show_2_exams_does_not_hide_conflict_between_two_authoritative_pages():
    merged = {"critical_input_issues": [CONFLICT]}
    result = policy.reconcile_merged_exam_date_conflict(merged, [
        extraction("2026-09-02", "FOUR_MAPS_REFRACTIVE"),
        extraction("2026-09-03", "BAD_DISPLAY"),
        extraction("2026-09-04", "SHOW_2_EXAMS_TOPOMETRIC"),
    ])
    assert result["critical_input_issues"] == [CONFLICT]


def test_wrapper_removes_only_false_exam_date_conflict_and_preserves_original_dates():
    core = SimpleNamespace()

    def base_merge(extractions):
        return {
            "critical_input_issues": [CONFLICT, "another issue"],
            "source_dates": [item["document_context"]["exam_date"] for item in extractions],
        }

    core.merge_extractions = base_merge
    policy._previous_merge_extractions = None
    policy.install(core)
    inputs = [extraction("2026-09-02"), extraction("02.09.2026")]
    merged = core.merge_extractions(inputs)
    assert merged["critical_input_issues"] == ["another issue"]
    assert merged["source_dates"] == ["2026-09-02", "02.09.2026"]


def test_wrapper_keeps_true_exam_date_conflict():
    def base_merge(extractions):
        return {"critical_input_issues": [CONFLICT]}

    policy._previous_merge_extractions = base_merge
    merged = policy.merge_extractions_with_exam_date_reconciliation([
        extraction("2026-09-02"), extraction("2026-09-03")
    ])
    assert merged["critical_input_issues"] == [CONFLICT]
