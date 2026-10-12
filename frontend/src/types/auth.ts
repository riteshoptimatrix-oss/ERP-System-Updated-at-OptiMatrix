export type RoleName =
  | 'SUPER_ADMIN'
  | 'ADMIN'
  | 'HR'
  | 'PRODUCTION_MANAGER'
  | 'INVENTORY_MANAGER'
  | 'QC_INSPECTOR'
  | 'SALES_DISPATCH'
  | 'EMPLOYEE';

export type ManufacturingUnit = 'Unit_1' | 'Unit_2' | 'BOTH';

export type AccountType = 'SUPER_ADMIN' | 'ADMIN' | 'HR' | 'EMPLOYEE';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: RoleName;
  account_type?: AccountType | string;
  department?: string;
  job_role?: string;
  job_roles?: string[];
  employee_code?: string;
  allowed_units: ManufacturingUnit[];
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
  permissions: string[];
  must_change_password?: boolean;
  password_changed_at?: string;
  password_reset_requested_at?: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  activeUnit: ManufacturingUnit;
  csrfToken: string | null;
}
