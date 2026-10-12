import { apiClient } from './api-client';
import {
  SalaryStructure,
  SalaryStructureInput,
  PayrollRun,
  PayrollRunCreate,
  PayrollItem,
  Payslip,
  PayrollJournalEntry,
  PayrollSummary,
} from '@/types/hr';
import { PaginatedResponse } from '@/types/master';

export interface ListPayrollRunsParams {
  unit_id?: string;
  status?: string;
  period?: string;
  page?: number;
  page_size?: number;
}

export const payrollClient = {
  /**
   * Get Payroll processing KPI metrics summary
   */
  async getSummary(unit_id?: string): Promise<PayrollSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<PayrollSummary>(`/payroll/summary${query}`);
    if (!res.data) throw new Error('Failed to retrieve payroll summary');
    return res.data;
  },

  /**
   * List configured employee salary structures
   */
  async listStructures(unit_id?: string): Promise<SalaryStructure[]> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<SalaryStructure[]>(`/payroll/structures${query}`);
    return res.data || [];
  },

  /**
   * Get single salary structure by employee ID or code
   */
  async getStructure(employeeId: string): Promise<SalaryStructure> {
    const res = await apiClient.get<SalaryStructure>(`/payroll/structures/${employeeId}`);
    if (!res.data) throw new Error('Salary structure not found');
    return res.data;
  },

  /**
   * Upsert salary structure
   */
  async upsertStructure(data: SalaryStructureInput): Promise<SalaryStructure> {
    const res = await apiClient.post<SalaryStructure>('/payroll/structures', data);
    if (!res.data) throw new Error('Failed to save salary structure');
    return res.data;
  },

  /**
   * List paginated payroll runs
   */
  async listRuns(params: ListPayrollRunsParams = {}): Promise<PaginatedResponse<PayrollRun>> {
    const query = new URLSearchParams();
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.status) query.append('status', params.status);
    if (params.period) query.append('period', params.period);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<PayrollRun>>(`/payroll/runs${qs}`);
    if (!res.data) throw new Error('Failed to retrieve payroll runs');
    return res.data;
  },

  /**
   * Create and calculate new monthly payroll run
   */
  async createRun(data: PayrollRunCreate): Promise<PayrollRun> {
    const res = await apiClient.post<PayrollRun>('/payroll/runs', data);
    if (!res.data) throw new Error('Failed to create payroll run');
    return res.data;
  },

  /**
   * Get payroll run by ID
   */
  async getRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.get<PayrollRun>(`/payroll/runs/${runId}`);
    if (!res.data) throw new Error('Payroll run not found');
    return res.data;
  },

  /**
   * List line items for payroll run
   */
  async listItems(runId: string): Promise<PayrollItem[]> {
    const res = await apiClient.get<PayrollItem[]>(`/payroll/runs/${runId}/items`);
    return res.data || [];
  },

  /**
   * Submit payroll run for review
   */
  async reviewRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.post<PayrollRun>(`/payroll/runs/${runId}/review`, {});
    if (!res.data) throw new Error('Failed to review payroll run');
    return res.data;
  },

  /**
   * Approve payroll run
   */
  async approveRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.post<PayrollRun>(`/payroll/runs/${runId}/approve`, {});
    if (!res.data) throw new Error('Failed to approve payroll run');
    return res.data;
  },

  /**
   * Post payroll run (lock ledger and prevent changes)
   */
  async postRun(runId: string): Promise<PayrollRun> {
    const res = await apiClient.post<PayrollRun>(`/payroll/runs/${runId}/post`, {});
    if (!res.data) throw new Error('Failed to post payroll run');
    return res.data;
  },

  /**
   * Get itemized payslip breakdown
   */
  async getPayslip(employeeId: string, period: string): Promise<Payslip> {
    const res = await apiClient.get<Payslip>(`/payroll/payslips/${employeeId}/${period}`);
    if (!res.data) throw new Error('Payslip not found');
    return res.data;
  },

  /**
   * Get balanced double-entry accounting journal export
   */
  async getAccountingExport(runId: string): Promise<PayrollJournalEntry> {
    const res = await apiClient.get<PayrollJournalEntry>(`/payroll/runs/${runId}/accounting-export`);
    if (!res.data) throw new Error('Failed to export accounting journal');
    return res.data;
  },
};
