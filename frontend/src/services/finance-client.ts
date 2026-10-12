import { apiClient } from './api-client';
import {
  Account,
  CustomerInvoice,
  SupplierBill,
  PaymentRecord,
  JournalEntry,
  TrialBalanceResponse,
  FinanceSummary,
} from '@/types/finance';
import { PaginatedResponse } from '@/types/master';

export const financeClient = {
  // Summary KPI
  async getSummary(unit_id?: string): Promise<FinanceSummary> {
    const q = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<FinanceSummary>(`/finance/summary${q}`);
    if (!res.data) throw new Error('Failed to fetch finance summary');
    return res.data;
  },

  // Chart of accounts
  async getAccounts(account_type?: string): Promise<Account[]> {
    const q = account_type ? `?account_type=${account_type}` : '';
    const res = await apiClient.get<Account[]>(`/finance/accounts${q}`);
    return res.data || [];
  },

  // Customer Invoices
  async listInvoices(params: { unit_id?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<CustomerInvoice>> {
    const q = new URLSearchParams();
    if (params.unit_id && params.unit_id !== 'BOTH') q.set('unit_id', params.unit_id);
    if (params.page) q.set('page', params.page.toString());
    if (params.page_size) q.set('page_size', params.page_size.toString());
    const res = await apiClient.get<PaginatedResponse<CustomerInvoice>>(`/finance/invoices?${q.toString()}`);
    if (!res.data) throw new Error('Failed to fetch invoices');
    return res.data;
  },

  // Supplier Bills
  async listBills(params: { unit_id?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<SupplierBill>> {
    const q = new URLSearchParams();
    if (params.unit_id && params.unit_id !== 'BOTH') q.set('unit_id', params.unit_id);
    if (params.page) q.set('page', params.page.toString());
    if (params.page_size) q.set('page_size', params.page_size.toString());
    const res = await apiClient.get<PaginatedResponse<SupplierBill>>(`/finance/bills?${q.toString()}`);
    if (!res.data) throw new Error('Failed to fetch bills');
    return res.data;
  },

  // Release QC Hold
  async releaseQCHold(billId: string, reason: string): Promise<SupplierBill> {
    const res = await apiClient.post<SupplierBill>(`/finance/bills/${billId}/release-qc-hold`, {
      release_reason: reason,
    });
    if (!res.data) throw new Error(res.error?.message || 'Failed to release QC hold');
    return res.data;
  },

  // Payments
  async listPayments(params: { unit_id?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<PaymentRecord>> {
    const q = new URLSearchParams();
    if (params.unit_id && params.unit_id !== 'BOTH') q.set('unit_id', params.unit_id);
    if (params.page) q.set('page', params.page.toString());
    if (params.page_size) q.set('page_size', params.page_size.toString());
    const res = await apiClient.get<PaginatedResponse<PaymentRecord>>(`/finance/payments?${q.toString()}`);
    if (!res.data) throw new Error('Failed to fetch payments');
    return res.data;
  },

  // Journal Entries
  async listJournalEntries(params: { unit_id?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<JournalEntry>> {
    const q = new URLSearchParams();
    if (params.unit_id && params.unit_id !== 'BOTH') q.set('unit_id', params.unit_id);
    if (params.page) q.set('page', params.page.toString());
    if (params.page_size) q.set('page_size', params.page_size.toString());
    const res = await apiClient.get<PaginatedResponse<JournalEntry>>(`/finance/journals?${q.toString()}`);
    if (!res.data) throw new Error('Failed to fetch journal entries');
    return res.data;
  },

  // Trial Balance
  async getTrialBalance(as_of_date?: string, unit_id?: string): Promise<TrialBalanceResponse> {
    const q = new URLSearchParams();
    if (as_of_date) q.set('as_of_date', as_of_date);
    if (unit_id && unit_id !== 'BOTH') q.set('unit_id', unit_id);
    const res = await apiClient.get<TrialBalanceResponse>(`/finance/reports/trial-balance?${q.toString()}`);
    if (!res.data) throw new Error('Failed to fetch trial balance');
    return res.data;
  },

  // Create Customer Invoice (AR)
  async createInvoice(payload: any): Promise<CustomerInvoice> {
    const res = await apiClient.post<CustomerInvoice>('/finance/invoices', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to create invoice');
    return res.data;
  },

  // Create Supplier Bill (AP)
  async createBill(payload: any): Promise<SupplierBill> {
    const res = await apiClient.post<SupplierBill>('/finance/bills', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to create supplier bill');
    return res.data;
  },

  // Record Payment / Receipt
  async createPayment(payload: any): Promise<PaymentRecord> {
    const res = await apiClient.post<PaymentRecord>('/finance/payments', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to record payment');
    return res.data;
  },

  // Post Journal Voucher (JV)
  async createJournalEntry(payload: any): Promise<JournalEntry> {
    const res = await apiClient.post<JournalEntry>('/finance/journals', payload);
    if (!res.data) throw new Error(res.error?.message || 'Failed to post journal entry');
    return res.data;
  },
};
