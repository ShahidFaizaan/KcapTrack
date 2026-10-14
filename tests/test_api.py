"""
Integration tests for FastAPI endpoints: root, health check, registration,
login, and biometric profile flow.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "KCapTrack" in response.text


@pytest.mark.asyncio
async def test_api_info_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "KCapTrack"
        assert data["status"] == "online"
        assert "docs" in data


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_user_flow_auth_and_profile():
    unique_id = uuid.uuid4().hex[:8]
    username = f"user_{unique_id}"
    email = f"user_{unique_id}@example.com"
    password = "SuperSecretPassword123!"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Register
        reg_resp = await client.post(
            "/api/v1/users/register",
            json={"username": username, "email": email, "password": password},
        )
        assert reg_resp.status_code == 201
        user_data = reg_resp.json()
        assert user_data["username"] == username
        assert user_data["email"] == email

        # 2. Login
        login_resp = await client.post(
            "/api/v1/users/login",
            json={"username": username, "password": password},
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Save Biometric Profile
        profile_payload = {
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "age": 26,
            "gender": "male",
            "activity_level": "moderately_active",
            "fitness_goal": "cut",
        }
        prof_resp = await client.post(
            "/api/v1/users/profile",
            json=profile_payload,
            headers=headers,
        )
        assert prof_resp.status_code == 200
        bio_data = prof_resp.json()
        assert bio_data["bmr"] > 0
        assert bio_data["tdee"] > bio_data["bmr"]
        assert bio_data["target_calories"] < bio_data["tdee"]  # Cut deficit
        assert bio_data["target_protein_g"] > 0
        assert bio_data["target_fat_g"] > 0
        assert bio_data["target_carbs_g"] > 0

        # 4. Get Biometric Profile
        get_prof = await client.get("/api/v1/users/profile", headers=headers)
        assert get_prof.status_code == 200
        assert get_prof.json()["weight_kg"] == 75.0

        # 5. Check Dashboard Summary
        dash_resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert "calories" in dash_data
        assert dash_data["calories"]["target"] == bio_data["target_calories"]

        # 6. Test Foods List
        foods_resp = await client.get("/api/v1/meals/foods")
        assert foods_resp.status_code == 200
        foods = foods_resp.json()
        assert len(foods) > 0
        food_names = [f["name"] for f in foods]
        assert "Pizza" in food_names or "Apple" in food_names

        # 7. Test Manual Meal Logging
        manual_resp = await client.post(
            "/api/v1/meals/log-manual",
            json={"food_name": "Dosa", "portion_g": 120, "meal_type": "breakfast"},
            headers=headers,
        )
        assert manual_resp.status_code == 201
        log_entry = manual_resp.json()
        assert log_entry["detected_class"] == "Dosa"
        assert log_entry["calories"] > 0
        assert log_entry["portion_g"] == 120.0

