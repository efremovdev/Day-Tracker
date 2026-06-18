"""Unit tests for the target math (P7).

All expected numbers are hand-computed from the formulas in DECISIONS.md
(2026-06-18): Mifflin-St Jeor BMR, TDEE x activity factor, percentage goal
adjustment (lose -15% / maintain 0 / gain +10%), and the macro split
(protein 2.0 g/kg, fat 25% of kcal, carbs the remainder). ``round`` is Python's
round-half-to-even; the inputs below avoid exact .5 boundaries so the expected
values are unambiguous.
"""

from __future__ import annotations

import pytest

from daytracker.targets import (
    ACTIVITY_FACTORS,
    GOAL_FACTORS,
    Activity,
    Goal,
    Sex,
    bmr,
    compute_targets,
    goal_kcal,
    macros_for,
    tdee,
)


def test_bmr_female() -> None:
    # 10*65 + 6.25*168 - 5*30 - 161 = 1389
    assert bmr(Sex.FEMALE, weight_kg=65, height_cm=168, age=30) == pytest.approx(1389.0)


def test_bmr_male_offset_is_plus_5() -> None:
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert bmr(Sex.MALE, weight_kg=80, height_cm=180, age=30) == pytest.approx(1780.0)


def test_bmr_sex_difference_is_166() -> None:
    # Male offset +5, female -161 -> a constant 166 kcal gap for identical inputs.
    male = bmr(Sex.MALE, weight_kg=70, height_cm=170, age=40)
    female = bmr(Sex.FEMALE, weight_kg=70, height_cm=170, age=40)
    assert male - female == pytest.approx(166.0)


@pytest.mark.parametrize(
    ("activity", "factor"),
    [
        (Activity.SEDENTARY, 1.2),
        (Activity.LIGHT, 1.375),
        (Activity.MODERATE, 1.55),
        (Activity.ACTIVE, 1.725),
        (Activity.VERY_ACTIVE, 1.9),
    ],
)
def test_tdee_applies_activity_factor(activity: Activity, factor: float) -> None:
    assert tdee(2000.0, activity) == pytest.approx(2000.0 * factor)


@pytest.mark.parametrize(
    ("goal", "expected"),
    [(Goal.LOSE, 1700), (Goal.MAINTAIN, 2000), (Goal.GAIN, 2200)],
)
def test_goal_kcal_adjustment(goal: Goal, expected: int) -> None:
    assert goal_kcal(2000.0, goal) == expected


def test_factor_tables_cover_every_enum_member() -> None:
    assert set(ACTIVITY_FACTORS) == set(Activity)
    assert set(GOAL_FACTORS) == set(Goal)


def test_macros_for_typical_split() -> None:
    # macros_for(1830, 65): protein 2.0*65=130; fat round(0.25*1830/9)=round(50.83)=51;
    # remaining 1830 - 130*4 - 51*9 = 851; carbs round(851/4)=round(212.75)=213.
    macros = macros_for(1830, 65)
    assert (macros.protein_g, macros.fat_g, macros.carbs_g) == (130, 51, 213)


def test_macros_for_clamps_carbs_at_zero() -> None:
    # High protein + low kcal drives the carb remainder negative -> clamp to 0.
    macros = macros_for(800, 120)
    assert macros.protein_g == 240
    assert macros.carbs_g == 0


def test_compute_targets_female_lose() -> None:
    # BMR 1389 -> TDEE 1389*1.55=2152.95 -> lose round(2152.95*0.85)=1830.
    targets = compute_targets(
        sex=Sex.FEMALE,
        weight_kg=65,
        height_cm=168,
        age=30,
        activity=Activity.MODERATE,
        goal=Goal.LOSE,
    )
    assert targets.kcal == 1830
    assert (targets.protein_g, targets.carbs_g, targets.fat_g) == (130, 213, 51)


def test_compute_targets_female_maintain() -> None:
    # BMR 1345.25 -> TDEE *1.2 = 1614.3 -> maintain round = 1614.
    targets = compute_targets(
        sex=Sex.FEMALE,
        weight_kg=60,
        height_cm=165,
        age=25,
        activity=Activity.SEDENTARY,
        goal=Goal.MAINTAIN,
    )
    assert targets.kcal == 1614
    assert (targets.protein_g, targets.carbs_g, targets.fat_g) == (120, 182, 45)


def test_compute_targets_male_gain() -> None:
    # BMR 1767.5 -> TDEE *1.375 = 2430.3125 -> gain round(*1.10)=2673.
    targets = compute_targets(
        sex=Sex.MALE,
        weight_kg=80,
        height_cm=178,
        age=30,
        activity=Activity.LIGHT,
        goal=Goal.GAIN,
    )
    assert targets.kcal == 2673
    assert (targets.protein_g, targets.carbs_g, targets.fat_g) == (160, 342, 74)


def test_lose_is_below_maintain_below_gain() -> None:
    kwargs = dict(sex=Sex.FEMALE, weight_kg=65, height_cm=168, age=30, activity=Activity.MODERATE)
    lose = compute_targets(goal=Goal.LOSE, **kwargs).kcal
    maintain = compute_targets(goal=Goal.MAINTAIN, **kwargs).kcal
    gain = compute_targets(goal=Goal.GAIN, **kwargs).kcal
    assert lose < maintain < gain
