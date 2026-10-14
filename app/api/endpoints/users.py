"""
KCapTrack — User & Profile endpoints.

Routes:
    POST /register       – create a new user
    POST /login          – authenticate and receive JWT
    POST /profile        – create / update biometric profile
    GET  /profile        – retrieve biometric profile with computed targets
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Biometric, User
from app.db.session import get_db
from app.schemas.schemas import (
    BiometricCreate,
    BiometricOut,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.biometrics import compute_biometrics

router = APIRouter(prefix="/users", tags=["Users & Profile"])


# ═══════════════════════════════════════════════════════════════════════
#  Registration
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Create a new user account.

    Returns the created user (without password).
    Raises 409 if username or email already exists.
    """
    # Check duplicates
    existing = await db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ═══════════════════════════════════════════════════════════════════════
#  Login (JWT)
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get a JWT token",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify credentials and return a bearer token."""
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


# ═══════════════════════════════════════════════════════════════════════
#  Biometric Profile — POST (upsert)
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/profile",
    response_model=BiometricOut,
    summary="Create or update biometric profile",
)
async def upsert_profile(
    payload: BiometricCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Biometric:
    """Save or update the authenticated user's biometric profile.

    Automatically computes BMI, BMR, TDEE, and macro targets using
    the Mifflin-St Jeor equation pipeline.
    """
    # Compute biometrics
    result = compute_biometrics(
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        goal=payload.goal,
    )

    # Upsert
    existing = await db.execute(
        select(Biometric).where(Biometric.user_id == user.id)
    )
    bio = existing.scalar_one_or_none()

    if bio:
        # Update existing
        for field_name in (
            "age", "gender", "height_cm", "weight_kg",
            "activity_level", "goal",
        ):
            setattr(bio, field_name, getattr(payload, field_name))
        bio.bmi = result.bmi
        bio.bmr = result.bmr
        bio.tdee = result.tdee
        bio.target_calories = result.target_calories
        bio.target_protein_g = result.target_protein_g
        bio.target_fat_g = result.target_fat_g
        bio.target_carbs_g = result.target_carbs_g
    else:
        bio = Biometric(
            user_id=user.id,
            **payload.model_dump(),
            bmi=result.bmi,
            bmr=result.bmr,
            tdee=result.tdee,
            target_calories=result.target_calories,
            target_protein_g=result.target_protein_g,
            target_fat_g=result.target_fat_g,
            target_carbs_g=result.target_carbs_g,
        )
        db.add(bio)

    await db.flush()
    await db.refresh(bio)
    return bio


# ═══════════════════════════════════════════════════════════════════════
#  Biometric Profile — GET
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/profile",
    response_model=BiometricOut,
    summary="Get biometric profile",
)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Biometric:
    """Retrieve the authenticated user's biometric profile."""
    result = await db.execute(
        select(Biometric).where(Biometric.user_id == user.id)
    )
    bio = result.scalar_one_or_none()

    if not bio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biometric profile not found. Please create one first.",
        )

    return bio
