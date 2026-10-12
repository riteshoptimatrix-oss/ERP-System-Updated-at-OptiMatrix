export type ScrapCategory =
  | 'CUTTING_OFFCUT'
  | 'MACHINING_SWARF'
  | 'REJECTED_DEFECTIVE'
  | 'TOOLING_SETUP'
  | 'DAMAGE_IN_HANDLING'
  | 'CONTAMINATION'
  | 'OBSOLETE_MATERIAL'
  | 'OTHER';

export type ScrapDisposition =
  | 'DISPOSAL'
  | 'RECYCLE_INTERNAL'
  | 'SCRAP_YARD_SALE'
  | 'HOLD_REVIEW';

export type ScrapEntryStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'APPROVED'
  | 'REJECTED';

export interface ScrapEntry {
  id: string;
  entry_number: string;
  entry_date: string;
  unit_id: string;
  production_order_id?: string | null;
  production_order_number?: string | null;
  item_id: string;
  item_code: string;
  item_name: string;
  item_type: string;
  scrap_category: ScrapCategory;
  quantity: number;
  uom: string;
  unit_cost: number;
  total_cost: number;
  reason: string;
  disposition: ScrapDisposition;
  status: ScrapEntryStatus;
  operator_name?: string | null;
  machine_id?: string | null;
  notes?: string | null;
  created_at: string;
  created_by: string;
  approved_at?: string | null;
  approved_by?: string | null;
  rejection_reason?: string | null;
}

export interface ScrapEntryCreateInput {
  entry_date?: string;
  unit_id: 'Unit_1' | 'Unit_2';
  production_order_id?: string | null;
  production_order_number?: string | null;
  item_id: string;
  item_code: string;
  item_name: string;
  item_type?: string;
  scrap_category: ScrapCategory;
  quantity: number;
  uom: string;
  reason: string;
  disposition?: ScrapDisposition;
  operator_name?: string;
  machine_id?: string;
  notes?: string;
}

export interface ComponentWastageComparison {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string;
  planned_quantity: number;
  planned_scrap_percentage: number;
  planned_scrap_quantity: number;
  actual_scrap_quantity: number;
  scrap_variance: number;
  unit_cost: number;
  planned_scrap_cost: number;
  actual_scrap_cost: number;
  cost_variance: number;
}

export interface PlannedVsActualWastage {
  production_order_id: string;
  order_number: string;
  product_code: string;
  product_name: string;
  unit_id: string;
  planned_production_qty: number;
  actual_produced_qty: number;
  components: ComponentWastageComparison[];
  total_planned_scrap_cost: number;
  total_actual_scrap_cost: number;
  total_cost_variance: number;
}

export interface CategoryScrapMetric {
  category: string;
  total_quantity: number;
  total_cost: number;
  entry_count: number;
}

export interface WastageSummary {
  total_scrap_entries: number;
  pending_approvals: number;
  approved_entries: number;
  total_scrap_cost: number;
  category_breakdown: CategoryScrapMetric[];
  unit_id?: string | null;
}
