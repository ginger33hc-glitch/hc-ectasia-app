from clean_engine.finalization import FinalizationInput, finalize
from clean_engine.models import PrkScoreValues


def inp(**changes):
    values = dict(
        procedure="LASIK", bad_d_status="NORMAL", lasik_erss_total=0,
        prk_scores=PrkScoreValues(), hard_stops=(), missing=(),
    )
    values.update(changes)
    return FinalizationInput(**values)


def test_lasik_favorable_finalizes_to_pass_with_caution():
    out = finalize(inp())
    assert out.upstream_status == "PASS"
    assert out.status == "PASS"


def test_hard_stop_has_priority_over_favorable_principal_inputs():
    out = finalize(inp(hard_stops=("PACHYMETRY_LT_480",)))
    assert out.upstream_status == "STOP-DEFER"
    assert out.status == "STOP-DEFER"
    assert out.rule == "PRESERVE_HARD_STOP"


def test_missing_principal_input_never_passes():
    out = finalize(inp(missing=("bad_d",)))
    assert out.upstream_status == "DATA INSUFFICIENT"
    assert out.status == "DATA INSUFFICIENT"


def test_lasik_score_three_cautions_while_score_four_is_expected_to_arrive_as_hard_stop():
    assert finalize(inp(lasik_erss_total=3)).status == "CAUTION"
    score4 = finalize(inp(lasik_erss_total=4, hard_stops=("ERSS_GE_4",)))
    assert score4.status == "STOP-DEFER"


def test_prk_score_two_has_no_status_escalation():
    out = finalize(inp(
        procedure="PRK", lasik_erss_total=None,
        prk_scores=PrkScoreValues(total=2, category="NO_SCORE_ESCALATION"),
    ))
    assert out.upstream_status == "PASS"
    assert out.status == "PASS"


def test_prk_score_three_defers_and_high_concern_stops():
    score3 = finalize(inp(
        procedure="PRK", lasik_erss_total=None,
        prk_scores=PrkScoreValues(total=3, category="CAUTION"),
    ))
    assert score3.status == "STOP-DEFER"
    score4 = finalize(inp(
        procedure="PRK", lasik_erss_total=None,
        prk_scores=PrkScoreValues(total=4, category="HIGH_CONCERN"),
    ))
    assert score4.status == "STOP-DEFER"


def test_prk_pta_evidence_gap_escalates_to_review_without_becoming_hard_stop():
    out = finalize(inp(
        procedure="PRK", lasik_erss_total=None,
        prk_scores=PrkScoreValues(total=0, category="NO_SCORE_ESCALATION", pta_evidence_gap=True),
    ))
    assert out.upstream_status == "CAUTION"
    assert out.status == "CAUTION"
