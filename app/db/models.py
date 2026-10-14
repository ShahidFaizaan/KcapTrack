"""
KCapTrack — SQLAlchemy ORM Models.

Defines five core domain tables:

* **User**           – credentials + timestamps
* **Biometric**      – physical stats, activity level, fitness goal
* **FoodItem**       – nutrition lookup table (per 100 g)
* **MealLog**        – individual detection results from a single scan
* **DailySummary**   – precomputed daily totals vs. target macros

All models use the shared ``Base`` from ``app.db.session``.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


from app.core.enums import ActivityLevel, FitnessGoal, Gender, MealType


# ── Utility ─────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════
#  1. User
# ═══════════════════════════════════════════════════════════════════════

class User(Base):
    """Application user with hashed credentials."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships ───────────────────────────────────────────────
    biometric: Mapped[Optional["Biometric"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan",
    )
    meal_logs: Mapped[List["MealLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )
    daily_summaries: Mapped[List["DailySummary"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ═══════════════════════════════════════════════════════════════════════
#  2. Biometric
# ═══════════════════════════════════════════════════════════════════════

class Biometric(Base):
    """User's physical profile used to compute BMR / TDEE / macro targets."""

    __tablename__ = "biometrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False,
    )

    # ── Raw inputs ──────────────────────────────────────────────────
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False, comment="Height in centimetres")
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, comment="Weight in kilograms")
    activity_level: Mapped[ActivityLevel] = mapped_column(Enum(ActivityLevel), nullable=False)
    goal: Mapped[FitnessGoal] = mapped_column(Enum(FitnessGoal), nullable=False)

    # ── Computed fields (set by the biometric service) ──────────────
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bmr: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Mifflin-St Jeor BMR (kcal/day)")
    tdee: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Total Daily Energy Expenditure")
    target_calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships ───────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="biometric")

    def __repr__(self) -> str:
        return f"<Biometric user_id={self.user_id} goal={self.goal.value}>"


# ═══════════════════════════════════════════════════════════════════════
#  3. FoodItem  (nutritional reference table)
# ═══════════════════════════════════════════════════════════════════════

class FoodItem(Base):
    """Nutritional data for a single food class (values per 100 g)."""

    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    yolo_class_name: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True,
        comment="Exact class label the YOLO model outputs",
    )
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_per_100g: Mapped[float] = mapped_column(Float, default=0.0)
    default_portion_g: Mapped[float] = mapped_column(
        Float, default=150.0,
        comment="Assumed portion when bbox area is unavailable",
    )
    source: Mapped[str] = mapped_column(String(60), default="seed_data", comment="USDA / seed_data / manual")

    def __repr__(self) -> str:
        return f"<FoodItem {self.name!r} cal={self.calories_per_100g}>"


# ═══════════════════════════════════════════════════════════════════════
#  4. MealLog  (one row per detected food item per scan)
# ═══════════════════════════════════════════════════════════════════════

class MealLog(Base):
    """A single detected food item from one image scan."""

    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    food_item_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("food_items.id", ondelete="SET NULL"), nullable=True,
    )

    # ── Detection metadata ──────────────────────────────────────────
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    detected_class: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Nutrition (computed at scan time) ────────────────────────────
    portion_g: Mapped[float] = mapped_column(Float, nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)

    meal_type: Mapped[MealType] = mapped_column(Enum(MealType), default=MealType.SNACK)
    consumed_at: Mapped[date] = mapped_column(Date, default=lambda: date.today())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # ── Relationships ───────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="meal_logs")
    food_item: Mapped[Optional["FoodItem"]] = relationship()

    def __repr__(self) -> str:
        return f"<MealLog user={self.user_id} class={self.detected_class!r} cal={self.calories}>"


# ═══════════════════════════════════════════════════════════════════════
#  5. DailySummary  (pre-aggregated daily totals)
# ═══════════════════════════════════════════════════════════════════════

class DailySummary(Base):
    """Pre-computed daily totals versus the user's target macros."""

    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "summary_date", name="uq_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Consumed totals ─────────────────────────────────────────────
    total_calories: Mapped[float] = mapped_column(Float, default=0.0)
    total_protein_g: Mapped[float] = mapped_column(Float, default=0.0)
    total_fat_g: Mapped[float] = mapped_column(Float, default=0.0)
    total_carbs_g: Mapped[float] = mapped_column(Float, default=0.0)
    meal_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Snapshot of targets at time of summary ──────────────────────
    target_calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships ───────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="daily_summaries")

    def __repr__(self) -> str:
        return f"<DailySummary user={self.user_id} date={self.summary_date}>"
