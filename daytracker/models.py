"""ORM models. Added per phase; P2 introduces the user profile + targets.

Each model subclasses :class:`daytracker.db.Base` and is registered for
``create_all`` simply by being imported (see ``db.init_db``).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

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
