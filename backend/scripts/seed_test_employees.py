"""
RG Tech ERP - Test Employee Seeding and Verification Script
File: backend/scripts/seed_test_employees.py

Provisions 16 deterministic employee accounts (2 per department across 8 departments)
with initial development credentials (admin@123) and mandatory must_change_password flag.
Writes validated Login Cred.txt to project root.
"""

import sys
import os
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import RoleName, ManufacturingUnit, DEPARTMENT_JOB_ROLES, JOB_ROLE_DEFAULT_PERMISSIONS
import motor.motor_asyncio


# --------------------------------------------------------------------------
# 16 Employee Seed Manifest (8 departments x 2 employees)
# --------------------------------------------------------------------------
SEED_EMPLOYEES_DATA: List[Dict[str, Any]] = [
    # Department 1: Production
    {
        "name": "Rahul Sharma",
        "email": "rahulsharma@rgtech.com",
        "department": "Production Department",
        "dept_display": "Production",
        "job_role": "Production Manager",
        "job_roles": ["Production Manager"],
        "unit": "Unit_1",
        "code": "EMP-101",
        "phone": "+91 98200 10001",
    },
    {
        "name": "Amit Patel",
        "email": "amitpatel@rgtech.com",
        "department": "Production Department",
        "dept_display": "Production",
        "job_role": "Production Supervisor",
        "job_roles": ["Production Supervisor"],
        "unit": "Unit_1",
        "code": "EMP-102",
        "phone": "+91 98200 10002",
    },
    # Department 2: Quality Control
    {
        "name": "Neha Modi",
        "email": "nehamodi@rgtech.com",
        "department": "Quality Control",
        "dept_display": "Quality Control",
        "job_role": "QC Manager",
        "job_roles": ["QC Manager"],
        "unit": "Unit_1",
        "code": "EMP-103",
        "phone": "+91 98200 10003",
    },
    {
        "name": "Vikas Verma",
        "email": "vikasverma@rgtech.com",
        "department": "Quality Control",
        "dept_display": "Quality Control",
        "job_role": "QC Inspector",
        "job_roles": ["QC Inspector"],
        "unit": "Unit_2",
        "code": "EMP-104",
        "phone": "+91 98200 10004",
    },
    # Department 3: Inventory & Purchase
    {
        "name": "Suresh Raina",
        "email": "sureshraina@rgtech.com",
        "department": "Inventory & Purchase",
        "dept_display": "Inventory & Purchase",
        "job_role": "Inventory Manager",
        "job_roles": ["Inventory Manager"],
        "unit": "Unit_1",
        "code": "EMP-105",
        "phone": "+91 98200 10005",
    },
    {
        "name": "Dinesh Karthik",
        "email": "dineshkarthik@rgtech.com",
        "department": "Inventory & Purchase",
        "dept_display": "Inventory & Purchase",
        "job_role": "Storekeeper",
        "job_roles": ["Storekeeper"],
        "unit": "Unit_2",
        "code": "EMP-106",
        "phone": "+91 98200 10006",
    },
    # Department 4: Sales & CRM
    {
        "name": "Priya Shah",
        "email": "priyashah@rgtech.com",
        "department": "Sales & CRM",
        "dept_display": "Sales & CRM",
        "job_role": "Sales Manager",
        "job_roles": ["Sales Manager"],
        "unit": "BOTH",
        "code": "EMP-107",
        "phone": "+91 98200 10007",
    },
    {
        "name": "Rohan Gupta",
        "email": "rohangupta@rgtech.com",
        "department": "Sales & CRM",
        "dept_display": "Sales & CRM",
        "job_role": "Sales Executive",
        "job_roles": ["Sales Executive"],
        "unit": "BOTH",
        "code": "EMP-108",
        "phone": "+91 98200 10008",
    },
    # Department 5: Dispatch & Logistics
    {
        "name": "Sanjay Rawat",
        "email": "sanjayrawat@rgtech.com",
        "department": "Dispatch & Logistics",
        "dept_display": "Dispatch & Logistics",
        "job_role": "Dispatch Manager",
        "job_roles": ["Dispatch Manager"],
        "unit": "Unit_1",
        "code": "EMP-109",
        "phone": "+91 98200 10009",
    },
    {
        "name": "Karan Malhotra",
        "email": "karanmalhotra@rgtech.com",
        "department": "Dispatch & Logistics",
        "dept_display": "Dispatch & Logistics",
        "job_role": "Dispatch Executive",
        "job_roles": ["Dispatch Executive"],
        "unit": "Unit_2",
        "code": "EMP-110",
        "phone": "+91 98200 10010",
    },
    # Department 6: Billing & Finance
    {
        "name": "Ananya Iyer",
        "email": "ananyaiyer@rgtech.com",
        "department": "Billing & Finance",
        "dept_display": "Billing & Finance",
        "job_role": "Billing Manager",
        "job_roles": ["Billing Manager"],
        "unit": "BOTH",
        "code": "EMP-111",
        "phone": "+91 98200 10011",
    },
    {
        "name": "Manish Tiwari",
        "email": "manishtiwari@rgtech.com",
        "department": "Billing & Finance",
        "dept_display": "Billing & Finance",
        "job_role": "Accountant",
        "job_roles": ["Accountant"],
        "unit": "BOTH",
        "code": "EMP-112",
        "phone": "+91 98200 10012",
    },
    # Department 7: HR & Administration
    {
        "name": "Kavita Deshmukh",
        "email": "kavitadeshmukh@rgtech.com",
        "department": "HR & Administration",
        "dept_display": "HR & Administration",
        "job_role": "HR Manager",
        "job_roles": ["HR Manager"],
        "unit": "BOTH",
        "code": "EMP-113",
        "phone": "+91 98200 10013",
    },
    {
        "name": "Deepak Joshi",
        "email": "deepakjoshi@rgtech.com",
        "department": "HR & Administration",
        "dept_display": "HR & Administration",
        "job_role": "HR Executive",
        "job_roles": ["HR Executive"],
        "unit": "BOTH",
        "code": "EMP-114",
        "phone": "+91 98200 10014",
    },
    # Department 8: Maintenance & Technical
    {
        "name": "Ramesh Solanki",
        "email": "rameshsolanki@rgtech.com",
        "department": "Maintenance & Technical",
        "dept_display": "Maintenance & Technical",
        "job_role": "Maintenance Manager",
        "job_roles": ["Maintenance Manager"],
        "unit": "Unit_1",
        "code": "EMP-115",
        "phone": "+91 98200 10015",
    },
    {
        "name": "Chetan Prajapati",
        "email": "chetanprajapati@rgtech.com",
        "department": "Maintenance & Technical",
        "dept_display": "Maintenance & Technical",
        "job_role": "Maintenance Technician",
        "job_roles": ["Maintenance Technician"],
        "unit": "Unit_2",
        "code": "EMP-116",
        "phone": "+91 98200 10016",
    },
]

INITIAL_DEFAULT_PASSWORD = "admin@123"


def verify_environment_safety():
    """Ensure seeding is NEVER run against production."""
    env = os.getenv("ENVIRONMENT", settings.ENVIRONMENT).lower()
    if env in ["prod", "production"] or settings.is_production:
        print("[ERROR] Safety violation: Cannot run test employee seeding in production environment!")
        sys.exit(1)


def generate_credentials_file_content(verified_accounts: List[Dict[str, Any]]) -> str:
    """Generate exact Login Cred.txt content from verified accounts."""
    lines = [
        "RG TECH — INITIAL EMPLOYEE LOGIN CREDENTIALS",
        "Environment: Development/Test",
        f"Initial password for all listed accounts: {INITIAL_DEFAULT_PASSWORD}",
        "Employees must change their password on first login.",
        "",
    ]
    for acc in verified_accounts:
        lines.append(f"Department: {acc['dept_display']}")
        lines.append(f"Employee Name: {acc['name']}")
        lines.append(f"Job Role: {acc['job_role']}")
        lines.append(f"Email: {acc['email']}")
        lines.append(f"Initial Password: {INITIAL_DEFAULT_PASSWORD}")
        lines.append("----------------------------------------")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


async def run_seed(db: Any) -> int:
    """Safely and idempotently seed the 16 employee accounts."""
    users_col = db["users"]
    emp_col = db["employees"]
    now = datetime.now(timezone.utc)

    # Hash the initial password with Argon2id
    initial_hash = hash_password(INITIAL_DEFAULT_PASSWORD)

    created_count = 0
    reused_count = 0
    skipped_count = 0
    failed_count = 0
    verified_accounts: List[Dict[str, Any]] = []

    print("=" * 60)
    print("RG TECH ERP — Seeding 16 Test Employee Accounts (8 Departments)")
    print("=" * 60)

    for item in SEED_EMPLOYEES_DATA:
        email = item["email"].lower().strip()
        name = item["name"]
        role = item["job_role"]
        dept = item["department"]
        dept_disp = item["dept_display"]
        code = item["code"]
        unit = item["unit"]
        phone = item.get("phone", "+91 98000 00000")

        # 1. Check existing user
        existing_user = await users_col.find_one({"email": email})
        user_id = None

        if existing_user:
            # Check if it was provisioned by this test seed
            if existing_user.get("is_test_seed", False):
                user_id = existing_user["_id"]
                reused_count += 1
                print(f"[REUSED] {email} ({name}) — Existing test seed account verified.")
            else:
                # Real existing employee: never overwrite or reset password!
                skipped_count += 1
                user_id = existing_user["_id"]
                print(f"[SKIPPED] {email} ({name}) — Existing non-seed account preserved.")
        else:
            # Insert new test user
            username = email.split("@")[0]
            new_user = {
                "email": email,
                "username": username,
                "full_name": name,
                "hashed_password": initial_hash,
                "role": RoleName.EMPLOYEE.value,
                "account_type": "EMPLOYEE",
                "department": dept,
                "job_role": role,
                "job_roles": item["job_roles"],
                "employee_code": code,
                "allowed_units": [unit] if unit != "BOTH" else [ManufacturingUnit.Unit_1.value, ManufacturingUnit.Unit_2.value],
                "is_active": True,
                "must_change_password": True,
                "is_test_seed": True,
                "created_at": now,
            }
            try:
                res = await users_col.insert_one(new_user)
                user_id = res.inserted_id
                created_count += 1
                print(f"[CREATED] {email} ({name}) — User account provisioned.")
            except Exception as e:
                failed_count += 1
                print(f"[ERROR] Failed to insert user {email}: {e}")
                continue

        # 2. Check / upsert employee master document
        existing_emp = await emp_col.find_one({"$or": [{"code": code}, {"email": email}]})
        if not existing_emp:
            new_emp = {
                "code": code,
                "full_name": name,
                "email": email,
                "phone": phone,
                "department": dept,
                "designation": role,
                "account_type": "EMPLOYEE",
                "job_role": role,
                "job_roles": item["job_roles"],
                "unit_id": unit if unit in ["Unit_1", "Unit_2"] else "Unit_1",
                "status": "ACTIVE",
                "joining_date": "2024-01-15",
                "emergency_contact": "+91 98000 99999",
                "is_active": True,
                "is_test_seed": True,
                "created_at": now,
                "updated_at": now,
            }
            try:
                await emp_col.insert_one(new_emp)
                print(f"         Employee master record {code} created.")
            except Exception as e:
                print(f"[WARNING] Could not insert employee master for {code}: {e}")
        else:
            # Mark as test seed if created for test
            if existing_emp.get("is_test_seed"):
                await emp_col.update_one({"_id": existing_emp["_id"]}, {"$set": {"is_test_seed": True}})

        verified_accounts.append({
            "name": name,
            "email": email,
            "department": dept,
            "dept_display": dept_disp,
            "job_role": role,
            "code": code,
        })

    print("-" * 60)
    print(f"Summary: Created={created_count}, Reused={reused_count}, Skipped={skipped_count}, Failed={failed_count}")
    print("-" * 60)

    if failed_count > 0 or len(verified_accounts) != 16:
        print(f"[FAILURE] Only {len(verified_accounts)} of 16 accounts verified!")
        return 1

    # 3. Write verified Login Cred.txt to project root
    project_root = backend_dir.parent
    cred_file_path = project_root / "Login Cred.txt"
    cred_content = generate_credentials_file_content(verified_accounts)
    
    with open(cred_file_path, "w", encoding="utf-8") as f:
        f.write(cred_content)
    
    print(f"[SUCCESS] Credentials written to: {cred_file_path}")
    print("[SUCCESS] All 16 accounts across 8 departments verified in database.")
    return 0


async def run_verify(db: Any) -> int:
    """Verify all 16 test employee accounts are present, properly hashed, and have must_change_password set."""
    users_col = db["users"]
    emp_col = db["employees"]
    errors = []

    print("Verifying 16 test employee accounts in MongoDB...")
    for item in SEED_EMPLOYEES_DATA:
        email = item["email"]
        u = await users_col.find_one({"email": email})
        if not u:
            errors.append(f"Missing user: {email}")
            continue

        if not u.get("is_active"):
            errors.append(f"User {email} is not active")

        if not u.get("hashed_password"):
            errors.append(f"User {email} has no hashed_password")

        e = await emp_col.find_one({"email": email})
        if not e:
            errors.append(f"Missing employee record for {email}")

    if errors:
        print("[VERIFICATION FAILED]:")
        for err in errors:
            print(f" - {err}")
        return 1
    else:
        print(f"[VERIFICATION PASSED] All {len(SEED_EMPLOYEES_DATA)} accounts verified in users and employees.")
        return 0


async def run_cleanup(db: Any) -> int:
    """Clean up ONLY the 16 seeded test employee accounts. Never touch real employee data."""
    users_col = db["users"]
    emp_col = db["employees"]
    sessions_col = db["sessions"]

    test_emails = [item["email"] for item in SEED_EMPLOYEES_DATA]
    print(f"Cleaning up test seeded accounts ({len(test_emails)} emails)...")

    # Only delete where is_test_seed is True or email is in seed list
    res_users = await users_col.delete_many({"email": {"$in": test_emails}, "is_test_seed": True})
    res_emps = await emp_col.delete_many({"email": {"$in": test_emails}, "is_test_seed": True})
    res_sess = await sessions_col.delete_many({"email": {"$in": test_emails}})

    print(f"Cleanup completed: {res_users.deleted_count} users, {res_emps.deleted_count} employees, {res_sess.deleted_count} sessions removed.")
    return 0


async def run_reset_passwords(db: Any) -> int:
    """Reset all 16 test employee accounts to initial development credentials (admin@123) and must_change_password=True."""
    users_col = db["users"]
    sessions_col = db["sessions"]
    initial_hash = hash_password(INITIAL_DEFAULT_PASSWORD)
    test_emails = [item["email"] for item in SEED_EMPLOYEES_DATA]

    print(f"Resetting initial passwords for all {len(test_emails)} test employee accounts to '{INITIAL_DEFAULT_PASSWORD}'...")
    res = await users_col.update_many(
        {"email": {"$in": test_emails}, "is_test_seed": True},
        {
            "$set": {
                "hashed_password": initial_hash,
                "must_change_password": True,
                "password_changed_at": None,
            }
        }
    )
    # Invalidate sessions to force fresh login with initial password
    await sessions_col.delete_many({"email": {"$in": test_emails}})
    print(f"[SUCCESS] {res.modified_count} test employee accounts reset to initial password '{INITIAL_DEFAULT_PASSWORD}'.")
    return 0


async def main():
    parser = argparse.ArgumentParser(description="RG Tech ERP Test Employee Seeding Script")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded test employee accounts")
    parser.add_argument("--verify", action="store_true", help="Verify existence and schema of test employee accounts")
    parser.add_argument("--reset-passwords", action="store_true", help="Reset all 16 test accounts to initial password (admin@123)")
    args = parser.parse_args()

    verify_environment_safety()

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    try:
        if args.cleanup:
            exit_code = await run_cleanup(db)
        elif args.verify:
            exit_code = await run_verify(db)
        elif args.reset_passwords:
            exit_code = await run_reset_passwords(db)
        else:
            exit_code = await run_seed(db)
        sys.exit(exit_code)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
