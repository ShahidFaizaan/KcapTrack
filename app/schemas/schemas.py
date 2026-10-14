"""
KCapTrack — Pydantic request / response schemas.

Organized by domain entity. All schemas use ``model_config`` with
``from_attributes = True`` so they can be built directly from ORM rows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import ActivityLevel, FitnessGoal, Gender, MealType


# ═══════════════════════════════════════════════════════════════════════
#  Auth / User
# ═══════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════════
#  Biometric / Profile
# ═══════════════════════════════════════════════════════════════════════

class BiometricCreate(BaseModel):
    """Payload sent when creating or updating a user's biometric profile."""
    age: int = Field(..., ge=13, le=120)
    gender: Gender
    height_cm: float = Field(..., ge=50, le=300)
    weight_kg: float = Field(..., ge=20, le=500)
    activity_level: ActivityLevel
    goal: FitnessGoal = Field(..., validation_alias=AliasChoices("goal", "fitness_goal"))


class BiometricOut(BaseModel):
    """Full biometric response including computed fields."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    age: int
    gender: Gender
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    goal: FitnessGoal
    bmi: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    target_calories: Optional[float] = None
    target_protein_g: Optional[float] = None
    target_fat_g: Optional[float] = None
    target_carbs_g: Optional[float] = None
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════
#  FoodItem
# ═══════════════════════════════════════════════════════════════════════

class FoodItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    yolo_class_name: str
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    fiber_per_100g: float
    default_portion_g: float
    source: str


# ═══════════════════════════════════════════════════════════════════════
#  Meal Scan / Log
# ═══════════════════════════════════════════════════════════════════════

class DetectedItem(BaseModel):
    """A single food item detected by the vision pipeline."""
    detected_class: str
    confidence: float
    bbox: List[float] = Field(default_factory=list, description="[x1, y1, x2, y2]")
    portion_g: float
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    portion_meta: Optional[str] = None


class MealScanResponse(BaseModel):
    """Response returned after scanning a meal image."""
    image_path: str
    detections: List[DetectedItem]
    detected_count: int = 0
    total_calories: float
    total_protein_g: float
    total_fat_g: float
    total_carbs_g: float
    meal_type: MealType
    consumed_at: date


class MealLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    detected_class: str
    confidence: float
    portion_g: float
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    meal_type: MealType
    consumed_at: date
    created_at: datetime


class ManualMealLog(BaseModel):
    """Payload for manually logging a food item without image scanning."""
    food_name: str = Field(..., min_length=1, max_length=120, description="Name of the food")
    portion_g: float = Field(..., gt=0, le=5000, description="Portion size in grams")
    meal_type: MealType = MealType.SNACK
    consumed_at: Optional[date] = None
    # Optional manual overrides (used when food not found in DB)
    calories_override: Optional[float] = Field(None, ge=0)
    protein_g_override: Optional[float] = Field(None, ge=0)
    fat_g_override: Optional[float] = Field(None, ge=0)
    carbs_g_override: Optional[float] = Field(None, ge=0)


# ═══════════════════════════════════════════════════════════════════════
#  Daily Summary / Dashboard
# ═══════════════════════════════════════════════════════════════════════

class MacroProgress(BaseModel):
    """Shows consumed vs target for a single macro."""
    consumed: float
    target: Optional[float] = None
    remaining: Optional[float] = None
    percentage: Optional[float] = None


class DailySummaryOut(BaseModel):
    """Dashboard-friendly daily summary with progress indicators."""
    model_config = ConfigDict(from_attributes=True)

    summary_date: date
    meal_count: int = 0

    calories: MacroProgress
    protein: MacroProgress
    fat: MacroProgress
    carbs: MacroProgress
