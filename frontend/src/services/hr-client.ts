import { apiClient } from './api-client';
import {
  ShiftConfig,
  ShiftConfigCreate,
  AttendanceEntry,
  AttendanceEntryCreate,
  AttendanceCorrectionRequest,
  LeaveApplication,
  LeaveApplicationCreate,
  LeaveApprovalRequest,
  HRAttendanceSummary,
} from '@/types/hr';
import { PaginatedResponse } from '@/types/master';

export interface ListAttendanceParams {
  date?: string;
  employee_id?: string;
  unit_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface ListLeavesParams {
  employee_id?: string;
  unit_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const hrClient = {
  /**
   * Get HR & Attendance KPI metrics summary
   */
  async getSummary(unit_id?: string): Promise<HRAttendanceSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<HRAttendanceSummary>(`/hr/summary${query}`);
    if (!res.data) throw new Error('Failed to retrieve HR summary');
    return res.data;
  },

  /**
   * List configured facility shifts
   */
  async listShifts(unit_id?: string): Promise<ShiftConfig[]> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<ShiftConfig[]>(`/hr/shifts${query}`);
    return res.data || [];
  },

  /**
   * Create a new facility shift
   */
  async createShift(data: ShiftConfigCreate): Promise<ShiftConfig> {
    const res = await apiClient.post<ShiftConfig>('/hr/shifts', data);
    if (!res.data) throw new Error('Failed to create shift');
    return res.data;
  },

  /**
   * List paginated attendance entries
   */
  async listAttendance(params: ListAttendanceParams = {}): Promise<PaginatedResponse<AttendanceEntry>> {
    const query = new URLSearchParams();
    if (params.date) query.append('date', params.date);
    if (params.employee_id) query.append('employee_id', params.employee_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.status) query.append('status', params.status);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<AttendanceEntry>>(`/hr/attendance${qs}`);
    if (!res.data) throw new Error('Failed to retrieve attendance entries');
    return res.data;
  },

  /**
   * Record daily employee attendance
   */
  async recordAttendance(data: AttendanceEntryCreate): Promise<AttendanceEntry> {
    const res = await apiClient.post<AttendanceEntry>('/hr/attendance', data);
    if (!res.data) throw new Error('Failed to record attendance');
    return res.data;
  },

  /**
   * Supervisor correction of attendance entry
   */
  async correctAttendance(recordId: string, data: AttendanceCorrectionRequest): Promise<AttendanceEntry> {
    const res = await apiClient.put<AttendanceEntry>(`/hr/attendance/${recordId}/correct`, data);
    if (!res.data) throw new Error('Failed to correct attendance');
    return res.data;
  },

  /**
   * List employee leave applications
   */
  async listLeaves(params: ListLeavesParams = {}): Promise<PaginatedResponse<LeaveApplication>> {
    const query = new URLSearchParams();
    if (params.employee_id) query.append('employee_id', params.employee_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.status) query.append('status', params.status);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<LeaveApplication>>(`/hr/leaves${qs}`);
    if (!res.data) throw new Error('Failed to retrieve leave applications');
    return res.data;
  },

  /**
   * Submit an employee leave application
   */
  async applyLeave(data: LeaveApplicationCreate): Promise<LeaveApplication> {
    const res = await apiClient.post<LeaveApplication>('/hr/leaves', data);
    if (!res.data) throw new Error('Failed to submit leave application');
    return res.data;
  },

  /**
   * Review or approve/reject leave application
   */
  async reviewLeave(leaveId: string, data: LeaveApprovalRequest): Promise<LeaveApplication> {
    const res = await apiClient.put<LeaveApplication>(`/hr/leaves/${leaveId}/review`, data);
    if (!res.data) throw new Error('Failed to review leave application');
    return res.data;
  },
};
