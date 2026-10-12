export type ReportType =
  | 'sales'
  | 'orders'
  | 'dispatch'
  | 'inventory'
  | 'bom'
  | 'production'
  | 'wip'
  | 'qc'
  | 'wastage'
  | 'downtime'
  | 'attendance'
  | 'payroll'
  | 'finance';

export type ExportFormat = 'json' | 'csv' | 'xlsx';

export type ImportEntityType =
  | 'customers'
  | 'vendors'
  | 'raw_materials'
  | 'finished_products'
  | 'employees'
  | 'warehouses'
  | 'categories'
  | 'uoms'
  | 'opening_stock';

export type ImportBatchStatus =
  | 'DRY_RUN_PASSED'
  | 'DRY_RUN_FAILED'
  | 'COMMITTED'
  | 'REJECTED';

export interface ReportSummaryKpi {
  metric_name: string;
  metric_value: number | string;
  formatted_value: string;
  description?: string;
}

export interface GenericReportResponse {
  report_type: ReportType;
  unit_id?: string;
  start_date?: string;
  end_date?: string;
  kpis: ReportSummaryKpi[];
  columns: { key: string; label: string }[];
  items: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  generated_at: string;
}

export interface RowErrorDetail {
  row_number: number;
  column?: string;
  value?: unknown;
  error_message: string;
  is_duplicate: boolean;
}

export interface ImportDryRunResponse {
  batch_token: string;
  entity_type: ImportEntityType;
  filename: string;
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  duplicate_rows_count: number;
  can_commit: boolean;
  errors: RowErrorDetail[];
  preview_rows: Record<string, unknown>[];
  validation_summary: string;
}

export interface ImportCommitRequest {
  batch_token: string;
  unit_id: string;
  notes?: string;
}

export interface ImportCommitResponse {
  batch_id: string;
  entity_type: string;
  status: string;
  inserted_count: number;
  skipped_count: number;
  committed_by: string;
  committed_at: string;
  message: string;
}

export interface ImportBatchSummary {
  id: string;
  batch_id: string;
  batch_token: string;
  entity_type: string;
  filename: string;
  unit_id: string;
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  status: string;
  committed_by?: string;
  committed_at?: string;
  created_at: string;
  created_by: string;
  errors_sample?: RowErrorDetail[];
}
