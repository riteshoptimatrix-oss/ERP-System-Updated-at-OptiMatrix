import { ManufacturingUnit } from './auth';

export type OrderStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'CONFIRMED'
  | 'PARTIALLY_DISPATCHED'
  | 'DISPATCHED'
  | 'CANCELLED';

export type DispatchStatus = 'PREPARED' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';

export interface OrderLineItem {
  product_id: string;
  product_code: string;
  product_name: string;
  uom: string;
  quantity: number;
  unit_price: number;
  discount_percent: number;
  tax_percent: number;
  dispatched_quantity: number;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  notes?: string;
}

export interface OrderActivity {
  id: string;
  order_id: string;
  action: string;
  description: string;
  performed_by: string;
  timestamp: string;
}

export interface SalesOrder {
  id: string;
  order_number: string;
  customer_id: string;
  customer_code: string;
  customer_name: string;
  customer_po_number?: string;
  unit_id: ManufacturingUnit;
  status: OrderStatus;
  order_date: string;
  delivery_due_date?: string;
  billing_address?: string;
  shipping_address?: string;
  items: OrderLineItem[];
  subtotal: number;
  tax_total: number;
  grand_total: number;
  total_ordered_qty: number;
  total_dispatched_qty: number;
  dispatch_percent: number;
  notes?: string;
  cancellation_reason?: string;
  created_at: string;
  created_by: string;
  updated_at?: string;
  updated_by?: string;
  activities?: OrderActivity[];
}

export interface PackingSlipItem {
  product_id: string;
  product_code: string;
  product_name: string;
  ordered_quantity: number;
  pack_quantity: number;
  package_type: string;
  notes?: string;
}

export interface PackingSlip {
  id: string;
  slip_number: string;
  order_id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  unit_id: ManufacturingUnit;
  packages_count: number;
  gross_weight_kg?: number;
  net_weight_kg?: number;
  special_handling_notes?: string;
  items: PackingSlipItem[];
  created_at: string;
  created_by: string;
}

export interface DispatchItem {
  product_id: string;
  product_code: string;
  product_name: string;
  quantity: number;
}

export interface DispatchRecord {
  id: string;
  dispatch_number: string;
  order_id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  packing_slip_id?: string;
  packing_slip_number?: string;
  unit_id: ManufacturingUnit;
  carrier_name: string;
  vehicle_number: string;
  lr_number?: string;
  driver_name?: string;
  driver_phone?: string;
  dispatched_date: string;
  status: DispatchStatus;
  items: DispatchItem[];
  total_quantity: number;
  remarks?: string;
  created_at: string;
  created_by: string;
}

export interface OrderDashboardSummary {
  total_orders: number;
  draft_orders: number;
  confirmed_orders: number;
  partially_dispatched_orders: number;
  fully_dispatched_orders: number;
  cancelled_orders: number;
  total_pipeline_value: number;
  total_dispatched_value: number;
  total_pending_dispatches: number;
}

export interface StockAvailabilityResult {
  product_id: string;
  product_code: string;
  unit_id: string;
  required_quantity: number;
  available_quantity?: number;
  is_sufficient: boolean;
  status: string;
  message: string;
}
