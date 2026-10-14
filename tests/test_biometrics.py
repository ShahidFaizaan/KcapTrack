"""
Unit tests for the Mifflin-St Jeor Biometric Engine in KCapTrack.
"""

import pytest

from app.core.enums import ActivityLevel, FitnessGoal, Gender
from app.services.biometrics import (
    calculate_bmi,
    calculate_bmr,
    calculate_macros,
    calculate_target_calories,
    calculate_tdee,
    compute_biometrics,
)


def test_calculate_bmi():
    # 70 kg, 175 cm -> 70 / (1.75^2) = 22.857... -> 22.9
    bmi = calculate_bmi(70.0, 175.0)
    assert bmi == 22.9


def test_calculate_bmi_invalid_height():
    with pytest.raises(ValueError):
        calculate_bmi(70.0, 0)
    with pytest.raises(ValueError):
        calculate_bmi(70.0, -10)


def test_calculate_bmr_male():
    # Male: 10 * 80 + 6.25 * 180 - 5 * 25 + 5
    # = 800 + 1125 - 125 + 5 = 1805
    bmr = calculate_bmr(80.0, 180.0, 25, Gender.MALE)
    assert bmr == 1805


def test_calculate_bmr_female():
    # Female: 10 * 60 + 6.25 * 165 - 5 * 30 - 161
    # = 600 + 1031.25 - 150 - 161 = 1320.25 -> 1320
    bmr = calculate_bmr(60.0, 165.0, 30, Gender.FEMALE)
    assert bmr == 1320


def test_calculate_tdee_multipliers():
    bmr = 2000.0
    assert calculate_tdee(bmr, ActivityLevel.SEDENTARY) == round(2000 * 1.2)
    assert calculate_tdee(bmr, ActivityLevel.LIGHTLY_ACTIVE) == round(2000 * 1.375)
    assert calculate_tdee(bmr, ActivityLevel.MODERATELY_ACTIVE) == round(2000 * 1.55)
    assert calculate_tdee(bmr, ActivityLevel.VERY_ACTIVE) == round(2000 * 1.725)
    assert calculate_tdee(bmr, ActivityLevel.EXTRA_ACTIVE) == round(2000 * 1.9)


def test_calculate_target_calories_goals():
    tdee = 2500.0
    # CUT: -20% -> 2000
    assert calculate_target_calories(tdee, FitnessGoal.CUT) == 2000.0
    # MAINTAIN: 100% -> 2500
    assert calculate_target_calories(tdee, FitnessGoal.MAINTAIN) == 2500.0
    # BULK: +15% -> 2875
    assert calculate_target_calories(tdee, FitnessGoal.BULK) == 2875.0


def test_calculate_macros():
    target_cal = 2000.0
    # CUT: 35% protein (700 kcal / 4 = 175g), 30% fat (600 kcal / 9 = 67g), 35% carbs (700 kcal / 4 = 175g)
    protein, fat, carbs = calculate_macros(target_cal, FitnessGoal.CUT)
    assert protein == 175
    assert fat == 67
    assert carbs == 175


def test_compute_biometrics_orchestrator():
    result = compute_biometrics(
        weight_kg=75.0,
        height_cm=178.0,
        age=28,
        gender=Gender.MALE,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=FitnessGoal.CUT,
    )
    assert result.bmi == 23.7
    assert result.bmr > 0
    assert result.tdee > result.bmr
    assert result.target_calories < result.tdee  # Cut should be lower than TDEE
    assert result.target_protein_g > 0
    assert result.target_fat_g > 0
    assert result.target_carbs_g > 0
