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


def test_identical_ambiguous_day_month_strings_are_not_a_conflict():
    inputs = [
        four_maps("03/09/2026", "OD"),
        four_maps("03/09/2026", "OS"),
    ]
    assert policy.dates_are_semantically_consistent(inputs)
    assert not policy.authoritative_exam_date_conflict(inputs)


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


def test_consistent_targeted_four_maps_rereads_replace_false_primary_ocr_conflict():
    inputs = [
        four_maps("23/09/2026", "OD"),
        four_maps("13/09/2026", "OS"),
    ]
    for item in inputs:
        item["document_context"]["targeted_exam_date_reread_evidence"] = {
            "value": "03/09/2026", "promoted": False,
        }
    assert policy.promote_consistent_targeted_exam_dates(inputs)
    assert not policy.authoritative_exam_date_conflict(inputs)
    assert [item["document_context"]["exam_date"] for item in inputs] == [
        "03/09/2026", "03/09/2026",
    ]
    assert [item["document_context"]["primary_exam_date_reading"] for item in inputs] == [
        "23/09/2026", "13/09/2026",
    ]
    assert all(
        item["document_context"]["targeted_exam_date_reread_evidence"]["promoted"]
        for item in inputs
    )


def test_incomplete_or_disagreeing_targeted_date_rereads_do_not_override_primary_reads():
    incomplete = [four_maps("23/09/2026", "OD"), four_maps("13/09/2026", "OS")]
    incomplete[0]["document_context"]["targeted_exam_date_reread_evidence"] = {
        "value": "03/09/2026", "promoted": False,
    }
    assert not policy.promote_consistent_targeted_exam_dates(incomplete)
    assert [item["document_context"]["exam_date"] for item in incomplete] == [
        "23/09/2026", "13/09/2026",
    ]

    disagreeing = [four_maps("23/09/2026", "OD"), four_maps("13/09/2026", "OS")]
    for item, value in zip(disagreeing, ("03/09/2026", "04/09/2026")):
        item["document_context"]["targeted_exam_date_reread_evidence"] = {
            "value": value, "promoted": False,
        }
    assert not policy.promote_consistent_targeted_exam_dates(disagreeing)
    assert policy.authoritative_exam_date_conflict(disagreeing)


def test_exam_date_module_exposes_no_install_time_merge_wrapper():
    assert not hasattr(policy, "install")
    assert not hasattr(policy, "merge_extractions_with_exam_date_reconciliation")
    assert not hasattr(policy, "reconcile_merged_exam_date_conflict")


def merged_conflict():
    return {
        "critical_input_issues": [CONFLICT, "Another source blocker."],
        "identity_warnings": [],
        "document_contexts": [
            {
                "document_type": "PENTACAM_TOPOGRAPHY", "source_filename": "od.png",
                "four_maps_eyes": ["OD"], "exam_date": "23/09/2026",
                "targeted_exam_date_reread_evidence": {"value": "03/09/2026"},
            },
            {
                "document_type": "PENTACAM_TOPOGRAPHY", "source_filename": "os.png",
                "four_maps_eyes": ["OS"], "exam_date": "13/09/2026",
                "targeted_exam_date_reread_evidence": {"value": None},
            },
        ],
    }


def test_surgeon_date_approval_removes_only_date_blocker_and_preserves_readings():
    original = merged_conflict()
    approved = policy.apply_surgeon_exam_date_approval(original, {
        policy.EXAM_DATE_CONFIRMATION_KEY: policy.EXAM_DATE_APPROVAL,
    })
    assert original["critical_input_issues"] == [CONFLICT, "Another source blocker."]
    assert approved["critical_input_issues"] == ["Another source blocker."]
    assert approved["surgeon_source_confirmations"] == [{
        "key": policy.EXAM_DATE_CONFIRMATION_KEY,
        "decision": policy.EXAM_DATE_APPROVAL,
        "evidence": [
            {"source_filename": "od.png", "eyes": ["OD"], "primary_reading": "23/09/2026",
             "targeted_reread": "03/09/2026", "effective_reading": "23/09/2026"},
            {"source_filename": "os.png", "eyes": ["OS"], "primary_reading": "13/09/2026",
             "targeted_reread": None, "effective_reading": "13/09/2026"},
        ],
    }]
    assert policy.EXAM_DATE_APPROVAL_WARNING in approved["identity_warnings"]


def test_date_approval_is_strict_and_idempotent():
    with __import__("pytest").raises(ValueError):
        policy.apply_surgeon_exam_date_approval({}, {
            policy.EXAM_DATE_CONFIRMATION_KEY: policy.EXAM_DATE_APPROVAL,
        })
    with __import__("pytest").raises(ValueError):
        policy.apply_surgeon_exam_date_approval(merged_conflict(), {"another_rule": "YES"})
    first = policy.apply_surgeon_exam_date_approval(merged_conflict(), {
        policy.EXAM_DATE_CONFIRMATION_KEY: policy.EXAM_DATE_APPROVAL,
    })
    second = policy.apply_surgeon_exam_date_approval(first, {
        policy.EXAM_DATE_CONFIRMATION_KEY: policy.EXAM_DATE_APPROVAL,
    })
    assert second == first
