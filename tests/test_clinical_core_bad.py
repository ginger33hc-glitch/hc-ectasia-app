from clinical_core.bad import (
    ABNORMAL,
    NORMAL,
    SUSPICIOUS,
    UNAVAILABLE,
    BADContext,
    evaluate_bad,
    final_bad_d_classification,
)


def test_final_bad_d_boundaries():
    assert final_bad_d_classification(1.60) == NORMAL
    assert final_bad_d_classification(1.61) == SUSPICIOUS
    assert final_bad_d_classification(2.59) == SUSPICIOUS
    assert final_bad_d_classification(2.60) == ABNORMAL


def test_missing_final_d_is_unavailable_and_not_reconstructed_from_components():
    result = evaluate_bad(None, context=BADContext(df=4.0, db=4.0, dp=4.0, dt=4.0, da=4.0))
    assert result.final_d is None
    assert result.classification == UNAVAILABLE


def test_components_are_contextual_and_do_not_change_final_d_classification():
    context = BADContext(df=7.0, db=-3.0, dp=9.0, dt=5.0, da=6.0)
    result = evaluate_bad(1.2, context=context)
    assert result.classification == NORMAL
    assert result.context == context


def test_artmax_is_informational_only_for_bad_decision():
    low_art = evaluate_bad(2.0, context=BADContext(artmax_um=120.0))
    high_art = evaluate_bad(2.0, context=BADContext(artmax_um=900.0))
    assert low_art.classification == SUSPICIOUS
    assert high_art.classification == SUSPICIOUS


def test_negative_component_signs_are_preserved():
    result = evaluate_bad(1.0, context=BADContext(df=-0.7, db=-1.2, da=-0.4))
    assert result.context.df == -0.7
    assert result.context.db == -1.2
    assert result.context.da == -0.4
