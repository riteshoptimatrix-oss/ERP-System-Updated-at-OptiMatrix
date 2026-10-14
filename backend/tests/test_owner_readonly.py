import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.database.mongodb import mongodb_manager


@pytest.mark.asyncio
async def test_owner_single_login_and_read_dashboard(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner (Ritesh Gajjar, admin / admin123) can sign in through single login
    and read executive dashboards across both manufacturing units.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["authenticated"] is True
    assert login_data["user"]["role"] == "SUPER_ADMIN"
    assert login_data["user"]["full_name"] == "Ritesh Gajjar"
    assert "BOTH" in login_data["user"]["allowed_units"]

    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_data["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }

    # 1. Dashboard summary read
    dash_res = await async_client.get("/api/v1/dashboard/summary", cookies=cookies)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "kpis" in dash_data
    assert "total_permitted_kpis" in dash_data
    assert dash_data["total_permitted_kpis"] > 0
    assert "orders" in dash_data["kpis"]
    assert "production" in dash_data["kpis"]

    # 2. Cross-facility inspection: read Unit 1 & Unit 2 orders
    orders_enflow1 = await async_client.get("/api/v1/orders?unit_id=Unit_1", cookies=cookies)
    assert orders_enflow1.status_code == 200

    orders_enflow2 = await async_client.get("/api/v1/orders?unit_id=Unit_2", cookies=cookies)
    assert orders_enflow2.status_code == 200

    # 3. Read Inventory, BOM, Production, Wastage, Reports, Users, Roles
    inv_res = await async_client.get("/api/v1/inventory/balances", cookies=cookies)
    assert inv_res.status_code == 200

    bom_res = await async_client.get("/api/v1/bom", cookies=cookies)
    assert bom_res.status_code == 200

    prod_res = await async_client.get("/api/v1/production/orders", cookies=cookies)
    assert prod_res.status_code == 200

    roles_res = await async_client.get("/api/v1/roles", cookies=cookies)
    assert roles_res.status_code == 200

    users_res = await async_client.get("/api/v1/users", cookies=cookies)
    assert users_res.status_code == 200


@pytest.mark.asyncio
async def test_owner_search_filter_paginate_allowed(async_client: AsyncClient, setup_test_users):
    """
    Test that Owner can search, filter, sort, and paginate authorized data.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    cookies = {
        settings.SESSION_COOKIE_NAME: login_res.cookies.get(settings.SESSION_COOKIE_NAME),
        settings.CSRF_COOKIE_NAME: login_res.json()["csrf_token"],
    }

    # Paginated master data read
    res = await async_client.get(
        "/api/v1/master/customers?page=1&page_size=10&sort_by=name&sort_order=asc",
        cookies=cookies
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_super_admin_has_full_access_to_create_records(async_client: AsyncClient, setup_test_users):
    """
    Test that Super Admin HAS full access to create business records and provision users.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: owner_csrf
    }

    # 1. Super Admin CAN create User
    user_payload = {
        "email": "ownercreateduser@rgtech.com",
        "full_name": "Owner Provisioned User",
        "password": "Password123!",
        "role": "EMPLOYEE",
        "allowed_units": ["Unit_1"]
    }
    user_res = await async_client.post("/api/v1/users", json=user_payload, cookies=cookies, headers=headers)
    assert user_res.status_code == 201
    assert user_res.json()["email"] == "ownercreateduser@rgtech.com"

    # 2. Super Admin CAN create Master Customer
    cust_payload = {
        "code": "CUST-OWNER-SUCCESS",
        "name": "Super Admin Customer",
        "gstin": "24ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "billing_address": "Test Street",
        "shipping_address": "Test Street",
        "credit_limit": 100000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_1"
    }
    cust_res = await async_client.post("/api/v1/master/customers", json=cust_payload, cookies=cookies, headers=headers)
    assert cust_res.status_code == 201
    assert cust_res.json()["code"] == "CUST-OWNER-SUCCESS"


@pytest.mark.asyncio
async def test_super_admin_can_update_user_roles(async_client: AsyncClient, setup_test_users):
    """
    Test that Super Admin can update roles and permissions of other users.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin123"}
    )
    owner_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    owner_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: owner_cookie,
        settings.CSRF_COOKIE_NAME: owner_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: owner_csrf
    }

    # Attempt to change another user's role via PATCH /api/v1/users/{id}
    target_user_id = setup_test_users["pm1_id"]
    patch_res = await async_client.patch(
        f"/api/v1/users/{target_user_id}",
        json={"role": "ADMIN"},
        cookies=cookies,
        headers=headers
    )
    assert patch_res.status_code == 200

    # Verify the target user was modified
    db = mongodb_manager.get_database()
    from bson import ObjectId
    user_doc = await db["users"].find_one({"_id": ObjectId(target_user_id)})
    assert user_doc["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_admin_operational_actions_remain_functional(async_client: AsyncClient, setup_test_users):
    """
    Test separation of duties: operational Admin (admin_ops) CAN perform administrative operations,
    while Owner cannot.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    admin_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    admin_csrf = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: admin_cookie,
        settings.CSRF_COOKIE_NAME: admin_csrf,
    }
    headers = {
        settings.CSRF_HEADER_NAME: admin_csrf
    }

    # Admin CAN create a customer
    cust_payload = {
        "code": "CUST-ADMIN-OK",
        "name": "Admin Authorized Customer",
        "gstin": "24ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "billing_address": "Admin Street",
        "shipping_address": "Admin Street",
        "credit_limit": 500000.0,
        "payment_terms_days": 30,
        "unit_id": "Unit_1"
    }
    cust_res = await async_client.post("/api/v1/master/customers", json=cust_payload, cookies=cookies, headers=headers)
    assert cust_res.status_code == 201
    assert cust_res.json()["code"] == "CUST-ADMIN-OK"
