import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.database.mongodb import mongodb_manager


@pytest.mark.asyncio
async def test_dashboard_summary_Unit_1_super_admin(async_client: AsyncClient, setup_test_users):
    """
    Test Super Admin receives full permitted summary for Unit 1.
    """
    # 1. Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

    # 2. Query dashboard summary for Unit 1
    res = await async_client.get(
        "/api/v1/dashboard/summary?unit_id=Unit_1",
        cookies={settings.SESSION_COOKIE_NAME: cookie}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["active_unit"] == "Unit_1"
    assert data["total_permitted_kpis"] == 8
    assert "orders" in data["kpis"]
    assert "production" in data["kpis"]
    assert data["kpis"]["orders"]["value"] == 0  # Verified real count from clean collection


@pytest.mark.asyncio
async def test_dashboard_summary_cross_unit_access_denial(async_client: AsyncClient, setup_test_users):
    """
    Test Unit 1 Production Manager cannot access Unit 2 dashboard summary (403 Forbidden).
    """
    # 1. Login as pm1 (scoped only to Unit_1)
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pm1@testcorp.com", "password": "ValidPassword123!"}
    )
    cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

    # 2. Attempt to query Unit_2
    res = await async_client.get(
        "/api/v1/dashboard/summary?unit_id=Unit_2",
        cookies={settings.SESSION_COOKIE_NAME: cookie}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_dashboard_summary_permission_masking(async_client: AsyncClient, setup_test_users):
    """
    Test Production Manager only receives KPIs for permitted modules (e.g., orders, production, inventory),
    while unauthorized modules (e.g., attendance, hr approvals) are masked (None).
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pm1@testcorp.com", "password": "ValidPassword123!"}
    )
    cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

    res = await async_client.get(
        "/api/v1/dashboard/summary?unit_id=Unit_1",
        cookies={settings.SESSION_COOKIE_NAME: cookie}
    )
    assert res.status_code == 200
    data = res.json()
    # Permitted for Production Manager:
    assert data["kpis"]["production"] is not None
    assert data["kpis"]["orders"] is not None
    # Masked/Unauthorized for Production Manager:
    assert data["kpis"]["attendance"] is None


@pytest.mark.asyncio
async def test_dashboard_activity_feed(async_client: AsyncClient, setup_test_users):
    """
    Test recent operations activity feed returns valid unit activities.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)

    res = await async_client.get(
        "/api/v1/dashboard/activity?unit_id=Unit_1",
        cookies={settings.SESSION_COOKIE_NAME: cookie}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["active_unit"] == "Unit_1"
    assert isinstance(data["activities"], list)
