import { apiClient } from './api-client';
import { env } from '@/lib/env';
import { PaginatedResponse, MasterEntityKey } from '@/types/master';

export interface ListMasterParams {
  search?: string;
  unit_id?: string;
  is_active?: boolean;
  category?: string;
  department?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const masterClient = {
  /**
   * Fetch paginated list of master records
   */
  async list<T>(entity: MasterEntityKey, params: ListMasterParams = {}): Promise<PaginatedResponse<T>> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params.category) query.append('category', params.category);
    if (params.department) query.append('department', params.department);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.sort_order) query.append('sort_order', params.sort_order);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<T>>(`/master/${entity}${queryString}`);
    if (!res.data) {
      if (res.status === 401 || res.status === 403) {
        return {
          items: [],
          total: 0,
          page: params.page || 1,
          page_size: params.page_size || 50,
          total_pages: 0,
        };
      }
      throw new Error(res.error?.message || 'Failed to retrieve master records');
    }
    return res.data;
  },

  /**
   * Get single master record by ID
   */
  async getById<T>(entity: MasterEntityKey, id: string): Promise<T> {
    const res = await apiClient.get<T>(`/master/${entity}/${id}`);
    if (!res.data) throw new Error('Record not found');
    return res.data;
  },

  /**
   * Create new master record
   */
  async create<T>(entity: MasterEntityKey, data: Record<string, unknown>): Promise<T> {
    const res = await apiClient.post<T>(`/master/${entity}`, data);
    if (!res.data) throw new Error('Failed to create master record');
    return res.data;
  },

  /**
   * Update existing master record
   */
  async update<T>(entity: MasterEntityKey, id: string, data: Record<string, unknown>): Promise<T> {
    const res = await apiClient.put<T>(`/master/${entity}/${id}`, data);
    if (!res.data) throw new Error('Failed to update master record');
    return res.data;
  },

  /**
   * Soft delete or deactivate record
   */
  async delete(entity: MasterEntityKey, id: string, permanent: boolean = false): Promise<void> {
    await apiClient.delete(`/master/${entity}/${id}?permanent=${permanent}`);
  },

  /**
   * Trigger download of CSV template
   */
  getTemplateUrl(entity: MasterEntityKey): string {
    const base = env.apiUrl.replace(/\/+$/, '').replace(/\/api\/v1\/?$/, '');
    return `${base}/api/v1/master/${entity}/template`;
  }
};
