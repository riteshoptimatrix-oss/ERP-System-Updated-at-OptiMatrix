from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
import logging
from app.schemas.hr import (
    ShiftConfigCreate,
    AttendanceEntryCreate,
    AttendanceCorrectionRequest,
    AttendanceStatus,
    LeaveApplicationCreate,
    LeaveApprovalRequest,
    LeaveStatus,
    LeaveType,
)
from app.models.user import ManufacturingUnit

logger = logging.getLogger(__name__)


class HRRepository:
    def __init__(self, db: Any):
        self.db = db
        self.shifts_col = db["shifts"]
        self.att_col = db["attendance_records"]
        self.leaves_col = db["leave_requests"]
        self.emp_col = db["employees"]

    async def generate_leave_number(self) -> str:
        """Generate unique leave application identifier e.g. LV-202610-0001."""
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.leaves_col.count_documents({
            "application_number": {"$regex": f"^LV-{ym_prefix}-"}
        })
        return f"LV-{ym_prefix}-{(count + 1):04d}"

    # -------------------------------------------------------------
    # 1. Shifts Management
    # -------------------------------------------------------------
    async def create_shift(self, shift_data: ShiftConfigCreate, created_by: str) -> Dict[str, Any]:
        """Create or configure a facility work shift."""
        existing = await self.shifts_col.find_one({"shift_code": shift_data.shift_code})
        if existing:
            raise ValueError(f"Shift with code '{shift_data.shift_code}' already exists.")

        now = datetime.now(timezone.utc)
        doc = {
            "shift_code": shift_data.shift_code,
            "name": shift_data.name,
            "shift_type": shift_data.shift_type.value,
            "start_time": shift_data.start_time,
            "end_time": shift_data.end_time,
            "break_duration_minutes": shift_data.break_duration_minutes,
            "grace_period_minutes": shift_data.grace_period_minutes,
            "standard_work_hours": shift_data.standard_work_hours,
            "unit_id": shift_data.unit_id.value,
            "is_active": shift_data.is_active,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.shifts_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_shifts(self, unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active shifts for a manufacturing unit."""
        query: Dict[str, Any] = {"is_active": True}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = {"$in": [unit_id, "BOTH"]}
        cursor = self.shifts_col.find(query).sort("shift_code", 1)
        return await cursor.to_list(length=50)

    # -------------------------------------------------------------
    # 2. Daily Attendance Logging & Verification
    # -------------------------------------------------------------
    async def record_attendance(self, att_data: AttendanceEntryCreate, created_by: str) -> Dict[str, Any]:
        """Record daily attendance with duplicate prevention and employee resolution."""
        emp_query = (
            {"_id": ObjectId(att_data.employee_id)}
            if ObjectId.is_valid(att_data.employee_id)
            else {"code": att_data.employee_code or att_data.employee_id}
        )
        emp_doc = await self.emp_col.find_one(emp_query)
        if not emp_doc:
            raise ValueError(f"Employee '{att_data.employee_id}' not found.")

        # Duplicate check: one record per employee per date
        existing = await self.att_col.find_one({
            "employee_id": str(emp_doc["_id"]),
            "date": att_data.date,
        })
        if existing:
            raise ValueError(
                f"Duplicate attendance entry prevented: Attendance for {emp_doc.get('full_name')} "
                f"({emp_doc.get('code')}) is already recorded for {att_data.date}."
            )

        now = datetime.now(timezone.utc)
        doc = {
            "employee_id": str(emp_doc["_id"]),
            "employee_code": emp_doc.get("code", att_data.employee_code),
            "employee_name": emp_doc.get("full_name", "Employee"),
            "department": emp_doc.get("department", "Operations"),
            "designation": emp_doc.get("designation", "Staff"),
            "date": att_data.date,
            "unit_id": att_data.unit_id.value if att_data.unit_id else emp_doc.get("unit_id", "Unit_1"),
            "shift_code": att_data.shift_code or "SHIFT-GEN",
            "check_in": att_data.check_in,
            "check_out": att_data.check_out,
            "status": att_data.status.value,
            "hours_worked": float(att_data.hours_worked),
            "overtime_hours": float(att_data.overtime_hours),
            "is_corrected": False,
            "correction_reason": None,
            "corrected_by": None,
            "remarks": att_data.remarks,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.att_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_attendance(
        self,
        date: Optional[str] = None,
        employee_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Paginated search for attendance entries."""
        query: Dict[str, Any] = {}
        if date:
            query["date"] = date
        if employee_id:
            query["$or"] = [
                {"employee_id": employee_id},
                {"employee_code": employee_id},
            ]
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status:
            query["status"] = status
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["date"] = date_filter

        total = await self.att_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.att_col.find(query).sort("date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    async def correct_attendance(
        self,
        record_id: str,
        correction: AttendanceCorrectionRequest,
        corrected_by: str,
    ) -> Dict[str, Any]:
        """Apply an authorized supervisor correction to an attendance record."""
        query = {"_id": ObjectId(record_id)} if ObjectId.is_valid(record_id) else {"_id": record_id}
        doc = await self.att_col.find_one(query)
        if not doc:
            raise ValueError("Attendance record not found.")

        update_ops: Dict[str, Any] = {
            "is_corrected": True,
            "correction_reason": correction.correction_reason,
            "corrected_by": corrected_by,
            "updated_at": datetime.now(timezone.utc),
        }
        if correction.check_in is not None:
            update_ops["check_in"] = correction.check_in
        if correction.check_out is not None:
            update_ops["check_out"] = correction.check_out
        if correction.status is not None:
            update_ops["status"] = correction.status.value
        if correction.hours_worked is not None:
            update_ops["hours_worked"] = float(correction.hours_worked)
        if correction.overtime_hours is not None:
            update_ops["overtime_hours"] = float(correction.overtime_hours)

        await self.att_col.update_one({"_id": doc["_id"]}, {"$set": update_ops})
        return await self.att_col.find_one({"_id": doc["_id"]})

    # -------------------------------------------------------------
    # 3. Leave Applications & Approvals
    # -------------------------------------------------------------
    async def apply_leave(self, leave_data: LeaveApplicationCreate, applied_by: str) -> Dict[str, Any]:
        """Submit a leave request."""
        emp_query = (
            {"_id": ObjectId(leave_data.employee_id)}
            if ObjectId.is_valid(leave_data.employee_id)
            else {"code": leave_data.employee_id}
        )
        emp_doc = await self.emp_col.find_one(emp_query)
        if not emp_doc:
            raise ValueError("Employee not found.")

        if leave_data.end_date < leave_data.start_date:
            raise ValueError("End date cannot precede start date.")

        app_num = await self.generate_leave_number()
        now = datetime.now(timezone.utc)
        doc = {
            "application_number": app_num,
            "employee_id": str(emp_doc["_id"]),
            "employee_code": emp_doc.get("code", "EMP"),
            "employee_name": emp_doc.get("full_name", "Employee"),
            "department": emp_doc.get("department", "Operations"),
            "unit_id": emp_doc.get("unit_id", "Unit_1"),
            "leave_type": leave_data.leave_type.value,
            "start_date": leave_data.start_date,
            "end_date": leave_data.end_date,
            "days_count": float(leave_data.days_count),
            "reason": leave_data.reason,
            "status": LeaveStatus.PENDING.value,
            "approved_by": None,
            "approved_at": None,
            "rejection_reason": None,
            "created_at": now,
            "created_by": applied_by,
        }
        res = await self.leaves_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def review_leave(
        self,
        leave_id: str,
        review: LeaveApprovalRequest,
        reviewer: str,
    ) -> Dict[str, Any]:
        """Approve or reject a leave application."""
        query = {"_id": ObjectId(leave_id)} if ObjectId.is_valid(leave_id) else {"application_number": leave_id}
        doc = await self.leaves_col.find_one(query)
        if not doc:
            raise ValueError("Leave application not found.")

        now = datetime.now(timezone.utc)
        update_ops: Dict[str, Any] = {
            "status": review.status.value,
            "approved_by": reviewer,
            "approved_at": now,
        }
        if review.rejection_reason:
            update_ops["rejection_reason"] = review.rejection_reason

        await self.leaves_col.update_one({"_id": doc["_id"]}, {"$set": update_ops})

        # Notify employee of the decision
        user_doc = await self.db["users"].find_one({
            "$or": [
                {"employee_code": doc.get("employee_code")},
                {"email": doc.get("created_by")},
            ]
        })
        if user_doc:
            await self.db["notifications"].insert_one({
                "user_id": str(user_doc["_id"]),
                "employee_code": doc.get("employee_code"),
                "title": f"Leave Request {review.status.value.title()}",
                "message": f"Your leave request {doc.get('application_number')} ({doc.get('days_count')} days) has been {review.status.value.lower()} by HR ({reviewer})." + (f" Reason: {review.rejection_reason}" if review.rejection_reason else ""),
                "notification_type": "SUCCESS" if review.status.value == "APPROVED" else "ALERT",
                "is_read": False,
                "link": "/employee/leave",
                "created_at": now,
            })

        return await self.leaves_col.find_one({"_id": doc["_id"]})

    async def list_leaves(
        self,
        employee_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Paginated list of leave requests."""
        query: Dict[str, Any] = {}
        if employee_id:
            query["$or"] = [
                {"employee_id": employee_id},
                {"employee_code": employee_id},
            ]
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status:
            query["status"] = status

        total = await self.leaves_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.leaves_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 4. Period Attendance Aggregation for Payroll
    # -------------------------------------------------------------
    async def get_employee_attendance_for_period(
        self,
        employee_id: str,
        period: str,  # "YYYY-MM"
    ) -> Dict[str, float]:
        """
        Aggregate total present days, paid leaves, unpaid LOP days, and overtime
        for a given employee across a specific payroll month (YYYY-MM).
        """
        cursor = self.att_col.find({
            "employee_id": employee_id,
            "date": {"$regex": f"^{period}-"},
        })
        records = await cursor.to_list(length=62)

        present_days = 0.0
        paid_leave_days = 0.0
        unpaid_leave_days = 0.0
        total_ot_hours = 0.0

        for r in records:
            st = r.get("status")
            if st == AttendanceStatus.PRESENT.value:
                present_days += 1.0
            elif st == AttendanceStatus.HALF_DAY.value:
                present_days += 0.5
                unpaid_leave_days += 0.5
            elif st == AttendanceStatus.ON_LEAVE.value:
                paid_leave_days += 1.0
            elif st == AttendanceStatus.ABSENT.value:
                unpaid_leave_days += 1.0

            total_ot_hours += float(r.get("overtime_hours", 0.0))

        return {
            "present_days": present_days,
            "paid_leave_days": paid_leave_days,
            "unpaid_leave_days": unpaid_leave_days,
            "overtime_hours": round(total_ot_hours, 2),
        }

    async def get_hr_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate workforce attendance KPIs for the active manufacturing unit."""
        unit_filter: Dict[str, Any] = {"is_active": True}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            unit_filter["unit_id"] = {"$in": [unit_id, "BOTH"]}

        total_employees = await self.emp_col.count_documents(unit_filter)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        att_filter: Dict[str, Any] = {"date": today_str}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            att_filter["unit_id"] = unit_id

        present_count = await self.att_col.count_documents({**att_filter, "status": AttendanceStatus.PRESENT.value})
        leave_count = await self.att_col.count_documents({**att_filter, "status": AttendanceStatus.ON_LEAVE.value})
        absent_count = await self.att_col.count_documents({**att_filter, "status": AttendanceStatus.ABSENT.value})

        # Overtime in current month
        month_prefix = today_str[:7]
        ot_pipeline = [
            {"$match": {"date": {"$regex": f"^{month_prefix}-"}}},
            {"$group": {"_id": None, "total_ot": {"$sum": "$overtime_hours"}}},
        ]
        ot_res = await self.att_col.aggregate(ot_pipeline).to_list(length=1)
        total_ot = float(ot_res[0].get("total_ot", 0.0)) if ot_res else 0.0

        pending_leaves = await self.leaves_col.count_documents({"status": LeaveStatus.PENDING.value})

        return {
            "unit_id": unit_id,
            "total_active_employees": total_employees,
            "present_today": present_count,
            "on_leave_today": leave_count,
            "absent_today": absent_count,
            "total_overtime_hours_month": round(total_ot, 1),
            "pending_leave_requests": pending_leaves,
        }
