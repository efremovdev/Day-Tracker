"""Target math: BMR, TDEE, goal adjustment, and the macro split.

Pure functions, no I/O — easy to unit-test (P7). Every factor and default the
bot uses lives here. See DECISIONS.md (2026-06-18) for the chosen parameters:
goal adjustment is percentage-based (lose -15% / maintain 0 / gain +10%) and
macros default to "higher protein" (2.0 g/kg, fat 25% of kcal, carbs remainder).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


class Activity(StrEnum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class Goal(StrEnum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


# Standard Mifflin–St Jeor activity multipliers.
ACTIVITY_FACTORS: dict[Activity, float] = {
    Activity.SEDENTARY: 1.2,
    Activity.LIGHT: 1.375,
    Activity.MODERATE: 1.55,
    Activity.ACTIVE: 1.725,
    Activity.VERY_ACTIVE: 1.9,
}

# Goal adjustment applied to TDEE.
GOAL_FACTORS: dict[Goal, float] = {
    Goal.LOSE: 0.85,
    Goal.MAINTAIN: 1.0,
    Goal.GAIN: 1.10,
}

# Macro defaults.
PROTEIN_G_PER_KG = 2.0
FAT_PCT_OF_KCAL = 0.25

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9


@dataclass(frozen=True, slots=True)
class Macros:
    protein_g: int
    carbs_g: int
    fat_g: int


@dataclass(frozen=True, slots=True)
class Targets:
    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


def bmr(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Basal metabolic rate via Mifflin–St Jeor."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex is Sex.MALE else -161)


def tdee(bmr_value: float, activity: Activity) -> float:
    """Total daily energy expenditure = BMR × activity factor."""
    return bmr_value * ACTIVITY_FACTORS[activity]


def goal_kcal(tdee_value: float, goal: Goal) -> int:
    """Apply the goal adjustment to TDEE and round to whole kcal."""
    return round(tdee_value * GOAL_FACTORS[goal])


def macros_for(kcal: int, weight_kg: float) -> Macros:
    """Split a kcal target into macros: protein g/kg, fat % of kcal, carbs remainder."""
    protein_g = round(PROTEIN_G_PER_KG * weight_kg)
    fat_g = round((FAT_PCT_OF_KCAL * kcal) / KCAL_PER_G_FAT)
    remaining = kcal - protein_g * KCAL_PER_G_PROTEIN - fat_g * KCAL_PER_G_FAT
    carbs_g = max(0, round(remaining / KCAL_PER_G_CARB))
    return Macros(protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g)


def compute_targets(
    *,
    sex: Sex,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity: Activity,
    goal: Goal,
) -> Targets:
    """Full pipeline: profile inputs → daily kcal + macro targets."""
    kcal = goal_kcal(tdee(bmr(sex, weight_kg, height_cm, age), activity), goal)
    macros = macros_for(kcal, weight_kg)
    return Targets(
        kcal=kcal,
        protein_g=macros.protein_g,
        carbs_g=macros.carbs_g,
        fat_g=macros.fat_g,
    )
