import logging
from datetime import datetime, timezone
from app.database.mongodb import mongodb_manager
from app.models.user import RoleName, ManufacturingUnit, DEFAULT_ROLE_PERMISSIONS
from app.core.security import hash_password

logger = logging.getLogger("app.database.seeds")

async def seed_initial_roles_and_admin() -> None:
    """
    Idempotent seeding routine that runs during application startup:
    1. Creates unique indexes on users and sessions collections.
    2. Seeds standard role permission matrices in `roles` collection.
    3. Seeds root Super Admin account if no users exist.
    """
    try:
        db = mongodb_manager.get_database()

        # 1. Indexes
        users_col = db["users"]
        sessions_col = db["sessions"]
        audit_col = db["audit_logs"]

        await users_col.create_index("email", unique=True)
        await sessions_col.create_index("token_hash", unique=True)
        await sessions_col.create_index("expires_at")
        await audit_col.create_index("timestamp")

        # Master data collections unique code indexes
        master_collections = [
            "customers", "vendors", "employees", "finished_products",
            "raw_materials", "uom", "warehouses", "categories"
        ]
        for col_name in master_collections:
            await db[col_name].create_index("code", unique=True)
            await db[col_name].create_index("is_active")
            if col_name in ["finished_products", "raw_materials", "warehouses", "employees"]:
                await db[col_name].create_index("unit_id")

        # CRM collections indexes
        await db["crm_leads"].create_index("code", unique=True)
        await db["crm_leads"].create_index("status")
        await db["crm_leads"].create_index("priority")
        await db["crm_leads"].create_index("assigned_to")
        await db["crm_leads"].create_index("next_follow_up")
        await db["crm_activities"].create_index([("lead_id", 1), ("created_at", -1)])

        # Orders & Dispatch collections indexes
        await db["sales_orders"].create_index("order_number", unique=True)
        await db["sales_orders"].create_index("customer_id")
        await db["sales_orders"].create_index("status")
        await db["sales_orders"].create_index("unit_id")
        await db["sales_orders"].create_index("created_at")
        await db["packing_slips"].create_index("slip_number", unique=True)
        await db["packing_slips"].create_index("order_id")
        await db["dispatch_records"].create_index("dispatch_number", unique=True)
        await db["dispatch_records"].create_index("order_id")
        await db["order_activities"].create_index([("order_id", 1), ("timestamp", -1)])

        # Inventory collections indexes
        await db["inventory_stock"].create_index(
            [("item_id", 1), ("warehouse_id", 1), ("batch_no", 1)],
            unique=True,
        )
        await db["inventory_stock"].create_index("item_code")
        await db["inventory_stock"].create_index("warehouse_code")
        await db["inventory_stock"].create_index("unit_id")
        await db["inventory_stock"].create_index("item_type")
        await db["inventory_ledger"].create_index("transaction_number", unique=True)
        await db["inventory_ledger"].create_index([("item_id", 1), ("created_at", -1)])
        await db["inventory_ledger"].create_index([("warehouse_id", 1), ("created_at", -1)])
        await db["inventory_ledger"].create_index("movement_type")
        await db["inventory_ledger"].create_index("created_at")

        # BOM collections indexes
        await db["boms"].create_index("bom_number", unique=True)
        await db["boms"].create_index([("product_id", 1), ("unit_id", 1), ("revision_no", 1)], unique=True)
        await db["boms"].create_index("product_code")
        await db["boms"].create_index("status")
        await db["boms"].create_index("is_active")

        # Production collections indexes
        await db["production_orders"].create_index("order_number", unique=True)
        await db["production_orders"].create_index("product_id")
        await db["production_orders"].create_index("bom_id")
        await db["production_orders"].create_index("unit_id")
        await db["production_orders"].create_index("status")
        await db["production_orders"].create_index("created_at")
        await db["production_outputs"].create_index([("order_id", 1), ("created_at", -1)])

        # Wastage & Scrap collections indexes
        await db["scrap_entries"].create_index("entry_number", unique=True)
        await db["scrap_entries"].create_index("unit_id")
        await db["scrap_entries"].create_index("production_order_id")
        await db["scrap_entries"].create_index("scrap_category")
        await db["scrap_entries"].create_index("status")
        await db["scrap_entries"].create_index("entry_date")

        # Electricity & Power-cut collections indexes
        await db["electricity_readings"].create_index("reading_number", unique=True)
        await db["electricity_readings"].create_index([("unit_id", 1), ("meter_id", 1), ("reading_date", 1)])
        await db["power_cuts"].create_index("incident_number", unique=True)
        await db["power_cuts"].create_index([("unit_id", 1), ("start_time", 1)])

        # HR, Attendance, and Payroll collections indexes
        await db["shifts"].create_index("shift_code", unique=True)
        await db["shifts"].create_index("unit_id")
        await db["attendance_records"].create_index([("employee_id", 1), ("date", 1)], unique=True)
        await db["attendance_records"].create_index("date")
        await db["attendance_records"].create_index("unit_id")
        await db["attendance_records"].create_index("status")
        await db["leave_requests"].create_index("application_number", unique=True)
        await db["leave_requests"].create_index("employee_id")
        await db["leave_requests"].create_index("status")
        await db["salary_structures"].create_index("employee_id", unique=True)
        await db["salary_structures"].create_index("unit_id")
        await db["payroll_runs"].create_index("run_number", unique=True)
        await db["payroll_runs"].create_index([("period", 1), ("unit_id", 1)])
        await db["payroll_runs"].create_index("status")
        await db["payroll_items"].create_index("payroll_run_id")
        await db["payroll_items"].create_index([("employee_id", 1), ("period", 1)])

        # Finance & Accounting collections indexes
        await db["accounts"].create_index("account_code", unique=True)
        await db["accounts"].create_index("account_type")
        await db["invoices"].create_index("invoice_number", unique=True)
        await db["invoices"].create_index("customer_id")
        await db["invoices"].create_index("status")
        await db["invoices"].create_index("unit_id")
        await db["supplier_bills"].create_index("bill_number", unique=True)
        await db["supplier_bills"].create_index([("vendor_id", 1), ("bill_number_vendor", 1)], unique=True)
        await db["supplier_bills"].create_index("status")
        await db["supplier_bills"].create_index("has_qc_hold")
        await db["payments"].create_index("payment_number", unique=True)
        await db["payments"].create_index("payment_type")
        await db["payments"].create_index("entity_id")
        await db["expenses"].create_index("expense_number", unique=True)
        await db["expenses"].create_index("expense_category")
        await db["journal_entries"].create_index("entry_number", unique=True)
        await db["journal_entries"].create_index("entry_date")
        await db["journal_entries"].create_index([("source_module", 1), ("source_reference", 1)])
        await db["journal_entries"].create_index("status")

        # Excel migration and imports tracking
        await db["import_batches"].create_index("batch_token", unique=True)
        await db["import_batches"].create_index("entity_type")
        await db["import_batches"].create_index("status")
        await db["import_batches"].create_index("created_at")

        # 2. Seed standard Chart of Accounts
        from app.repositories.finance_repository import FinanceRepository
        finance_repo = FinanceRepository(db)
        await finance_repo.seed_chart_of_accounts()

        # 3. Roles collection
        roles_col = db["roles"]
        for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            await roles_col.update_one(
                {"name": role_name.value},
                {
                    "$set": {
                        "name": role_name.value,
                        "permissions": perms,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True
            )

        # 3. Super Admin root user (RG Tech Owner)
        admin_primary_email = "admin@rgtech.com"
        admin_username = "admin"
        admin_password_hash = hash_password("admin123")

        # Upsert or seed Super Admin (Owner)
        existing_admin = await users_col.find_one({
            "$or": [
                {"email": admin_primary_email},
                {"username": admin_username},
                {"email": "admin@RGmachines.com"}
            ]
        })

        if not existing_admin:
            logger.info(f"Seeding default Super Admin account: {admin_username} / {admin_primary_email}")
            admin_doc = {
                "email": admin_primary_email,
                "username": admin_username,
                "full_name": "Ritesh Gajjar",
                "hashed_password": admin_password_hash,
                "role": RoleName.SUPER_ADMIN.value,
                "allowed_units": [ManufacturingUnit.BOTH.value],
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "last_login_at": None,
            }
            await users_col.insert_one(admin_doc)
            logger.info("Default Super Admin (Ritesh Gajjar) created successfully.")
        else:
            # Keep credentials aligned with configured owner credentials
            await users_col.update_one(
                {"_id": existing_admin["_id"]},
                {
                    "$set": {
                        "username": admin_username,
                        "email": admin_primary_email,
                        "full_name": "Ritesh Gajjar",
                        "hashed_password": admin_password_hash,
                        "role": RoleName.SUPER_ADMIN.value,
                        "is_active": True,
                        "allowed_units": [ManufacturingUnit.BOTH.value],
                    }
                }
            )
            logger.info("Super Admin (Ritesh Gajjar) credentials synchronized successfully.")

        # 4. HR User Account (hr@rgtech.com / admin123)
        hr_email = "hr@rgtech.com"
        hr_pass_hash = hash_password("admin123")
        existing_hr = await users_col.find_one({"email": hr_email})
        if not existing_hr:
            await users_col.insert_one({
                "email": hr_email,
                "username": "hr_admin",
                "full_name": "Pooja Patel",
                "hashed_password": hr_pass_hash,
                "role": RoleName.HR.value,
                "account_type": "HR",
                "department": "HR & Administration",
                "job_role": "HR Manager",
                "job_roles": ["HR Manager", "Payroll Manager"],
                "allowed_units": [ManufacturingUnit.BOTH.value],
                "is_active": True,
                "must_change_password": False,
                "created_at": datetime.now(timezone.utc),
            })
            logger.info("HR Account (hr@rgtech.com) seeded.")

        # 5. Operational Employee Account (mayan@rgtech.com / admin123)
        emp_email = "mayan@rgtech.com"
        emp_code = "EMP-001"
        existing_emp_user = await users_col.find_one({"email": emp_email})
        if not existing_emp_user:
            emp_user_res = await users_col.insert_one({
                "email": emp_email,
                "username": "mayank_gajjar",
                "full_name": "Mayank Gajjar",
                "hashed_password": hash_password("admin123"),
                "role": RoleName.EMPLOYEE.value,
                "account_type": "EMPLOYEE",
                "department": "Inventory & Purchase",
                "job_role": "Purchase Executive",
                "job_roles": ["Purchase Executive"],
                "employee_code": emp_code,
                "allowed_units": [ManufacturingUnit.Unit_1.value],
                "is_active": True,
                "must_change_password": False,
                "created_at": datetime.now(timezone.utc),
            })
            emp_user_id = emp_user_res.inserted_id
            logger.info("Employee Account (mayan@rgtech.com) seeded.")
        else:
            emp_user_id = existing_emp_user["_id"]

        # 6. Employee Master Document in `employees`
        emp_col = db["employees"]
        existing_emp_master = await emp_col.find_one({"code": emp_code})
        now = datetime.now(timezone.utc)
        if not existing_emp_master:
            await emp_col.insert_one({
                "code": emp_code,
                "full_name": "Mayank Gajjar",
                "email": emp_email,
                "phone": "+91 98250 12345",
                "department": "Inventory & Purchase",
                "designation": "Purchase Executive",
                "account_type": "EMPLOYEE",
                "job_role": "Purchase Executive",
                "unit_id": "Unit_1",
                "status": "ACTIVE",
                "joining_date": "2023-04-01",
                "emergency_contact": "+91 98250 99999",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })
            logger.info("Employee Master Record (EMP-001) seeded.")

        # 7. Standard Manufacturing Shift in `shifts`
        shifts_col = db["shifts"]
        existing_shift = await shifts_col.find_one({"shift_code": "SHIFT-GEN"})
        if not existing_shift:
            await shifts_col.insert_one({
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
                "created_at": now,
                "created_by": "SYSTEM",
            })
            logger.info("Standard General Shift seeded.")

        # 8. Baseline Salary Structure for EMP-001 in `salary_structures`
        sal_col = db["salary_structures"]
        existing_sal = await sal_col.find_one({"employee_code": emp_code})
        if not existing_sal:
            await sal_col.insert_one({
                "employee_id": str(emp_user_id),
                "employee_code": emp_code,
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
                "created_at": now,
            })
            logger.info("Salary structure for EMP-001 seeded.")

        # 9. Corporate Announcement in `announcements`
        ann_col = db["announcements"]
        if await ann_col.count_documents({}) == 0:
            await ann_col.insert_one({
                "title": "Welcome to RG Tech Operational ERP",
                "content": "All manufacturing staff and supervisors across Unit 1 and Unit 2 must record daily shift check-ins and submit leave applications through the Employee Workspace.",
                "priority": "HIGH",
                "unit_id": "BOTH",
                "author_name": "HR Department",
                "author_role": "HR Manager",
                "published_at": now,
                "expires_at": None,
            })

    except Exception as exc:
        logger.error(f"Error seeding initial database: {exc}", exc_info=True)
