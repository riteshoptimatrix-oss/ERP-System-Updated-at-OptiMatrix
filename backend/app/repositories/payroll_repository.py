from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
import logging
from app.schemas.payroll import (
    SalaryStructureInput,
    PayrollRunCreate,
    PayrollRunStatus,
)
from app.repositories.hr_repository import HRRepository
from app.models.user import ManufacturingUnit

logger = logging.getLogger(__name__)


class PayrollRepository:
    def __init__(self, db: Any):
        self.db = db
        self.struct_col = db["salary_structures"]
        self.runs_col = db["payroll_runs"]
        self.items_col = db["payroll_items"]
        self.emp_col = db["employees"]
        self.hr_repo = HRRepository(db)

    async def generate_run_number(self) -> str:
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.runs_col.count_documents({
            "run_number": {"$regex": f"^PAY-{ym_prefix}-"}
        })
        return f"PAY-{ym_prefix}-{(count + 1):04d}"

    async def generate_payslip_number(self) -> str:
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.items_col.count_documents({
            "payslip_number": {"$regex": f"^SLIP-{ym_prefix}-"}
        })
        return f"SLIP-{ym_prefix}-{(count + 1):04d}"

    # -------------------------------------------------------------
    # 1. Salary Structure Management
    # -------------------------------------------------------------
    async def upsert_salary_structure(
        self,
        data: SalaryStructureInput,
        updated_by: str,
    ) -> Dict[str, Any]:
        """Define or update employee compensation and allowance structure."""
        emp_query = (
            {"_id": ObjectId(data.employee_id)}
            if ObjectId.is_valid(data.employee_id)
            else {"code": data.employee_id}
        )
        emp_doc = await self.emp_col.find_one(emp_query)
        if not emp_doc:
            raise ValueError(f"Employee '{data.employee_id}' not found.")

        now = datetime.now(timezone.utc)
        gross_monthly = round(
            data.basic_salary + data.hra + data.conveyance_allowance + data.special_allowance, 2
        )

        doc = {
            "employee_id": str(emp_doc["_id"]),
            "employee_code": emp_doc.get("code", "EMP"),
            "employee_name": emp_doc.get("full_name", "Employee"),
            "department": emp_doc.get("department", "Operations"),
            "designation": emp_doc.get("designation", "Staff"),
            "unit_id": data.unit_id.value if data.unit_id else emp_doc.get("unit_id", "Unit_1"),
            "base_monthly_salary": float(data.base_monthly_salary),
            "basic_salary": float(data.basic_salary),
            "hra": float(data.hra),
            "conveyance_allowance": float(data.conveyance_allowance),
            "special_allowance": float(data.special_allowance),
            "overtime_hourly_rate": float(data.overtime_hourly_rate),
            "gross_monthly_standard": gross_monthly,
            "pf_applicable": data.pf_applicable,
            "pf_percentage": float(data.pf_percentage),
            "esi_applicable": data.esi_applicable,
            "esi_percentage": float(data.esi_percentage),
            "professional_tax": float(data.professional_tax),
            "tds_monthly": float(data.tds_monthly),
            "bank_name": data.bank_name,
            "bank_account_number": data.bank_account_number,
            "bank_ifsc": data.bank_ifsc,
            "updated_at": now,
            "updated_by": updated_by,
        }

        existing = await self.struct_col.find_one({"employee_id": str(emp_doc["_id"])})
        if existing:
            await self.struct_col.update_one({"_id": existing["_id"]}, {"$set": doc})
            doc["_id"] = existing["_id"]
            doc["created_at"] = existing.get("created_at", now)
        else:
            doc["created_at"] = now
            res = await self.struct_col.insert_one(doc)
            doc["_id"] = res.inserted_id

        return doc

    async def get_salary_structure(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve employee salary structure."""
        emp_query = (
            {"_id": ObjectId(employee_id)}
            if ObjectId.is_valid(employee_id)
            else {"code": employee_id}
        )
        emp_doc = await self.emp_col.find_one(emp_query)
        target_id = str(emp_doc["_id"]) if emp_doc else employee_id
        target_code = emp_doc.get("code") if emp_doc else employee_id

        return await self.struct_col.find_one({
            "$or": [
                {"employee_id": target_id},
                {"employee_id": target_code},
                {"employee_code": target_code},
            ]
        })

    async def list_salary_structures(self, unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all configured salary structures."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        cursor = self.struct_col.find(query).sort("employee_code", 1)
        return await cursor.to_list(length=100)

    # -------------------------------------------------------------
    # 2. Automated Payroll Calculations & Run Processing
    # -------------------------------------------------------------
    async def create_and_calculate_payroll_run(
        self,
        run_data: PayrollRunCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Calculates monthly payroll run based on attendance, Loss-of-Pay (LOP),
        and approved overtime hours.
        Prevents duplicate posted runs for the same period.
        """
        # Duplicate check: check if already POSTED
        posted_existing = await self.runs_col.find_one({
            "period": run_data.period,
            "unit_id": run_data.unit_id.value,
            "status": PayrollRunStatus.POSTED.value,
        })
        if posted_existing:
            raise ValueError(
                f"Duplicate payroll run prevented: Period {run_data.period} for {run_data.unit_id.value} "
                f"is already POSTED and locked (Run: {posted_existing.get('run_number')})."
            )

        # Retrieve active employees for this facility
        emp_query: Dict[str, Any] = {"is_active": True}
        if run_data.unit_id.value not in ["ALL", "BOTH"]:
            emp_query["unit_id"] = {"$in": [run_data.unit_id.value, "BOTH"]}

        employees = await self.emp_col.find(emp_query).to_list(length=200)
        if not employees:
            raise ValueError(f"No active employees found for facility {run_data.unit_id.value}.")

        now = datetime.now(timezone.utc)
        run_number = await self.generate_run_number()

        total_gross = 0.0
        total_ded = 0.0
        total_net = 0.0
        processed_items: List[Dict[str, Any]] = []

        working_days = run_data.working_days_in_month

        for emp in employees:
            emp_id = str(emp["_id"])
            emp_code = emp.get("code", "")
            struct = await self.struct_col.find_one({
                "$or": [
                    {"employee_id": emp_id},
                    {"employee_id": emp_code},
                    {"employee_code": emp_code},
                ]
            })

            # Base salary figures
            base_monthly = float(struct.get("base_monthly_salary", 0.0)) if struct else 0.0
            basic = float(struct.get("basic_salary", 0.0)) if struct else 0.0
            hra = float(struct.get("hra", 0.0)) if struct else 0.0
            conveyance = float(struct.get("conveyance_allowance", 0.0)) if struct else 0.0
            special = float(struct.get("special_allowance", 0.0)) if struct else 0.0
            ot_rate = float(struct.get("overtime_hourly_rate", 0.0)) if struct else 0.0

            # Daily rate for LOP proration
            daily_rate = round(base_monthly / working_days, 2) if working_days > 0 and base_monthly > 0 else 0.0

            # Pull actual attendance for period
            att = await self.hr_repo.get_employee_attendance_for_period(emp_id, run_data.period)
            present_days = att.get("present_days", 0.0)
            paid_leave_days = att.get("paid_leave_days", 0.0)
            unpaid_days = att.get("unpaid_leave_days", 0.0)
            ot_hours = att.get("overtime_hours", 0.0)

            # Calculations
            ot_pay = round(ot_hours * ot_rate, 2)
            gross_earnings = round(basic + hra + conveyance + special + ot_pay, 2)

            lop_deduction = round(unpaid_days * daily_rate, 2)
            pf_pct = float(struct.get("pf_percentage", 12.0)) if struct and struct.get("pf_applicable") else 0.0
            pf_deduction = round(basic * (pf_pct / 100.0), 2)

            esi_pct = float(struct.get("esi_percentage", 0.75)) if struct and struct.get("esi_applicable") else 0.0
            esi_deduction = round(gross_earnings * (esi_pct / 100.0), 2)

            pt = float(struct.get("professional_tax", 0.0)) if struct else 0.0
            tds = float(struct.get("tds_monthly", 0.0)) if struct else 0.0

            total_deductions = round(lop_deduction + pf_deduction + esi_deduction + pt + tds, 2)
            net_pay = max(0.0, round(gross_earnings - total_deductions, 2))

            payslip_number = f"SLIP-{run_data.period}-{emp.get('code', 'EMP')}"

            item_doc = {
                "payroll_run_number": run_number,
                "payslip_number": payslip_number,
                "employee_id": emp_id,
                "employee_code": emp.get("code", ""),
                "employee_name": emp.get("full_name", ""),
                "department": emp.get("department", "Operations"),
                "designation": emp.get("designation", "Staff"),
                "period": run_data.period,
                "unit_id": run_data.unit_id.value,
                "standard_working_days": working_days,
                "present_days": present_days,
                "paid_leave_days": paid_leave_days,
                "unpaid_leave_days": unpaid_days,
                "overtime_hours": ot_hours,
                "basic": basic,
                "hra": hra,
                "conveyance": conveyance,
                "special_allowance": special,
                "overtime_pay": ot_pay,
                "gross_earnings": gross_earnings,
                "lop_deduction": lop_deduction,
                "pf_deduction": pf_deduction,
                "esi_deduction": esi_deduction,
                "professional_tax": pt,
                "tds_deduction": tds,
                "total_deductions": total_deductions,
                "net_pay": net_pay,
                "bank_name": struct.get("bank_name") if struct else None,
                "bank_account_number": struct.get("bank_account_number") if struct else None,
                "bank_ifsc": struct.get("bank_ifsc") if struct else None,
                "created_at": now,
            }

            processed_items.append(item_doc)
            total_gross += gross_earnings
            total_ded += total_deductions
            total_net += net_pay

        # Insert Run Document
        run_doc = {
            "run_number": run_number,
            "period": run_data.period,
            "unit_id": run_data.unit_id.value,
            "working_days_in_month": working_days,
            "total_employees": len(processed_items),
            "total_gross_payout": round(total_gross, 2),
            "total_deductions": round(total_ded, 2),
            "total_net_payout": round(total_net, 2),
            "status": PayrollRunStatus.DRAFT.value,
            "notes": run_data.notes,
            "created_at": now,
            "created_by": created_by,
            "reviewed_at": None,
            "reviewed_by": None,
            "approved_at": None,
            "approved_by": None,
            "posted_at": None,
            "posted_by": None,
        }

        res_run = await self.runs_col.insert_one(run_doc)
        run_doc["_id"] = res_run.inserted_id

        # Insert Items with reference to run_id
        for it in processed_items:
            it["payroll_run_id"] = str(res_run.inserted_id)

        if processed_items:
            await self.items_col.insert_many(processed_items)

        return run_doc

    async def get_payroll_run_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        query = {"_id": ObjectId(run_id)} if ObjectId.is_valid(run_id) else {"run_number": run_id}
        return await self.runs_col.find_one(query)

    async def list_payroll_runs(
        self,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        period: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status:
            query["status"] = status
        if period:
            query["period"] = period

        total = await self.runs_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.runs_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    async def list_payroll_items(self, run_id: str) -> List[Dict[str, Any]]:
        cursor = self.items_col.find({"payroll_run_id": run_id}).sort("employee_code", 1)
        return await cursor.to_list(length=300)

    # -------------------------------------------------------------
    # 3. Workflow Transitions: Review, Approve, Post
    # -------------------------------------------------------------
    async def review_payroll_run(self, run_id: str, reviewer: str) -> Dict[str, Any]:
        doc = await self.get_payroll_run_by_id(run_id)
        if not doc:
            raise ValueError("Payroll run not found.")
        if doc.get("status") != PayrollRunStatus.DRAFT.value:
            raise ValueError(f"Cannot submit payroll in status '{doc.get('status')}' for review.")

        now = datetime.now(timezone.utc)
        await self.runs_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": PayrollRunStatus.UNDER_REVIEW.value,
                    "reviewed_at": now,
                    "reviewed_by": reviewer,
                }
            },
        )
        return await self.runs_col.find_one({"_id": doc["_id"]})

    async def approve_payroll_run(self, run_id: str, approver: str) -> Dict[str, Any]:
        doc = await self.get_payroll_run_by_id(run_id)
        if not doc:
            raise ValueError("Payroll run not found.")
        if doc.get("status") not in [PayrollRunStatus.DRAFT.value, PayrollRunStatus.UNDER_REVIEW.value]:
            raise ValueError(f"Cannot approve payroll in status '{doc.get('status')}'.")

        now = datetime.now(timezone.utc)
        await self.runs_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": PayrollRunStatus.APPROVED.value,
                    "approved_at": now,
                    "approved_by": approver,
                }
            },
        )
        return await self.runs_col.find_one({"_id": doc["_id"]})

    async def post_payroll_run(self, run_id: str, poster: str) -> Dict[str, Any]:
        """Final posting: locks records, prevents changes or duplicate runs."""
        doc = await self.get_payroll_run_by_id(run_id)
        if not doc:
            raise ValueError("Payroll run not found.")
        if doc.get("status") != PayrollRunStatus.APPROVED.value:
            raise ValueError("Only APPROVED payroll runs can be POSTED to general ledger.")

        now = datetime.now(timezone.utc)
        await self.runs_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": PayrollRunStatus.POSTED.value,
                    "posted_at": now,
                    "posted_by": poster,
                }
            },
        )
        return await self.runs_col.find_one({"_id": doc["_id"]})

    # -------------------------------------------------------------
    # 4. Payslip Retrieval
    # -------------------------------------------------------------
    async def get_payslip(self, employee_id: str, period: str) -> Optional[Dict[str, Any]]:
        """Retrieve individual payslip details."""
        emp_query = (
            {"_id": ObjectId(employee_id)}
            if ObjectId.is_valid(employee_id)
            else {"code": employee_id}
        )
        emp_doc = await self.emp_col.find_one(emp_query)
        emp_id_str = str(emp_doc["_id"]) if emp_doc else employee_id

        item = await self.items_col.find_one({
            "$or": [{"employee_id": emp_id_str}, {"employee_code": employee_id}],
            "period": period,
        })
        if not item:
            return None

        return {
            "payslip_number": item.get("payslip_number", f"SLIP-{period}"),
            "period": item.get("period", period),
            "unit_id": item.get("unit_id", "Unit_1"),
            "employee_id": item.get("employee_id"),
            "employee_code": item.get("employee_code"),
            "employee_name": item.get("employee_name"),
            "department": item.get("department"),
            "designation": item.get("designation"),
            "bank_name": item.get("bank_name"),
            "bank_account_number": item.get("bank_account_number"),
            "bank_ifsc": item.get("bank_ifsc"),
            "standard_working_days": item.get("standard_working_days", 26),
            "present_days": item.get("present_days", 0.0),
            "paid_leave_days": item.get("paid_leave_days", 0.0),
            "lop_days": item.get("unpaid_leave_days", 0.0),
            "overtime_hours": item.get("overtime_hours", 0.0),
            "basic": item.get("basic", 0.0),
            "hra": item.get("hra", 0.0),
            "conveyance": item.get("conveyance", 0.0),
            "special_allowance": item.get("special_allowance", 0.0),
            "overtime_pay": item.get("overtime_pay", 0.0),
            "total_earnings": item.get("gross_earnings", 0.0),
            "lop_deduction": item.get("lop_deduction", 0.0),
            "pf_deduction": item.get("pf_deduction", 0.0),
            "esi_deduction": item.get("esi_deduction", 0.0),
            "professional_tax": item.get("professional_tax", 0.0),
            "tds_deduction": item.get("tds_deduction", 0.0),
            "total_deductions": item.get("total_deductions", 0.0),
            "net_salary_payable": item.get("net_pay", 0.0),
            "generated_at": datetime.now(timezone.utc),
        }

    # -------------------------------------------------------------
    # 5. Accounting Integration Interface
    # -------------------------------------------------------------
    async def get_accounting_export(self, run_id: str) -> Dict[str, Any]:
        """
        Generate balanced double-entry journal entry export:
        Debit: Salary & Wages Expense (Total Gross)
        Credit: PF Payable, ESI Payable, PT Payable, TDS Payable, Net Salaries Payable.
        """
        run = await self.get_payroll_run_by_id(run_id)
        if not run:
            raise ValueError("Payroll run not found.")

        items = await self.list_payroll_items(run_id)

        # Standard Gross is gross_earnings; effective salary expense after unpaid leave (LOP) proration is (gross_earnings - lop_deduction)
        tot_gross = round(sum(it.get("gross_earnings", 0.0) for it in items), 2)
        tot_lop = round(sum(it.get("lop_deduction", 0.0) for it in items), 2)
        tot_pf = round(sum(it.get("pf_deduction", 0.0) for it in items), 2)
        tot_esi = round(sum(it.get("esi_deduction", 0.0) for it in items), 2)
        tot_pt = round(sum(it.get("professional_tax", 0.0) for it in items), 2)
        tot_tds = round(sum(it.get("tds_deduction", 0.0) for it in items), 2)
        tot_net = round(sum(it.get("net_pay", 0.0) for it in items), 2)

        # Net Expense to debit is gross earnings minus unpaid absence deduction
        net_expense = round(tot_gross - tot_lop, 2)

        lines = [
            {
                "account_code": "EXP-SALARY-WAGES",
                "account_name": "Salaries, Wages & Allowances Expense (Net of LOP)",
                "debit": net_expense,
                "credit": 0.0,
                "description": f"Payroll expense for period {run.get('period')}",
            },
            {
                "account_code": "LIAB-PF-PAYABLE",
                "account_name": "Provident Fund (PF) Payable",
                "debit": 0.0,
                "credit": tot_pf,
                "description": "Employee PF deductions withheld",
            },
            {
                "account_code": "LIAB-ESI-PAYABLE",
                "account_name": "Employee State Insurance (ESI) Payable",
                "debit": 0.0,
                "credit": tot_esi,
                "description": "Employee ESI deductions withheld",
            },
            {
                "account_code": "LIAB-PT-PAYABLE",
                "account_name": "Professional Tax (PT) Payable",
                "debit": 0.0,
                "credit": tot_pt,
                "description": "State Professional Tax withheld",
            },
            {
                "account_code": "LIAB-TDS-PAYABLE",
                "account_name": "TDS / Income Tax Withholding Payable",
                "debit": 0.0,
                "credit": tot_tds,
                "description": "TDS tax withheld",
            },
            {
                "account_code": "LIAB-SALARY-NET-PAYABLE",
                "account_name": "Net Salaries Payable (Bank Disbursement)",
                "debit": 0.0,
                "credit": tot_net,
                "description": "Net salary payable to employee bank accounts",
            },
        ]

        total_credits = round(tot_pf + tot_esi + tot_pt + tot_tds + tot_net, 2)
        is_balanced = abs(net_expense - total_credits) < 0.05

        return {
            "voucher_number": f"JV-PAY-{run.get('period')}-{run.get('unit_id')}",
            "payroll_run_id": run_id,
            "period": run.get("period"),
            "unit_id": run.get("unit_id"),
            "posting_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "lines": lines,
            "total_debit": net_expense,
            "total_credit": total_credits,
            "is_balanced": is_balanced,
        }

    async def get_payroll_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate payroll summary metrics."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        active_runs_count = await self.runs_col.count_documents(query)
        latest_run = await self.runs_col.find_one(query, sort=[("created_at", -1)])

        latest_period = latest_run.get("period") if latest_run else None
        tot_gross = float(latest_run.get("total_gross_payout", 0.0)) if latest_run else 0.0
        tot_net = float(latest_run.get("total_net_payout", 0.0)) if latest_run else 0.0
        tot_ded = float(latest_run.get("total_deductions", 0.0)) if latest_run else 0.0

        struct_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            struct_query["unit_id"] = unit_id
        configured_structs = await self.struct_col.count_documents(struct_query)

        return {
            "unit_id": unit_id,
            "active_payroll_runs": active_runs_count,
            "latest_period": latest_period,
            "total_gross_payout": tot_gross,
            "total_net_payout": tot_net,
            "total_statutory_deductions": tot_ded,
            "configured_salary_structures_count": configured_structs,
        }
