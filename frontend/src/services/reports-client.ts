import { apiClient } from './api-client';
import {
  ReportType,
  ExportFormat,
  GenericReportResponse,
  ImportEntityType,
  ImportDryRunResponse,
  ImportCommitRequest,
  ImportCommitResponse,
  ImportBatchSummary,
} from '@/types/reports';
import { PaginatedResponse } from '@/types/master';

export const reportsClient = {
  // Get scoped analytics report
  async getReport(
    reportType: ReportType,
    params?: {
      unit_id?: string;
      start_date?: string;
      end_date?: string;
      search?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<GenericReportResponse> {
    const query = new URLSearchParams();
    if (params?.unit_id && params.unit_id !== 'BOTH') query.set('unit_id', params.unit_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.search) query.set('search', params.search);
    if (params?.page) query.set('page', params.page.toString());
    if (params?.page_size) query.set('page_size', params.page_size.toString());

    const qs = query.toString();
    const endpoint = `/reports/${reportType}${qs ? `?${qs}` : ''}`;
    const res = await apiClient.get<GenericReportResponse>(endpoint);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch report');
    return res.data;
  },

  // Export report as CSV or XLSX
  getExportUrl(
    reportType: ReportType,
    format: ExportFormat,
    params?: {
      unit_id?: string;
      start_date?: string;
      end_date?: string;
      search?: string;
    }
  ): string {
    const query = new URLSearchParams();
    query.set('export_format', format);
    if (params?.unit_id && params.unit_id !== 'BOTH') query.set('unit_id', params.unit_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.search) query.set('search', params.search);

    const baseUrl = getApiV1Base();
    return `${baseUrl}/reports/${reportType}/export?${query.toString()}`;
  },

  // Download template
  getTemplateUrl(entityType: ImportEntityType): string {
    const baseUrl = getApiV1Base();
    return `${baseUrl}/imports/templates/${entityType}`;
  },

  // Dry-run upload
  async dryRunImport(entityType: ImportEntityType, file: File): Promise<ImportDryRunResponse> {
    const formData = new FormData();
    formData.append('entity_type', entityType);
    formData.append('file', file);

    const res = await fetch(`${getApiV1Base()}/imports/dry-run`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRF-Token': getCsrfTokenFromCookie(),
      },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Dry-run validation failed');
    }

    return res.json();
  },

  // Commit batch
  async commitBatch(data: ImportCommitRequest): Promise<ImportCommitResponse> {
    const res = await apiClient.post<ImportCommitResponse>('/imports/commit', data);
    if (!res.data) throw new Error(res.error?.message || 'Failed to commit batch');
    return res.data;
  },

  // List past batches
  async listBatches(page = 1, pageSize = 20): Promise<PaginatedResponse<ImportBatchSummary>> {
    const res = await apiClient.get<PaginatedResponse<ImportBatchSummary>>(`/imports/batches?page=${page}&page_size=${pageSize}`);
    if (!res.data) throw new Error(res.error?.message || 'Failed to fetch import batches');
    return res.data;
  },
};

function getApiV1Base(): string {
  const base = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    .replace(/\/+$/, '')
    .replace(/\/api\/v1\/?$/, '');
  return `${base}/api/v1`;
}

function getCsrfTokenFromCookie(): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/(?:^|; )RG_csrf=([^;]*)/) ||
    document.cookie.match(/(?:^|; )RG_csrf_token=([^;]*)/);
  return match && match[1] ? decodeURIComponent(match[1]) : '';
}
