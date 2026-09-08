"""Monday acceptance locks for pure planning policy."""

from clinical_core.planning import (
    LASIK_PLANS,
    MMC_MANDATORY,
    MMC_NOT_APPLICABLE,
    MMC_RECOMMENDED,
    MMC_REVIEW_REQUIRED,
    PlanEvaluation,
    mmc_guidance,
    select_first_safe_lasik_plan,
)
from clinical_core.refraction import HYPEROPIC, MIXED, MYOPIC


def test_lasik_plan_sequence_is_exactly_a_b_c():
    assert LASIK_PLANS == (
        {"name": "Plan A", "flap_um": 100.0, "optical_zone_mm": 6.5, "transition_zone_mm": 9.0},
        {"name": "Plan B", "flap_um": 100.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
        {"name": "Plan C", "flap_um": 90.0, "optical_zone_mm": 6.0, "transition_zone_mm": 8.5},
    )


def test_first_safe_plan_is_selected_and_rejected_plans_remain_visible():
    calls = []

    def evaluator(spec):
        calls.append(spec["name"])
        if spec["name"] == "Plan A":
            return PlanEvaluation("Plan A", False, ("RSB <300 µm",))
        return PlanEvaluation(spec["name"], True)

    result = select_first_safe_lasik_plan(evaluator)
    assert calls == ["Plan A", "Plan B"]
    assert result.selected_plan == "Plan B"
    assert result.sequence[0].safe is False
    assert result.sequence[0].rejection_reasons == ("RSB <300 µm",)
    assert result.sequence[1].safe is True


def test_all_three_plans_use_the_same_evaluator_and_none_selected_if_all_unsafe():
    evaluator_ids = []

    def evaluator(spec):
        evaluator_ids.append(id(evaluator))
        return PlanEvaluation(spec["name"], False, (f"{spec['name']} unsafe",))

    result = select_first_safe_lasik_plan(evaluator)
    assert len(result.sequence) == 3
    assert len(set(evaluator_ids)) == 1
    assert result.selected_plan is None
    assert [item.plan for item in result.sequence] == ["Plan A", "Plan B", "Plan C"]


def test_mmc_myopic_boundary_is_exactly_four_diopters():
    assert mmc_guidance("PRK", MYOPIC, -3.99) == MMC_RECOMMENDED
    assert mmc_guidance("PRK", MYOPIC, -4.00) == MMC_MANDATORY
    assert mmc_guidance("PRK", MYOPIC, -6.00) == MMC_MANDATORY


def test_hyperopic_prk_mmc_is_mandatory():
    assert mmc_guidance("PRK", HYPEROPIC, +1.0) == MMC_MANDATORY
    assert mmc_guidance("PRK", HYPEROPIC, +5.0) == MMC_MANDATORY


def test_mixed_prk_does_not_borrow_myopic_scalar_mmc_rule():
    assert mmc_guidance("PRK", MIXED, 0.0) == MMC_REVIEW_REQUIRED


def test_mmc_is_not_applicable_to_lasik():
    assert mmc_guidance("LASIK", MYOPIC, -5.0) == MMC_NOT_APPLICABLE
