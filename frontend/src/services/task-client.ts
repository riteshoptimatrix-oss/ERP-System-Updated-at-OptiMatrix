import { apiClient } from './api-client';
import {
  TaskItem,
  TaskCreatePayload,
  TaskUpdatePayload,
  TaskSubmitPayload,
  TaskReviewPayload,
  TaskMessage,
  ReportingOfficerOption,
} from '@/types/tasks';

export class TaskClient {
  /**
   * List authorized reporting officers and department managers
   */
  async listReportingOfficers(): Promise<ReportingOfficerOption[]> {
    const res = await apiClient.get<ReportingOfficerOption[]>('/api/v1/tasks/reporting-officers');
    if (!res.data) {
      if (res.status === 401) return [];
      throw new Error(res.error?.message || 'Failed to fetch reporting officers');
    }
    return res.data;
  }

  /**
   * Create a new employee task
   */
  async createTask(payload: TaskCreatePayload): Promise<TaskItem> {
    const res = await apiClient.post<TaskItem>('/api/v1/tasks', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to create task');
    return res.data;
  }

  /**
   * List tasks created by or assigned to current employee
   */
  async listMyTasks(status?: string): Promise<TaskItem[]> {
    const query = status && status !== 'ALL' ? `?status=${encodeURIComponent(status)}` : '';
    const res = await apiClient.get<TaskItem[]>(`/api/v1/tasks/my${query}`);
    if (!res.data) {
      if (res.status === 401) return [];
      throw new Error(res.error?.message || 'Failed to fetch your tasks');
    }
    return res.data;
  }

  /**
   * List tasks awaiting review where current user is designated Reporting Officer
   */
  async listReviewQueue(status?: string): Promise<TaskItem[]> {
    const query = status && status !== 'ALL' ? `?status=${encodeURIComponent(status)}` : '';
    const res = await apiClient.get<TaskItem[]>(`/api/v1/tasks/review-queue${query}`);
    if (!res.data) {
      if (res.status === 401) return [];
      throw new Error(res.error?.message || 'Failed to fetch tasks for review');
    }
    return res.data;
  }

  /**
   * List all organizational tasks (Super Admin / HR oversight)
   */
  async listAllTasks(status?: string): Promise<TaskItem[]> {
    const query = status && status !== 'ALL' ? `?status=${encodeURIComponent(status)}` : '';
    const res = await apiClient.get<TaskItem[]>(`/api/v1/tasks/all${query}`);
    if (!res.data) {
      if (res.status === 401) return [];
      throw new Error(res.error?.message || 'Failed to fetch all tasks');
    }
    return res.data;
  }

  /**
   * Get single task details
   */
  async getTask(taskId: string): Promise<TaskItem> {
    const res = await apiClient.get<TaskItem>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to get task details');
    return res.data;
  }

  /**
   * Update task details
   */
  async updateTask(taskId: string, payload: TaskUpdatePayload): Promise<TaskItem> {
    const res = await apiClient.patch<TaskItem>(`/api/v1/tasks/${encodeURIComponent(taskId)}`, payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to update task');
    return res.data;
  }

  /**
   * Mark as Done & Submit for Review
   */
  async submitForReview(taskId: string, payload: TaskSubmitPayload): Promise<TaskItem> {
    const res = await apiClient.post<TaskItem>(`/api/v1/tasks/${encodeURIComponent(taskId)}/submit`, payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to submit task for review');
    return res.data;
  }

  /**
   * Reporting Officer Review (Approve or Request Revisions)
   */
  async reviewTask(taskId: string, payload: TaskReviewPayload): Promise<TaskItem> {
    const res = await apiClient.post<TaskItem>(`/api/v1/tasks/${encodeURIComponent(taskId)}/review`, payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to review task submission');
    return res.data;
  }

  /**
   * Get task-specific discussion messages
   */
  async listMessages(taskId: string): Promise<TaskMessage[]> {
    const res = await apiClient.get<TaskMessage[]>(`/api/v1/tasks/${encodeURIComponent(taskId)}/messages`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to load task discussion');
    return res.data;
  }

  /**
   * Post message to task-specific discussion
   */
  async sendMessage(taskId: string, message: string): Promise<TaskMessage> {
    const res = await apiClient.post<TaskMessage>(`/api/v1/tasks/${encodeURIComponent(taskId)}/messages`, {
      message,
    });
    if (!res.data) throw new Error(res.error?.message || 'Failed to send message');
    return res.data;
  }
}

export const taskClient = new TaskClient();
