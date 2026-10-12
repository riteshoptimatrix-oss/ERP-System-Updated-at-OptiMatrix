import { apiClient } from './api-client';
import {
  ProductionOrder,
  ProductionOrderCreateInput,
  MaterialIssueItemInput,
  ProductionOutputInput,
  ProductionVarianceReport,
  ProductionDashboardSummary,
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
    if (!res.data) throw new Error('Failed to fetch production dashboard metrics');
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
    if (!res.data) throw new Error('Failed to retrieve production orders');
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
};
