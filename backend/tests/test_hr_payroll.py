import pytest
from httpx import AsyncClient
from app.core.config import settings
from datetime import datetime, timezone


@pytest.fixture
async def seed_hr_payroll_test_data(setup_test_db):
    """Seed test employees and facility records for HR and Payroll testing."""
    db = setup_test_db

    # 1. Active employee 1 in Unit_1
    emp1_res = await db["employees"].insert_one({
        "code": "EMP-001",
        "full_name": "Ramesh Sharma",
        "email": "ramesh.sharma@RGmachines.com",
        "phone": "+91 9876543210",
        "department": "Production",
        "designation": "CNC Machinist",
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    emp1_id = str(emp1_res.inserted_id)

    # 2. Active employee 2 in Unit_1
    emp2_res = await db["employees"].insert_one({
        "code": "EMP-002",
        "full_name": "Pooja Patel",
        "email": "pooja.patel@RGmachines.com",
        "phone": "+91 9876543211",
        "department": "Quality",
        "designation": "QC Inspector",
        "unit_id": "Unit_1",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })
    emp2_id = str(emp2_res.inserted_id)

    return {
        "emp1_id": emp1_id,
        "emp2_id": emp2_id,
    }


@pytest.mark.asyncio
async def test_hr_shift_and_attendance_lifecycle(async_client: AsyncClient, setup_test_users, seed_hr_payroll_test_data):
    """Test creating shifts, logging attendance, duplicate prevention, and supervisor corrections."""
    data = seed_hr_payroll_test_data
    emp1_id = data["emp1_id"]

    # 1. Login as super admin
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 2. Configure a plant shift
    shift_res = await async_client.post(
        "/api/v1/hr/shifts",
        headers=headers,
        json={
            "shift_code": "SHIFT-MORN-01",
            "name": "Morning Production Shift",
            "shift_type": "SHIFT_1",
            "start_time": "08:00",
            "end_time": "16:30",
            "break_duration_minutes": 30,
            "grace_period_minutes": 15,
            "standard_work_hours": 8.0,
            "unit_id": "Unit_1",
            "is_active": True,
        },
    )
    assert shift_res.status_code == 201
    shift_json = shift_res.json()
    assert shift_json["shift_code"] == "SHIFT-MORN-01"

    # 3. Record daily attendance for EMP-001
    att_res = await async_client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={
            "employee_id": emp1_id,
            "employee_code": "EMP-001",
            "date": "2026-10-01",
            "unit_id": "Unit_1",
            "shift_code": "SHIFT-MORN-01",
            "check_in": "08:05",
            "check_out": "18:35",
            "status": "PRESENT",
            "hours_worked": 10.0,
            "overtime_hours": 2.0,
            "remarks": "On-time arrival with 2h OT for press assembly",
        },
    )
    assert att_res.status_code == 201
    att_doc = att_res.json()
    att_id = att_doc["id"]
    assert att_doc["employee_name"] == "Ramesh Sharma"
    assert att_doc["overtime_hours"] == 2.0

    # 4. Duplicate prevention test: attempting to submit same employee on same date
    dup_res = await async_client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={
            "employee_id": emp1_id,
            "employee_code": "EMP-001",
            "date": "2026-10-01",
            "unit_id": "Unit_1",
            "status": "PRESENT",
            "hours_worked": 8.0,
            "overtime_hours": 0.0,
        },
    )
    assert dup_res.status_code == 400
    err_msg = dup_res.json().get("error", {}).get("message", "")
    assert "Duplicate attendance entry prevented" in err_msg

    # 5. Supervisor correction workflow
    correct_res = await async_client.put(
        f"/api/v1/hr/attendance/{att_id}/correct",
        headers=headers,
        json={
            "check_out": "19:05",
            "hours_worked": 10.5,
            "overtime_hours": 2.5,
            "correction_reason": "Punch machine missed out-time due to plant network downtime; verified by shop supervisor",
        },
    )
    assert correct_res.status_code == 200
    corrected = correct_res.json()
    assert corrected["is_corrected"] is True
    assert corrected["overtime_hours"] == 2.5
    assert "shop supervisor" in corrected["correction_reason"]


@pytest.mark.asyncio
async def test_leave_application_and_approval_workflow(async_client: AsyncClient, setup_test_users, seed_hr_payroll_test_data):
    """Test employee leave application, approval, and listing."""
    data = seed_hr_payroll_test_data
    emp2_id = data["emp2_id"]

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Apply for leave
    leave_res = await async_client.post(
        "/api/v1/hr/leaves",
        headers=headers,
        json={
            "employee_id": emp2_id,
            "leave_type": "CASUAL_LEAVE",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "days_count": 2.0,
            "reason": "Family function",
        },
    )
    assert leave_res.status_code == 201
    leave_doc = leave_res.json()
    leave_id = leave_doc["id"]
    assert leave_doc["status"] == "PENDING"
    assert leave_doc["days_count"] == 2.0

    # 2. Approve leave
    review_res = await async_client.put(
        f"/api/v1/hr/leaves/{leave_id}/review",
        headers=headers,
        json={
            "status": "APPROVED",
            "notes": "Approved by plant HR manager",
        },
    )
    assert review_res.status_code == 200
    reviewed = review_res.json()
    assert reviewed["status"] == "APPROVED"
    assert reviewed["approved_by"] == "admin_ops@testcorp.com"

    # 3. Check HR summary
    summary_res = await async_client.get("/api/v1/hr/summary?unit_id=Unit_1", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_active_employees"] >= 2


@pytest.mark.asyncio
async def test_payroll_calculation_posting_and_immutability(async_client: AsyncClient, setup_test_users, seed_hr_payroll_test_data):
    """
    Test end-to-end payroll:
    1. Upsert salary structures (Basic, HRA, Conveyance, OT rate, PF, ESI, PT).
    2. Add attendance records with OT and LOP for period 2026-10.
    3. Generate and calculate draft payroll run.
    4. Verify calculations (Gross, LOP deduction, PF, ESI, PT, Net pay).
    5. Review, Approve, and POST payroll run.
    6. Verify locked immutability: cannot post duplicate run for same period and unit.
    7. Retrieve individual payslip and double-entry accounting export.
    """
    data = seed_hr_payroll_test_data
    emp1_id = data["emp1_id"]

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ops@testcorp.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    csrf_token = login_res.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {settings.CSRF_HEADER_NAME: csrf_token}

    # 1. Upsert salary structure for EMP-001
    # Monthly base CTC = 26000 (Daily rate = 1000 for 26 days)
    # Basic = 15000, HRA = 6000, Conveyance = 2000, Special = 3000
    # OT rate = 150/hr
    # PF 12% of 15000 = 1800
    # ESI 0.75%
    # PT = 200
    struct_res = await async_client.post(
        "/api/v1/payroll/structures",
        headers=headers,
        json={
            "employee_id": emp1_id,
            "unit_id": "Unit_1",
            "base_monthly_salary": 26000.0,
            "basic_salary": 15000.0,
            "hra": 6000.0,
            "conveyance_allowance": 2000.0,
            "special_allowance": 3000.0,
            "overtime_hourly_rate": 150.0,
            "pf_applicable": True,
            "pf_percentage": 12.0,
            "esi_applicable": True,
            "esi_percentage": 0.75,
            "professional_tax": 200.0,
            "tds_monthly": 0.0,
            "bank_name": "State Bank of India",
            "bank_account_number": "123456789012",
            "bank_ifsc": "SBIN0001234",
        },
    )
    assert struct_res.status_code == 200
    struct_data = struct_res.json()
    assert struct_data["gross_monthly_standard"] == 26000.0

    # 2. Add attendance records for EMP-001:
    # 24 Present days with 10 OT hours total, and 2 Absent days (Loss of pay = 2 * 1000 = 2000)
    for day in range(1, 25):
        day_str = f"2026-10-{day:02d}"
        ot = 1.0 if day <= 10 else 0.0
        await async_client.post(
            "/api/v1/hr/attendance",
            headers=headers,
            json={
                "employee_id": emp1_id,
                "employee_code": "EMP-001",
                "date": day_str,
                "unit_id": "Unit_1",
                "status": "PRESENT",
                "hours_worked": 8.0 + ot,
                "overtime_hours": ot,
            },
        )

    # 2 absent days
    await async_client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={
            "employee_id": emp1_id,
            "employee_code": "EMP-001",
            "date": "2026-10-25",
            "unit_id": "Unit_1",
            "status": "ABSENT",
            "hours_worked": 0.0,
            "overtime_hours": 0.0,
        },
    )
    await async_client.post(
        "/api/v1/hr/attendance",
        headers=headers,
        json={
            "employee_id": emp1_id,
            "employee_code": "EMP-001",
            "date": "2026-10-26",
            "unit_id": "Unit_1",
            "status": "ABSENT",
            "hours_worked": 0.0,
            "overtime_hours": 0.0,
        },
    )

    # 3. Create payroll run for period 2026-10
    run_res = await async_client.post(
        "/api/v1/payroll/runs",
        headers=headers,
        json={
            "period": "2026-10",
            "unit_id": "Unit_1",
            "working_days_in_month": 26,
            "notes": "October 2026 Production Payroll Run",
        },
    )
    assert run_res.status_code == 201
    run_doc = run_res.json()
    run_id = run_doc["id"]
    assert run_doc["status"] == "DRAFT"
    assert run_doc["total_employees"] >= 1

    # 4. Fetch payroll items and inspect calculations for EMP-001
    items_res = await async_client.get(f"/api/v1/payroll/runs/{run_id}/items", headers=headers)
    assert items_res.status_code == 200
    items = items_res.json()
    emp1_item = next((it for it in items if it["employee_code"] == "EMP-001"), None)
    assert emp1_item is not None

    # Verify OT and LOP figures
    # OT hours = 10 hrs * 150 = 1500.0
    assert emp1_item["overtime_hours"] == 10.0
    assert emp1_item["overtime_pay"] == 1500.0
    # Gross = 15000 + 6000 + 2000 + 3000 + 1500 = 27500.0
    assert emp1_item["gross_earnings"] == 27500.0
    # LOP = 2 days * 1000 = 2000.0
    assert emp1_item["lop_deduction"] == 2000.0
    # PF = 12% of 15000 = 1800.0
    assert emp1_item["pf_deduction"] == 1800.0
    # ESI = 0.75% of 27500.0 = 206.25
    assert emp1_item["esi_deduction"] == 206.25
    # PT = 200.0
    assert emp1_item["professional_tax"] == 200.0
    # Total deductions = 2000 + 1800 + 206.25 + 200 = 4206.25
    assert emp1_item["total_deductions"] == 4206.25
    # Net pay = 27500 - 4206.25 = 23293.75
    assert emp1_item["net_pay"] == 23293.75

    # 5. Workflow transitions: DRAFT -> UNDER_REVIEW -> APPROVED -> POSTED
    review_res = await async_client.post(f"/api/v1/payroll/runs/{run_id}/review", headers=headers)
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "UNDER_REVIEW"

    approve_res = await async_client.post(f"/api/v1/payroll/runs/{run_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    post_res = await async_client.post(f"/api/v1/payroll/runs/{run_id}/post", headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "POSTED"

    # 6. Verify duplicate run prevention: Cannot create another run for 2026-10 in Unit_1
    dup_run_res = await async_client.post(
        "/api/v1/payroll/runs",
        headers=headers,
        json={
            "period": "2026-10",
            "unit_id": "Unit_1",
            "working_days_in_month": 26,
        },
    )
    assert dup_run_res.status_code == 400
    err_msg = dup_run_res.json().get("error", {}).get("message", "")
    assert "Duplicate payroll run prevented" in err_msg

    # 7. Payslip retrieval
    slip_res = await async_client.get(f"/api/v1/payroll/payslips/{emp1_id}/2026-10", headers=headers)
    assert slip_res.status_code == 200
    slip = slip_res.json()
    assert slip["employee_name"] == "Ramesh Sharma"
    assert slip["net_salary_payable"] == 23293.75
    assert slip["standard_working_days"] == 26
    assert slip["lop_days"] == 2.0

    # 8. Double-entry accounting export
    jv_res = await async_client.get(f"/api/v1/payroll/runs/{run_id}/accounting-export", headers=headers)
    assert jv_res.status_code == 200
    jv = jv_res.json()
    assert jv["is_balanced"] is True
    assert len(jv["lines"]) >= 5
    assert jv["total_debit"] > 0
    assert abs(jv["total_debit"] - jv["total_credit"]) < 0.05
