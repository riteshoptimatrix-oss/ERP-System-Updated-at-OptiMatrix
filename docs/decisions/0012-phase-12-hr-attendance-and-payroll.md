# Architecture Decision Record (ADR) 0012: Phase 12 - HR, Attendance, and Payroll Management

## Context
RG Tech operates two manufacturing facilities (`Unit 1` and `Unit 2`) with specialized production line staff, CNC machinists, QC technicians, warehouse workers, and general administration personnel. To ensure seamless production operations, accurate cost allocation, and strict statutory compliance, the enterprise requires an auditable Human Resources, Attendance, and Payroll management module.

Crucial business mandates for this implementation:
1. **Attendance-to-Payroll Integration**: Payroll calculations must be grounded in verified daily punch records, approved leaves, loss-of-pay (LOP) deductions for unpaid absences, and supervisor-approved overtime hours.
2. **Deterministic Statutory Rules**: Calculations must strictly follow approved statutory standards:
   - Provident Fund (PF): 12% on Basic Salary component.
   - Employee State Insurance (ESI): 0.75% on Total Gross Earnings.
   - Professional Tax (PT): State-mandated slab deduction (₹200).
   - Loss of Pay (LOP): Prorated daily rate calculated as $\text{Base Monthly Salary} / \text{Standard Working Days}$.
   - Overtime Pay: Approved overtime hours $\times$ configured hourly overtime rate.
3. **Workflow Transitions & Immutability**:
   - Payroll runs follow a controlled lifecycle: `DRAFT` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` $\rightarrow$ `POSTED`.
   - Once marked `POSTED`, the payroll run is locked against edits, and duplicate runs for the same period and manufacturing unit are strictly blocked.
4. **General Ledger Journal Voucher Export**:
   - Double-entry accounting voucher interface with balanced debits ($\text{Salaries \& Wages Expense}$) and credits ($\text{PF Payable}, \text{ESI Payable}, \text{PT Payable}, \text{TDS Withholding}, \text{Net Salaries Payable}$).
5. **Role-Based Access Control (RBAC)**: Protect sensitive salary and compensation records from unauthorized exposure through backend route permissions.

## Decision
1. **Collections & Schema Design in MongoDB**:
   - `shifts`: Configurable plant shifts (`shift_code`, `start_time`, `end_time`, `break_duration_minutes`, `grace_period_minutes`, `unit_id`, `is_active`).
   - `attendance_records`: Unique compound index on `(employee_id, date)`. Stores check-in, check-out, hours worked, approved overtime hours, status (`PRESENT`, `HALF_DAY`, `ABSENT`, `ON_LEAVE`, `HOLIDAY`), and supervisor correction tracking (`is_corrected`, `correction_reason`, `corrected_by`).
   - `leave_requests`: Unique application numbering (`LV-YYYYMM-XXXX`), start/end dates, leave types (`CASUAL_LEAVE`, `SICK_LEAVE`, `EARNED_LEAVE`, `UNPAID_LEAVE`), and review workflows (`status`, `approved_by`, `rejection_reason`).
   - `salary_structures`: Unique index on `employee_id`. Stores Base Monthly CTC, Basic Salary, HRA, Conveyance, Special Allowance, Overtime Hourly Rate, PF/ESI applicability, PT, TDS, and bank details.
   - `payroll_runs`: Unique `run_number` (`PAY-YYYYMM-XXXX`), `period`, `unit_id`, `working_days_in_month`, status (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `POSTED`), total gross, deductions, and net payouts.
   - `payroll_items`: Unique item per employee per period. Itemized line breakdowns including attendance totals, calculated earnings, LOP deductions, statutory deductions, net pay, and payslip reference (`SLIP-YYYYMM-EMPCODE`).

2. **Backend Architecture**:
   - Repository `HRRepository` (`backend/app/repositories/hr_repository.py`): Shift management, attendance logging with duplicate prevention, supervisor correction audit, leave lifecycle, and period attendance aggregation (`get_employee_attendance_for_period`).
   - Repository `PayrollRepository` (`backend/app/repositories/payroll_repository.py`): Salary structures CRUD, automated attendance-backed payroll calculation, workflow lifecycle (`review`, `approve`, `post`), duplicate run prevention, payslip breakdown retrieval, and balanced general ledger journal voucher export.
   - API endpoints registered under `/api/v1/hr` and `/api/v1/payroll` with CSRF protection and role-based permissions (`hr:*`, `attendance:*`, `payroll:*`).

3. **Frontend Architecture**:
   - `/attendance`: Plant attendance tracking, punch logging, supervisor correction modal, leave request workflow, and KPI cards.
   - `/payroll`: Monthly payroll run generator, line-item inspector, payslip viewer, double-entry journal voucher modal, and salary structure configuration master.
   - `/hr`: Staff directory with department and facility filters, and plant shift configuration master.

## Status
Accepted and verified.

## Consequences
- **Positive**: Complete automated pipeline from daily biometric/attendance punches to net salary disbursement and double-entry accounting entries.
- **Data Integrity**: Duplicate attendance punches and duplicate posted payroll runs are physically rejected at the database and application layer.
- **Auditability**: Supervisor corrections on punches and payroll approvals are timestamped with user credentials and immutably locked upon posting.
