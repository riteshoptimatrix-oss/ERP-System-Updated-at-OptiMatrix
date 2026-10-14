import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import RoleName, ManufacturingUnit


@pytest.fixture
async def setup_announcement_test_data(setup_test_users, setup_test_db):
    """
    Ensure active employees are present in both users and employees collections.
    """
    db = setup_test_db

    # Create emp1 user and employee record
    await db["users"].update_one(
        {"email": "emp1@testcorp.com"},
        {
            "$set": {
                "email": "emp1@testcorp.com",
                "employee_code": "EMP-001",
                "full_name": "Rohan Sharma",
                "hashed_password": hash_password("ValidPassword123!"),
                "role": RoleName.EMPLOYEE.value,
                "allowed_units": [ManufacturingUnit.Unit_1.value],
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True
    )
    await db["employees"].update_one(
        {"code": "EMP-001"},
        {
            "$set": {
                "code": "EMP-001",
                "name": "Rohan Sharma",
                "email": "emp1@testcorp.com",
                "department": "Assembly",
                "designation": "Technician",
                "unit_id": "Unit_1",
                "is_active": True,
            }
        },
        upsert=True
    )

    # Create emp2 user and employee record
    await db["users"].update_one(
        {"email": "emp2@testcorp.com"},
        {
            "$set": {
                "email": "emp2@testcorp.com",
                "employee_code": "EMP-002",
                "full_name": "Priya Patel",
                "hashed_password": hash_password("ValidPassword123!"),
                "role": RoleName.EMPLOYEE.value,
                "allowed_units": [ManufacturingUnit.Unit_2.value],
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True
    )
    await db["employees"].update_one(
        {"code": "EMP-002"},
        {
            "$set": {
                "code": "EMP-002",
                "name": "Priya Patel",
                "email": "emp2@testcorp.com",
                "department": "Machining",
                "designation": "CNC Operator",
                "unit_id": "Unit_2",
                "is_active": True,
            }
        },
        upsert=True
    )


async def get_auth_cookies(async_client: AsyncClient, email: str, password: str):
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200, f"Login failed for {email}: {login_res.text}"
    session_cookie = login_res.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = login_res.json()["csrf_token"]
    cookies = {
        settings.SESSION_COOKIE_NAME: session_cookie,
        settings.CSRF_COOKIE_NAME: csrf_token,
    }
    headers = {
        settings.CSRF_HEADER_NAME: csrf_token,
    }
    return cookies, headers


@pytest.mark.asyncio
async def test_super_admin_can_create_announcement_all(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test Super Admin can post an announcement targeted to @All.
    """
    cookies, headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    payload = {
        "title": "Annual Company Strategy Meeting",
        "message": "All plant operations and office staff will convene for the annual strategy session.",
        "priority": "HIGH",
        "unit_id": "BOTH",
        "audience_type": "all",
    }

    res = await async_client.post(
        "/api/v1/announcements",
        json=payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["message"] == payload["message"]
    assert data["audience_type"] == "all"
    assert data["priority"] == "HIGH"
    assert data["author_role"] == "SUPER_ADMIN"
    assert "id" in data


@pytest.mark.asyncio
async def test_super_admin_can_create_announcement_specific(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test Super Admin can post an announcement targeted to specific employees.
    """
    cookies, headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    payload = {
        "title": "Machine Maintenance Shift Reminder",
        "message": "Special maintenance shift assigned to select technicians.",
        "priority": "URGENT",
        "unit_id": "Unit_1",
        "audience_type": "specific",
        "recipients": ["emp1@testcorp.com", "EMP-001"],
        "recipient_names": ["Rohan Sharma (EMP-001)"],
    }

    res = await async_client.post(
        "/api/v1/announcements",
        json=payload,
        cookies=cookies,
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["audience_type"] == "specific"
    assert len(data["recipients"]) == 2
    assert "emp1@testcorp.com" in data["recipients"]


@pytest.mark.asyncio
async def test_create_announcement_validation_failure(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test validation errors: empty title/message or specific audience without recipients.
    """
    cookies, headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    # 1. Missing / short title
    res1 = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Hi", "message": "Valid message text here.", "audience_type": "all"},
        cookies=cookies,
        headers=headers,
    )
    assert res1.status_code == 422

    # 2. Specific audience with empty recipients
    res2 = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Valid Announcement Title", "message": "Valid message text here.", "audience_type": "specific", "recipients": []},
        cookies=cookies,
        headers=headers,
    )
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_non_super_admin_forbidden_from_create_update_delete(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test any non-Super Admin (Admin, Production Manager, Employee) receives 403 Forbidden.
    """
    # 1. Create one announcement first as Super Admin
    sa_cookies, sa_headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")
    create_res = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Company Memo", "message": "Memo text for testing permissions.", "audience_type": "all"},
        cookies=sa_cookies,
        headers=sa_headers,
    )
    assert create_res.status_code == 201
    ann_id = create_res.json()["id"]

    # 2. Admin (non-super-admin) tries to create -> 403 Forbidden
    admin_cookies, admin_headers = await get_auth_cookies(async_client, "admin_ops@testcorp.com", "ValidPassword123!")
    admin_post = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Admin Notice", "message": "Admin announcement attempt.", "audience_type": "all"},
        cookies=admin_cookies,
        headers=admin_headers,
    )
    assert admin_post.status_code == 403
    assert "exclusively restricted to the Super Admin" in admin_post.text

    # 3. PM tries to update -> 403 Forbidden
    pm_cookies, pm_headers = await get_auth_cookies(async_client, "pm1@testcorp.com", "ValidPassword123!")
    pm_put = await async_client.put(
        f"/api/v1/announcements/{ann_id}",
        json={"title": "Hacked Title"},
        cookies=pm_cookies,
        headers=pm_headers,
    )
    assert pm_put.status_code == 403

    # 4. Employee tries to delete -> 403 Forbidden
    emp_cookies, emp_headers = await get_auth_cookies(async_client, "emp1@testcorp.com", "ValidPassword123!")
    emp_del = await async_client.delete(
        f"/api/v1/announcements/{ann_id}",
        cookies=emp_cookies,
        headers=emp_headers,
    )
    assert emp_del.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_update_and_delete(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test Super Admin can update and soft-delete an announcement.
    """
    cookies, headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    create_res = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Initial Title", "message": "Initial announcement message.", "priority": "LOW", "audience_type": "all"},
        cookies=cookies,
        headers=headers,
    )
    ann_id = create_res.json()["id"]

    # Update
    update_res = await async_client.put(
        f"/api/v1/announcements/{ann_id}",
        json={"title": "Updated Strategy Title", "priority": "URGENT"},
        cookies=cookies,
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Strategy Title"
    assert update_res.json()["priority"] == "URGENT"

    # Delete
    del_res = await async_client.delete(
        f"/api/v1/announcements/{ann_id}",
        cookies=cookies,
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Check that deleted announcement does not show up in list
    list_res = await async_client.get("/api/v1/announcements", cookies=cookies)
    assert list_res.status_code == 200
    assert not any(a["id"] == ann_id for a in list_res.json())


@pytest.mark.asyncio
async def test_audience_filtering_between_employees(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test employee visibility:
    - @All is visible to all employees.
    - Specific announcement targeted to emp1 is visible to emp1, but NOT to emp2 or pm1.
    """
    sa_cookies, sa_headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    # 1. Post @All
    await async_client.post(
        "/api/v1/announcements",
        json={"title": "Holiday Schedule", "message": "Plant will be closed on Friday.", "audience_type": "all"},
        cookies=sa_cookies,
        headers=sa_headers,
    )

    # 2. Post Specific targeted to emp1
    await async_client.post(
        "/api/v1/announcements",
        json={"title": "Special Task for Emp1", "message": "Review machine calibrations.", "audience_type": "specific", "recipients": ["emp1@testcorp.com"]},
        cookies=sa_cookies,
        headers=sa_headers,
    )

    # 3. Check as emp1
    emp1_cookies, _ = await get_auth_cookies(async_client, "emp1@testcorp.com", "ValidPassword123!")
    emp1_list = await async_client.get("/api/v1/announcements", cookies=emp1_cookies)
    assert emp1_list.status_code == 200
    emp1_titles = [a["title"] for a in emp1_list.json()]
    assert "Holiday Schedule" in emp1_titles
    assert "Special Task for Emp1" in emp1_titles

    # 4. Check as emp2
    emp2_cookies, _ = await get_auth_cookies(async_client, "emp2@testcorp.com", "ValidPassword123!")
    emp2_list = await async_client.get("/api/v1/announcements", cookies=emp2_cookies)
    assert emp2_list.status_code == 200
    emp2_titles = [a["title"] for a in emp2_list.json()]
    assert "Holiday Schedule" in emp2_titles
    assert "Special Task for Emp1" not in emp2_titles  # emp2 must NOT see specific announcement for emp1!


@pytest.mark.asyncio
async def test_unread_count_and_mark_as_read_flow(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test unread count calculation, mark as read, and mark all as read.
    """
    sa_cookies, sa_headers = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")

    # Create 2 announcements
    res1 = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Notice 1", "message": "Content for notice 1.", "audience_type": "all"},
        cookies=sa_cookies,
        headers=sa_headers,
    )
    ann1_id = res1.json()["id"]

    res2 = await async_client.post(
        "/api/v1/announcements",
        json={"title": "Notice 2", "message": "Content for notice 2.", "audience_type": "all"},
        cookies=sa_cookies,
        headers=sa_headers,
    )
    ann2_id = res2.json()["id"]

    # Check unread count as emp1
    emp1_cookies, emp1_headers = await get_auth_cookies(async_client, "emp1@testcorp.com", "ValidPassword123!")
    count_res1 = await async_client.get("/api/v1/announcements/unread-count", cookies=emp1_cookies)
    assert count_res1.status_code == 200
    assert count_res1.json()["unread_count"] >= 2

    initial_count = count_res1.json()["unread_count"]

    # Mark notice 1 as read
    mark1_res = await async_client.patch(
        f"/api/v1/announcements/{ann1_id}/read",
        cookies=emp1_cookies,
        headers=emp1_headers,
    )
    assert mark1_res.status_code == 200
    assert mark1_res.json()["is_read"] is True

    # Unread count should decrease by 1
    count_res2 = await async_client.get("/api/v1/announcements/unread-count", cookies=emp1_cookies)
    assert count_res2.json()["unread_count"] == initial_count - 1

    # Mark all as read
    mark_all_res = await async_client.patch(
        "/api/v1/announcements/read-all",
        cookies=emp1_cookies,
        headers=emp1_headers,
    )
    assert mark_all_res.status_code == 200

    # Unread count should now be 0
    count_res3 = await async_client.get("/api/v1/announcements/unread-count", cookies=emp1_cookies)
    assert count_res3.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_recipients_endpoint_access_control(async_client: AsyncClient, setup_announcement_test_data):
    """
    Test GET /announcements/recipients is restricted to Super Admin.
    """
    sa_cookies, _ = await get_auth_cookies(async_client, "admin@rgtech.com", "admin123")
    sa_res = await async_client.get("/api/v1/announcements/recipients", cookies=sa_cookies)
    assert sa_res.status_code == 200
    recipients = sa_res.json()
    assert isinstance(recipients, list)
    codes = [r["code"] for r in recipients]
    assert "EMP-001" in codes

    emp_cookies, _ = await get_auth_cookies(async_client, "emp1@testcorp.com", "ValidPassword123!")
    emp_res = await async_client.get("/api/v1/announcements/recipients", cookies=emp_cookies)
    assert emp_res.status_code == 403
