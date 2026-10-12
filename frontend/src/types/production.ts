import { ManufacturingUnit } from './auth';

export type ProductionOrderStatus =
  | 'DRAFT'
  | 'RELEASED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED';

export interface ProductionMaterialRequirement {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string;
  standard_quantity_per_unit: number;
  total_standard_required: number;
  total_issued: number;
  unit_cost: number;
  standard_total_cost: number;
  actual_total_cost: number;
}

export interface ProductionOrder {
  id: string;
  order_number: string;
  product_id: string;
  product_code: string;
  product_name: string;
  product_uom: string;
  bom_id: string;
  bom_number: string;
  bom_revision_no: string;
  unit_id: ManufacturingUnit;
  target_warehouse_id: string;
  target_warehouse_code: string;
  planned_quantity: number;
  produced_quantity: number;
  rejected_quantity: number;
  remaining_quantity: number;
  status: ProductionOrderStatus;
  completion_percentage: number;
  materials: ProductionMaterialRequirement[];
  scheduled_start_date?: string;
  target_completion_date?: string;
  actual_start_date?: string;
  actual_completion_date?: string;
  notes?: string;
  cancellation_reason?: string;
  created_at: string;
  created_by: string;
}

export interface ProductionOrderCreateInput {
  product_id: string;
  bom_id?: string;
  unit_id: ManufacturingUnit;
  target_warehouse_id: string;
  planned_quantity: number;
  scheduled_start_date?: string;
  target_completion_date?: string;
  notes?: string;
}

export interface MaterialIssueItemInput {
  material_id: string;
  warehouse_id: string;
  quantity: number;
  batch_no?: string;
  notes?: string;
}

export interface ProductionOutputInput {
  produced_quantity: number;
  rejected_quantity: number;
  warehouse_id: string;
  batch_no?: string;
  operator_name?: string;
  notes?: string;
}

export interface MaterialVarianceItem {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string;
  standard_required: number;
  actual_issued: number;
  variance_quantity: number;
  is_favorable: boolean;
  standard_cost: number;
  actual_cost: number;
  cost_variance: number;
}

export interface ProductionVarianceReport {
  order_id: string;
  order_number: string;
  product_code: string;
  product_name: string;
  planned_quantity: number;
  produced_quantity: number;
  rejected_quantity: number;
  yield_efficiency_percentage: number;
  total_standard_cost: number;
  total_actual_cost: number;
  net_cost_variance: number;
  material_variances: MaterialVarianceItem[];
}

export interface ProductionDashboardSummary {
  total_orders: number;
  draft_orders: number;
  released_orders: number;
  in_progress_orders: number;
  completed_orders: number;
  total_planned_units: number;
  total_produced_units: number;
  total_rejected_units: number;
  overall_yield_percentage: number;
}
