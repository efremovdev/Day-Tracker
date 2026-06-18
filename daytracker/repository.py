"""Async data-access helpers — a thin persistence layer over the ORM.

Keeps SQLAlchemy session handling out of the handlers. All target math stays in
:mod:`daytracker.targets`; here we only read and write rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ActivityLog, Meal, MealItem, Profile, UserChat, WaterLog, WeightLog
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


async def get_day_meals(
    session: AsyncSession, *, telegram_user_id: int, log_date: date
) -> list[Meal]:
    """Today's meals in log order (for the ``/azi`` view)."""
    stmt = (
        select(Meal)
        .where(Meal.telegram_user_id == telegram_user_id, Meal.log_date == log_date)
        .order_by(Meal.created_at, Meal.id)
    )
    return list((await session.scalars(stmt)).all())


# --- Activity / water / weight (P4) -------------------------------------------


async def add_activity(
    session: AsyncSession, *, telegram_user_id: int, log_date: date, text: str
) -> ActivityLog:
    """Store a free-text activity (logged only — no calorie add-back)."""
    row = ActivityLog(telegram_user_id=telegram_user_id, log_date=log_date, raw_text=text)
    session.add(row)
    await session.commit()
    return row


async def add_water(
    session: AsyncSession, *, telegram_user_id: int, log_date: date, ml: int
) -> WaterLog:
    """Store a water entry (additive — the day's water is the sum of its rows)."""
    row = WaterLog(telegram_user_id=telegram_user_id, log_date=log_date, ml=ml)
    session.add(row)
    await session.commit()
    return row


async def add_weight(
    session: AsyncSession, *, telegram_user_id: int, log_date: date, weight_kg: float
) -> WeightLog:
    """Store a weigh-in. Does not touch the profile or recompute targets."""
    row = WeightLog(telegram_user_id=telegram_user_id, log_date=log_date, weight_kg=weight_kg)
    session.add(row)
    await session.commit()
    return row


async def get_day_activities(
    session: AsyncSession, *, telegram_user_id: int, log_date: date
) -> list[ActivityLog]:
    """Today's activities in log order."""
    stmt = (
        select(ActivityLog)
        .where(ActivityLog.telegram_user_id == telegram_user_id, ActivityLog.log_date == log_date)
        .order_by(ActivityLog.created_at, ActivityLog.id)
    )
    return list((await session.scalars(stmt)).all())


async def get_day_water_ml(session: AsyncSession, *, telegram_user_id: int, log_date: date) -> int:
    """Total millilitres of water logged today."""
    stmt = select(func.coalesce(func.sum(WaterLog.ml), 0)).where(
        WaterLog.telegram_user_id == telegram_user_id, WaterLog.log_date == log_date
    )
    return int((await session.scalar(stmt)) or 0)


async def get_latest_weight_today(
    session: AsyncSession, *, telegram_user_id: int, log_date: date
) -> WeightLog | None:
    """The most recent weigh-in logged *today*, or ``None`` if she didn't weigh in."""
    stmt = (
        select(WeightLog)
        .where(WeightLog.telegram_user_id == telegram_user_id, WeightLog.log_date == log_date)
        .order_by(WeightLog.created_at.desc(), WeightLog.id.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def get_latest_weight(session: AsyncSession, *, telegram_user_id: int) -> WeightLog | None:
    """The most recent weigh-in across *all* days (latest known weight, for /sumar)."""
    stmt = (
        select(WeightLog)
        .where(WeightLog.telegram_user_id == telegram_user_id)
        .order_by(WeightLog.created_at.desc(), WeightLog.id.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


# --- Corrections: last entry + delete (P4) ------------------------------------


@dataclass(frozen=True, slots=True)
class LastEntry:
    """The most recent entry across all types — what ``/sterge`` offers to delete.

    Carries enough data for the confirmation message; the repository returns the
    raw values and :mod:`daytracker.strings` formats the Romanian description.
    """

    kind: str  # "masa" | "activitate" | "apa" | "cantar"
    id: int
    created_at: datetime
    text: str | None = None
    kcal: int | None = None
    ml: int | None = None
    weight_kg: float | None = None


async def get_last_entry(session: AsyncSession, *, telegram_user_id: int) -> LastEntry | None:
    """Return the single most recent entry of any kind, or ``None`` if there are none.

    Queries the latest row of each table and picks the overall newest by
    ``created_at`` (ties resolve to meal → activity → water → weight).
    """
    candidates: list[LastEntry] = []

    meal = await session.scalar(
        select(Meal)
        .where(Meal.telegram_user_id == telegram_user_id)
        .order_by(Meal.created_at.desc(), Meal.id.desc())
        .limit(1)
    )
    if meal is not None:
        candidates.append(
            LastEntry("masa", meal.id, meal.created_at, text=meal.raw_text, kcal=meal.total_kcal)
        )

    activity = await session.scalar(
        select(ActivityLog)
        .where(ActivityLog.telegram_user_id == telegram_user_id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(1)
    )
    if activity is not None:
        candidates.append(
            LastEntry("activitate", activity.id, activity.created_at, text=activity.raw_text)
        )

    water = await session.scalar(
        select(WaterLog)
        .where(WaterLog.telegram_user_id == telegram_user_id)
        .order_by(WaterLog.created_at.desc(), WaterLog.id.desc())
        .limit(1)
    )
    if water is not None:
        candidates.append(LastEntry("apa", water.id, water.created_at, ml=water.ml))

    weight = await session.scalar(
        select(WeightLog)
        .where(WeightLog.telegram_user_id == telegram_user_id)
        .order_by(WeightLog.created_at.desc(), WeightLog.id.desc())
        .limit(1)
    )
    if weight is not None:
        candidates.append(
            LastEntry("cantar", weight.id, weight.created_at, weight_kg=weight.weight_kg)
        )

    if not candidates:
        return None
    return max(candidates, key=lambda entry: entry.created_at)


async def delete_entry(session: AsyncSession, *, kind: str, entry_id: int) -> None:
    """Delete one entry by kind + id. A meal also removes its child items."""
    if kind == "masa":
        await session.execute(delete(MealItem).where(MealItem.meal_id == entry_id))
        await session.execute(delete(Meal).where(Meal.id == entry_id))
    elif kind == "activitate":
        await session.execute(delete(ActivityLog).where(ActivityLog.id == entry_id))
    elif kind == "apa":
        await session.execute(delete(WaterLog).where(WaterLog.id == entry_id))
    elif kind == "cantar":
        await session.execute(delete(WeightLog).where(WeightLog.id == entry_id))
    await session.commit()


# --- Daily summary: chat memory + day bundle (P5) ------------------------------


async def remember_chat(session: AsyncSession, *, telegram_user_id: int, chat_id: int) -> None:
    """Record the chat the user last wrote in (where the auto-summary is posted)."""
    row = await session.get(UserChat, telegram_user_id)
    if row is None:
        session.add(UserChat(telegram_user_id=telegram_user_id, chat_id=chat_id))
    elif row.chat_id != chat_id:
        row.chat_id = chat_id
    else:
        return  # unchanged — skip the write
    await session.commit()


async def get_chat_id(session: AsyncSession, *, telegram_user_id: int) -> int | None:
    """The chat the user last wrote in, or ``None`` if she hasn't messaged yet."""
    row = await session.get(UserChat, telegram_user_id)
    return row.chat_id if row is not None else None


@dataclass(frozen=True, slots=True)
class DaySummary:
    """Everything one day's summary needs, gathered in a single read.

    Shared by ``/sumar`` and the scheduled 21:00 job so both render identical output
    (PLAN.md P5 acceptance). ``latest_weight`` is the latest weigh-in across *all*
    days (not today-only, unlike ``/azi``), per KNOWN_ISSUES.md.
    """

    log_date: date
    meals: list[Meal]
    totals: DayTotals
    activities: list[ActivityLog]
    water_ml: int
    latest_weight: WeightLog | None
    profile: Profile | None

    @property
    def weighed_today(self) -> bool:
        return self.latest_weight is not None and self.latest_weight.log_date == self.log_date

    @property
    def is_empty(self) -> bool:
        """True when nothing at all was logged *today* (no meal/activity/water/weigh-in)."""
        return (
            not self.meals and not self.activities and self.water_ml == 0 and not self.weighed_today
        )


async def get_day_summary(
    session: AsyncSession, *, telegram_user_id: int, log_date: date
) -> DaySummary:
    """Gather all data for a day's summary (meals, totals, activity, water, weight, profile)."""
    return DaySummary(
        log_date=log_date,
        meals=await get_day_meals(session, telegram_user_id=telegram_user_id, log_date=log_date),
        totals=await get_day_totals(session, telegram_user_id=telegram_user_id, log_date=log_date),
        activities=await get_day_activities(
            session, telegram_user_id=telegram_user_id, log_date=log_date
        ),
        water_ml=await get_day_water_ml(
            session, telegram_user_id=telegram_user_id, log_date=log_date
        ),
        latest_weight=await get_latest_weight(session, telegram_user_id=telegram_user_id),
        profile=await get_profile(session, telegram_user_id),
    )


# --- Weekly report: per-day stats over a Mon–Sun window (P6) -------------------


@dataclass(frozen=True, slots=True)
class DayStat:
    """One calendar day's meal totals within a weekly window (0-filled if unlogged)."""

    log_date: date
    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    meals: int

    @property
    def has_meals(self) -> bool:
        return self.meals > 0


@dataclass(frozen=True, slots=True)
class WeekSummary:
    """Everything the weekly report needs, gathered in a single read.

    Shared by ``/saptamana`` and the scheduled Sunday-night job so both render
    identical output. The window is the ISO calendar week (Monday → ``end_date``);
    on the Sunday job ``end_date`` is that Sunday, so it spans the full Mon–Sun
    (DECISIONS.md, 2026-06-18). ``days`` holds one entry per *elapsed* day in the
    window (unlogged days 0-filled); averages divide by ``num_days``.
    """

    start_date: date
    end_date: date
    num_days: int
    days: list[DayStat]
    weigh_ins: list[WeightLog]  # weigh-ins within the window, oldest → newest
    latest_weight: WeightLog | None  # latest across all days (fallback for the trend)
    profile: Profile | None

    @property
    def days_with_meals(self) -> int:
        return sum(1 for day in self.days if day.has_meals)

    @property
    def total_kcal(self) -> int:
        return sum(day.kcal for day in self.days)

    @property
    def total_protein_g(self) -> int:
        return sum(day.protein_g for day in self.days)

    @property
    def total_carbs_g(self) -> int:
        return sum(day.carbs_g for day in self.days)

    @property
    def total_fat_g(self) -> int:
        return sum(day.fat_g for day in self.days)

    @property
    def avg_kcal(self) -> int:
        return round(self.total_kcal / self.num_days)

    @property
    def avg_protein_g(self) -> int:
        return round(self.total_protein_g / self.num_days)

    @property
    def avg_carbs_g(self) -> int:
        return round(self.total_carbs_g / self.num_days)

    @property
    def avg_fat_g(self) -> int:
        return round(self.total_fat_g / self.num_days)

    @property
    def is_empty(self) -> bool:
        """True when the week has no meals *and* no weigh-ins (the report's subjects)."""
        return self.days_with_meals == 0 and not self.weigh_ins


async def get_week_summary(
    session: AsyncSession, *, telegram_user_id: int, end_date: date
) -> WeekSummary:
    """Gather the weekly report for the ISO week containing ``end_date`` (Mon → end_date)."""
    start_date = end_date - timedelta(days=end_date.weekday())  # Monday of that week
    num_days = (end_date - start_date).days + 1

    stmt = (
        select(
            Meal.log_date,
            func.coalesce(func.sum(Meal.total_kcal), 0),
            func.coalesce(func.sum(Meal.total_protein_g), 0),
            func.coalesce(func.sum(Meal.total_carbs_g), 0),
            func.coalesce(func.sum(Meal.total_fat_g), 0),
            func.count(Meal.id),
        )
        .where(
            Meal.telegram_user_id == telegram_user_id,
            Meal.log_date >= start_date,
            Meal.log_date <= end_date,
        )
        .group_by(Meal.log_date)
    )
    by_date: dict[date, DayStat] = {
        row[0]: DayStat(row[0], int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]))
        for row in (await session.execute(stmt)).all()
    }
    days = [
        by_date.get(day, DayStat(day, 0, 0, 0, 0, 0))
        for day in (start_date + timedelta(days=offset) for offset in range(num_days))
    ]

    weigh_ins = list(
        (
            await session.scalars(
                select(WeightLog)
                .where(
                    WeightLog.telegram_user_id == telegram_user_id,
                    WeightLog.log_date >= start_date,
                    WeightLog.log_date <= end_date,
                )
                .order_by(WeightLog.created_at, WeightLog.id)
            )
        ).all()
    )

    return WeekSummary(
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        days=days,
        weigh_ins=weigh_ins,
        latest_weight=await get_latest_weight(session, telegram_user_id=telegram_user_id),
        profile=await get_profile(session, telegram_user_id),
    )
