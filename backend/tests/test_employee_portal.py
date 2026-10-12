import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from app.models.user import RoleName, ManufacturingUnit
from app.core.security import hash_password


@pytest.fixture
async def setup_employee_test_data(setup_test_db):
    """
    Seeds test users:
    1. Mayank Gajjar (Employee, EMP-001, Unit 1)
    2. Suresh Kumar (Employee, EMP-002, Unit 2)
    3. HR Manager (Pooja Patel, Both)
    """
    db = setup_test_db

    # 1. Mayank (EMP-001)
    emp1_id = await db["users"].insert_one({
        "email": "mayan@rgtech.com",
        "username": "mayank_gajjar",
        "full_name": "Mayank Gajjar",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "department": "Inventory & Purchase",
        "job_role": "Purchase Executive",
        "job_roles": ["Purchase Executive"],
        "employee_code": "EMP-001",
        "allowed_units": [ManufacturingUnit.Unit_1.value],
        "is_active": True,
        "must_change_password": False,
        "created_at": datetime.now(timezone.utc),
    })

    await db["employees"].insert_one({
        "code": "EMP-001",
        "full_name": "Mayank Gajjar",
        "email": "mayan@rgtech.com",
        "phone": "+91 98250 12345",
        "department": "Inventory & Purchase",
        "designation": "Purchase Executive",
        "unit_id": "Unit_1",
        "status": "ACTIVE",
        "joining_date": "2023-04-01",
        "emergency_contact": "+91 98250 99999",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # 2. Suresh (EMP-002)
    emp2_id = await db["users"].insert_one({
        "email": "suresh@rgtech.com",
        "username": "suresh_kumar",
        "full_name": "Suresh Kumar",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": RoleName.EMPLOYEE.value,
        "account_type": "EMPLOYEE",
        "department": "Production Department",
        "job_role": "Machine Operator",
        "job_roles": ["Machine Operator"],
        "employee_code": "EMP-002",
        "allowed_units": [ManufacturingUnit.Unit_2.value],
        "is_active": True,
        "must_change_password": False,
        "created_at": datetime.now(timezone.utc),
    })

    await db["employees"].insert_one({
        "code": "EMP-002",
        "full_name": "Suresh Kumar",
        "email": "suresh@rgtech.com",
        "phone": "+91 98250 54321",
        "department": "Production Department",
        "designation": "Machine Operator",
        "unit_id": "Unit_2",
        "status": "ACTIVE",
        "joining_date": "2024-01-10",
        "emergency_contact": "+91 98250 88888",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    })

    # 3. Seed Shift
    await db["shifts"].insert_one({
        "shift_code": "SHIFT-GEN",
        "name": "General Production Shift",
        "shift_type": "GENERAL",
        "start_time": "09:00",
        "end_time": "18:00",
        "break_duration_minutes": 60,
        "grace_period_minutes": 15,
        "standard_work_hours": 8.0,
        "unit_id": "BOTH",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": "SYSTEM",
    })

    # 4. Salary Structures
    await db["salary_structures"].insert_one({
        "employee_id": str(emp1_id.inserted_id),
        "employee_code": "EMP-001",
        "employee_name": "Mayank Gajjar",
        "department": "Inventory & Purchase",
        "designation": "Purchase Executive",
        "unit_id": "Unit_1",
        "base_monthly_salary": 38000.0,
        "basic_salary": 19000.0,
        "hra": 9500.0,
        "conveyance_allowance": 3000.0,
        "special_allowance": 6500.0,
        "overtime_hourly_rate": 200.0,
        "gross_monthly_standard": 38000.0,
        "pf_applicable": True,
        "pf_percentage": 12.0,
        "esi_applicable": False,
        "esi_percentage": 0.75,
        "professional_tax": 200.0,
        "tds_monthly": 500.0,
        "bank_name": "HDFC Bank",
        "bank_account_number": "50100234567891",
        "bank_ifsc": "HDFC0000123",
        "created_at": datetime.now(timezone.utc),
    })

    await db["salary_structures"].insert_one({
        "employee_id": str(emp2_id.inserted_id),
        "employee_code": "EMP-002",
        "employee_name": "Suresh Kumar",
        "department": "Production Department",
        "designation": "Machine Operator",
        "unit_id": "Unit_2",
        "base_monthly_salary": 28000.0,
        "basic_salary": 14000.0,
        "hra": 7000.0,
        "conveyance_allowance": 2000.0,
        "special_allowance": 5000.0,
        "overtime_hourly_rate": 150.0,
        "gross_monthly_standard": 28000.0,
        "pf_applicable": True,
        "pf_percentage": 12.0,
        "esi_applicable": False,
        "esi_percentage": 0.75,
        "professional_tax": 200.0,
        "tds_monthly": 0.0,
        "bank_name": "ICICI Bank",
        "bank_account_number": "001122334455",
        "bank_ifsc": "ICIC0000456",
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "emp1_id": str(emp1_id.inserted_id),
        "emp2_id": str(emp2_id.inserted_id),
    }


@pytest.mark.asyncio
async def test_employee_dashboard_and_profile(async_client: AsyncClient, setup_employee_test_data):
    # 1. Login as Mayank Gajjar (EMP-001)
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "mayan@rgtech.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]

    # 2. Retrieve Employee Dashboard
    dash_res = await async_client.get("/api/v1/employee/dashboard?unit_id=Unit_1")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["employee_code"] == "EMP-001"
    assert dash["full_name"] == "Mayank Gajjar"
    assert dash["department"] == "Inventory & Purchase"
    assert len(dash["leave_balances"]) == 4
    assert dash["current_shift"]["shift_code"] == "SHIFT-GEN"

    # 3. Retrieve Profile
    prof_res = await async_client.get("/api/v1/employee/profile")
    assert prof_res.status_code == 200
    prof = prof_res.json()
    assert prof["employee_code"] == "EMP-001"
    assert prof["phone"] == "+91 98250 12345"
    assert "hashed_password" not in prof

    # 4. Submit Profile Correction Request
    corr_res = await async_client.post(
        "/api/v1/employee/profile/correction-request",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "field_name": "emergency_contact",
            "requested_value": "+91 98250 77777",
            "reason": "Updated primary family emergency contact number"
        }
    )
    assert corr_res.status_code == 201
    assert corr_res.json()["status"] == "PENDING"
    assert "PCR-" in corr_res.json()["request_number"]


def get_error_message(res) -> str:
    data = res.json()
    if "error" in data and "message" in data["error"]:
        return data["error"]["message"]
    return data.get("detail", "")


@pytest.mark.asyncio
async def test_employee_attendance_checkin_checkout_and_history(async_client: AsyncClient, setup_employee_test_data):
    # Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "mayan@rgtech.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]

    # 1. Check-in
    checkin_res = await async_client.post(
        "/api/v1/employee/attendance/check-in",
        headers={"X-CSRF-Token": csrf_token},
        json={"unit_id": "Unit_1", "remarks": "On time arrival at machine shop"}
    )
    assert checkin_res.status_code == 200
    att_doc = checkin_res.json()
    assert att_doc["employee_code"] == "EMP-001"
    assert att_doc["status"] == "PRESENT"
    assert att_doc["check_in"] is not None

    # Duplicate check-in on same day should be rejected
    dup_res = await async_client.post(
        "/api/v1/employee/attendance/check-in",
        headers={"X-CSRF-Token": csrf_token},
        json={"unit_id": "Unit_1"}
    )
    assert dup_res.status_code == 400
    assert "Already checked in" in get_error_message(dup_res)

    # 2. Check-out
    checkout_res = await async_client.post(
        "/api/v1/employee/attendance/check-out",
        headers={"X-CSRF-Token": csrf_token},
        json={"remarks": "End of shift"}
    )
    assert checkout_res.status_code == 200
    assert checkout_res.json()["check_out"] is not None

    # Duplicate check-out should be rejected
    dup_out = await async_client.post(
        "/api/v1/employee/attendance/check-out",
        headers={"X-CSRF-Token": csrf_token},
        json={}
    )
    assert dup_out.status_code == 400

    # 3. History
    hist_res = await async_client.get("/api/v1/employee/attendance")
    assert hist_res.status_code == 200
    assert hist_res.json()["total"] >= 1

    # 4. Submit Attendance Correction Request
    corr_res = await async_client.post(
        "/api/v1/employee/attendance/correction-request",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "date": "2026-10-10",
            "requested_check_in": "09:00",
            "requested_check_out": "18:00",
            "requested_status": "PRESENT",
            "reason": "Forgot badge scan due to turnstile maintenance"
        }
    )
    assert corr_res.status_code == 201
    assert "ACR-" in corr_res.json()["request_number"]


@pytest.mark.asyncio
async def test_employee_leave_lifecycle_and_cancellation(async_client: AsyncClient, setup_employee_test_data):
    # Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "mayan@rgtech.com", "password": "ValidPassword123!"}
    )
    csrf_token = login_res.json()["csrf_token"]

    # 1. Apply Leave
    leave_res = await async_client.post(
        "/api/v1/employee/leaves",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "leave_type": "CASUAL_LEAVE",
            "start_date": "2026-11-10",
            "end_date": "2026-11-12",
            "days_count": 3.0,
            "reason": "Family wedding in Ahmedabad"
        }
    )
    assert leave_res.status_code == 201
    leave_data = leave_res.json()
    leave_id = leave_data["id"]
    assert leave_data["status"] == "PENDING"
    assert "LV-" in leave_data["application_number"]

    # 2. Overlapping Leave Application should be rejected
    overlap_res = await async_client.post(
        "/api/v1/employee/leaves",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "leave_type": "SICK_LEAVE",
            "start_date": "2026-11-11",
            "end_date": "2026-11-13",
            "days_count": 3.0,
            "reason": "Overlapping request"
        }
    )
    assert overlap_res.status_code == 400
    assert "Overlapping leave request prevented" in get_error_message(overlap_res)

    # 3. List my leaves
    list_res = await async_client.get("/api/v1/employee/leaves")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. Cancel leave
    cancel_res = await async_client.post(
        f"/api/v1/employee/leaves/{leave_id}/cancel",
        headers={"X-CSRF-Token": csrf_token}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_salary_and_payslip_bola_prevention(async_client: AsyncClient, setup_employee_test_data):
    """
    CRITICAL SECURITY TEST:
    Verifies that Mayank (EMP-001) CANNOT view Suresh's (EMP-002) salary structure,
    corporate payroll runs, or colleague payslips.
    """
    # Login as Mayank (EMP-001)
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "mayan@rgtech.com", "password": "ValidPassword123!"}
    )
    assert login_res.status_code == 200

    # 1. Mayank can view his OWN salary structure via portal
    own_sal_res = await async_client.get("/api/v1/employee/salary")
    assert own_sal_res.status_code == 200
    assert own_sal_res.json()["employee_code"] == "EMP-001"
    assert own_sal_res.json()["base_monthly_salary"] == 38000.0

    # 2. Mayank attempts direct API access to Suresh's salary structure -> MUST BE FORBIDDEN (403)
    suresh_sal_res = await async_client.get("/api/v1/payroll/structures/EMP-002")
    assert suresh_sal_res.status_code == 403
    assert "Access denied" in get_error_message(suresh_sal_res) or "Permission denied" in get_error_message(suresh_sal_res)

    # 3. Mayank attempts to list all company payroll runs -> MUST BE FORBIDDEN (403)
    runs_res = await async_client.get("/api/v1/payroll/runs")
    assert runs_res.status_code == 403

    # 4. Mayank attempts to view company payroll metrics -> MUST BE FORBIDDEN (403)
    sum_res = await async_client.get("/api/v1/payroll/summary")
    assert sum_res.status_code == 403

    # 5. Mayank attempts to access Suresh's payslip -> MUST BE FORBIDDEN (403)
    suresh_slip_res = await async_client.get("/api/v1/payroll/payslips/EMP-002/2026-09")
    assert suresh_slip_res.status_code == 403
