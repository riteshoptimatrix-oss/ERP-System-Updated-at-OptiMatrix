import io
import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.database.mongodb import mongodb_manager
from app.models.user import RoleName, ManufacturingUnit
from app.schemas.reports import ImportEntityType, ImportBatchStatus


@pytest.mark.asyncio
async def test_cross_module_reports_reconciliation(async_client: AsyncClient, setup_test_users, setup_test_db):
    """Verify that reports aggregate real data across orders, invoices, and inventory."""
    db = setup_test_db

    # Login as Super Admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # Seed test invoice
    await db["invoices"].insert_one({
        "invoice_number": "INV-TEST-REP-01",
        "invoice_date": "2026-10-10",
        "customer_name": "Test Customer Ltd",
        "unit_id": "Unit_1",
        "total_amount": 50000.0,
        "amount_paid": 30000.0,
        "balance_amount": 20000.0,
        "status": "PARTIALLY_PAID",
    })

    # Seed test stock balance
    await db["stock_balances"].insert_one({
        "material_code": "RM-REP-01",
        "material_name": "Aluminium Ingot",
        "quantity": 120.0,
        "uom": "KG",
        "reorder_level": 50.0,
        "unit_id": "Unit_1",
        "item_type": "RAW_MATERIAL",
    })

    # Test Sales Report
    res_sales = await async_client.get(
        "/api/v1/reports/sales?unit_id=Unit_1&start_date=2026-10-01&end_date=2026-10-31",
        headers=headers,
    )
    assert res_sales.status_code == 200
    sales_json = res_sales.json()
    assert sales_json["report_type"] == "sales"
    assert len(sales_json["items"]) >= 1
    assert sales_json["items"][0]["invoice_number"] == "INV-TEST-REP-01"
    assert sales_json["total"] >= 1

    # Test Inventory Report
    res_inv = await async_client.get(
        "/api/v1/reports/inventory?unit_id=Unit_1",
        headers=headers,
    )
    assert res_inv.status_code == 200
    inv_json = res_inv.json()
    assert inv_json["report_type"] == "inventory"
    assert any(i["item_code"] == "RM-REP-01" for i in inv_json["items"])

    # Test Report Export to CSV
    res_csv = await async_client.get(
        "/api/v1/reports/sales/export?export_format=csv&unit_id=Unit_1",
        headers=headers,
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert b"INV-TEST-REP-01" in res_csv.content


@pytest.mark.asyncio
async def test_excel_migration_template_and_dry_run_validation(async_client: AsyncClient, setup_test_users, setup_test_db):
    """Test template generation, CSV/XLSX upload, dry-run error detection, and duplicate checking."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Download Customer template
    tmpl_res = await async_client.get(
        "/api/v1/imports/templates/customers",
        headers=headers,
    )
    assert tmpl_res.status_code == 200
    assert len(tmpl_res.content) > 0

    # 2. Upload file with valid row and intentional invalid/duplicate rows
    csv_content = (
        "Code,Name,GSTIN,PAN,Contact Person,Phone,Email,Billing Address,Shipping Address,Credit Limit,Payment Terms Days,Facility\n"
        "CUST-NEW-01,Alpha Industrial,24ABCDE1111A1Z1,ABCDE1111A,John,9998887771,alpha@test.com,Plot 1,Plot 1,100000,30,Unit_1\n"
        ",Missing Code Corp,24ABCDE2222A1Z2,ABCDE2222A,Jane,9998887772,jane@test.com,Plot 2,Plot 2,200000,30,Unit_1\n"
        "CUST-NEW-01,Duplicate Code Corp,24ABCDE3333A1Z3,ABCDE3333A,Jack,9998887773,jack@test.com,Plot 3,Plot 3,300000,30,INVALID_UNIT\n"
    ).encode("utf-8")

    files = {"file": ("test_customers.csv", csv_content, "text/csv")}
    data = {"entity_type": "customers"}

    dry_res = await async_client.post(
        "/api/v1/imports/dry-run",
        data=data,
        files=files,
        headers=headers,
    )
    assert dry_res.status_code == 200
    dry_json = dry_res.json()
    assert dry_json["total_rows"] == 3
    assert dry_json["can_commit"] is False  # Has missing code and duplicate
    assert dry_json["error_rows_count"] >= 2
    assert len(dry_json["errors"]) >= 2
    error_msgs = [e["error_message"] for e in dry_json["errors"]]
    assert any("Missing required field 'Code'" in m for m in error_msgs)
    assert any("Duplicate value" in m for m in error_msgs)


@pytest.mark.asyncio
async def test_excel_migration_idempotent_commit(async_client: AsyncClient, setup_test_users, setup_test_db):
    """Test valid dry-run commit into production database and idempotent protection."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    valid_csv = (
        "Code,Name,GSTIN,PAN,Contact Person,Phone,Email,Billing Address,Shipping Address,Credit Limit,Payment Terms Days,Facility\n"
        "CUST-CLEAN-01,Clean Precision Ltd,24CLEAN1111A1Z1,CLEAN1111A,Karan,9876543210,karan@clean.com,Plot 10,Plot 10,500000,30,Unit_1\n"
        "CUST-CLEAN-02,Apex Engineering,24APEX2222A1Z2,APEX2222A,Suresh,9876543211,suresh@apex.com,Plot 20,Plot 20,750000,45,BOTH\n"
    ).encode("utf-8")

    files = {"file": ("valid_customers.csv", valid_csv, "text/csv")}
    data = {"entity_type": "customers"}

    # 1. Dry run
    dry_res = await async_client.post(
        "/api/v1/imports/dry-run",
        data=data,
        files=files,
        headers=headers,
    )
    assert dry_res.status_code == 200
    dry_json = dry_res.json()
    assert dry_json["can_commit"] is True
    assert dry_json["valid_rows_count"] == 2
    batch_token = dry_json["batch_token"]

    # 2. Authorized Commit
    commit_res = await async_client.post(
        "/api/v1/imports/commit",
        json={
            "batch_token": batch_token,
            "unit_id": "Unit_1",
            "notes": "Initial legacy migration",
        },
        headers=headers,
    )
    assert commit_res.status_code == 201
    commit_json = commit_res.json()
    assert commit_json["status"] == "COMMITTED"
    assert commit_json["inserted_count"] == 2

    # 3. Verify records landed in production MongoDB collection
    db = setup_test_db
    doc1 = await db["customers"].find_one({"code": "CUST-CLEAN-01"})
    assert doc1 is not None
    assert doc1["name"] == "Clean Precision Ltd"

    # 4. Verify idempotent commit attempt does not re-insert or error
    commit_again = await async_client.post(
        "/api/v1/imports/commit",
        json={
            "batch_token": batch_token,
            "unit_id": "Unit_1",
        },
        headers=headers,
    )
    assert commit_again.status_code == 201
    assert "already committed" in commit_again.json()["message"]

    # 5. Verify batch listed in audit batch history
    batch_list_res = await async_client.get(
        "/api/v1/imports/batches",
        headers=headers,
    )
    assert batch_list_res.status_code == 200
    batches = batch_list_res.json()["items"]
    assert any(b["batch_token"] == batch_token for b in batches)
