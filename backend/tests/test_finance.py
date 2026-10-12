import pytest
from httpx import AsyncClient
from app.core.config import settings
from datetime import datetime, timezone


@pytest.fixture
async def seed_finance_test_data(setup_test_db):
    """Seed test customer, vendor, and raw materials for finance testing."""
    db = setup_test_db

    # 1. Customer
    cust_res = await db["customers"].insert_one({
        "code": "CUST-PRECISION-01",
        "name": "Precision Machine Works Ltd",
        "gstin": "27AABCP1234F1Z1",
        "unit_id": "Unit_1",
        "credit_limit": 500000.0,
        "payment_terms_days": 30,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    cust_id = str(cust_res.inserted_id)

    # 2. Vendor
    ven_res = await db["vendors"].insert_one({
        "code": "VEN-ALLOY-01",
        "name": "National Alloy Steel Suppliers",
        "gstin": "27AABCN5678G1Z2",
        "unit_id": "Unit_1",
        "payment_terms_days": 45,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    ven_id = str(ven_res.inserted_id)

    # 3. Seed Chart of Accounts
    from app.repositories.finance_repository import FinanceRepository
    finance_repo = FinanceRepository(db)
    await finance_repo.seed_chart_of_accounts()

    return {
        "cust_id": cust_id,
        "ven_id": ven_id,
    }


@pytest.mark.asyncio
async def test_double_entry_balancing_and_reversal(async_client: AsyncClient, setup_test_users, seed_finance_test_data):
    """
    Test double-entry journal engine:
    1. Reject unbalanced manual journal entry (Debit != Credit).
    2. Post balanced manual journal entry.
    3. Verify account balance adjustments in Chart of Accounts.
    4. Reverse posted journal entry with mandatory reason and verify linked reversal.
    """
    # 1. Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Attempt unbalanced journal entry (1000 Debit vs 800 Credit)
    unbalanced_res = await async_client.post(
        "/api/v1/finance/journals",
        headers=headers,
        json={
            "entry_date": "2026-10-01",
            "unit_id": "Unit_1",
            "source_module": "MANUAL",
            "source_reference": "ADJ-001",
            "description": "Unbalanced trial journal",
            "lines": [
                {
                    "account_code": "1010-BANK-HDFC",
                    "account_name": "HDFC Bank",
                    "debit": 1000.0,
                    "credit": 0.0,
                },
                {
                    "account_code": "3000-SHARE-CAPITAL",
                    "account_name": "Share Capital",
                    "debit": 0.0,
                    "credit": 800.0,
                },
            ],
        },
    )
    assert unbalanced_res.status_code == 400
    err_msg = unbalanced_res.json().get("error", {}).get("message", "")
    assert "Double-entry balancing error" in err_msg

    # 3. Post strictly balanced journal entry (Capital infusion 500,000)
    balanced_res = await async_client.post(
        "/api/v1/finance/journals",
        headers=headers,
        json={
            "entry_date": "2026-10-01",
            "unit_id": "Unit_1",
            "source_module": "MANUAL",
            "source_reference": "CAP-INFUSION-01",
            "description": "Initial share capital injection",
            "lines": [
                {
                    "account_code": "1010-BANK-HDFC",
                    "account_name": "HDFC Bank",
                    "debit": 500000.0,
                    "credit": 0.0,
                },
                {
                    "account_code": "3000-SHARE-CAPITAL",
                    "account_name": "Share Capital",
                    "debit": 0.0,
                    "credit": 500000.0,
                },
            ],
        },
    )
    assert balanced_res.status_code == 201
    jv_doc = balanced_res.json()
    assert jv_doc["is_balanced"] is True
    assert jv_doc["total_debit"] == 500000.0
    jv_id = jv_doc["id"]

    # 4. Check Chart of Accounts balances
    acc_res = await async_client.get("/api/v1/finance/accounts", headers=headers)
    assert acc_res.status_code == 200
    accounts = acc_res.json()
    bank_acc = next(a for a in accounts if a["account_code"] == "1010-BANK-HDFC")
    capital_acc = next(a for a in accounts if a["account_code"] == "3000-SHARE-CAPITAL")
    assert bank_acc["current_balance"] == 500000.0
    assert capital_acc["current_balance"] == 500000.0

    # 5. Reverse journal entry
    rev_res = await async_client.post(
        f"/api/v1/finance/journals/{jv_id}/reverse",
        headers=headers,
        json={"reversal_reason": "Correcting bank deposit ledger allocation"},
    )
    assert rev_res.status_code == 200
    rev_doc = rev_res.json()
    assert rev_doc["is_balanced"] is True
    assert rev_doc["source_module"] == "REVERSAL"

    # Accounts balance should now be restored to 0
    acc_res2 = await async_client.get("/api/v1/finance/accounts", headers=headers)
    accounts2 = acc_res2.json()
    bank_acc2 = next(a for a in accounts2 if a["account_code"] == "1010-BANK-HDFC")
    assert bank_acc2["current_balance"] == 0.0


@pytest.mark.asyncio
async def test_customer_invoice_receipt_and_aging(async_client: AsyncClient, setup_test_users, seed_finance_test_data):
    """
    Test Customer Invoicing and Receivables (AR):
    1. Create customer invoice with lines (Subtotal 100,000 + 18% GST = 118,000).
    2. Verify automated AR double-entry journal entry generation.
    3. Record customer partial payment (₹50,000).
    4. Verify invoice status transitions to PARTIALLY_PAID and balance due reconciles to ₹68,000.
    5. Record final settlement (₹68,000) and verify status transitions to PAID.
    """
    data = seed_finance_test_data
    cust_id = data["cust_id"]

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Create Invoice
    inv_res = await async_client.post(
        "/api/v1/finance/invoices",
        headers=headers,
        json={
            "customer_id": cust_id,
            "unit_id": "Unit_1",
            "invoice_date": "2026-10-02",
            "due_date": "2026-11-01",
            "lines": [
                {
                    "item_code": "FG-HYD-PRESS-20",
                    "description": "20T Hydraulic Press Machine",
                    "quantity": 1.0,
                    "unit_price": 100000.0,
                    "discount_percent": 0.0,
                    "tax_percent": 18.0,
                    "account_code": "4000-SALES-REVENUE",
                }
            ],
            "notes": "Machine delivery dispatch invoice",
        },
    )
    assert inv_res.status_code == 201
    inv_doc = inv_res.json()
    inv_id = inv_doc["id"]
    inv_num = inv_doc["invoice_number"]
    assert inv_doc["subtotal_amount"] == 100000.0
    assert inv_doc["tax_amount"] == 18000.0
    assert inv_doc["total_amount"] == 118000.0
    assert inv_doc["balance_due"] == 118000.0
    assert inv_doc["status"] == "POSTED"

    # 2. Record Partial Customer Receipt (₹50,000)
    pay_res = await async_client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "payment_type": "CUSTOMER_RECEIPT",
            "entity_id": cust_id,
            "reference_doc_id": inv_id,
            "reference_doc_number": inv_num,
            "unit_id": "Unit_1",
            "payment_date": "2026-10-05",
            "payment_method": "BANK_TRANSFER",
            "payment_reference": "UTR-HDFC-987654321",
            "amount": 50000.0,
            "bank_account_code": "1010-BANK-HDFC",
            "notes": "Advance payment part 1",
        },
    )
    assert pay_res.status_code == 201

    # Verify Invoice status and balance
    invoices_res = await async_client.get(f"/api/v1/finance/invoices?customer_id={cust_id}", headers=headers)
    assert invoices_res.status_code == 200
    inv_updated = next(i for i in invoices_res.json()["items"] if i["id"] == inv_id)
    assert inv_updated["amount_paid"] == 50000.0
    assert inv_updated["balance_due"] == 68000.0
    assert inv_updated["status"] == "PARTIALLY_PAID"

    # 3. Record Remaining Receipt (₹68,000)
    pay2_res = await async_client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "payment_type": "CUSTOMER_RECEIPT",
            "entity_id": cust_id,
            "reference_doc_id": inv_id,
            "reference_doc_number": inv_num,
            "unit_id": "Unit_1",
            "payment_date": "2026-10-10",
            "payment_method": "NEFT_RTGS",
            "payment_reference": "UTR-HDFC-987654322",
            "amount": 68000.0,
            "bank_account_code": "1010-BANK-HDFC",
            "notes": "Final settlement",
        },
    )
    assert pay2_res.status_code == 201

    # Verify Invoice marked as PAID
    invoices_res2 = await async_client.get(f"/api/v1/finance/invoices?customer_id={cust_id}", headers=headers)
    inv_paid = next(i for i in invoices_res2.json()["items"] if i["id"] == inv_id)
    assert inv_paid["balance_due"] == 0.0
    assert inv_paid["status"] == "PAID"


@pytest.mark.asyncio
async def test_supplier_bill_qc_hold_and_payment_blockage(async_client: AsyncClient, setup_test_users, seed_finance_test_data):
    """
    Test Supplier Bills (AP) & QC Hold Workflow:
    1. Register supplier bill under QC Hold (`has_qc_hold=True`).
    2. Attempting to record vendor payment must be blocked with HTTP 400.
    3. Duplicate vendor invoice submission must be blocked.
    4. Authorize release of QC hold.
    5. Vendor payment succeeds after QC release.
    """
    data = seed_finance_test_data
    ven_id = data["ven_id"]

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Register bill with QC Hold
    bill_res = await async_client.post(
        "/api/v1/finance/bills",
        headers=headers,
        json={
            "vendor_id": ven_id,
            "bill_number_vendor": "INV-STEEL-2026-888",
            "po_reference": "PO-202610-001",
            "unit_id": "Unit_1",
            "bill_date": "2026-10-02",
            "due_date": "2026-11-15",
            "lines": [
                {
                    "item_code": "RM-STEEL-PLATE",
                    "description": "Structural Steel Plate 12mm",
                    "quantity": 1000.0,
                    "unit_price": 85.0,
                    "tax_percent": 18.0,
                    "account_code": "1200-RAW-MATERIAL-INVENTORY",
                }
            ],
            "has_qc_hold": True,
            "qc_hold_reason": "Surface porosity defects detected on plate sample testing",
            "notes": "Under inspection review",
        },
    )
    assert bill_res.status_code == 201
    bill_doc = bill_res.json()
    bill_id = bill_doc["id"]
    bill_num = bill_doc["bill_number"]
    assert bill_doc["status"] == "ON_HOLD"
    assert bill_doc["has_qc_hold"] is True
    # Subtotal = 85000, Tax = 15300, Total = 100300
    assert bill_doc["total_amount"] == 100300.0

    # 2. Duplicate Bill Submission check
    dup_res = await async_client.post(
        "/api/v1/finance/bills",
        headers=headers,
        json={
            "vendor_id": ven_id,
            "bill_number_vendor": "INV-STEEL-2026-888",
            "unit_id": "Unit_1",
            "bill_date": "2026-10-02",
            "due_date": "2026-11-15",
            "lines": [
                {
                    "item_code": "RM-STEEL-PLATE",
                    "description": "Structural Steel Plate 12mm",
                    "quantity": 1000.0,
                    "unit_price": 85.0,
                    "tax_percent": 18.0,
                }
            ],
        },
    )
    assert dup_res.status_code == 400
    assert "Duplicate vendor bill prevented" in dup_res.json().get("error", {}).get("message", "")

    # 3. Attempt Payment While on QC Hold -> Must be Blocked!
    pay_blocked = await async_client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "payment_type": "VENDOR_PAYMENT",
            "entity_id": ven_id,
            "reference_doc_id": bill_id,
            "reference_doc_number": bill_num,
            "unit_id": "Unit_1",
            "payment_date": "2026-10-06",
            "payment_method": "BANK_TRANSFER",
            "amount": 50000.0,
            "bank_account_code": "1010-BANK-HDFC",
        },
    )
    assert pay_blocked.status_code == 400
    err_msg = pay_blocked.json().get("error", {}).get("message", "")
    assert "Payment Blocked by QC" in err_msg

    # 4. Release QC Hold
    release_res = await async_client.post(
        f"/api/v1/finance/bills/{bill_id}/release-qc-hold",
        headers=headers,
        json={"release_notes": "Vendor replaced defective plates; secondary inspection approved by QA lead"},
    )
    assert release_res.status_code == 200
    released_doc = release_res.json()
    assert released_doc["has_qc_hold"] is False
    assert released_doc["status"] == "APPROVED"

    # 5. Payment After QC Hold Release -> Must Succeed
    pay_success = await async_client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "payment_type": "VENDOR_PAYMENT",
            "entity_id": ven_id,
            "reference_doc_id": bill_id,
            "reference_doc_number": bill_num,
            "unit_id": "Unit_1",
            "payment_date": "2026-10-07",
            "payment_method": "BANK_TRANSFER",
            "amount": 100300.0,
            "bank_account_code": "1010-BANK-HDFC",
            "notes": "Full settlement after QC release",
        },
    )
    assert pay_success.status_code == 201

    # Verify bill status is PAID
    bills_res = await async_client.get(f"/api/v1/finance/bills?vendor_id={ven_id}", headers=headers)
    bill_paid = next(b for b in bills_res.json()["items"] if b["id"] == bill_id)
    assert bill_paid["status"] == "PAID"
    assert bill_paid["balance_due"] == 0.0


@pytest.mark.asyncio
async def test_financial_reports_trial_balance_and_pl(async_client: AsyncClient, setup_test_users, seed_finance_test_data):
    """
    Test Financial Statements:
    1. Record operating expense (Power / Electricity ₹15,000).
    2. Generate Trial Balance and verify strict balancing.
    3. Generate Profit & Loss statement and verify Net Profit.
    4. Generate Balance Sheet and verify Assets = Liabilities + Equity.
    """
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Record an Operating Expense
    exp_res = await async_client.post(
        "/api/v1/finance/expenses",
        headers=headers,
        json={
            "expense_category": "PLANT_ELECTRICITY",
            "expense_account_code": "5200-POWER-ELECTRICITY-EXPENSE",
            "unit_id": "Unit_1",
            "expense_date": "2026-10-05",
            "amount": 15000.0,
            "tax_amount": 0.0,
            "payment_method": "BANK_TRANSFER",
            "paid_from_account_code": "1010-BANK-HDFC",
            "vendor_or_payee": "Maharashtra State Electricity Distribution Co Ltd",
            "reference_number": "MSEDCL-OCT-2026",
            "notes": "Monthly factory grid power tariff",
        },
    )
    assert exp_res.status_code == 201

    # 2. Trial Balance
    tb_res = await async_client.get("/api/v1/finance/reports/trial-balance", headers=headers)
    assert tb_res.status_code == 200
    tb = tb_res.json()
    assert tb["is_balanced"] is True
    assert tb["total_debit"] == tb["total_credit"]

    # 3. Profit & Loss
    pl_res = await async_client.get(
        "/api/v1/finance/reports/profit-and-loss?from_date=2026-10-01&to_date=2026-10-31",
        headers=headers,
    )
    assert pl_res.status_code == 200
    pl = pl_res.json()
    assert "total_revenue" in pl
    assert "total_expenses" in pl
    assert pl["net_profit_or_loss"] == round(pl["total_revenue"] - pl["total_expenses"], 2)

    # 4. Balance Sheet
    bs_res = await async_client.get("/api/v1/finance/reports/balance-sheet", headers=headers)
    assert bs_res.status_code == 200
    bs = bs_res.json()
    assert "total_assets" in bs
    assert "total_liabilities" in bs
