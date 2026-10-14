"""
KCapTrack — Dashboard / Summary endpoints.

Routes:
    GET /summary  – daily progress vs. biometric targets
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Biometric, DailySummary, MealLog, User
from app.db.session import get_db
from app.schemas.schemas import DailySummaryOut, MacroProgress

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _progress(consumed: float, target: Optional[float]) -> MacroProgress:
    """Build a MacroProgress object with remaining and percentage."""
    if target and target > 0:
        remaining = round(target - consumed, 1)
        percentage = round((consumed / target) * 100, 1)
    else:
        remaining = None
        percentage = None
    return MacroProgress(
        consumed=round(consumed, 1),
        target=round(target, 1) if target else None,
        remaining=remaining,
        percentage=percentage,
    )


@router.get(
    "/summary",
    response_model=DailySummaryOut,
    summary="Get daily nutrition progress vs. targets",
)
async def get_daily_summary(
    summary_date: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the authenticated user's daily nutrition totals and progress.

    Aggregates all ``meal_logs`` for the requested date and compares
    against the user's biometric targets.  If a ``daily_summaries``
    cache row exists it is updated; otherwise one is created.
    """
    target_date = summary_date or date.today()

    # ── Aggregate consumed totals from meal_logs ────────────────────
    agg = await db.execute(
        select(
            func.coalesce(func.sum(MealLog.calories), 0).label("cal"),
            func.coalesce(func.sum(MealLog.protein_g), 0).label("pro"),
            func.coalesce(func.sum(MealLog.fat_g), 0).label("fat"),
            func.coalesce(func.sum(MealLog.carbs_g), 0).label("carb"),
            func.count(MealLog.id).label("cnt"),
        ).where(
            MealLog.user_id == user.id,
            MealLog.consumed_at == target_date,
        )
    )
    row = agg.one()
    cal, pro, fat, carb, meal_count = (
        float(row.cal), float(row.pro), float(row.fat), float(row.carb), int(row.cnt),
    )

    # ── Load targets from biometric profile ─────────────────────────
    bio_result = await db.execute(
        select(Biometric).where(Biometric.user_id == user.id)
    )
    bio = bio_result.scalar_one_or_none()

    t_cal = bio.target_calories if bio else None
    t_pro = bio.target_protein_g if bio else None
    t_fat = bio.target_fat_g if bio else None
    t_carb = bio.target_carbs_g if bio else None

    # ── Upsert daily_summaries cache ────────────────────────────────
    ds_result = await db.execute(
        select(DailySummary).where(
            DailySummary.user_id == user.id,
            DailySummary.summary_date == target_date,
        )
    )
    ds = ds_result.scalar_one_or_none()

    if ds:
        ds.total_calories = cal
        ds.total_protein_g = pro
        ds.total_fat_g = fat
        ds.total_carbs_g = carb
        ds.meal_count = meal_count
        ds.target_calories = t_cal
        ds.target_protein_g = t_pro
        ds.target_fat_g = t_fat
        ds.target_carbs_g = t_carb
    else:
        ds = DailySummary(
            user_id=user.id,
            summary_date=target_date,
            total_calories=cal,
            total_protein_g=pro,
            total_fat_g=fat,
            total_carbs_g=carb,
            meal_count=meal_count,
            target_calories=t_cal,
            target_protein_g=t_pro,
            target_fat_g=t_fat,
            target_carbs_g=t_carb,
        )
        db.add(ds)

    await db.flush()

    # ── Build response ──────────────────────────────────────────────
    return {
        "summary_date": target_date,
        "meal_count": meal_count,
        "calories": _progress(cal, t_cal),
        "protein": _progress(pro, t_pro),
        "fat": _progress(fat, t_fat),
        "carbs": _progress(carb, t_carb),
    }
