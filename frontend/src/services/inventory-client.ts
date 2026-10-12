import { apiClient } from './api-client';
import {
  StockBalance,
  StockMovementLedger,
  LowStockAlert,
  InventoryDashboardSummary,
  MaterialInwardInput,
  MaterialOutwardInput,
  StockTransferInput,
  StockAdjustmentInput,
  OpeningStockImportInput,
} from '@/types/inventory';
import { PaginatedResponse } from '@/types/master';

export interface ListBalancesParams {
  item_type?: string;
  warehouse_id?: string;
  unit_id?: string;
  search?: string;
  below_reorder_only?: boolean;
  page?: number;
  page_size?: number;
}

export interface ListLedgerParams {
  item_id?: string;
  warehouse_id?: string;
  unit_id?: string;
  movement_type?: string;
  page?: number;
  page_size?: number;
}

export const inventoryClient = {
  /**
   * Fetch Inventory Dashboard KPI metrics
   */
  async getDashboard(unit_id?: string): Promise<InventoryDashboardSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<InventoryDashboardSummary>(`/inventory/dashboard${query}`);
    if (!res.data) throw new Error('Failed to fetch inventory dashboard metrics');
    return res.data;
  },

  /**
   * List paginated stock balances
   */
  async listBalances(params: ListBalancesParams = {}): Promise<PaginatedResponse<StockBalance>> {
    const query = new URLSearchParams();
    if (params.item_type) query.append('item_type', params.item_type);
    if (params.warehouse_id) query.append('warehouse_id', params.warehouse_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.search) query.append('search', params.search);
    if (params.below_reorder_only) query.append('below_reorder_only', 'true');
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<StockBalance>>(`/inventory/balances${qs}`);
    if (!res.data) throw new Error('Failed to retrieve stock balances');
    return res.data;
  },

  /**
   * List immutable stock movement ledger entries
   */
  async listLedger(params: ListLedgerParams = {}): Promise<PaginatedResponse<StockMovementLedger>> {
    const query = new URLSearchParams();
    if (params.item_id) query.append('item_id', params.item_id);
    if (params.warehouse_id) query.append('warehouse_id', params.warehouse_id);
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.movement_type) query.append('movement_type', params.movement_type);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<StockMovementLedger>>(`/inventory/ledger${qs}`);
    if (!res.data) throw new Error('Failed to retrieve movement ledger');
    return res.data;
  },

  /**
   * Fetch low stock / reorder alerts
   */
  async getLowStockAlerts(unit_id?: string): Promise<LowStockAlert[]> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<LowStockAlert[]>(`/inventory/low-stock-alerts${query}`);
    return res.data || [];
  },

  /**
   * Material Inward (GRN / Production Receipt)
   */
  async materialInward(data: MaterialInwardInput): Promise<StockMovementLedger> {
    const res = await apiClient.post<StockMovementLedger>('/inventory/inward', data);
    if (!res.data) throw new Error('Failed to process material inward');
    return res.data;
  },

  /**
   * Material Outward (Issue to Production Floor)
   */
  async materialOutward(data: MaterialOutwardInput): Promise<StockMovementLedger> {
    const res = await apiClient.post<StockMovementLedger>('/inventory/outward', data);
    if (!res.data) throw new Error('Failed to process material outward');
    return res.data;
  },

  /**
   * Inter-Warehouse / Facility Stock Transfer
   */
  async stockTransfer(data: StockTransferInput): Promise<Record<string, unknown>> {
    const res = await apiClient.post<Record<string, unknown>>('/inventory/transfer', data);
    if (!res.data) throw new Error('Failed to process stock transfer');
    return res.data;
  },

  /**
   * Stock Adjustment with mandatory justification
   */
  async stockAdjustment(data: StockAdjustmentInput): Promise<StockMovementLedger> {
    const res = await apiClient.post<StockMovementLedger>('/inventory/adjust', data);
    if (!res.data) throw new Error('Failed to post stock adjustment');
    return res.data;
  },

  /**
   * Opening Stock Bulk Import
   */
  async importOpeningStock(data: OpeningStockImportInput): Promise<Record<string, unknown>> {
    const res = await apiClient.post<Record<string, unknown>>('/inventory/opening-stock', data);
    if (!res.data) throw new Error('Failed to import opening stock');
    return res.data;
  },
};
