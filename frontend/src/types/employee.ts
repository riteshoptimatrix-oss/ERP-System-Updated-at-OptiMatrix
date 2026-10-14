import { AttendanceEntry, LeaveApplication } from './hr';
import { Payslip, SalaryStructure } from './hr';

export interface EmployeeShiftSummary {
  shift_code: string;
  name: string;
  start_time: string;
  end_time: string;
  grace_period_minutes: number;
  standard_work_hours: number;
  unit_id: string;
}

export interface EmployeeAttendanceToday {
  record_id?: string;
  date: string;
  status: string;
  check_in?: string;
  check_out?: string;
  hours_worked: number;
  overtime_hours: number;
  shift_code?: string;
  is_checked_in: boolean;
  is_checked_out: boolean;
}

export interface LeaveBalanceItem {
  leave_type: string;
  name: string;
  quota_days: number;
  used_days: number;
  pending_days: number;
  remaining_balance: number;
}

export interface NotificationItem {
  id: string;
  user_id?: string;
  employee_code?: string;
  title: string;
  message: string;
  notification_type: 'INFO' | 'SUCCESS' | 'WARNING' | 'ALERT' | 'LEAVE' | 'ATTENDANCE' | 'TASK' | 'PAYROLL' | 'ANNOUNCEMENT';
  is_read: boolean;
  link?: string;
  created_at: string;
  read_at?: string;
  metadata?: Record<string, unknown>;
}

export interface AnnouncementItem {
  id: string;
  title: string;
  content: string;
  message?: string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  unit_id: string;
  audience_type?: 'all' | 'specific' | 'department' | 'role';
  recipients?: string[];
  recipient_names?: string[];
  author_id?: string;
  author_name: string;
  author_role: string;
  is_read?: boolean;
  read_at?: string;
  read_count?: number;
  published_at: string;
  created_at?: string;
  expires_at?: string;
}

export interface AnnouncementRecipientOption {
  id: string;
  code: string;
  name: string;
  email: string;
  department?: string;
  role?: string;
  unit_id?: string;
}

export interface EmployeeDashboardResponse {
  employee_code: string;
  full_name: string;
  email: string;
  department: string;
  designation: string;
  job_roles: string[];
  unit_id: string;
  allowed_units: string[];
  today_attendance?: EmployeeAttendanceToday;
  current_shift?: EmployeeShiftSummary;
  leave_balances: LeaveBalanceItem[];
  pending_tasks_count: number;
  upcoming_deadlines_count: number;
  pending_leaves_count: number;
  unread_notifications_count: number;
  recent_notifications: NotificationItem[];
  announcements: AnnouncementItem[];
  authorized_modules: string[];
}

export interface EmployeeProfileResponse {
  user_id: string;
  employee_id?: string;
  employee_code: string;
  full_name: string;
  email: string;
  phone?: string;
  department: string;
  designation: string;
  job_role?: string;
  job_roles: string[];
  unit_id: string;
  allowed_units: string[];
  account_type: string;
  role: string;
  status: string;
  joining_date?: string;
  emergency_contact?: string;
  is_active: boolean;
  must_change_password: boolean;
  created_at?: string;
  permissions: string[];
}

export interface ProfileCorrectionRequest {
  id: string;
  request_number: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  field_name: string;
  requested_value: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface AttendanceCorrectionResponseItem {
  id: string;
  request_number: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  date: string;
  requested_check_in?: string;
  requested_check_out?: string;
  requested_status?: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewed_by?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface EmployeeTask {
  id: string;
  task_number: string;
  title: string;
  description: string;
  source_module: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  due_date?: string;
  related_record?: string;
  related_link?: string;
  unit_id: string;
  notes?: string;
  completion_evidence?: string;
  supervisor_feedback?: string;
  created_at: string;
  updated_at?: string;
}
