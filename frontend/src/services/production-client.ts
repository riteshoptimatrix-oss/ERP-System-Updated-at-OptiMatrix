import { apiClient } from './api-client';
import {
  ProductionOrder,
  ProductionOrderCreateInput,
  MaterialIssueItemInput,
  ProductionOutputInput,
  ProductionVarianceReport,
  ProductionDashboardSummary,
  DailyProductionEntry,
  DailyProductionCreate,
  DailyProductionUpdate,
  DailyProductionSummary,
} from '@/types/production';
import { PaginatedResponse } from '@/types/master';

export interface ListProductionOrdersParams {
  product_id?: string;
  unit_id?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const productionClient = {
  /**
   * Fetch shop floor WIP & production KPIs
   */
  async getDashboard(unit_id?: string): Promise<ProductionDashboardSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<ProductionDashboardSummary>(`/production/dashboard${query}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch production dashboard metrics');
    return res.data;
  },

  /**
   * List paginated production orders
   */
  async listOrders(params: ListProductionOrdersParams = {}): Promise<PaginatedResponse<ProductionOrder>> {
    const query = new URLSearchParams();
    if (params.product_id) query.append('product_id', params.product_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.status) query.append('status', params.status);
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<ProductionOrder>>(`/production/orders${qs}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to retrieve production orders');
    return res.data;
  },

  /**
   * Get single production order details
   */
  async getOrder(id: string): Promise<ProductionOrder> {
    const res = await apiClient.get<ProductionOrder>(`/production/orders/${id}`);
    if (!res.data) throw new Error('Production order not found');
    return res.data;
  },

  /**
   * Create new draft production order
   */
  async createOrder(data: ProductionOrderCreateInput): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>('/production/orders', data);
    if (!res.data) throw new Error('Failed to create production order');
    return res.data;
  },

  /**
   * Release production order & reserve raw materials
   */
  async releaseOrder(id: string): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/production/orders/${id}/release`, {});
    if (!res.data) throw new Error('Failed to release production order');
    return res.data;
  },

  /**
   * Issue materials to shop-floor (consumption)
   */
  async issueMaterials(id: string, items: MaterialIssueItemInput[]): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/production/orders/${id}/issue-materials`, { items });
    if (!res.data) throw new Error('Failed to issue materials');
    return res.data;
  },

  /**
   * Record production output and receipt good finished goods into stock
   */
  async recordOutput(id: string, output: ProductionOutputInput): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(`/production/orders/${id}/record-output`, output);
    if (!res.data) throw new Error('Failed to record production output');
    return res.data;
  },

  /**
   * Cancel production order and release reservations
   */
  async cancelOrder(id: string, reason: string): Promise<ProductionOrder> {
    const res = await apiClient.post<ProductionOrder>(
      `/production/orders/${id}/cancel?reason=${encodeURIComponent(reason)}`,
      {}
    );
    if (!res.data) throw new Error('Failed to cancel production order');
    return res.data;
  },

  /**
   * Fetch production variance report
   */
  async getVarianceReport(id: string): Promise<ProductionVarianceReport> {
    const res = await apiClient.get<ProductionVarianceReport>(`/production/orders/${id}/variance`);
    if (!res.data) throw new Error('Failed to fetch variance report');
    return res.data;
  },

  /**
   * Daily Production Planning & Actual
   * Main daily entry screen for Shivakumar
   */
  async listDaily(params?: {
    date?: string;
    department?: string;
    unit_id?: string;
    labour?: string;
    machine?: string;
    search?: string;
  }): Promise<DailyProductionEntry[]> {
    const query = new URLSearchParams();
    if (params?.date) query.set('date', params.date);
    if (params?.department && params.department !== 'ALL') query.set('department', params.department);
    if (params?.unit_id) query.set('unit_id', params.unit_id);
    if (params?.labour) query.set('labour', params.labour);
    if (params?.machine) query.set('machine', params.machine);
    if (params?.search) query.set('search', params.search);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<DailyProductionEntry[]>(`/production/daily${qs}`);
    return res.data || [];
  },

  async getDailySummary(params?: {
    date?: string;
    department?: string;
    unit_id?: string;
  }): Promise<DailyProductionSummary> {
    const query = new URLSearchParams();
    if (params?.date) query.set('date', params.date);
    if (params?.department && params.department !== 'ALL') query.set('department', params.department);
    if (params?.unit_id) query.set('unit_id', params.unit_id);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<DailyProductionSummary>(`/production/daily/summary${qs}`);
    if (!res.data) {
      return {
        total_entries: 0,
        total_planned_qty: 0,
        total_actual_qty: 0,
        total_good_qty: 0,
        total_scrap_qty: 0,
        total_rework_qty: 0,
        overall_completion_pct: 0,
        overall_performance_pct: 0,
        total_daily_earned_inr: 0,
        department_breakdown: [],
      };
    }
    return res.data;
  },

  async createDaily(data: DailyProductionCreate): Promise<DailyProductionEntry> {
    const res = await apiClient.post<DailyProductionEntry>('/production/daily', data);
    if (!res.data) throw new Error('Failed to create daily production record');
    return res.data;
  },

  async updateDaily(id: string, data: DailyProductionUpdate): Promise<DailyProductionEntry> {
    const res = await apiClient.put<DailyProductionEntry>(`/production/daily/${id}`, data);
    if (!res.data) throw new Error('Failed to update daily production record');
    return res.data;
  },

  async deleteDaily(id: string): Promise<void> {
    await apiClient.delete(`/production/daily/${id}`);
  },
};

