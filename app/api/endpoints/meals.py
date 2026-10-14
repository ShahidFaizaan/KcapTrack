"""
KCapTrack — Meal Scan endpoints.

Routes:
    POST /scan  – upload an image, run YOLO, log detected items
    GET  /logs  – retrieve meal logs for a given date
"""

from __future__ import annotations

import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.cv.inference import DetectionResult, NutritionInfo, run_inference
from app.db.models import FoodItem, MealLog, MealType, User
from app.db.session import get_db
from app.schemas.schemas import MealLogOut, MealScanResponse

router = APIRouter(prefix="/meals", tags=["Meal Scanning"])
settings = get_settings()


async def _build_nutrition_lookup(db: AsyncSession) -> dict[str, NutritionInfo]:
    """Load all FoodItem rows into an in-memory lookup keyed by yolo_class_name."""
    result = await db.execute(select(FoodItem))
    items = result.scalars().all()
    return {
        item.yolo_class_name: NutritionInfo(
            food_item_id=item.id,
            name=item.name,
            calories_per_100g=item.calories_per_100g,
            protein_per_100g=item.protein_per_100g,
            fat_per_100g=item.fat_per_100g,
            carbs_per_100g=item.carbs_per_100g,
            default_portion_g=item.default_portion_g,
        )
        for item in items
    }


def _save_upload(upload: UploadFile) -> Path:
    """Persist an uploaded file to the uploads directory."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(upload.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = upload_dir / filename

    with open(dest, "wb") as f:
        shutil.copyfileobj(upload.file, f)

    return dest


# ═══════════════════════════════════════════════════════════════════════
#  POST /meals/scan
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/scan",
    response_model=MealScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Scan a meal image with YOLO or Gemini and log nutrition",
)
async def scan_meal(
    image: Optional[UploadFile] = File(None, description="Meal photo (JPEG/PNG/WEBP)"),
    file: Optional[UploadFile] = File(None, description="Alternative upload field"),
    meal_type: MealType = Form(MealType.SNACK),
    consumed_at: Optional[date] = Form(None, description="Date consumed (defaults to today)"),
    gemini_key: Optional[str] = Form(None, description="Optional per-request Gemini API key"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a meal image, run inference (Gemini or YOLO), and persist results.

    **Pipeline:**
    1. Accept either 'image' or 'file' multipart field.
    2. Save uploaded image to ``uploads/``.
    3. Run Gemini Vision (if configured/provided) or YOLO COCO fallback.
    4. Fuzzy-match detected food items to nutrition DB.
    5. Persist each detection as a MealLog row.
    6. Return aggregated totals and itemized breakdown.
    """
    upload_file = image or file
    if not upload_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided. Please attach an image.",
        )

    # Validate content type if available
    if upload_file.content_type and upload_file.content_type not in (
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/octet-stream",
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, or WebP images are accepted.",
        )

    scan_date = consumed_at or date.today()
    saved_path = _save_upload(upload_file)

    # Build lookup
    nutrition_lookup = await _build_nutrition_lookup(db)

    # Run inference
    try:
        detections: List[DetectionResult] = run_inference(
            image_path=saved_path,
            nutrition_lookup=nutrition_lookup,
            gemini_api_key=gemini_key.strip() if gemini_key else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {e}",
        )

    if not detections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No food items detected in the image. "
                "Try a clearer photo, or add a free Google Gemini API key to recognize any cuisine (like Dosa, Biryani, Curries)!"
            ),
        )

    # Persist each detection as a MealLog row
    totals = {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}

    for det in detections:
        log = MealLog(
            user_id=user.id,
            food_item_id=det.food_item_id,
            image_path=str(saved_path),
            detected_class=det.detected_class,
            confidence=det.confidence,
            bbox_x1=det.bbox[0] if len(det.bbox) >= 4 else None,
            bbox_y1=det.bbox[1] if len(det.bbox) >= 4 else None,
            bbox_x2=det.bbox[2] if len(det.bbox) >= 4 else None,
            bbox_y2=det.bbox[3] if len(det.bbox) >= 4 else None,
            portion_g=det.portion_g,
            calories=det.calories,
            protein_g=det.protein_g,
            fat_g=det.fat_g,
            carbs_g=det.carbs_g,
            meal_type=meal_type,
            consumed_at=scan_date,
        )
        db.add(log)

        totals["calories"] += det.calories
        totals["protein_g"] += det.protein_g
        totals["fat_g"] += det.fat_g
        totals["carbs_g"] += det.carbs_g

    await db.flush()

    return {
        "image_path": str(saved_path),
        "detections": [
            {
                "detected_class": d.detected_class,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "portion_g": d.portion_g,
                "calories": d.calories,
                "protein_g": d.protein_g,
                "fat_g": d.fat_g,
                "carbs_g": d.carbs_g,
                "portion_meta": d.portion_meta,
            }
            for d in detections
        ],
        "detected_count": len(detections),
        "total_calories": round(totals["calories"], 1),
        "total_protein_g": round(totals["protein_g"], 1),
        "total_fat_g": round(totals["fat_g"], 1),
        "total_carbs_g": round(totals["carbs_g"], 1),
        "meal_type": meal_type,
        "consumed_at": scan_date,
    }


# ═══════════════════════════════════════════════════════════════════════
#  GET /meals/logs
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/logs",
    response_model=List[MealLogOut],
    summary="Get meal logs for a specific date",
)
async def get_meal_logs(
    log_date: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    """Return all meal log entries for the given date (defaults to today)."""
    target_date = log_date or date.today()
    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == user.id, MealLog.consumed_at == target_date)
        .order_by(MealLog.created_at.desc())
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
#  POST /meals/log-manual
# ═══════════════════════════════════════════════════════════════════════

from app.schemas.schemas import ManualMealLog
from app.cv.inference import NutritionInfo, _fuzzy_match_nutrition, scale_nutrition


@router.post(
    "/log-manual",
    response_model=MealLogOut,
    status_code=status.HTTP_201_CREATED,
    summary="Manually log a food item by name and portion",
)
async def log_manual_meal(
    payload: ManualMealLog,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealLog:
    """Log a food item manually — no image needed.

    Looks up the food name in the DB using fuzzy matching.
    If not found, uses the provided macro overrides.
    """
    nutrition_lookup = await _build_nutrition_lookup(db)
    info = _fuzzy_match_nutrition(payload.food_name, nutrition_lookup)

    if info and not payload.calories_override:
        scaled = scale_nutrition(info, payload.portion_g)
        calories = scaled["calories"]
        protein_g = scaled["protein_g"]
        fat_g = scaled["fat_g"]
        carbs_g = scaled["carbs_g"]
        food_item_id = info.food_item_id
        display_name = info.name
    else:
        # Use provided overrides or zeros
        calories = payload.calories_override or 0.0
        protein_g = payload.protein_g_override or 0.0
        fat_g = payload.fat_g_override or 0.0
        carbs_g = payload.carbs_g_override or 0.0
        food_item_id = None
        display_name = payload.food_name

    log = MealLog(
        user_id=user.id,
        food_item_id=food_item_id,
        image_path=None,
        detected_class=display_name,
        confidence=1.0,  # Manual entry = full confidence
        portion_g=payload.portion_g,
        calories=calories,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        meal_type=payload.meal_type,
        consumed_at=payload.consumed_at or date.today(),
    )
    db.add(log)
    await db.flush()
    return log


# ═══════════════════════════════════════════════════════════════════════
#  GET /meals/foods
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/foods",
    summary="List registered food database items for search/autocomplete",
)
async def list_food_items(
    db: AsyncSession = Depends(get_db),
) -> list:
    """Return all known food items from the food database."""
    result = await db.execute(select(FoodItem).order_by(FoodItem.name))
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "yolo_class_name": item.yolo_class_name,
            "calories_per_100g": item.calories_per_100g,
            "protein_per_100g": item.protein_per_100g,
            "fat_per_100g": item.fat_per_100g,
            "carbs_per_100g": item.carbs_per_100g,
            "default_portion_g": item.default_portion_g,
        }
        for item in items
    ]

