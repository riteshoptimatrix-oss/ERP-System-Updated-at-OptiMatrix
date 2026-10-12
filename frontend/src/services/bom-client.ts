import { apiClient } from './api-client';
import {
  BOM,
  BOMCreateInput,
  BOMUpdateInput,
  BOMRevisionInput,
  BOMApprovalInput,
  BOMDashboardSummary,
  MaterialRequirementCalculation,
} from '@/types/bom';
import { PaginatedResponse } from '@/types/master';

export interface ListBOMParams {
  product_id?: string;
  unit_id?: string;
  status?: string;
  is_active?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}

export const bomClient = {
  /**
   * Fetch high-level BOM dashboard KPIs
   */
  async getDashboard(unit_id?: string): Promise<BOMDashboardSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<BOMDashboardSummary>(`/bom/dashboard${query}`);
    if (!res.data) {
      if (res.status === 401 || res.status === 403) {
        return {
          total_boms: 0,
          approved_boms: 0,
          pending_approval_boms: 0,
          draft_boms: 0,
          active_boms: 0,
          products_with_bom_count: 0,
        };
      }
      throw new Error(res.error?.message || 'Failed to fetch BOM metrics');
    }
    return res.data;
  },

  /**
   * List paginated BOMs
   */
  async listBOMs(params: ListBOMParams = {}): Promise<PaginatedResponse<BOM>> {
    const query = new URLSearchParams();
    if (params.product_id) query.append('product_id', params.product_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.status) query.append('status', params.status);
    if (params.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<BOM>>(`/bom${qs}`);
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
      throw new Error(res.error?.message || 'Failed to retrieve Bill of Materials');
    }
    return res.data;
  },

  /**
   * Get single BOM by ID or BOM number
   */
  async getBOM(id: string): Promise<BOM> {
    const res = await apiClient.get<BOM>(`/bom/${id}`);
    if (!res.data) throw new Error('BOM not found');
    return res.data;
  },

  /**
   * Create new draft BOM
   */
  async createBOM(data: BOMCreateInput): Promise<BOM> {
    const res = await apiClient.post<BOM>('/bom', data);
    if (!res.data) throw new Error('Failed to create BOM');
    return res.data;
  },

  /**
   * Update draft BOM
   */
  async updateBOM(id: string, data: BOMUpdateInput): Promise<BOM> {
    const res = await apiClient.put<BOM>(`/bom/${id}`, data);
    if (!res.data) throw new Error('Failed to update BOM');
    return res.data;
  },

  /**
   * Clone new engineering revision
   */
  async createRevision(id: string, data: BOMRevisionInput): Promise<BOM> {
    const res = await apiClient.post<BOM>(`/bom/${id}/revisions`, data);
    if (!res.data) throw new Error('Failed to generate new revision');
    return res.data;
  },

  /**
   * Submit draft BOM for approval
   */
  async submitForApproval(id: string): Promise<BOM> {
    const res = await apiClient.post<BOM>(`/bom/${id}/submit`, {});
    if (!res.data) throw new Error('Failed to submit BOM for approval');
    return res.data;
  },

  /**
   * Approve or reject BOM revision
   */
  async approveBOM(id: string, action: BOMApprovalInput): Promise<BOM> {
    const res = await apiClient.post<BOM>(`/bom/${id}/approve`, action);
    if (!res.data) throw new Error('Failed to approve BOM');
    return res.data;
  },

  /**
   * Calculate material explosion and check shortages against live inventory
   */
  async calculateRequirements(
    id: string,
    production_quantity: number,
    warehouse_id?: string
  ): Promise<MaterialRequirementCalculation> {
    const res = await apiClient.post<MaterialRequirementCalculation>(
      `/bom/${id}/calculate-requirements`,
      { production_quantity, warehouse_id }
    );
    if (!res.data) throw new Error('Failed to compute material requirements');
    return res.data;
  },

  /**
   * Bulk import BOMs
   */
  async importBOMs(items: Record<string, unknown>[], auto_approve = false): Promise<Record<string, unknown>> {
    const res = await apiClient.post<Record<string, unknown>>('/bom/import', { items, auto_approve });
    if (!res.data) throw new Error('Failed to import BOMs');
    return res.data;
  },
};
