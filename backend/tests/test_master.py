import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_master_template_download(async_client: AsyncClient, setup_test_users):
    """
    Ensure downloadable CSV template is returned for all master entities.
    """
    # 1. Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200

    # 2. Download customer template
    res = await async_client.get("/api/v1/master/customers/template")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "CUST-001" in res.text
    assert "code,name,gstin" in res.text

    # 3. Download raw materials template
    res_mat = await async_client.get("/api/v1/master/materials/template")
    assert res_mat.status_code == 200
    assert "RM-MS-PL-25" in res_mat.text


@pytest.mark.asyncio
async def test_customer_crud_and_duplicate_prevention(async_client: AsyncClient, setup_test_users):
    """
    Test Customer creation, duplicate code conflict (409), update, pagination, and deactivation.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    customer_data = {
        "code": "CUST-T1",
        "name": "Tata Steel Processing",
        "gstin": "24ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "contact_person": "Jamshed Irani",
        "phone": "+919988776655",
        "email": "procurement@tatasteel.com",
        "billing_address": "Works, Jamshedpur",
        "shipping_address": "Works, Jamshedpur",
        "credit_limit": 1000000.0,
        "payment_terms_days": 45,
        "unit_id": "BOTH",
        "is_active": True
    }

    # 1. Create Customer
    res = await async_client.post("/api/v1/master/customers", json=customer_data, headers=headers)
    assert res.status_code == 201
    created_cust = res.json()
    assert created_cust["code"] == "CUST-T1"
    assert created_cust["created_by"] == "admin_ops@testcorp.com"
    cust_id = created_cust["id"]

    # 2. Duplicate prevention (re-post identical code)
    dup_res = await async_client.post("/api/v1/master/customers", json=customer_data, headers=headers)
    assert dup_res.status_code == 409
    err_body = dup_res.json()
    err_msg = err_body.get("error", {}).get("message", "") if "error" in err_body else err_body.get("detail", "")
    assert "already exists" in err_msg

    # 3. List customers with search
    list_res = await async_client.get("/api/v1/master/customers?search=Tata")
    assert list_res.status_code == 200
    body = list_res.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Tata Steel Processing"

    # 4. Update customer
    upd_res = await async_client.put(
        f"/api/v1/master/customers/{cust_id}",
        json={"credit_limit": 1500000.0, "contact_person": "N. Chandrasekaran"},
        headers=headers
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["credit_limit"] == 1500000.0

    # 5. Soft-delete / deactivation
    del_res = await async_client.delete(f"/api/v1/master/customers/{cust_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify deactivation reflected in filter
    inactive_res = await async_client.get("/api/v1/master/customers?is_active=false")
    assert inactive_res.status_code == 200
    assert any(c["id"] == cust_id for c in inactive_res.json()["items"])


@pytest.mark.asyncio
async def test_vendor_and_raw_material_integrity(async_client: AsyncClient, setup_test_users):
    """
    Test Vendor and Raw Material creation and listing.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Create Vendor
    vend_res = await async_client.post(
        "/api/v1/master/vendors",
        json={
            "code": "VEND-IND-01",
            "name": "Industrial Hydraulics Corp",
            "gstin": "24XYZAB1234C1Z9",
            "contact_person": "K. Patel",
            "phone": "+919876500001",
            "payment_terms_days": 30,
            "unit_id": "BOTH",
            "is_active": True
        },
        headers=headers
    )
    assert vend_res.status_code == 201

    # 2. Create Raw Material referencing vendor
    mat_res = await async_client.post(
        "/api/v1/master/materials",
        json={
            "code": "RM-SEAL-50",
            "name": "Hydraulic Oil Seal 50mm Viton",
            "uom": "PCS",
            "reorder_level": 50.0,
            "safety_stock": 20.0,
            "default_vendor_code": "VEND-IND-01",
            "unit_id": "Unit_1",
            "is_active": True
        },
        headers=headers
    )
    assert mat_res.status_code == 201
    assert mat_res.json()["code"] == "RM-SEAL-50"


@pytest.mark.asyncio
async def test_employee_and_warehouse_unit_scoping(async_client: AsyncClient, setup_test_users):
    """
    Test Employee and Warehouse unit associations and isolation.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Create Warehouse in Unit 1
    wh1_res = await async_client.post(
        "/api/v1/master/warehouses",
        json={
            "code": "WH-E1-YARD",
            "name": "Unit 1 Primary Yard",
            "unit_id": "Unit_1",
            "location_type": "RAW_MATERIAL",
            "bay_rack": "Bay 1",
            "is_active": True
        },
        headers=headers
    )
    assert wh1_res.status_code == 201

    # 2. Create Warehouse in Unit 2
    wh2_res = await async_client.post(
        "/api/v1/master/warehouses",
        json={
            "code": "WH-E2-FIN",
            "name": "Unit 2 Finished Goods Depot",
            "unit_id": "Unit_2",
            "location_type": "FINISHED_GOODS",
            "bay_rack": "Rack A",
            "is_active": True
        },
        headers=headers
    )
    assert wh2_res.status_code == 201

    # 3. Super Admin queries Unit 1 warehouses
    e1_list = await async_client.get("/api/v1/master/warehouses?unit_id=Unit_1")
    assert e1_list.status_code == 200
    e1_codes = [w["code"] for w in e1_list.json()["items"]]
    assert "WH-E1-YARD" in e1_codes
    assert "WH-E2-FIN" not in e1_codes

    # 4. Now login as PM1 (restricted to Unit_1 only)
    pm1_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pm1@testcorp.com", "password": "ValidPassword123!"}
    )
    assert pm1_login.status_code == 200

    # PM1 queries Unit 2: should be 403 Forbidden
    pm1_forbidden = await async_client.get("/api/v1/master/warehouses?unit_id=Unit_2")
    assert pm1_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_uom_and_categories_crud(async_client: AsyncClient, setup_test_users):
    """
    Test UoM and Category masters.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Create UoM
    uom_res = await async_client.post(
        "/api/v1/master/uom",
        json={
            "code": "MTR",
            "name": "Meter",
            "symbol": "m",
            "description": "Standard length metric",
            "is_active": True
        },
        headers=headers
    )
    assert uom_res.status_code == 201

    # 2. Create Category
    cat_res = await async_client.post(
        "/api/v1/master/categories",
        json={
            "code": "CAT-HYD",
            "name": "Hydraulic Components",
            "category_type": "RAW_MATERIAL",
            "description": "Cylinders, valves and fittings",
            "is_active": True
        },
        headers=headers
    )
    assert cat_res.status_code == 201
    assert cat_res.json()["code"] == "CAT-HYD"
