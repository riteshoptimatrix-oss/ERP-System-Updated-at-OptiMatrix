from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging
from app.schemas.employee import (
    EmployeeShiftSummary,
    EmployeeAttendanceToday,
    LeaveBalanceItem,
    EmployeeDashboardResponse,
    EmployeeProfileResponse,
    ProfileCorrectionRequestCreate,
    AttendanceCorrectionSubmission,
    EmployeeTaskUpdate,
)
from app.schemas.hr import LeaveType, LeaveStatus, AttendanceStatus
from app.schemas.notification import NotificationType

logger = logging.getLogger("app.repositories.employee")

# Configured annual leave quotas for RG Tech manufacturing staff
ANNUAL_LEAVE_QUOTAS = {
    LeaveType.CASUAL_LEAVE.value: {"name": "Casual Leave (CL)", "quota": 12.0},
    LeaveType.SICK_LEAVE.value: {"name": "Sick Leave (SL)", "quota": 10.0},
    LeaveType.EARNED_LEAVE.value: {"name": "Earned Leave (EL)", "quota": 15.0},
    LeaveType.UNPAID_LEAVE.value: {"name": "Unpaid Leave (LOP)", "quota": 999.0},
}


class EmployeeRepository:
    def __init__(self, db: Any):
        self.db = db
        self.users_col = db["users"]
        self.emp_col = db["employees"]
        self.att_col = db["attendance_records"]
        self.shifts_col = db["shifts"]
        self.leaves_col = db["leave_requests"]
        self.salary_struct_col = db["salary_structures"]
        self.payroll_items_col = db["payroll_items"]
        self.payroll_runs_col = db["payroll_runs"]
        self.tasks_col = db["employee_tasks"]
        self.notif_col = db["notifications"]
        self.announcements_col = db["announcements"]
        self.prof_corr_col = db["profile_corrections"]
        self.att_corr_col = db["attendance_correction_requests"]
        self.audit_col = db["audit_logs"]

    # -------------------------------------------------------------
    # Helper: Resolve Employee Master Document
    # -------------------------------------------------------------
    async def resolve_employee_doc(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finds or auto-links the employee master document corresponding to the authenticated user.
        Ensures consistency between user accounts and employee master records.
        """
        emp_code = user_doc.get("employee_code")
        emp_doc = None
        if emp_code:
            emp_doc = await self.emp_col.find_one({"code": emp_code})
        if not emp_doc:
            emp_doc = await self.emp_col.find_one({"email": user_doc["email"]})

        if not emp_doc:
            # Auto-provision employee master record if missing
            now = datetime.now(timezone.utc)
            code = emp_code or f"EMP-{str(user_doc['_id'])[-4:].upper()}"
            allowed_u = user_doc.get("allowed_units", ["Unit_1"])
            unit_id = allowed_u[0] if allowed_u and allowed_u[0] != "BOTH" else "Unit_1"
            new_emp = {
                "code": code,
                "full_name": user_doc.get("full_name", "Employee"),
                "email": user_doc["email"],
                "phone": user_doc.get("phone", "+91 98000 00000"),
                "department": user_doc.get("department", "Operations"),
                "designation": user_doc.get("job_role", "Staff"),
                "account_type": user_doc.get("account_type", "EMPLOYEE"),
                "job_role": user_doc.get("job_role", "Staff"),
                "unit_id": unit_id,
                "status": "ACTIVE",
                "joining_date": user_doc.get("created_at", now).strftime("%Y-%m-%d") if isinstance(user_doc.get("created_at"), datetime) else "2024-01-01",
                "emergency_contact": "+91 98000 11111",
                "is_active": user_doc.get("is_active", True),
                "created_at": now,
                "updated_at": now,
            }
            res = await self.emp_col.insert_one(new_emp)
            new_emp["_id"] = res.inserted_id
            emp_doc = new_emp

            # Synchronize user doc
            await self.users_col.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"employee_code": code}}
            )
            user_doc["employee_code"] = code

        return emp_doc

    # -------------------------------------------------------------
    # 1. Employee Dashboard Aggregation
    # -------------------------------------------------------------
    async def get_dashboard(self, user_doc: Dict[str, Any], unit_id: Optional[str] = None) -> EmployeeDashboardResponse:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code", user_doc.get("employee_code", "EMP-001"))
        emp_id_str = str(emp_doc["_id"])

        active_unit = unit_id or emp_doc.get("unit_id", "Unit_1")
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Today's Attendance
        today_att_doc = await self.att_col.find_one({
            "$or": [
                {"employee_id": emp_id_str, "date": today_str},
                {"employee_code": emp_code, "date": today_str},
            ]
        })

        today_attendance = None
        if today_att_doc:
            today_attendance = EmployeeAttendanceToday(
                record_id=str(today_att_doc["_id"]),
                date=today_att_doc["date"],
                status=today_att_doc.get("status", "PRESENT"),
                check_in=today_att_doc.get("check_in"),
                check_out=today_att_doc.get("check_out"),
                hours_worked=float(today_att_doc.get("hours_worked", 0.0)),
                overtime_hours=float(today_att_doc.get("overtime_hours", 0.0)),
                shift_code=today_att_doc.get("shift_code"),
                is_checked_in=bool(today_att_doc.get("check_in")),
                is_checked_out=bool(today_att_doc.get("check_out")),
            )

        # 2. Current Shift
        shift_code = today_att_doc.get("shift_code", "SHIFT-GEN") if today_att_doc else "SHIFT-GEN"
        shift_doc = await self.shifts_col.find_one({"shift_code": shift_code})
        if not shift_doc:
            shift_doc = await self.shifts_col.find_one({"is_active": True})

        current_shift = None
        if shift_doc:
            current_shift = EmployeeShiftSummary(
                shift_code=shift_doc["shift_code"],
                name=shift_doc["name"],
                start_time=shift_doc["start_time"],
                end_time=shift_doc["end_time"],
                grace_period_minutes=shift_doc.get("grace_period_minutes", 15),
                standard_work_hours=float(shift_doc.get("standard_work_hours", 8.0)),
                unit_id=shift_doc.get("unit_id", "BOTH"),
            )
        else:
            current_shift = EmployeeShiftSummary(
                shift_code="SHIFT-GEN",
                name="General Production Shift",
                start_time="09:00",
                end_time="18:00",
                grace_period_minutes=15,
                standard_work_hours=8.0,
                unit_id=active_unit,
            )

        # 3. Leave Balances
        leave_balances = await self.calculate_leave_balances(emp_id_str, emp_code)

        # 4. Pending Tasks & Operational Work
        tasks, pending_tasks_count, deadlines_count = await self.get_employee_tasks_summary(
            user_doc=user_doc,
            emp_doc=emp_doc,
            unit_id=active_unit
        )

        # 5. Pending Leaves Count
        pending_leaves_count = await self.leaves_col.count_documents({
            "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}],
            "status": LeaveStatus.PENDING.value,
        })

        # 6. Notifications & Announcements
        unread_notifs = await self.notif_col.count_documents({
            "$or": [
                {"user_id": str(user_doc["_id"])},
                {"employee_code": emp_code},
                {"recipient_role": "ALL"},
            ],
            "is_read": False,
        })

        recent_notifs_cursor = self.notif_col.find({
            "$or": [
                {"user_id": str(user_doc["_id"])},
                {"employee_code": emp_code},
                {"recipient_role": "ALL"},
            ]
        }).sort("created_at", -1).limit(5)
        recent_notifs_raw = await recent_notifs_cursor.to_list(length=5)
        recent_notifications = [
            {
                "id": str(n["_id"]),
                "user_id": n.get("user_id"),
                "employee_code": n.get("employee_code"),
                "title": n.get("title", "Notification"),
                "message": n.get("message", ""),
                "notification_type": n.get("notification_type", "INFO"),
                "is_read": n.get("is_read", False),
                "link": n.get("link"),
                "created_at": n.get("created_at", datetime.now(timezone.utc)),
                "read_at": n.get("read_at"),
                "metadata": n.get("metadata"),
            }
            for n in recent_notifs_raw
        ]

        # Announcements scoped to facility or BOTH
        ann_cursor = self.announcements_col.find({
            "unit_id": {"$in": [active_unit, "BOTH"]},
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gte": datetime.now(timezone.utc)}},
            ]
        }).sort("published_at", -1).limit(3)
        ann_raw = await ann_cursor.to_list(length=3)
        announcements = [
            {
                "id": str(a["_id"]),
                "title": a.get("title", ""),
                "content": a.get("content", ""),
                "priority": a.get("priority", "NORMAL"),
                "unit_id": a.get("unit_id", "BOTH"),
                "author_name": a.get("author_name", "Management"),
                "author_role": a.get("author_role", "HR"),
                "published_at": a.get("published_at", datetime.now(timezone.utc)),
                "expires_at": a.get("expires_at"),
            }
            for a in ann_raw
        ]

        # Extract authorized modules
        perms = user_doc.get("permissions", [])
        modules = sorted(list(set(p.split(":")[0] for p in perms if ":" in p)))

        j_roles = user_doc.get("job_roles")
        if not j_roles and user_doc.get("job_role"):
            j_roles = [user_doc["job_role"]]
        elif not j_roles:
            j_roles = [emp_doc.get("designation", "Staff")]

        return EmployeeDashboardResponse(
            employee_code=emp_code,
            full_name=emp_doc.get("full_name", user_doc.get("full_name")),
            email=user_doc["email"],
            department=emp_doc.get("department", user_doc.get("department", "Operations")),
            designation=emp_doc.get("designation", user_doc.get("job_role", "Staff")),
            job_roles=j_roles,
            unit_id=active_unit,
            allowed_units=user_doc.get("allowed_units", ["Unit_1"]),
            today_attendance=today_attendance,
            current_shift=current_shift,
            leave_balances=leave_balances,
            pending_tasks_count=pending_tasks_count,
            upcoming_deadlines_count=deadlines_count,
            pending_leaves_count=pending_leaves_count,
            unread_notifications_count=unread_notifs,
            recent_notifications=recent_notifications,
            announcements=announcements,
            authorized_modules=modules,
        )

    # -------------------------------------------------------------
    # 2. Leave Balance Calculation
    # -------------------------------------------------------------
    async def calculate_leave_balances(self, emp_id: str, emp_code: str) -> List[LeaveBalanceItem]:
        current_year = datetime.now(timezone.utc).year
        year_prefix = f"^{current_year}-"

        # Query all approved leaves for current calendar year
        cursor = self.leaves_col.find({
            "$or": [{"employee_id": emp_id}, {"employee_code": emp_code}],
            "status": LeaveStatus.APPROVED.value,
            "start_date": {"$regex": year_prefix},
        })
        approved_leaves = await cursor.to_list(length=100)

        # Query all pending leaves
        pending_cursor = self.leaves_col.find({
            "$or": [{"employee_id": emp_id}, {"employee_code": emp_code}],
            "status": LeaveStatus.PENDING.value,
            "start_date": {"$regex": year_prefix},
        })
        pending_leaves = await pending_cursor.to_list(length=100)

        used_by_type: Dict[str, float] = {}
        for l in approved_leaves:
            l_type = l.get("leave_type", LeaveType.CASUAL_LEAVE.value)
            used_by_type[l_type] = used_by_type.get(l_type, 0.0) + float(l.get("days_count", 0.0))

        pending_by_type: Dict[str, float] = {}
        for l in pending_leaves:
            l_type = l.get("leave_type", LeaveType.CASUAL_LEAVE.value)
            pending_by_type[l_type] = pending_by_type.get(l_type, 0.0) + float(l.get("days_count", 0.0))

        result: List[LeaveBalanceItem] = []
        for l_type, config in ANNUAL_LEAVE_QUOTAS.items():
            quota = config["quota"]
            used = used_by_type.get(l_type, 0.0)
            pending = pending_by_type.get(l_type, 0.0)
            remaining = max(0.0, quota - used) if quota < 900 else 999.0

            result.append(
                LeaveBalanceItem(
                    leave_type=l_type,
                    name=config["name"],
                    quota_days=quota if quota < 900 else 0.0,
                    used_days=used,
                    pending_days=pending,
                    remaining_balance=remaining if quota < 900 else 0.0,
                )
            )

        return result

    # -------------------------------------------------------------
    # 3. Dynamic Operational Tasks Aggregation
    # -------------------------------------------------------------
    async def get_employee_tasks_summary(
        self, user_doc: Dict[str, Any], emp_doc: Dict[str, Any], unit_id: str
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Dynamically aggregates tasks based on employee's job roles, facility unit, and department.
        Does NOT invent fake records — queries active production, inventory, QC, and maintenance records.
        """
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])
        dept = emp_doc.get("department", "").lower()
        role = user_doc.get("job_role", "").lower()

        # Direct explicit tasks assigned to this employee
        direct_cursor = self.tasks_col.find({
            "$or": [
                {"assigned_to_id": emp_id_str},
                {"assigned_to_code": emp_code},
                {"assigned_to_email": user_doc["email"]},
            ],
            "status": {"$in": ["PENDING", "IN_PROGRESS"]},
        }).sort("priority", -1).limit(20)
        direct_tasks = await direct_cursor.to_list(length=20)

        # Operational tasks aggregation from real modules
        op_tasks: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        def normalize_date_str(val: Any) -> Optional[str]:
            if not val:
                return None
            if isinstance(val, datetime):
                return val.strftime("%Y-%m-%d")
            return str(val)[:10]

        formatted_direct_tasks: List[Dict[str, Any]] = []
        for dt in direct_tasks:
            formatted_direct_tasks.append({
                "id": str(dt.get("_id", dt.get("id"))),
                "task_number": dt.get("task_number") or f"TASK-{str(dt.get('_id', ''))[:6]}",
                "title": dt.get("title", "Assigned Task"),
                "description": dt.get("description", ""),
                "source_module": dt.get("source_module", "tasks"),
                "priority": dt.get("priority", "MEDIUM"),
                "status": dt.get("status", "PENDING"),
                "due_date": normalize_date_str(dt.get("due_date")),
                "related_record": dt.get("related_record"),
                "related_link": dt.get("related_link", "/employee/tasks"),
                "unit_id": dt.get("unit_id", unit_id),
                "notes": dt.get("notes"),
                "completion_evidence": dt.get("completion_evidence"),
                "supervisor_feedback": dt.get("supervisor_feedback"),
                "created_at": dt.get("created_at", now),
            })

        # 1. Production Department Tasks
        if "production" in dept or "machine" in role or "assembly" in role or "operator" in role:
            prod_cursor = self.db["production_orders"].find({
                "unit_id": unit_id,
                "status": {"$in": ["IN_PROGRESS", "DRAFT", "RELEASED"]},
            }).limit(5)
            prod_orders = await prod_cursor.to_list(length=5)
            for po in prod_orders:
                op_tasks.append({
                    "id": str(po["_id"]),
                    "task_number": f"TASK-PRD-{po.get('order_number')}",
                    "title": f"Process Batch {po.get('order_number')}: {po.get('product_name')}",
                    "description": f"Target output: {po.get('planned_quantity')} {po.get('product_uom')}. Machine shop execution.",
                    "source_module": "production",
                    "priority": "HIGH" if po.get("status") == "IN_PROGRESS" else "MEDIUM",
                    "status": "IN_PROGRESS" if po.get("status") == "IN_PROGRESS" else "PENDING",
                    "due_date": normalize_date_str(po.get("target_completion_date")),
                    "related_record": po.get("order_number"),
                    "related_link": f"/production",
                    "unit_id": po.get("unit_id", unit_id),
                    "created_at": po.get("created_at", now),
                })

        # 2. Inventory & Purchase Department Tasks
        if "inventory" in dept or "purchase" in dept or "store" in role:
            stock_cursor = self.db["inventory_stock"].find({
                "unit_id": unit_id,
                "$expr": {"$lte": ["$current_quantity", "$reorder_level"]},
            }).limit(5)
            reorder_items = await stock_cursor.to_list(length=5)
            for itm in reorder_items:
                op_tasks.append({
                    "id": str(itm["_id"]),
                    "task_number": f"TASK-INV-{itm.get('item_code')}",
                    "title": f"Restock Reorder Alert: {itm.get('item_name')}",
                    "description": f"Current stock ({itm.get('current_quantity')}) is at or below minimum threshold ({itm.get('reorder_level')}). Prepare purchase indent.",
                    "source_module": "inventory",
                    "priority": "HIGH",
                    "status": "PENDING",
                    "due_date": today_str,
                    "related_record": itm.get("item_code"),
                    "related_link": f"/inventory",
                    "unit_id": unit_id,
                    "created_at": now,
                })

        # 3. Quality Control Tasks
        if "qc" in dept or "quality" in dept or "inspector" in role:
            scrap_cursor = self.db["scrap_entries"].find({
                "unit_id": unit_id,
                "status": "UNRECONCILED",
            }).limit(5)
            scraps = await scrap_cursor.to_list(length=5)
            for sc in scraps:
                op_tasks.append({
                    "id": str(sc["_id"]),
                    "task_number": f"TASK-QC-{sc.get('entry_number')}",
                    "title": f"Quality Audit Scrap Entry {sc.get('entry_number')}",
                    "description": f"Verify dimensional rejection ({sc.get('quantity')} {sc.get('uom')}) reported on shop floor.",
                    "source_module": "qc",
                    "priority": "MEDIUM",
                    "status": "PENDING",
                    "due_date": normalize_date_str(sc.get("entry_date")) or today_str,
                    "related_record": sc.get("entry_number"),
                    "related_link": f"/wastage",
                    "unit_id": unit_id,
                    "created_at": sc.get("created_at", now),
                })

        # Combine direct and operational tasks
        combined = formatted_direct_tasks + op_tasks
        pending_count = len(combined)
        deadlines_count = sum(1 for t in combined if t.get("due_date") and str(t["due_date"]) <= today_str)

        return combined, pending_count, deadlines_count

    # -------------------------------------------------------------
    # 4. Check-in & Check-out Operations
    # -------------------------------------------------------------
    async def check_in(self, user_doc: Dict[str, Any], unit_id: Optional[str] = None, remarks: Optional[str] = None) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        now_utc = datetime.now(timezone.utc)
        # IST is UTC + 5:30
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        date_str = now_ist.strftime("%Y-%m-%d")
        time_str = now_ist.strftime("%H:%M")

        facility = unit_id or emp_doc.get("unit_id", "Unit_1")
        # Enforce allowed units
        allowed_units = user_doc.get("allowed_units", ["Unit_1"])
        if "BOTH" not in allowed_units and facility not in allowed_units:
            raise ValueError(f"You are not authorized to check in at facility '{facility}'.")

        # Duplicate check: cannot check in twice on same day
        existing = await self.att_col.find_one({
            "$or": [
                {"employee_id": emp_id_str, "date": date_str},
                {"employee_code": emp_code, "date": date_str},
            ]
        })
        if existing and existing.get("check_in"):
            raise ValueError(f"Already checked in today at {existing.get('check_in')}.")

        # Shift resolution
        shift_doc = await self.shifts_col.find_one({"is_active": True})
        shift_code = shift_doc.get("shift_code", "SHIFT-GEN") if shift_doc else "SHIFT-GEN"

        record_data = {
            "employee_id": emp_id_str,
            "employee_code": emp_code,
            "employee_name": emp_doc.get("full_name", user_doc.get("full_name")),
            "department": emp_doc.get("department", "Operations"),
            "designation": emp_doc.get("designation", "Staff"),
            "date": date_str,
            "unit_id": facility,
            "shift_code": shift_code,
            "check_in": time_str,
            "check_out": None,
            "status": AttendanceStatus.PRESENT.value,
            "hours_worked": 0.0,
            "overtime_hours": 0.0,
            "is_corrected": False,
            "remarks": remarks,
            "created_at": now_utc,
            "created_by": user_doc["email"],
        }

        if existing:
            await self.att_col.update_one(
                {"_id": existing["_id"]},
                {"$set": record_data}
            )
            doc_id = existing["_id"]
        else:
            res = await self.att_col.insert_one(record_data)
            doc_id = res.inserted_id

        # Notification
        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Check-In Confirmed",
            message=f"Logged check-in for {date_str} at {time_str} ({facility}).",
            notif_type=NotificationType.ATTENDANCE,
            link="/attendance",
        )

        return await self.att_col.find_one({"_id": doc_id})

    async def check_out(self, user_doc: Dict[str, Any], remarks: Optional[str] = None) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        date_str = now_ist.strftime("%Y-%m-%d")
        time_str = now_ist.strftime("%H:%M")

        existing = await self.att_col.find_one({
            "$or": [
                {"employee_id": emp_id_str, "date": date_str},
                {"employee_code": emp_code, "date": date_str},
            ]
        })

        if not existing or not existing.get("check_in"):
            raise ValueError(f"No check-in record found for today ({date_str}). Please check in first.")

        if existing.get("check_out"):
            raise ValueError(f"Already checked out today at {existing.get('check_out')}.")

        # Calculate hours worked
        check_in_time = existing["check_in"]
        try:
            t_in = datetime.strptime(f"{date_str} {check_in_time}", "%Y-%m-%d %H:%M")
            t_out = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            diff_seconds = max(0, (t_out - t_in).total_seconds())
            hours_worked = round(diff_seconds / 3600.0, 2)
        except Exception:
            hours_worked = 8.0

        # Overtime calculation: standard is 8 hours
        overtime_hours = max(0.0, round(hours_worked - 8.0, 2))

        update_ops = {
            "check_out": time_str,
            "hours_worked": hours_worked,
            "overtime_hours": overtime_hours,
            "updated_at": now_utc,
        }
        if remarks:
            update_ops["remarks"] = f"{existing.get('remarks', '')} | Out: {remarks}".strip(" |")

        await self.att_col.update_one({"_id": existing["_id"]}, {"$set": update_ops})

        # Notification
        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Check-Out Recorded",
            message=f"Logged check-out for {date_str} at {time_str}. Total hours: {hours_worked}h (OT: {overtime_hours}h).",
            notif_type=NotificationType.ATTENDANCE,
            link="/attendance",
        )

        return await self.att_col.find_one({"_id": existing["_id"]})

    # -------------------------------------------------------------
    # 5. Attendance Correction Request
    # -------------------------------------------------------------
    async def submit_attendance_correction(self, user_doc: Dict[str, Any], payload: AttendanceCorrectionSubmission) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.att_corr_col.count_documents({
            "request_number": {"$regex": f"^ACR-{ym_prefix}-"}
        })
        req_number = f"ACR-{ym_prefix}-{(count + 1):04d}"

        doc = {
            "request_number": req_number,
            "employee_id": emp_id_str,
            "employee_code": emp_code,
            "employee_name": emp_doc.get("full_name", user_doc.get("full_name")),
            "date": payload.date,
            "requested_check_in": payload.requested_check_in,
            "requested_check_out": payload.requested_check_out,
            "requested_status": payload.requested_status,
            "reason": payload.reason,
            "status": "PENDING",
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "created_at": now,
            "created_by": user_doc["email"],
        }
        res = await self.att_corr_col.insert_one(doc)
        doc["_id"] = res.inserted_id

        # Audit log
        await self.audit_col.insert_one({
            "email": user_doc["email"],
            "action": "ATTENDANCE_CORRECTION_REQUESTED",
            "resource": req_number,
            "timestamp": now,
            "status": "PENDING",
            "details": {"date": payload.date, "reason": payload.reason}
        })

        # Notification
        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Correction Request Submitted",
            message=f"Attendance correction request {req_number} submitted for {payload.date}.",
            notif_type=NotificationType.ATTENDANCE,
        )

        return doc

    # -------------------------------------------------------------
    # 6. Leave Application & Policy Enforcement
    # -------------------------------------------------------------
    async def apply_leave(self, user_doc: Dict[str, Any], leave_data: Any) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        if leave_data.end_date < leave_data.start_date:
            raise ValueError("End date cannot precede start date.")

        # Duplicate / Overlap check
        overlap = await self.leaves_col.find_one({
            "$or": [{"employee_id": emp_id_str}, {"employee_code": emp_code}],
            "status": {"$in": [LeaveStatus.PENDING.value, LeaveStatus.APPROVED.value]},
            "$or": [
                {"start_date": {"$lte": leave_data.end_date}, "end_date": {"$gte": leave_data.start_date}},
            ]
        })
        if overlap:
            raise ValueError(
                f"Overlapping leave request prevented: You already have a {overlap.get('status')} "
                f"leave ({overlap.get('application_number')}) from {overlap.get('start_date')} to {overlap.get('end_date')}."
            )

        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.leaves_col.count_documents({
            "application_number": {"$regex": f"^LV-{ym_prefix}-"}
        })
        app_num = f"LV-{ym_prefix}-{(count + 1):04d}"

        doc = {
            "application_number": app_num,
            "employee_id": emp_id_str,
            "employee_code": emp_code,
            "employee_name": emp_doc.get("full_name", user_doc.get("full_name")),
            "department": emp_doc.get("department", "Operations"),
            "unit_id": emp_doc.get("unit_id", "Unit_1"),
            "leave_type": leave_data.leave_type.value if hasattr(leave_data.leave_type, "value") else str(leave_data.leave_type),
            "start_date": leave_data.start_date,
            "end_date": leave_data.end_date,
            "days_count": float(leave_data.days_count),
            "reason": leave_data.reason,
            "status": LeaveStatus.PENDING.value,
            "approved_by": None,
            "approved_at": None,
            "rejection_reason": None,
            "created_at": now,
            "created_by": user_doc["email"],
        }
        res = await self.leaves_col.insert_one(doc)
        doc["_id"] = res.inserted_id

        # Notification
        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Leave Application Submitted",
            message=f"Leave application {app_num} ({leave_data.days_count} days) submitted for review.",
            notif_type=NotificationType.LEAVE,
            link="/attendance",
        )

        return doc

    async def cancel_leave(self, user_doc: Dict[str, Any], leave_id: str) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        query = {"_id": ObjectId(leave_id)} if ObjectId.is_valid(leave_id) else {"application_number": leave_id}
        doc = await self.leaves_col.find_one(query)
        if not doc:
            raise ValueError("Leave application not found.")

        # Ownership verification
        if doc.get("employee_id") != emp_id_str and doc.get("employee_code") != emp_code:
            raise ValueError("Unauthorized: You can only cancel your own leave applications.")

        if doc.get("status") != LeaveStatus.PENDING.value:
            raise ValueError(f"Cannot cancel leave application with status '{doc.get('status')}'. Only PENDING requests can be cancelled.")

        now = datetime.now(timezone.utc)
        await self.leaves_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": LeaveStatus.CANCELLED.value, "cancelled_at": now, "cancelled_by": user_doc["email"]}}
        )

        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Leave Application Cancelled",
            message=f"Leave application {doc.get('application_number')} was successfully cancelled.",
            notif_type=NotificationType.LEAVE,
        )

        return await self.leaves_col.find_one({"_id": doc["_id"]})

    # -------------------------------------------------------------
    # 7. Profile Correction Request
    # -------------------------------------------------------------
    async def submit_profile_correction(self, user_doc: Dict[str, Any], payload: ProfileCorrectionRequestCreate) -> Dict[str, Any]:
        emp_doc = await self.resolve_employee_doc(user_doc)
        emp_code = emp_doc.get("code")
        emp_id_str = str(emp_doc["_id"])

        # Prevent unauthorized modifications to system security fields
        protected_fields = ["department", "role", "permissions", "unit_id", "allowed_units", "account_type", "is_active", "password"]
        field_lower = payload.field_name.lower().strip()
        if field_lower in protected_fields:
            # Stored as a formal HR change request, NOT auto-applied
            pass

        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.prof_corr_col.count_documents({
            "request_number": {"$regex": f"^PCR-{ym_prefix}-"}
        })
        req_number = f"PCR-{ym_prefix}-{(count + 1):04d}"

        doc = {
            "request_number": req_number,
            "employee_id": emp_id_str,
            "employee_code": emp_code,
            "employee_name": emp_doc.get("full_name", user_doc.get("full_name")),
            "field_name": payload.field_name,
            "requested_value": payload.requested_value,
            "reason": payload.reason,
            "status": "PENDING",
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "created_at": now,
            "created_by": user_doc["email"],
        }
        res = await self.prof_corr_col.insert_one(doc)
        doc["_id"] = res.inserted_id

        await self.create_notification(
            user_id=str(user_doc["_id"]),
            employee_code=emp_code,
            title="Profile Correction Requested",
            message=f"Request {req_number} submitted to HR for field '{payload.field_name}'.",
            notif_type=NotificationType.INFO,
        )

        return doc

    # -------------------------------------------------------------
    # 8. Notifications Helper
    # -------------------------------------------------------------
    async def create_notification(
        self,
        user_id: Optional[str],
        employee_code: Optional[str],
        title: str,
        message: str,
        notif_type: NotificationType = NotificationType.INFO,
        link: Optional[str] = None,
        recipient_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "employee_code": employee_code,
            "title": title,
            "message": message,
            "notification_type": notif_type.value if hasattr(notif_type, "value") else str(notif_type),
            "is_read": False,
            "link": link,
            "recipient_role": recipient_role,
            "metadata": metadata or {},
            "created_at": now,
            "read_at": None,
        }
        res = await self.notif_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc
