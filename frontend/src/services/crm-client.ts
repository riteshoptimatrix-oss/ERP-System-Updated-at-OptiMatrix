import { apiClient } from './api-client';
import { Lead, LeadConvertPayload, CrmDashboardSummary } from '@/types/crm';
import { PaginatedResponse } from '@/types/master';

export interface ListLeadsParams {
  search?: string;
  status?: string;
  priority?: string;
  source?: string;
  assigned_to?: string;
  unit_id?: string;
  follow_up_filter?: 'today' | 'overdue' | 'upcoming';
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const crmClient = {
  /**
   * Fetch CRM KPI dashboard metrics
   */
  async getDashboard(unit_id?: string): Promise<CrmDashboardSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<CrmDashboardSummary>(`/crm/dashboard${query}`);
    if (!res.data) throw new Error('Failed to fetch CRM dashboard');
    return res.data;
  },

  /**
   * List paginated leads
   */
  async listLeads(params: ListLeadsParams = {}): Promise<PaginatedResponse<Lead>> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status) query.append('status', params.status);
    if (params.priority) query.append('priority', params.priority);
    if (params.source) query.append('source', params.source);
    if (params.assigned_to) query.append('assigned_to', params.assigned_to);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.follow_up_filter) query.append('follow_up_filter', params.follow_up_filter);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.sort_order) query.append('sort_order', params.sort_order);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<Lead>>(`/crm/leads${qs}`);
    if (!res.data) throw new Error('Failed to retrieve leads');
    return res.data;
  },

  /**
   * Get single lead with activity timeline
   */
  async getLead(id: string): Promise<Lead> {
    const res = await apiClient.get<Lead>(`/crm/leads/${id}`);
    if (!res.data) throw new Error('Lead not found');
    return res.data;
  },

  /**
   * Create new lead
   */
  async createLead(data: Record<string, unknown>): Promise<Lead> {
    const res = await apiClient.post<Lead>('/crm/leads', data);
    if (!res.data) throw new Error('Failed to create lead');
    return res.data;
  },

  /**
   * Update lead
   */
  async updateLead(id: string, data: Record<string, unknown>): Promise<Lead> {
    const res = await apiClient.put<Lead>(`/crm/leads/${id}`, data);
    if (!res.data) throw new Error('Failed to update lead');
    return res.data;
  },

  /**
   * Log an activity / follow-up
   */
  async addActivity(leadId: string, activity: {
    activity_type: string;
    summary: string;
    details?: string;
    next_follow_up?: string;
  }): Promise<void> {
    await apiClient.post(`/crm/leads/${leadId}/activities`, activity);
  },

  /**
   * Convert lead to Customer Master record
   */
  async convertLead(leadId: string, payload: LeadConvertPayload): Promise<{
    customer_id: string;
    customer_code: string;
  }> {
    const res = await apiClient.post<{
      customer_id: string;
      customer_code: string;
    }>(`/crm/leads/${leadId}/convert`, payload);
    if (!res.data) throw new Error('Conversion failed');
    return res.data;
  },

  /**
   * Get 360-degree Lead/Project financial and lifecycle overview
   */
  async getProjectSummary(leadId: string): Promise<any> {
    const res = await apiClient.get<any>(`/crm/leads/${leadId}/project-summary`);
    if (!res.data) throw new Error('Failed to retrieve project summary');
    return res.data;
  },

  /**
   * Add a Material Requirement / BOM item for this project
   */
  async addMaterialRequirement(leadId: string, payload: Record<string, unknown>): Promise<any> {
    const res = await apiClient.post<any>(`/crm/leads/${leadId}/materials`, payload);
    if (!res.data) throw new Error('Failed to add material requirement');
    return res.data;
  },
};
