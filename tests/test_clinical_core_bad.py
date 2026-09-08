import pytest

from clinical_core.bad import (
    ABNORMAL,
    NORMAL,
    SUSPICIOUS,
    UNAVAILABLE,
    BADContext,
    evaluate_bad,
    final_bad_d_classification,
)


@pytest.mark.parametrize("key,low,high,inverse", [
    ("ppi_min", 0.80, 0.86, False), ("ppi_avg", 1.08, 1.17, False),
    ("ppi_max", 1.40, 1.52, False), ("artmax_um", 357, 368, True),
])
def test_pachymetric_display_boundaries_and_missing_values(key, low, high, inverse):
    for value, expected in [(low - 0.001, ABNORMAL if inverse else NORMAL),
                            (low, SUSPICIOUS), (high, SUSPICIOUS),
                            (high + 0.001, NORMAL if inverse else ABNORMAL),
                            (None, UNAVAILABLE), (float('nan'), UNAVAILABLE),
                            (0, UNAVAILABLE), (-1, UNAVAILABLE)]:
        result = evaluate_bad(1.0, context=BADContext(**{key: value}))
        assert result.component_interpretations[key]["classification"] == expected
        assert result.classification == NORMAL


def test_component_display_bands_do_not_change_final_bad_authority():
    result = evaluate_bad(1.0, context=BADContext(df=1.599, db=1.60, dp=2.599, dt=2.60, da=None))
    bands = result.component_interpretations
    assert [bands[k]["classification"] for k in ("df", "db", "dp", "dt", "da")] == [NORMAL, SUSPICIOUS, SUSPICIOUS, ABNORMAL, UNAVAILABLE]
    assert bands["db"]["range"] == "1.60 to < 2.60"
    assert bands["dt"]["range"] == ">= 2.60"
    assert result.classification == NORMAL


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
