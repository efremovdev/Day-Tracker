"""Async data-access helpers — a thin persistence layer over the ORM.

Keeps SQLAlchemy session handling out of the handlers. All target math stays in
:mod:`daytracker.targets`; here we only read and write rows.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Profile
from .targets import Targets


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
