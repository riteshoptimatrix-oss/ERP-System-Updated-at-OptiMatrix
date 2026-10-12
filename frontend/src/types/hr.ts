export type ShiftType = 'GENERAL' | 'SHIFT_1' | 'SHIFT_2' | 'NIGHT';
export type AttendanceStatus = 'PRESENT' | 'HALF_DAY' | 'ABSENT' | 'ON_LEAVE' | 'HOLIDAY';
export type LeaveType = 'CASUAL_LEAVE' | 'SICK_LEAVE' | 'EARNED_LEAVE' | 'UNPAID_LEAVE';
export type LeaveStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
export type PayrollRunStatus = 'DRAFT' | 'UNDER_REVIEW' | 'APPROVED' | 'POSTED';

// Shift Configuration
export interface ShiftConfig {
  id: string;
  shift_code: string;
  name: string;
  shift_type: ShiftType;
  start_time: string;
  end_time: string;
  break_duration_minutes: number;
  grace_period_minutes: number;
  standard_work_hours: number;
  unit_id: string;
  is_active: boolean;
  created_at: string;
  created_by: string;
}

export interface ShiftConfigCreate {
  shift_code: string;
  name: string;
  shift_type: ShiftType;
  start_time: string;
  end_time: string;
  break_duration_minutes: number;
  grace_period_minutes: number;
  standard_work_hours: number;
  unit_id: string;
  is_active: boolean;
}

// Attendance
export interface AttendanceEntry {
  id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  date: string;
  unit_id: string;
  shift_code: string;
  check_in?: string;
  check_out?: string;
  status: AttendanceStatus;
  hours_worked: number;
  overtime_hours: number;
  is_corrected: boolean;
  correction_reason?: string;
  corrected_by?: string;
  created_at: string;
  created_by: string;
}

export interface AttendanceEntryCreate {
  employee_id: string;
  employee_code: string;
  date: string;
  unit_id: string;
  shift_code?: string;
  check_in?: string;
  check_out?: string;
  status: AttendanceStatus;
  hours_worked: number;
  overtime_hours: number;
  remarks?: string;
}

export interface AttendanceCorrectionRequest {
  check_in?: string;
  check_out?: string;
  status?: AttendanceStatus;
  hours_worked?: number;
  overtime_hours?: number;
  correction_reason: string;
}

// Leave Application
export interface LeaveApplication {
  id: string;
  application_number: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  unit_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days_count: number;
  reason: string;
  status: LeaveStatus;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
  created_by: string;
}

export interface LeaveApplicationCreate {
  employee_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days_count: number;
  reason: string;
}

export interface LeaveApprovalRequest {
  status: LeaveStatus;
  rejection_reason?: string;
  notes?: string;
}

// HR Summary
export interface HRAttendanceSummary {
  unit_id?: string;
  total_active_employees: number;
  present_today: number;
  on_leave_today: number;
  absent_today: number;
  total_overtime_hours_month: number;
  pending_leave_requests: number;
}

// Salary Structure
export interface SalaryStructure {
  id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  unit_id: string;
  base_monthly_salary: number;
  basic_salary: number;
  hra: number;
  conveyance_allowance: number;
  special_allowance: number;
  overtime_hourly_rate: number;
  gross_monthly_standard: number;
  pf_applicable: boolean;
  pf_percentage: number;
  esi_applicable: boolean;
  esi_percentage: number;
  professional_tax: number;
  tds_monthly: number;
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  created_at: string;
  updated_at?: string;
}

export interface SalaryStructureInput {
  employee_id: string;
  unit_id: string;
  base_monthly_salary: number;
  basic_salary: number;
  hra: number;
  conveyance_allowance: number;
  special_allowance: number;
  overtime_hourly_rate: number;
  pf_applicable: boolean;
  pf_percentage: number;
  esi_applicable: boolean;
  esi_percentage: number;
  professional_tax: number;
  tds_monthly: number;
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
}

// Payroll Run
export interface PayrollRun {
  id: string;
  run_number: string;
  period: string;
  unit_id: string;
  working_days_in_month: number;
  total_employees: number;
  total_gross_payout: number;
  total_deductions: number;
  total_net_payout: number;
  status: PayrollRunStatus;
  notes?: string;
  created_at: string;
  created_by: string;
  reviewed_at?: string;
  reviewed_by?: string;
  approved_at?: string;
  approved_by?: string;
  posted_at?: string;
  posted_by?: string;
}

export interface PayrollRunCreate {
  period: string;
  unit_id: string;
  working_days_in_month: number;
  notes?: string;
}

export interface PayrollItem {
  id: string;
  payroll_run_id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  period: string;
  unit_id: string;
  standard_working_days: number;
  present_days: number;
  paid_leave_days: number;
  unpaid_leave_days: number;
  overtime_hours: number;
  basic: number;
  hra: number;
  conveyance: number;
  special_allowance: number;
  overtime_pay: number;
  gross_earnings: number;
  lop_deduction: number;
  pf_deduction: number;
  esi_deduction: number;
  professional_tax: number;
  tds_deduction: number;
  total_deductions: number;
  net_pay: number;
  bank_account_number?: string;
  bank_ifsc?: string;
}

export interface Payslip {
  payslip_number: string;
  period: string;
  unit_id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  bank_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  standard_working_days: number;
  present_days: number;
  paid_leave_days: number;
  lop_days: number;
  overtime_hours: number;
  basic: number;
  hra: number;
  conveyance: number;
  special_allowance: number;
  overtime_pay: number;
  total_earnings: number;
  lop_deduction: number;
  pf_deduction: number;
  esi_deduction: number;
  professional_tax: number;
  tds_deduction: number;
  total_deductions: number;
  net_salary_payable: number;
  generated_at: string;
}

export interface JournalEntryLine {
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  description: string;
}

export interface PayrollJournalEntry {
  voucher_number: string;
  payroll_run_id: string;
  period: string;
  unit_id: string;
  posting_date: string;
  lines: JournalEntryLine[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

export interface PayrollSummary {
  unit_id?: string;
  active_payroll_runs: number;
  latest_period?: string;
  total_gross_payout: number;
  total_net_payout: number;
  total_statutory_deductions: number;
  configured_salary_structures_count: number;
}
