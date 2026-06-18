"""Async data-access helpers — a thin persistence layer over the ORM.

Keeps SQLAlchemy session handling out of the handlers. All target math stays in
:mod:`daytracker.targets`; here we only read and write rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Meal, MealItem, Profile
from .targets import Targets

if TYPE_CHECKING:
    from .estimator import MealEstimate


async def get_profile(session: AsyncSession, telegram_user_id: int) -> Profile | None:
    """Return the profile for this user, or ``None`` if not onboarded yet."""
    return await session.get(Profile, telegram_user_id)


async def upsert_profile(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    sex: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: str,
    goal: str,
    targets: Targets,
) -> Profile:
    """Create or replace the profile and its computed targets.

    Always clears any manual kcal override — re-running ``/profil`` starts fresh.
    """
    profile = await session.get(Profile, telegram_user_id)
    if profile is None:
        profile = Profile(telegram_user_id=telegram_user_id)
        session.add(profile)

    profile.sex = sex
    profile.age = age
    profile.height_cm = height_cm
    profile.weight_kg = weight_kg
    profile.activity = activity
    profile.goal = goal
    profile.target_kcal = targets.kcal
    profile.target_protein_g = targets.protein_g
    profile.target_carbs_g = targets.carbs_g
    profile.target_fat_g = targets.fat_g
    profile.manual_kcal = None

    await session.commit()
    return profile


async def update_targets(
    session: AsyncSession,
    profile: Profile,
    *,
    manual_kcal: int,
    targets: Targets,
) -> Profile:
    """Apply a manual kcal override (from ``/tinte``) and its recomputed macros."""
    profile.manual_kcal = manual_kcal
    profile.target_kcal = targets.kcal
    profile.target_protein_g = targets.protein_g
    profile.target_carbs_g = targets.carbs_g
    profile.target_fat_g = targets.fat_g

    await session.commit()
    return profile


# --- Meals (P3) ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DayTotals:
    """Aggregated macro totals for one user on one local date."""

    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    meals: int


async def add_meal(
    session: AsyncSession,
    *,
    telegram_user_id: int,
    log_date: date,
    raw_text: str,
    estimate: MealEstimate,
) -> Meal:
    """Persist a meal and its per-item macros; returns the committed row."""
    meal = Meal(
        telegram_user_id=telegram_user_id,
        log_date=log_date,
        raw_text=raw_text,
        total_kcal=estimate.kcal,
        total_protein_g=estimate.protein_g,
        total_carbs_g=estimate.carbs_g,
        total_fat_g=estimate.fat_g,
        approximate=estimate.approximate,
        note=estimate.note,
    )
    for position, item in enumerate(estimate.items):
        meal.items.append(
            MealItem(
                position=position,
                name=item.name,
                grams=item.grams,
                kcal=item.kcal,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
            )
        )
    session.add(meal)
    await session.commit()
    return meal


async def get_day_totals(
    session: AsyncSession, *, telegram_user_id: int, log_date: date
) -> DayTotals:
    """Sum all of the user's meal totals for ``log_date`` (the running daily total)."""
    stmt = select(
        func.coalesce(func.sum(Meal.total_kcal), 0),
        func.coalesce(func.sum(Meal.total_protein_g), 0),
        func.coalesce(func.sum(Meal.total_carbs_g), 0),
        func.coalesce(func.sum(Meal.total_fat_g), 0),
        func.count(Meal.id),
    ).where(Meal.telegram_user_id == telegram_user_id, Meal.log_date == log_date)
    kcal, protein, carbs, fat, meals = (await session.execute(stmt)).one()
    return DayTotals(
        kcal=int(kcal),
        protein_g=int(protein),
        carbs_g=int(carbs),
        fat_g=int(fat),
        meals=int(meals),
    )
