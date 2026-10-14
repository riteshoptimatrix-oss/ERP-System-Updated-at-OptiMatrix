import { apiClient } from './api-client';
import {
  SalesOrder,
  PackingSlip,
  DispatchRecord,
  OrderDashboardSummary,
  StockAvailabilityResult,
} from '@/types/orders';
import { PaginatedResponse } from '@/types/master';

export interface ListOrdersParams {
  search?: string;
  status?: string;
  customer_id?: string;
  unit_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const ordersClient = {
  /**
   * Fetch Sales Order & Dispatch KPI metrics
   */
  async getDashboard(unit_id?: string): Promise<OrderDashboardSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<OrderDashboardSummary>(`/orders/dashboard${query}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch orders dashboard metrics');
    return res.data;
  },

  /**
   * List paginated sales orders
   */
  async listOrders(params: ListOrdersParams = {}): Promise<PaginatedResponse<SalesOrder>> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status) query.append('status', params.status);
    if (params.customer_id) query.append('customer_id', params.customer_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.sort_order) query.append('sort_order', params.sort_order);

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<SalesOrder>>(`/orders${qs}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to retrieve sales orders');
    return res.data;
  },

  /**
   * Get single sales order details with activity timeline
   */
  async getOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.get<SalesOrder>(`/orders/${id}`);
    if (!res.data) throw new Error('Sales order not found');
    return res.data;
  },

  /**
   * Create new sales order
   */
  async createOrder(data: Record<string, unknown>): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>('/orders', data);
    if (!res.data) throw new Error('Failed to create sales order');
    return res.data;
  },

  /**
   * Update sales order (DRAFT / SUBMITTED)
   */
  async updateOrder(id: string, data: Record<string, unknown>): Promise<SalesOrder> {
    const res = await apiClient.put<SalesOrder>(`/orders/${id}`, data);
    if (!res.data) throw new Error('Failed to update sales order');
    return res.data;
  },

  /**
   * Submit sales order for approval
   */
  async submitOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/orders/${id}/submit`, {});
    if (!res.data) throw new Error('Failed to submit sales order');
    return res.data;
  },

  /**
   * Confirm sales order
   */
  async confirmOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/orders/${id}/confirm`, {});
    if (!res.data) throw new Error('Failed to confirm sales order');
    return res.data;
  },

  /**
   * Cancel sales order
   */
  async cancelOrder(id: string, reason: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/orders/${id}/cancel`, { reason });
    if (!res.data) throw new Error('Failed to cancel sales order');
    return res.data;
  },

  /**
   * Generate packing slip
   */
  async createPackingSlip(orderId: string, data: Record<string, unknown>): Promise<PackingSlip> {
    const res = await apiClient.post<PackingSlip>(`/orders/${orderId}/packing-slips`, data);
    if (!res.data) throw new Error('Failed to generate packing slip');
    return res.data;
  },

  /**
   * List packing slips for order
   */
  async listPackingSlips(orderId: string): Promise<PackingSlip[]> {
    const res = await apiClient.get<PackingSlip[]>(`/orders/${orderId}/packing-slips`);
    return res.data || [];
  },

  /**
   * Post dispatch record
   */
  async postDispatch(orderId: string, data: Record<string, unknown>): Promise<DispatchRecord> {
    const res = await apiClient.post<DispatchRecord>(`/orders/${orderId}/dispatch`, data);
    if (!res.data) throw new Error('Failed to post dispatch record');
    return res.data;
  },

  /**
   * List dispatch records for order
   */
  async listDispatches(orderId: string): Promise<DispatchRecord[]> {
    const res = await apiClient.get<DispatchRecord[]>(`/orders/${orderId}/dispatches`);
    return res.data || [];
  },

  /**
   * Check stock availability contract
   */
  async checkStock(productId: string, unitId: string, requiredQty: number): Promise<StockAvailabilityResult> {
    const res = await apiClient.get<StockAvailabilityResult>(
      `/orders/check-stock/${productId}?unit_id=${unitId}&required_qty=${requiredQty}`
    );
    if (!res.data) throw new Error('Failed to check stock availability');
    return res.data;
  },
};
