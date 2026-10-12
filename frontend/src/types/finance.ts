export type AccountType = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE';

export interface Account {
  id: string;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  parent_code?: string;
  current_balance: number;
  is_active: boolean;
}

export interface InvoiceLineItem {
  product_id?: string;
  product_code: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  tax_amount: number;
  line_total: number;
}

export interface CustomerInvoice {
  id: string;
  invoice_number: string;
  customer_id: string;
  customer_code: string;
  customer_name: string;
  sales_order_id?: string;
  sales_order_number?: string;
  project_id?: string;
  project_code?: string;
  unit_id: string;
  invoice_date: string;
  due_date: string;
  subtotal_amount?: number;
  subtotal?: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  balance_due?: number;
  balance_amount?: number;
  status: 'DRAFT' | 'POSTED' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';
  lines: InvoiceLineItem[];
  created_at: string;
}

export interface BillLineItem {
  item_code?: string;
  material_id?: string;
  material_code?: string;
  material_name?: string;
  description?: string;
  quantity: number;
  unit_price?: number;
  unit_cost?: number;
  tax_percent?: number;
  tax_rate?: number;
  tax_amount?: number;
  total?: number;
  line_total?: number;
}

export interface SupplierBill {
  id: string;
  bill_number: string;
  vendor_id: string;
  vendor_code: string;
  vendor_name: string;
  bill_number_vendor?: string;
  po_reference?: string;
  project_id?: string;
  project_code?: string;
  unit_id: string;
  bill_date: string;
  due_date: string;
  subtotal_amount?: number;
  subtotal?: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  balance_due?: number;
  balance_amount?: number;
  status: 'DRAFT' | 'POSTED' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED' | 'ON_HOLD' | 'APPROVED';
  has_qc_hold: boolean;
  qc_hold_reason?: string;
  qc_hold_reference?: string;
  qc_released_by?: string;
  qc_released_at?: string;
  lines: BillLineItem[];
  created_at: string;
}

export interface PaymentRecord {
  id: string;
  payment_number: string;
  payment_type: 'CUSTOMER_RECEIPT' | 'VENDOR_PAYMENT' | 'DIRECT_EXPENSE' | 'EXPENSE_PAYMENT' | 'OTHER';
  unit_id: string;
  payment_date: string;
  entity_id?: string;
  entity_code?: string;
  entity_name?: string;
  party_id?: string;
  party_name?: string;
  reference_doc_id?: string;
  reference_doc_number?: string;
  project_id?: string;
  project_code?: string;
  payment_method?: string;
  payment_mode?: string;
  payment_reference?: string;
  bank_account_code?: string;
  payment_account_code?: string;
  amount: number;
  transaction_ref?: string;
  journal_entry_id?: string;
  created_at: string;
}

export interface CustomerInvoicePayload {
  customer_id: string;
  customer_name?: string;
  sales_order_id?: string;
  sales_order_number?: string;
  project_id?: string;
  project_code?: string;
  unit_id: string;
  invoice_date: string;
  due_date: string;
  lines: {
    item_code: string;
    description: string;
    quantity: number;
    unit_price: number;
    discount_percent?: number;
    tax_percent?: number;
    account_code?: string;
  }[];
  notes?: string;
}

export interface SupplierBillPayload {
  vendor_id: string;
  vendor_name?: string;
  bill_number_vendor: string;
  po_reference?: string;
  project_id?: string;
  project_code?: string;
  unit_id: string;
  bill_date: string;
  due_date: string;
  lines: {
    item_code: string;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percent?: number;
    account_code?: string;
  }[];
  has_qc_hold?: boolean;
  qc_hold_reason?: string;
  notes?: string;
}

export interface PaymentPayload {
  payment_type: 'CUSTOMER_RECEIPT' | 'VENDOR_PAYMENT';
  entity_id: string;
  reference_doc_id?: string;
  reference_doc_number?: string;
  project_id?: string;
  project_code?: string;
  unit_id: string;
  payment_date: string;
  payment_method: string;
  payment_reference?: string;
  amount: number;
  bank_account_code: string;
  notes?: string;
}

export interface JournalEntryPayload {
  entry_date: string;
  unit_id: string;
  source_module: string;
  source_reference: string;
  description: string;
  lines: {
    account_code: string;
    account_name?: string;
    debit: number;
    credit: number;
    description?: string;
  }[];
}

export interface JournalLine {
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  description?: string;
}

export interface JournalEntry {
  id: string;
  entry_number: string;
  entry_date: string;
  unit_id: string;
  source_module: string;
  source_reference: string;
  description: string;
  total_debit: number;
  total_credit: number;
  status: 'POSTED' | 'REVERSED';
  is_reversal: boolean;
  reversed_by_entry?: string;
  lines: JournalLine[];
  created_at: string;
}

export interface TrialBalanceItem {
  account_code: string;
  account_name: string;
  account_type: string;
  debit: number;
  credit: number;
}

export interface TrialBalanceResponse {
  as_of_date: string;
  unit_id?: string;
  accounts?: TrialBalanceItem[];
  lines?: TrialBalanceItem[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

export interface FinanceSummary {
  unit_id: string;
  total_receivables: number;
  total_payables: number;
  cash_bank_balance: number;
  qc_holds_count: number;
}
