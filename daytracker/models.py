"""ORM models. Added per phase; P2 introduces the user profile + targets.

Each model subclasses :class:`daytracker.db.Base` and is registered for
``create_all`` simply by being imported (see ``db.init_db``).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Profile(Base):
    """The tracked user's profile inputs and computed daily targets.

    Keyed by Telegram user id — single user today, but a row-per-user keeps the
    door open for multi-user later without a schema change. ``manual_kcal`` is
    set only when the kcal target was overridden via ``/tinte``; re-running
    ``/profil`` recomputes everything and clears it.
    """

    __tablename__ = "profiles"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    sex: Mapped[str] = mapped_column(String(8))
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    activity: Mapped[str] = mapped_column(String(16))
    goal: Mapped[str] = mapped_column(String(8))

    target_kcal: Mapped[int] = mapped_column(Integer)
    target_protein_g: Mapped[int] = mapped_column(Integer)
    target_carbs_g: Mapped[int] = mapped_column(Integer)
    target_fat_g: Mapped[int] = mapped_column(Integer)
    manual_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Meal(Base):
    """One logged meal (P3): the raw caption text plus estimated macro totals.

    ``log_date`` is the local calendar date in the configured timezone at the moment
    it was logged — the day a meal counts toward (DECISIONS.md, 2026-06-18). Per-item
    macros live in :class:`MealItem`; ``total_*`` are stored denormalized for fast
    daily/weekly rollups. ``approximate`` marks a best-effort estimate (vague input).
    """

    __tablename__ = "meals"
    __table_args__ = (Index("ix_meals_user_date", "telegram_user_id", "log_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    log_date: Mapped[date] = mapped_column(Date)

    raw_text: Mapped[str] = mapped_column(Text)
    total_kcal: Mapped[int] = mapped_column(Integer)
    total_protein_g: Mapped[int] = mapped_column(Integer)
    total_carbs_g: Mapped[int] = mapped_column(Integer)
    total_fat_g: Mapped[int] = mapped_column(Integer)
    approximate: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list[MealItem]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        order_by="MealItem.position",
    )


class MealItem(Base):
    """A single food item within a :class:`Meal`, with its estimated macros."""

    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)

    name: Mapped[str] = mapped_column(String(120))
    grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[int] = mapped_column(Integer)
    carbs_g: Mapped[int] = mapped_column(Integer)
    fat_g: Mapped[int] = mapped_column(Integer)

    meal: Mapped[Meal] = relationship(back_populates="items")
