export type ManufacturingUnit = 'Unit_1' | 'Unit_2' | 'BOTH';

export interface AuditBase {
  created_at: string;
  created_by: string;
  updated_at?: string;
  updated_by?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 1. Customer
export interface Customer extends AuditBase {
  id: string;
  code: string;
  name: string;
  gstin?: string;
  pan?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  billing_address?: string;
  shipping_address?: string;
  credit_limit: number;
  payment_terms_days: number;
  unit_id: ManufacturingUnit;
  is_active: boolean;
}

// 2. Vendor
export interface Vendor extends AuditBase {
  id: string;
  code: string;
  name: string;
  gstin?: string;
  pan?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  payment_terms_days: number;
  category?: string;
  rating?: number;
  unit_id: ManufacturingUnit;
  is_active: boolean;
}

// 3. Employee
export interface Employee extends AuditBase {
  id: string;
  code: string;
  full_name: string;
  email?: string;
  phone?: string;
  department: string;
  designation: string;
  account_type?: string;
  job_role?: string;
  joining_date?: string;
  unit_id: ManufacturingUnit;
  status: string;
  emergency_contact?: string;
  is_active: boolean;
  user_id?: string;
}

// 4. Finished Product
export interface FinishedProduct extends AuditBase {
  id: string;
  code: string;
  name: string;
  description?: string;
  category_id?: string;
  uom: string;
  drawing_no?: string;
  revision_no?: string;
  standard_cost: number;
  selling_price: number;
  min_stock_level: number;
  unit_id: ManufacturingUnit;
  is_active: boolean;
}

// 5. Raw Material
export interface RawMaterial extends AuditBase {
  id: string;
  code: string;
  name: string;
  description?: string;
  category_id?: string;
  uom: string;
  hsn_code?: string;
  reorder_level: number;
  safety_stock: number;
  standard_cost?: number;
  default_vendor_code?: string;
  unit_id: ManufacturingUnit;
  is_active: boolean;
}

// 6. Unit of Measure (UoM)
export interface UoM extends AuditBase {
  id: string;
  code: string;
  name: string;
  symbol?: string;
  description?: string;
  is_active: boolean;
}

// 7. Warehouse & Storage Location
export interface Warehouse extends AuditBase {
  id: string;
  code: string;
  name: string;
  unit_id: ManufacturingUnit;
  location_type: string;
  bay_rack?: string;
  capacity_description?: string;
  is_active: boolean;
}

// 8. Categories
export interface Category extends AuditBase {
  id: string;
  code: string;
  name: string;
  category_type: string;
  description?: string;
  is_active: boolean;
}

export type MasterEntityKey =
  | 'customers'
  | 'vendors'
  | 'employees'
  | 'products'
  | 'finished_products'
  | 'materials'
  | 'raw_materials'
  | 'uom'
  | 'warehouses'
  | 'categories';
