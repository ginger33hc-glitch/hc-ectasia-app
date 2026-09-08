from pentacam_canonical_source_lock import (
    BAD_STRIP,
    FOUR_MAPS_LOWER_LEFT,
    SHOW_2_CORNEA_FRONT,
    SHOW_2_INDICES,
)
from pentacam_provenance import (
    CONFLICT,
    EXAM_SELECTION_REQUIRED,
    RESOLVED,
    SURGEON_CONFIRMED,
    UNREADABLE,
    Observation,
    resolve_field,
    surgeon_confirm,
)


def obs(*, eye="OD", exam="2026-09-07", field="I_S", source=SHOW_2_INDICES, value=0.5, origin="AUTO"):
    return Observation(eye=eye, exam_id=exam, field=field, source_id=source, value=value, origin=origin)


def test_wrong_screen_duplicate_is_ignored_not_conflict():
    result = resolve_field(
        [
            obs(value=0.51),
            obs(source=FOUR_MAPS_LOWER_LEFT, value=1.8),
        ],
        eye="OD",
        field="I_S",
    )
    assert result.status == RESOLVED
    assert result.value == 0.51
    assert len(result.ignored_wrong_source) == 1


def test_same_eye_same_exam_same_source_disagreement_is_conflict():
    result = resolve_field(
        [obs(value=0.51), obs(value=0.52)],
        eye="OD",
        field="I_S",
    )
    assert result.status == CONFLICT
    assert result.value is None


def test_identical_same_source_reads_resolve_once():
    result = resolve_field(
        [obs(value=-0.18), obs(value=-0.18)],
        eye="OD",
        field="I_S",
    )
    assert result.status == RESOLVED
    assert result.value == -0.18


def test_different_exam_dates_never_merge():
    result = resolve_field(
        [obs(exam="2026-09-01", value=0.2), obs(exam="2026-09-07", value=0.8)],
        eye="OD",
        field="I_S",
    )
    assert result.status == EXAM_SELECTION_REQUIRED
    assert result.value is None


def test_explicit_exam_selection_resolves_only_selected_exam():
    observations = [
        obs(exam="2026-09-01", value=0.2),
        obs(exam="2026-09-07", value=0.8),
    ]
    result = resolve_field(observations, eye="OD", field="I_S", exam_id="2026-09-07")
    assert result.status == RESOLVED
    assert result.value == 0.8


def test_od_and_os_never_cross_fill():
    result = resolve_field([obs(eye="OS", value=1.4)], eye="OD", field="I_S")
    assert result.status == UNREADABLE
    assert result.value is None


def test_bad_final_d_requires_exact_bad_strip_source():
    observations = [
        Observation("OD", "2026-09-07", "BAD_D", BAD_STRIP, 2.59),
        Observation("OD", "2026-09-07", "BAD_D", SHOW_2_CORNEA_FRONT, 3.1),
    ]
    result = resolve_field(observations, eye="OD", field="BAD_D")
    assert result.status == RESOLVED
    assert result.value == 2.59
    assert len(result.ignored_wrong_source) == 1


def test_surgeon_confirmation_replaces_active_value_but_preserves_audit_history():
    automatic = resolve_field([obs(value=0.62)], eye="OD", field="I_S")
    corrected = surgeon_confirm(automatic, value=0.58)
    assert corrected.status == RESOLVED
    assert corrected.value == 0.58
    assert corrected.provenance[0].origin == SURGEON_CONFIRMED
    assert corrected.audit_history[0].value == 0.62


def test_conflicting_surgeon_confirmations_are_conflict():
    observations = [
        obs(value=0.62),
        obs(value=0.58, origin=SURGEON_CONFIRMED),
        obs(value=0.60, origin=SURGEON_CONFIRMED),
    ]
    result = resolve_field(observations, eye="OD", field="I_S")
    assert result.status == CONFLICT
    assert result.value is None
