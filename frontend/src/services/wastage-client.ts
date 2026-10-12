import { apiClient } from './api-client';
import {
  ScrapEntry,
  ScrapEntryCreateInput,
  PlannedVsActualWastage,
  WastageSummary,
} from '@/types/wastage';
import { PaginatedResponse } from '@/types/master';

export interface ListScrapEntriesParams {
  unit_id?: string;
  production_order_id?: string;
  scrap_category?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const wastageClient = {
  /**
   * Fetch wastage metrics summary
   */
  async getSummary(unit_id?: string): Promise<WastageSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<WastageSummary>(`/wastage/summary${query}`);
    if (!res.data) throw new Error('Failed to retrieve wastage summary');
    return res.data;
  },

  /**
   * List paginated scrap records
   */
  async listEntries(params: ListScrapEntriesParams = {}): Promise<PaginatedResponse<ScrapEntry>> {
    const query = new URLSearchParams();
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.production_order_id) query.append('production_order_id', params.production_order_id);
    if (params.scrap_category) query.append('scrap_category', params.scrap_category);
    if (params.status) query.append('status', params.status);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<ScrapEntry>>(`/wastage/entries${qs}`);
    if (!res.data) throw new Error('Failed to retrieve scrap records');
    return res.data;
  },

  /**
   * Get single scrap entry details
   */
  async getEntry(id: string): Promise<ScrapEntry> {
    const res = await apiClient.get<ScrapEntry>(`/wastage/entries/${id}`);
    if (!res.data) throw new Error('Scrap entry not found');
    return res.data;
  },

  /**
   * Create daily scrap entry
   */
  async createEntry(input: ScrapEntryCreateInput): Promise<ScrapEntry> {
    const res = await apiClient.post<ScrapEntry>('/wastage/entries', input);
    if (!res.data) throw new Error('Failed to record scrap entry');
    return res.data;
  },

  /**
   * Update/correct scrap entry
   */
  async updateEntry(id: string, input: Partial<ScrapEntryCreateInput>): Promise<ScrapEntry> {
    const res = await apiClient.put<ScrapEntry>(`/wastage/entries/${id}`, input);
    if (!res.data) throw new Error('Failed to update scrap entry');
    return res.data;
  },

  /**
   * Approve scrap entry and disposition
   */
  async approveEntry(id: string, notes?: string, disposition?: string): Promise<ScrapEntry> {
    const res = await apiClient.post<ScrapEntry>(`/wastage/entries/${id}/approve`, {
      notes,
      disposition,
    });
    if (!res.data) throw new Error('Failed to approve scrap entry');
    return res.data;
  },

  /**
   * Reject scrap entry
   */
  async rejectEntry(id: string, rejection_reason: string): Promise<ScrapEntry> {
    const res = await apiClient.post<ScrapEntry>(`/wastage/entries/${id}/reject`, {
      rejection_reason,
    });
    if (!res.data) throw new Error('Failed to reject scrap entry');
    return res.data;
  },

  /**
   * Reconcile planned vs actual wastage for a production order
   */
  async getPlannedVsActual(order_id: string): Promise<PlannedVsActualWastage> {
    const res = await apiClient.get<PlannedVsActualWastage>(`/wastage/comparison/${order_id}`);
    if (!res.data) throw new Error('Failed to compute planned vs actual wastage');
    return res.data;
  },
};
