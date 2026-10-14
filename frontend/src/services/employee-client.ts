import { apiClient } from './api-client';
import {
  EmployeeDashboardResponse,
  EmployeeProfileResponse,
  ProfileCorrectionRequest,
  AttendanceCorrectionResponseItem,
  EmployeeTask,
  NotificationItem,
  AnnouncementItem,
  AnnouncementRecipientOption,
} from '@/types/employee';
import { AttendanceEntry, LeaveApplication, Payslip, SalaryStructure } from '@/types/hr';
import { PaginatedResponse } from '@/types/master';

class EmployeeClient {
  /**
   * Fetch aggregated personalized employee dashboard data
   */
  async getDashboard(unitId?: string): Promise<EmployeeDashboardResponse> {
    const url = unitId ? `/api/v1/employee/dashboard?unit_id=${encodeURIComponent(unitId)}` : '/api/v1/employee/dashboard';
    const res = await apiClient.get<EmployeeDashboardResponse>(url);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch dashboard data');
    return res.data;
  }

  /**
   * Fetch full employee profile
   */
  async getProfile(): Promise<EmployeeProfileResponse> {
    const res = await apiClient.get<EmployeeProfileResponse>('/api/v1/employee/profile');
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch employee profile');
    return res.data;
  }

  /**
   * Submit formal profile correction request for HR review
   */
  async submitProfileCorrection(data: { field_name: string; requested_value: string; reason: string }): Promise<ProfileCorrectionRequest> {
    const res = await apiClient.post<ProfileCorrectionRequest>('/api/v1/employee/profile/correction-request', data);
    if (!res.data) throw new Error(res.error?.message || 'Failed to submit profile correction request');
    return res.data;
  }

  /**
   * Self-service check-in timestamp logging
   */
  async checkIn(data?: { unit_id?: string; remarks?: string }): Promise<AttendanceEntry> {
    const res = await apiClient.post<AttendanceEntry>('/api/v1/employee/attendance/check-in', data || {});
    if (!res.data) throw new Error(res.error?.message || 'Check-in failed');
    return res.data;
  }

  /**
   * Self-service check-out timestamp logging
   */
  async checkOut(data?: { remarks?: string }): Promise<AttendanceEntry> {
    const res = await apiClient.post<AttendanceEntry>('/api/v1/employee/attendance/check-out', data || {});
    if (!res.data) throw new Error(res.error?.message || 'Check-out failed');
    return res.data;
  }

  /**
   * Retrieve personal attendance history
   */
  async getAttendanceHistory(params?: {
    month?: string;
    date?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<AttendanceEntry>> {
    const query = new URLSearchParams();
    if (params?.month) query.append('month', params.month);
    if (params?.date) query.append('date', params.date);
    if (params?.start_date) query.append('start_date', params.start_date);
    if (params?.end_date) query.append('end_date', params.end_date);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());

    const res = await apiClient.get<PaginatedResponse<AttendanceEntry>>(`/api/v1/employee/attendance?${query.toString()}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch attendance history');
    return res.data;
  }

  /**
   * Submit attendance correction request for supervisor review
   */
  async submitAttendanceCorrection(data: {
    date: string;
    requested_check_in?: string;
    requested_check_out?: string;
    requested_status?: string;
    reason: string;
  }): Promise<AttendanceCorrectionResponseItem> {
    const res = await apiClient.post<AttendanceCorrectionResponseItem>('/api/v1/employee/attendance/correction-request', data);
    if (!res.data) throw new Error(res.error?.message || 'Failed to submit attendance correction');
    return res.data;
  }

  /**
   * List submitted attendance correction requests
   */
  async listAttendanceCorrections(): Promise<AttendanceCorrectionResponseItem[]> {
    const res = await apiClient.get<AttendanceCorrectionResponseItem[]>('/api/v1/employee/attendance/correction-requests');
    if (!res.data) throw new Error(res.error?.message || 'Failed to list attendance corrections');
    return res.data;
  }

  /**
   * List personal leave requests
   */
  async listLeaves(status?: string, page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<LeaveApplication>> {
    const query = new URLSearchParams();
    if (status) query.append('status', status);
    query.append('page', page.toString());
    query.append('page_size', pageSize.toString());

    const res = await apiClient.get<PaginatedResponse<LeaveApplication>>(`/api/v1/employee/leaves?${query.toString()}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to list leaves');
    return res.data;
  }

  /**
   * Apply for leave with overlap protection and balance deduction
   */
  async applyLeave(data: {
    leave_type: string;
    start_date: string;
    end_date: string;
    days_count: number;
    reason: string;
  }): Promise<LeaveApplication> {
    const res = await apiClient.post<LeaveApplication>('/api/v1/employee/leaves', data);
    if (!res.data) throw new Error(res.error?.message || 'Failed to submit leave application');
    return res.data;
  }

  /**
   * Cancel an eligible pending leave application
   */
  async cancelLeave(leaveId: string): Promise<LeaveApplication> {
    const res = await apiClient.post<LeaveApplication>(`/api/v1/employee/leaves/${encodeURIComponent(leaveId)}/cancel`, {});
    if (!res.data) throw new Error(res.error?.message || 'Failed to cancel leave application');
    return res.data;
  }

  /**
   * List operational tasks assigned to the employee
   */
  async listTasks(status?: string): Promise<EmployeeTask[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const res = await apiClient.get<EmployeeTask[]>(`/api/v1/employee/tasks${query}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch tasks');
    return res.data;
  }

  /**
   * Update task progress or submit completion notes
   */
  async updateTask(taskId: string, data: { status?: string; notes?: string; completion_evidence?: string }): Promise<{ status: string; message: string }> {
    const res = await apiClient.patch<{ status: string; message: string }>(`/api/v1/employee/tasks/${encodeURIComponent(taskId)}`, data);
    if (!res.data) throw new Error(res.error?.message || 'Failed to update task');
    return res.data;
  }

  /**
   * Fetch personal salary structure
   */
  async getSalaryStructure(): Promise<SalaryStructure> {
    const res = await apiClient.get<SalaryStructure>('/api/v1/employee/salary');
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch salary structure');
    return res.data;
  }

  /**
   * List personal finalized payslips
   */
  async listPayslips(): Promise<Payslip[]> {
    const res = await apiClient.get<Payslip[]>('/api/v1/employee/payslips');
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch payslips');
    return res.data;
  }

  /**
   * Fetch specific itemized payslip by period
   */
  async getPayslip(period: string): Promise<Payslip> {
    const res = await apiClient.get<Payslip>(`/api/v1/employee/payslips/${encodeURIComponent(period)}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch payslip');
    return res.data;
  }

  /**
   * List notifications
   */
  async listNotifications(isRead?: boolean): Promise<NotificationItem[]> {
    const query = isRead !== undefined ? `?is_read=${isRead}` : '';
    const res = await apiClient.get<NotificationItem[]>(`/api/v1/notifications${query}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch notifications');
    return res.data;
  }

  /**
   * Mark a notification as read
   */
  async markNotificationRead(id: string): Promise<NotificationItem> {
    const res = await apiClient.patch<NotificationItem>(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {});
    if (!res.data) throw new Error(res.error?.message || 'Failed to mark notification as read');
    return res.data;
  }

  /**
   * Mark all notifications as read
   */
  async markAllNotificationsRead(): Promise<void> {
    await apiClient.post('/api/v1/notifications/mark-all-read', {});
  }

  /**
   * List announcements (scoped to audience and permissions)
   */
  async listAnnouncements(params?: {
    unitId?: string;
    audienceType?: string;
    priority?: string;
    search?: string;
  }): Promise<AnnouncementItem[]> {
    const q = new URLSearchParams();
    if (params?.unitId) q.append('unit_id', params.unitId);
    if (params?.audienceType) q.append('audience_type', params.audienceType);
    if (params?.priority) q.append('priority', params.priority);
    if (params?.search) q.append('search', params.search);
    const qs = q.toString() ? `?${q.toString()}` : '';
    const res = await apiClient.get<AnnouncementItem[]>(`/api/v1/announcements${qs}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch announcements');
    return res.data;
  }

  /**
   * Fetch targetable recipients (Super Admin only)
   */
  async listAnnouncementRecipients(): Promise<AnnouncementRecipientOption[]> {
    const res = await apiClient.get<AnnouncementRecipientOption[]>('/api/v1/announcements/recipients');
    if (!res.data) throw new Error(res.error?.message || 'Failed to load recipients');
    return res.data;
  }

  /**
   * Create announcement (Super Admin only)
   */
  async createAnnouncement(payload: {
    title: string;
    message: string;
    priority?: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
    unit_id?: string;
    audience_type: 'all' | 'specific' | 'department' | 'role';
    recipients?: string[];
    recipient_names?: string[];
    expires_at?: string | null;
  }): Promise<AnnouncementItem> {
    const res = await apiClient.post<AnnouncementItem>('/api/v1/announcements', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to create announcement');
    return res.data;
  }

  /**
   * Update announcement (Super Admin only)
   */
  async updateAnnouncement(
    id: string,
    payload: {
      title?: string;
      message?: string;
      priority?: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
      unit_id?: string;
      audience_type?: 'all' | 'specific' | 'department' | 'role';
      recipients?: string[];
      recipient_names?: string[];
      expires_at?: string | null;
    }
  ): Promise<AnnouncementItem> {
    const res = await apiClient.put<AnnouncementItem>(`/api/v1/announcements/${encodeURIComponent(id)}`, payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to update announcement');
    return res.data;
  }

  /**
   * Delete announcement (Super Admin only)
   */
  async deleteAnnouncement(id: string): Promise<void> {
    const res = await apiClient.delete(`/api/v1/announcements/${encodeURIComponent(id)}`);
    if (res.error) throw new Error(res.error.message || 'Failed to delete announcement');
  }

  /**
   * Mark announcement as read
   */
  async markAnnouncementRead(id: string): Promise<void> {
    await apiClient.patch(`/api/v1/announcements/${encodeURIComponent(id)}/read`, {});
  }
}

export const employeeClient = new EmployeeClient();
