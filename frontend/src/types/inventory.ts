import { ManufacturingUnit } from './auth';

export type ItemType = 'RAW_MATERIAL' | 'FINISHED_GOOD';

export type MovementType =
  | 'OPENING_STOCK'
  | 'MATERIAL_INWARD'
  | 'MATERIAL_OUTWARD'
  | 'TRANSFER_OUT'
  | 'TRANSFER_IN'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'
  | 'SALES_DISPATCH'
  | 'PRODUCTION_CONSUMPTION'
  | 'PRODUCTION_RECEIPT';

export type AdjustmentReason =
  | 'PHYSICAL_COUNT_DISCREPANCY'
  | 'DAMAGED_GOODS'
  | 'OBSOLETE_SCRAP'
  | 'QUALITY_REJECT'
  | 'SAMPLE_TESTING'
  | 'CORRECTION';

export interface StockBalance {
  id: string;
  item_id: string;
  item_code: string;
  item_name: string;
  item_type: ItemType;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  unit_id: ManufacturingUnit;
  batch_no: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  uom: string;
  valuation_rate: number;
  total_valuation: number;
  reorder_level: number;
  safety_stock: number;
  is_below_reorder: boolean;
  updated_at: string;
}

export interface StockMovementLedger {
  id: string;
  transaction_number: string;
  movement_type: MovementType;
  item_id: string;
  item_code: string;
  item_name: string;
  item_type: ItemType;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  unit_id: ManufacturingUnit;
  batch_no: string;
  quantity_change: number;
  balance_after: number;
  uom: string;
  reference_id?: string;
  reference_type?: string;
  reason?: string;
  notes?: string;
  created_at: string;
  created_by: string;
}

export interface LowStockAlert {
  item_id: string;
  item_code: string;
  item_name: string;
  item_type: ItemType;
  unit_id: ManufacturingUnit;
  total_on_hand: number;
  total_reserved: number;
  total_available: number;
  uom: string;
  reorder_level: number;
  safety_stock: number;
  shortage_quantity: number;
}

export interface InventoryDashboardSummary {
  total_items_tracked: number;
  raw_material_items: number;
  finished_goods_items: number;
  total_valuation_inr: number;
  low_stock_alerts_count: number;
  warehouses_count: number;
  movements_today_count: number;
}

export interface MaterialInwardInput {
  item_id: string;
  item_type: ItemType;
  warehouse_id: string;
  unit_id?: ManufacturingUnit;
  quantity: number;
  unit_cost?: number;
  batch_no?: string;
  supplier_id?: string;
  invoice_no?: string;
  po_number?: string;
  notes?: string;
}

export interface MaterialOutwardInput {
  item_id: string;
  warehouse_id: string;
  unit_id?: ManufacturingUnit;
  quantity: number;
  destination?: string;
  department?: string;
  batch_no?: string;
  notes?: string;
}

export interface StockTransferInput {
  source_warehouse_id: string;
  target_warehouse_id: string;
  item_id: string;
  quantity: number;
  batch_no?: string;
  transfer_reason?: string;
  vehicle_number?: string;
  notes?: string;
}

export interface StockAdjustmentInput {
  item_id: string;
  warehouse_id: string;
  unit_id?: ManufacturingUnit;
  quantity_delta: number;
  reason: AdjustmentReason;
  batch_no?: string;
  notes: string;
}

export interface OpeningStockImportItem {
  item_code: string;
  item_type: ItemType;
  warehouse_code: string;
  unit_id?: ManufacturingUnit;
  quantity: number;
  unit_cost?: number;
  batch_no?: string;
}

export interface OpeningStockImportInput {
  items: OpeningStockImportItem[];
  notes?: string;
}
