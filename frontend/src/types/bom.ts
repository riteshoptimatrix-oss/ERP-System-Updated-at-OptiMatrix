import { ManufacturingUnit } from './auth';

export type BOMStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'OBSOLETE';

export interface BOMComponent {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string;
  net_quantity: number;
  scrap_percentage: number;
  gross_quantity: number;
  unit_cost: number;
  estimated_cost: number;
  notes?: string;
}

export interface BOM {
  id: string;
  bom_number: string;
  product_id: string;
  product_code: string;
  product_name: string;
  product_uom: string;
  unit_id: ManufacturingUnit;
  base_quantity: number;
  revision_no: string;
  status: BOMStatus;
  is_active: boolean;
  effective_from?: string;
  effective_to?: string;
  description?: string;
  total_estimated_cost: number;
  components: BOMComponent[];
  approved_by?: string;
  approved_at?: string;
  created_at: string;
  created_by: string;
  updated_at?: string;
  updated_by?: string;
}

export interface BOMComponentInput {
  material_id: string;
  net_quantity: number;
  uom: string;
  scrap_percentage: number;
  notes?: string;
}

export interface BOMCreateInput {
  product_id: string;
  unit_id: ManufacturingUnit;
  base_quantity: number;
  revision_no: string;
  effective_from?: string;
  effective_to?: string;
  description?: string;
  components: BOMComponentInput[];
}

export interface BOMUpdateInput {
  base_quantity?: number;
  effective_from?: string;
  effective_to?: string;
  description?: string;
  components?: BOMComponentInput[];
}

export interface BOMRevisionInput {
  new_revision_no: string;
  description?: string;
  components?: BOMComponentInput[];
}

export interface BOMApprovalInput {
  approved: boolean;
  remarks?: string;
  set_as_active: boolean;
}

export interface MaterialRequirementItem {
  material_id: string;
  material_code: string;
  material_name: string;
  uom: string;
  net_required_quantity: number;
  scrap_percentage: number;
  gross_required_quantity: number;
  unit_cost: number;
  total_estimated_cost: number;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  shortage_quantity: number;
  is_shortage: boolean;
}

export interface MaterialRequirementCalculation {
  bom_id: string;
  bom_number: string;
  product_code: string;
  product_name: string;
  revision_no: string;
  unit_id: ManufacturingUnit;
  production_quantity: number;
  total_estimated_material_cost: number;
  total_shortages_count: number;
  has_sufficient_stock: boolean;
  requirements: MaterialRequirementItem[];
}

export interface BOMDashboardSummary {
  total_boms: number;
  approved_boms: number;
  pending_approval_boms: number;
  draft_boms: number;
  active_boms: number;
  products_with_bom_count: number;
}
