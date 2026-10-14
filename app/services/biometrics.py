
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.core.enums import ActivityLevel, FitnessGoal, Gender


# ── Activity multipliers (Harris-Benedict convention) ───────────────────
ACTIVITY_MULTIPLIERS: Dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
    ActivityLevel.EXTRA_ACTIVE: 1.9,
}

# ── Goal calorie adjustments ───────────────────────────────────────────
GOAL_ADJUSTMENTS: Dict[FitnessGoal, float] = {
    FitnessGoal.CUT: 0.80,       # −20 % deficit
    FitnessGoal.MAINTAIN: 1.00,
    FitnessGoal.BULK: 1.15,      # +15 % surplus
}

# ── Macro splits  (protein_pct, fat_pct, carb_pct) ─────────────────────
MACRO_SPLITS: Dict[FitnessGoal, tuple[float, float, float]] = {
    FitnessGoal.CUT: (0.35, 0.30, 0.35),
    FitnessGoal.MAINTAIN: (0.30, 0.25, 0.45),
    FitnessGoal.BULK: (0.25, 0.25, 0.50),
}

# Calorie-per-gram constants
KCAL_PER_G_PROTEIN = 4.0
KCAL_PER_G_FAT = 9.0
KCAL_PER_G_CARB = 4.0


@dataclass(frozen=True)
class BiometricResult:

    bmi: float
    bmr: float
    tdee: float
    target_calories: float
    target_protein_g: float
    target_fat_g: float
    target_carbs_g: float


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI = weight / height_m^2."""
    if height_cm <= 0:
        raise ValueError("height_cm must be positive")
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: Gender,
) -> float:
    """Basal Metabolic Rate via Mifflin-St Jeor: Men = 10W + 6.25H - 5A + 5, Women = -161."""
    base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
    bmr = base + 5.0 if gender == Gender.MALE else base - 161.0
    return round(bmr)


def calculate_tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """TDEE = BMR × activity multiplier."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return round(bmr * multiplier)


def calculate_target_calories(tdee: float, goal: FitnessGoal) -> float:
    """Adjust TDEE by goal: cut (-20%), maintain, bulk (+15%)."""
    factor = GOAL_ADJUSTMENTS.get(goal, 1.0)
    return round(tdee * factor)


def calculate_macros(
    target_calories: float,
    goal: FitnessGoal,
) -> tuple[float, float, float]:
    """Protein / fat / carb targets in grams using goal-based macro split."""
    p_pct, f_pct, c_pct = MACRO_SPLITS.get(goal, (0.30, 0.25, 0.45))

    protein_g = round((target_calories * p_pct) / KCAL_PER_G_PROTEIN)
    fat_g = round((target_calories * f_pct) / KCAL_PER_G_FAT)
    carbs_g = round((target_calories * c_pct) / KCAL_PER_G_CARB)

    return protein_g, fat_g, carbs_g


def compute_biometrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: Gender,
    activity_level: ActivityLevel,
    goal: FitnessGoal,
) -> BiometricResult:
    bmi = calculate_bmi(weight_kg, height_cm)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    target_cal = calculate_target_calories(tdee, goal)
    protein_g, fat_g, carbs_g = calculate_macros(target_cal, goal)

    return BiometricResult(
        bmi=bmi,
        bmr=bmr,
        tdee=tdee,
        target_calories=target_cal,
        target_protein_g=protein_g,
        target_fat_g=fat_g,
        target_carbs_g=carbs_g,
    )
