'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { financeClient } from '@/services/finance-client';
import { masterClient } from '@/services/master-client';
import { crmClient } from '@/services/crm-client';
import {
  CustomerInvoice,
  SupplierBill,
  PaymentRecord,
  JournalEntry,
  TrialBalanceResponse,
  FinanceSummary,
  Account,
} from '@/types/finance';
import { Lead } from '@/types/crm';
import {
  IndianRupee,
  Receipt,
  FileText,
  CreditCard,
  Layers,
  Scale,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Plus,
  Trash2,
  Lock,
  Calendar,
  Building2,
  Briefcase,
} from 'lucide-react';

export default function FinanceDashboardPage() {
  const { activeUnit, hasPermission, user } = useAuth();
  const canApprove = hasPermission('finance', 'approve');
  const canCreate =
    hasPermission('finance', 'create') ||
    hasPermission('finance', 'post') ||
    user?.role === 'SUPER_ADMIN' ||
    user?.role === 'ADMIN';

  const [activeTab, setActiveTab] = useState<'invoices' | 'bills' | 'payments' | 'journals' | 'trial_balance'>('invoices');
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [invoices, setInvoices] = useState<CustomerInvoice[]>([]);
  const [bills, setBills] = useState<SupplierBill[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [releaseLoading, setReleaseLoading] = useState<string | null>(null);

  // Fallback real-world catalog items so dropdowns are always populated immediately
  const DEFAULT_CUSTOMERS = [
    { id: 'CUST-001', code: 'CUST-001', name: 'Ravi Stationery Pvt Ltd' },
    { id: 'CUST-002', code: 'CUST-002', name: 'National Paper Industries' },
    { id: 'CUST-2026-0002', code: 'CUST-2026-0002', name: 'Apex Engineering Systems Pvt Ltd' },
    { id: 'CUST-003', code: 'CUST-003', name: 'Gujarat Paper Crafts Ltd' },
    { id: 'CUST-004', code: 'CUST-004', name: 'Surat Envelope & Packaging Co' },
  ];

  const DEFAULT_VENDORS = [
    { id: 'VEND-001', code: 'VEND-001', name: 'Jindal Steel & Power Ltd' },
    { id: 'VEND-002', code: 'VEND-002', name: 'Bharat Electrical Motors' },
    { id: 'VEND-003', code: 'VEND-003', name: 'Ahmedabad Rubber Products' },
    { id: 'VEND-004', code: 'VEND-004', name: 'SKF Bearings India Ltd' },
    { id: 'VEND-005', code: 'VEND-005', name: 'Asian Paints Industrial Coatings' },
  ];

  const DEFAULT_PRODUCTS = [
    { id: 'FP-ENV-100', code: 'FP-ENV-100', name: 'Automatic Envelope Making Machine ENV-100', selling_price: 245000, standard_cost: 185000 },
    { id: 'FP-ENV-200', code: 'FP-ENV-200', name: 'High-Speed Commercial Envelope Making Machine ENV-200', selling_price: 415000, standard_cost: 310000 },
    { id: 'FP-PKG-300', code: 'FP-PKG-300', name: 'Corrugated Carton Automatic Packing Machine PKG-300', selling_price: 565000, standard_cost: 420000 },
    { id: 'FP-ENV-MINI', code: 'FP-ENV-MINI', name: 'Semi-Automatic Tabletop Envelope Machine ENV-MINI', selling_price: 128000, standard_cost: 95000 },
    { id: 'FP-DIE-PUNCH-40', code: 'FP-DIE-PUNCH-40', name: 'Heavy Duty Hydraulic Die Punching Machine DP-40', selling_price: 325000, standard_cost: 240000 },
    { id: 'FP-PAPER-FOLD-120', code: 'FP-PAPER-FOLD-120', name: 'High-Precision Commercial Paper Folder PF-120', selling_price: 295000, standard_cost: 215000 },
    { id: 'FP-GLUE-APPL-10', code: 'FP-GLUE-APPL-10', name: 'Precision Hot-Melt Adhesive Applicator GA-10', selling_price: 85000, standard_cost: 62000 },
    { id: 'FP-SPARE-FEEDER-VAC', code: 'FP-SPARE-FEEDER-VAC', name: 'Top Suction Vacuum Feeder Assembly Module', selling_price: 65000, standard_cost: 48000 },
    { id: 'FP-SPARE-ROLLER-CR', code: 'FP-SPARE-ROLLER-CR', name: 'Hard Chrome Plated Steel Pressure Roller Set', selling_price: 28000, standard_cost: 19500 },
    { id: 'FP-TOOL-DIE-A4', code: 'FP-TOOL-DIE-A4', name: 'Custom Hardened Steel Envelope Cutting Die Set (C5/A4)', selling_price: 42000, standard_cost: 31000 },
  ];

  const DEFAULT_MATERIALS = [
    { id: 'RM-MS-PLATE-6MM', code: 'RM-MS-PLATE-6MM', name: 'Mild Steel Plate 6mm IS 2062', standard_cost: 65 },
    { id: 'RM-MS-PLATE-10MM', code: 'RM-MS-PLATE-10MM', name: 'Mild Steel Plate 10mm IS 2062', standard_cost: 68 },
    { id: 'RM-SS-ROD-20MM', code: 'RM-SS-ROD-20MM', name: 'Stainless Steel Round Bar 20mm SS304', standard_cost: 240 },
    { id: 'RM-CI-CAST-001', code: 'RM-CI-CAST-001', name: 'Cast Iron Main Gearbox Housing Body', standard_cost: 35000 },
    { id: 'RM-MS-CHANNEL', code: 'RM-MS-CHANNEL', name: 'MS Structural Channel 100x50 mm', standard_cost: 72 },
    { id: 'RM-MOTOR-0.5HP', code: 'RM-MOTOR-0.5HP', name: 'AC Induction Motor 0.5 HP 3-Phase 1440 RPM', standard_cost: 4500 },
    { id: 'RM-MOTOR-1HP', code: 'RM-MOTOR-1HP', name: 'AC Induction Motor 1.0 HP 3-Phase 1440 RPM', standard_cost: 7800 },
    { id: 'RM-BEARING-6205', code: 'RM-BEARING-6205', name: 'Deep Groove Ball Bearing 6205-2RS SKF', standard_cost: 350 },
    { id: 'RM-CAPACITOR-25', code: 'RM-CAPACITOR-25', name: 'Motor Run Capacitor 25 MFD 440V', standard_cost: 180 },
    { id: 'RM-RUBBER-GSKT', code: 'RM-RUBBER-GSKT', name: 'Nitrile Rubber Sealing Gasket Strip 3mm', standard_cost: 120 },
    { id: 'RM-NYLON-BUSH', code: 'RM-NYLON-BUSH', name: 'Nylon 6 Self-Lubricating Bush 20mm ID', standard_cost: 85 },
    { id: 'RM-WELD-ROD-E6013', code: 'RM-WELD-ROD-E6013', name: 'Mild Steel Welding Electrode E6013 3.15mm', standard_cost: 320 },
    { id: 'RM-CUTTING-OIL', code: 'RM-CUTTING-OIL', name: 'Water Soluble Cutting & CNC Coolant Oil', standard_cost: 220 },
    { id: 'RM-PAINT-GREY', code: 'RM-PAINT-GREY', name: 'Industrial Epoxy Machine Grey Paint', standard_cost: 380 },
    { id: 'RM-PNEU-CYL-32', code: 'RM-PNEU-CYL-32', name: 'Double Acting Pneumatic Air Cylinder 32x100mm', standard_cost: 1850 },
    { id: 'RM-TIMING-BELT', code: 'RM-TIMING-BELT', name: 'Rubber Timing Belt 8M Pitch 30mm Wide', standard_cost: 750 },
    { id: 'RM-SENSOR-PROX', code: 'RM-SENSOR-PROX', name: 'Inductive Proximity Sensor M12 NPN NO', standard_cost: 620 },
  ];

  // Master Dropdown State
  const [customers, setCustomers] = useState<{ id: string; name: string; code: string }[]>(DEFAULT_CUSTOMERS);
  const [vendors, setVendors] = useState<{ id: string; name: string; code: string }[]>(DEFAULT_VENDORS);
  const [products, setProducts] = useState<{ id: string; name: string; code: string; selling_price?: number; standard_cost?: number }[]>(DEFAULT_PRODUCTS);
  const [rawMaterials, setRawMaterials] = useState<{ id: string; name: string; code: string; standard_cost?: number; selling_price?: number }[]>(DEFAULT_MATERIALS);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);

  // Modals Open State
  const [isInvoiceModalOpen, setIsInvoiceModalOpen] = useState(false);
  const [isBillModalOpen, setIsBillModalOpen] = useState(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isJournalModalOpen, setIsJournalModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // 1. Invoice Form State
  const [invoiceForm, setInvoiceForm] = useState({
    customer_id: '',
    project_id: '',
    unit_id: 'Unit_1',
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    notes: '',
    lines: [{ item_code: '', description: '', quantity: 1, unit_price: 0, tax_percent: 18 }],
  });

  // 2. Bill Form State
  const [billForm, setBillForm] = useState({
    vendor_id: '',
    bill_number_vendor: '',
    po_reference: '',
    project_id: '',
    unit_id: 'Unit_1',
    bill_date: new Date().toISOString().split('T')[0],
    due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    has_qc_hold: false,
    qc_hold_reason: '',
    notes: '',
    lines: [{ item_code: '', description: '', quantity: 1, unit_price: 0, tax_percent: 18 }],
  });

  // 3. Payment Form State
  const [paymentForm, setPaymentForm] = useState({
    payment_type: 'CUSTOMER_RECEIPT' as 'CUSTOMER_RECEIPT' | 'VENDOR_PAYMENT',
    entity_id: '',
    reference_doc_number: '',
    project_id: '',
    unit_id: 'Unit_1',
    payment_date: new Date().toISOString().split('T')[0],
    payment_method: 'BANK_TRANSFER',
    payment_reference: '',
    amount: 0,
    bank_account_code: '1010-BANK-HDFC',
    notes: '',
  });

  // 4. Journal Voucher Form State
  const [journalForm, setJournalForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    unit_id: 'Unit_1',
    source_module: 'MANUAL',
    source_reference: 'JV-' + Math.floor(1000 + Math.random() * 9000),
    description: '',
    lines: [
      { account_code: '1010-BANK-HDFC', debit: 0, credit: 0, description: '' },
      { account_code: '5300-OPERATING-EXPENSES', debit: 0, credit: 0, description: '' },
    ],
  });

  // Load Dropdowns
  useEffect(() => {
    const fetchMasterData = async () => {
      try {
        const [cRes, vRes, pRes, rRes, aRes, lRes] = await Promise.allSettled([
          masterClient.list('customers', { page_size: 100 }),
          masterClient.list('vendors', { page_size: 100 }),
          masterClient.list('products', { page_size: 100 }),
          masterClient.list('materials', { page_size: 100 }),
          financeClient.getAccounts(),
          crmClient.listLeads({ page_size: 100 }),
        ]);
        if (cRes.status === 'fulfilled' && (cRes.value.items as any)?.length > 0) {
          setCustomers(cRes.value.items as any);
        }
        if (vRes.status === 'fulfilled' && (vRes.value.items as any)?.length > 0) {
          setVendors(vRes.value.items as any);
        }
        if (pRes.status === 'fulfilled' && (pRes.value.items as any)?.length > 0) {
          setProducts(pRes.value.items as any);
        }
        if (rRes.status === 'fulfilled' && (rRes.value.items as any)?.length > 0) {
          setRawMaterials(rRes.value.items as any);
        }
        if (aRes.status === 'fulfilled' && aRes.value?.length > 0) {
          setAccounts(aRes.value);
        }
        if (lRes.status === 'fulfilled' && lRes.value.items?.length > 0) {
          setLeads(lRes.value.items);
        }
      } catch {
        // Silently continue
      }
    };
    fetchMasterData();
  }, []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const unitParam = activeUnit === 'BOTH' ? undefined : activeUnit;
      const sum = await financeClient.getSummary(unitParam);
      setSummary(sum);

      if (activeTab === 'invoices') {
        const inv = await financeClient.listInvoices({ unit_id: unitParam, page: 1, page_size: 50 });
        setInvoices(inv.items);
      } else if (activeTab === 'bills') {
        const bl = await financeClient.listBills({ unit_id: unitParam, page: 1, page_size: 50 });
        setBills(bl.items);
      } else if (activeTab === 'payments') {
        const py = await financeClient.listPayments({ unit_id: unitParam, page: 1, page_size: 50 });
        setPayments(py.items);
      } else if (activeTab === 'journals') {
        const jn = await financeClient.listJournalEntries({ unit_id: unitParam, page: 1, page_size: 50 });
        setJournals(jn.items);
      } else if (activeTab === 'trial_balance') {
        const tb = await financeClient.getTrialBalance(undefined, unitParam);
        setTrialBalance(tb);
      }
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  }, [activeTab, activeUnit]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleReleaseQCHold = async (billId: string) => {
    const reason = window.prompt('Enter reason for releasing QC payment hold:');
    if (!reason) return;
    try {
      setReleaseLoading(billId);
      await financeClient.releaseQCHold(billId, reason);
      alert('QC hold released successfully. Bill is now eligible for payment.');
      loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to release QC hold');
    } finally {
      setReleaseLoading(null);
    }
  };

  // Submit Invoice
  const handleCreateInvoice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoiceForm.customer_id) {
      setFormError('Please select a customer.');
      return;
    }
    const selectedLead = leads.find((l) => l.id === invoiceForm.project_id);
    try {
      setSubmitting(true);
      setFormError(null);
      await financeClient.createInvoice({
        customer_id: invoiceForm.customer_id,
        project_id: invoiceForm.project_id || undefined,
        project_code: selectedLead?.code || undefined,
        unit_id: invoiceForm.unit_id,
        invoice_date: invoiceForm.invoice_date,
        due_date: invoiceForm.due_date,
        lines: invoiceForm.lines.map((l) => ({
          item_code: l.item_code || 'GENERIC',
          description: l.description || 'Sales Item',
          quantity: Number(l.quantity),
          unit_price: Number(l.unit_price),
          tax_percent: Number(l.tax_percent),
          account_code: '4000-SALES-REVENUE',
        })),
        notes: invoiceForm.notes,
      });
      setIsInvoiceModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create invoice');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Supplier Bill
  const handleCreateBill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!billForm.vendor_id || !billForm.bill_number_vendor) {
      setFormError('Please select vendor and enter Vendor Bill Number.');
      return;
    }
    const selectedLead = leads.find((l) => l.id === billForm.project_id);
    try {
      setSubmitting(true);
      setFormError(null);
      await financeClient.createBill({
        vendor_id: billForm.vendor_id,
        bill_number_vendor: billForm.bill_number_vendor,
        po_reference: billForm.po_reference || selectedLead?.code || undefined,
        project_id: billForm.project_id || undefined,
        project_code: selectedLead?.code || undefined,
        unit_id: billForm.unit_id,
        bill_date: billForm.bill_date,
        due_date: billForm.due_date,
        has_qc_hold: billForm.has_qc_hold,
        qc_hold_reason: billForm.has_qc_hold ? billForm.qc_hold_reason : undefined,
        lines: billForm.lines.map((l) => ({
          item_code: l.item_code || 'RAW-MAT',
          description: l.description || 'Raw Material / Expense',
          quantity: Number(l.quantity),
          unit_price: Number(l.unit_price),
          tax_percent: Number(l.tax_percent),
          account_code: '1200-RAW-MATERIAL-INVENTORY',
        })),
        notes: billForm.notes,
      });
      setIsBillModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create supplier bill');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Payment / Receipt
  const handleCreatePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentForm.entity_id || Number(paymentForm.amount) <= 0) {
      setFormError('Please select entity and valid payment amount.');
      return;
    }
    const selectedLead = leads.find((l) => l.id === paymentForm.project_id);
    try {
      setSubmitting(true);
      setFormError(null);
      await financeClient.createPayment({
        payment_type: paymentForm.payment_type,
        entity_id: paymentForm.entity_id,
        reference_doc_number: paymentForm.reference_doc_number || undefined,
        project_id: paymentForm.project_id || undefined,
        project_code: selectedLead?.code || undefined,
        unit_id: paymentForm.unit_id,
        payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        payment_reference: paymentForm.payment_reference || undefined,
        amount: Number(paymentForm.amount),
        bank_account_code: paymentForm.bank_account_code,
        notes: paymentForm.notes,
      });
      setIsPaymentModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to record payment');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Journal Voucher
  const handleCreateJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    const totDeb = journalForm.lines.reduce((s, l) => s + Number(l.debit || 0), 0);
    const totCred = journalForm.lines.reduce((s, l) => s + Number(l.credit || 0), 0);
    if (Math.abs(totDeb - totCred) > 0.01) {
      setFormError(`Journal is unbalanced! Total Debits (₹${totDeb}) must equal Total Credits (₹${totCred}). Difference: ₹${(totDeb - totCred).toFixed(2)}`);
      return;
    }
    if (totDeb <= 0) {
      setFormError('Journal entry amount must be greater than zero.');
      return;
    }
    try {
      setSubmitting(true);
      setFormError(null);
      await financeClient.createJournalEntry({
        entry_date: journalForm.entry_date,
        unit_id: journalForm.unit_id,
        source_module: journalForm.source_module,
        source_reference: journalForm.source_reference,
        description: journalForm.description || 'Manual Journal Voucher',
        lines: journalForm.lines.map((l) => {
          const acc = accounts.find((a) => a.account_code === l.account_code);
          return {
            account_code: l.account_code,
            account_name: acc?.account_name || 'Account',
            debit: Number(l.debit || 0),
            credit: Number(l.credit || 0),
            description: l.description || journalForm.description,
          };
        }),
      });
      setIsJournalModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to post journal entry');
    } finally {
      setSubmitting(false);
    }
  };

  // Calculations for active forms
  const invoiceSubtotal = invoiceForm.lines.reduce((s, l) => s + Number(l.quantity || 0) * Number(l.unit_price || 0), 0);
  const invoiceTax = invoiceForm.lines.reduce((s, l) => s + (Number(l.quantity || 0) * Number(l.unit_price || 0) * Number(l.tax_percent || 0)) / 100, 0);
  const invoiceTotal = invoiceSubtotal + invoiceTax;

  const billSubtotal = billForm.lines.reduce((s, l) => s + Number(l.quantity || 0) * Number(l.unit_price || 0), 0);
  const billTax = billForm.lines.reduce((s, l) => s + (Number(l.quantity || 0) * Number(l.unit_price || 0) * Number(l.tax_percent || 0)) / 100, 0);
  const billTotal = billSubtotal + billTax;

  const jDeb = journalForm.lines.reduce((s, l) => s + Number(l.debit || 0), 0);
  const jCred = journalForm.lines.reduce((s, l) => s + Number(l.credit || 0), 0);
  const isJournalBalanced = Math.abs(jDeb - jCred) <= 0.01 && jDeb > 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <IndianRupee className="w-7 h-7 text-purple-600" />
            Billing & Finance Operations Hub
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            End-to-end sales invoicing (AR), vendor bills (AP), disbursements, receipts, balanced double-entry vouchers, and Trial Balance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canCreate && (
            <div className="flex items-center gap-2 flex-wrap">
              {activeTab === 'invoices' && (
                <Button size="sm" onClick={() => setIsInvoiceModalOpen(true)} className="bg-purple-600 hover:bg-purple-700 text-white flex items-center gap-1.5">
                  <Plus className="w-4 h-4" /> Create Sales Invoice (AR)
                </Button>
              )}
              {activeTab === 'bills' && (
                <Button size="sm" onClick={() => setIsBillModalOpen(true)} className="bg-amber-600 hover:bg-amber-700 text-white flex items-center gap-1.5">
                  <Plus className="w-4 h-4" /> Record Supplier Bill (AP)
                </Button>
              )}
              {activeTab === 'payments' && (
                <Button size="sm" onClick={() => setIsPaymentModalOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5">
                  <Plus className="w-4 h-4" /> Record Payment / Receipt
                </Button>
              )}
              {activeTab === 'journals' && (
                <Button size="sm" onClick={() => setIsJournalModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5">
                  <Plus className="w-4 h-4" /> New Journal Voucher (JV)
                </Button>
              )}
            </div>
          )}
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading} className="flex items-center gap-1.5">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Financial KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-white border-[#E7E5DE] shadow-xs">
          <span className="text-xs font-medium text-slate-500 block truncate">Outstanding Receivables (AR)</span>
          <span className="text-xl font-bold text-blue-600 mt-1 block">
            ₹{(summary?.total_receivables || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
        </Card>
        <Card className="p-4 bg-white border-[#E7E5DE] shadow-xs">
          <span className="text-xs font-medium text-slate-500 block truncate">Outstanding Payables (AP)</span>
          <span className="text-xl font-bold text-amber-600 mt-1 block">
            ₹{(summary?.total_payables || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
        </Card>
        <Card className="p-4 bg-white border-[#E7E5DE] shadow-xs">
          <span className="text-xs font-medium text-slate-500 block truncate">Cash & Bank Balance</span>
          <span className="text-xl font-bold text-emerald-600 mt-1 block">
            ₹{(summary?.cash_bank_balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
        </Card>
        <Card className="p-4 bg-white border-[#E7E5DE] shadow-xs">
          <span className="text-xs font-medium text-slate-500 block truncate">Active QC Payment Holds</span>
          <span className="text-xl font-bold text-rose-600 mt-1 block flex items-center gap-1.5">
            <ShieldAlert className="w-5 h-5 text-rose-500" />
            {summary?.qc_holds_count || 0}
          </span>
        </Card>
      </div>

      {/* Tab Selection */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-[#E7E5DE]">
        {[
          { id: 'invoices', label: 'Sales Invoices (AR)', icon: Receipt },
          { id: 'bills', label: 'Supplier Bills (AP)', icon: FileText },
          { id: 'payments', label: 'Disbursements & Receipts', icon: CreditCard },
          { id: 'journals', label: 'Journal Vouchers', icon: Layers },
          { id: 'trial_balance', label: 'Trial Balance & Balancing', icon: Scale },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive ? 'bg-purple-600 text-white shadow-sm' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content Tables */}
      <Card className="p-0 overflow-hidden border-[#E7E5DE] shadow-xs">
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-purple-500" />
            Loading financial records...
          </div>
        ) : activeTab === 'invoices' ? (
          <div className="overflow-x-auto">
            <div className="p-3 bg-slate-50 border-b border-[#E7E5DE] flex justify-between items-center text-xs text-slate-600">
              <span className="font-semibold">Customer Accounts Receivable (AR) Invoices</span>
              {canCreate && (
                <Button size="sm" onClick={() => setIsInvoiceModalOpen(true)} className="h-7 text-xs bg-purple-600 text-white">
                  + New Invoice
                </Button>
              )}
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-[#E7E5DE]">
                <tr>
                  <th className="py-3 px-4">Invoice #</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Linked Project</th>
                  <th className="py-3 px-4">Unit</th>
                  <th className="py-3 px-4">Total (₹)</th>
                  <th className="py-3 px-4">Paid (₹)</th>
                  <th className="py-3 px-4">Balance (₹)</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.length === 0 ? (
                  <tr><td colSpan={9} className="py-8 text-center text-slate-400">No invoices recorded.</td></tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-bold text-slate-900">{inv.invoice_number}</td>
                      <td className="py-3 px-4 text-slate-500">{inv.invoice_date}</td>
                      <td className="py-3 px-4 font-medium text-slate-800">{inv.customer_name}</td>
                      <td className="py-3 px-4 font-mono text-purple-700">{inv.project_code || '-'}</td>
                      <td className="py-3 px-4 text-slate-500">
                        {inv.unit_id === 'Unit_1' ? 'Unit 1' : inv.unit_id === 'Unit_2' ? 'Unit 2' : 'All Units'}
                      </td>
                      <td className="py-3 px-4 font-semibold">₹{(inv.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-4 text-emerald-600">₹{(inv.amount_paid || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-4 text-rose-600 font-semibold">
                        ₹{(inv.balance_due ?? inv.balance_amount ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          inv.status === 'PAID' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'bills' ? (
          <div className="overflow-x-auto">
            <div className="p-3 bg-slate-50 border-b border-[#E7E5DE] flex justify-between items-center text-xs text-slate-600">
              <span className="font-semibold">Supplier Bills & Material Procurement (AP)</span>
              {canCreate && (
                <Button size="sm" onClick={() => setIsBillModalOpen(true)} className="h-7 text-xs bg-amber-600 text-white">
                  + Record Bill
                </Button>
              )}
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-[#E7E5DE]">
                <tr>
                  <th className="py-3 px-4">Bill #</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Vendor</th>
                  <th className="py-3 px-4">Vendor Bill #</th>
                  <th className="py-3 px-4">Linked Project</th>
                  <th className="py-3 px-4">Total (₹)</th>
                  <th className="py-3 px-4">Balance (₹)</th>
                  <th className="py-3 px-4">QC Hold Status</th>
                  <th className="py-3 px-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {bills.length === 0 ? (
                  <tr><td colSpan={9} className="py-8 text-center text-slate-400">No supplier bills found.</td></tr>
                ) : (
                  bills.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-bold text-slate-900">{b.bill_number}</td>
                      <td className="py-3 px-4 text-slate-500">{b.bill_date}</td>
                      <td className="py-3 px-4 font-medium">{b.vendor_name}</td>
                      <td className="py-3 px-4 font-mono text-slate-600">{b.bill_number_vendor || '-'}</td>
                      <td className="py-3 px-4 font-mono text-purple-700">{b.project_code || b.po_reference || '-'}</td>
                      <td className="py-3 px-4 font-semibold">₹{(b.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-4 text-rose-600 font-semibold">
                        ₹{(b.balance_due ?? b.balance_amount ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4">
                        {b.has_qc_hold ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 flex items-center gap-1 w-fit">
                            <Lock className="w-3 h-3" /> QC PAYMENT HOLD
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1 w-fit">
                            <CheckCircle2 className="w-3 h-3" /> RELEASED / CLEAR
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {b.has_qc_hold && canApprove && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={releaseLoading === b.id}
                            onClick={() => handleReleaseQCHold(b.id)}
                            className="text-[11px] py-1 px-2 border-rose-300 text-rose-700 hover:bg-rose-50"
                          >
                            Release Hold
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'payments' ? (
          <div className="overflow-x-auto">
            <div className="p-3 bg-slate-50 border-b border-[#E7E5DE] flex justify-between items-center text-xs text-slate-600">
              <span className="font-semibold">Disbursements & Customer Receipts</span>
              {canCreate && (
                <Button size="sm" onClick={() => setIsPaymentModalOpen(true)} className="h-7 text-xs bg-emerald-600 text-white">
                  + Record Payment / Receipt
                </Button>
              )}
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-[#E7E5DE]">
                <tr>
                  <th className="py-3 px-4">Payment #</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Party</th>
                  <th className="py-3 px-4">Linked Project</th>
                  <th className="py-3 px-4">Mode / Ref</th>
                  <th className="py-3 px-4">Amount (₹)</th>
                  <th className="py-3 px-4">Voucher</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payments.length === 0 ? (
                  <tr><td colSpan={8} className="py-8 text-center text-slate-400">No payment transactions recorded.</td></tr>
                ) : (
                  payments.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-bold text-slate-900">{p.payment_number}</td>
                      <td className="py-3 px-4 text-slate-500">{p.payment_date}</td>
                      <td className="py-3 px-4 font-semibold">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                          p.payment_type === 'CUSTOMER_RECEIPT' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {p.payment_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-medium">{p.entity_name || p.party_name || '-'}</td>
                      <td className="py-3 px-4 font-mono text-purple-700">{p.project_code || '-'}</td>
                      <td className="py-3 px-4 text-slate-500">{p.payment_method || p.payment_mode || 'BANK'}</td>
                      <td className="py-3 px-4 font-semibold text-emerald-600">
                        ₹{(p.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 font-mono text-purple-600">{p.journal_entry_id ? 'VOUCHER-LINKED' : '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'journals' ? (
          <div className="overflow-x-auto">
            <div className="p-3 bg-slate-50 border-b border-[#E7E5DE] flex justify-between items-center text-xs text-slate-600">
              <span className="font-semibold">General Ledger Double-Entry Journal Vouchers</span>
              {canCreate && (
                <Button size="sm" onClick={() => setIsJournalModalOpen(true)} className="h-7 text-xs bg-indigo-600 text-white">
                  + New Journal Voucher
                </Button>
              )}
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-[#E7E5DE]">
                <tr>
                  <th className="py-3 px-4">Entry #</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Debit (₹)</th>
                  <th className="py-3 px-4">Credit (₹)</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {journals.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No journal vouchers found.</td></tr>
                ) : (
                  journals.map((j) => (
                    <tr key={j.id} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-bold text-slate-900">{j.entry_number}</td>
                      <td className="py-3 px-4 text-slate-500">{j.entry_date}</td>
                      <td className="py-3 px-4 font-semibold text-purple-600">{j.source_module}</td>
                      <td className="py-3 px-4 text-slate-600">{j.description}</td>
                      <td className="py-3 px-4 font-mono font-semibold">₹{(j.total_debit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-4 font-mono font-semibold">₹{(j.total_credit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          j.status === 'POSTED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {j.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#E7E5DE]">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Scale className="w-4 h-4 text-purple-600" />
                Trial Balance & Double-Entry Balancing Verification
              </h3>
              {trialBalance?.is_balanced ? (
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> BALANCED (Σ Debit = Σ Credit)
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> UNBALANCED
                </span>
              )}
            </div>

            <div className="overflow-x-auto border border-[#E7E5DE] rounded-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-[#E7E5DE]">
                  <tr>
                    <th className="py-2.5 px-3">Code</th>
                    <th className="py-2.5 px-3">Account Name</th>
                    <th className="py-2.5 px-3">Classification</th>
                    <th className="py-2.5 px-3 text-right">Debit (₹)</th>
                    <th className="py-2.5 px-3 text-right">Credit (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(() => {
                    const accountsList = trialBalance?.accounts || trialBalance?.lines || [];
                    if (accountsList.length === 0) {
                      return (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-400">
                            No ledger transactions recorded for this period yet.
                          </td>
                        </tr>
                      );
                    }
                    return accountsList.map((acc) => (
                      <tr key={acc.account_code}>
                        <td className="py-2 px-3 font-mono font-bold text-purple-600">{acc.account_code}</td>
                        <td className="py-2 px-3 font-medium">{acc.account_name}</td>
                        <td className="py-2 px-3 text-slate-400">{acc.account_type}</td>
                        <td className="py-2 px-3 text-right font-mono">
                          {acc.debit > 0 ? `₹${acc.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                        </td>
                        <td className="py-2 px-3 text-right font-mono">
                          {acc.credit > 0 ? `₹${acc.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                        </td>
                      </tr>
                    ));
                  })()}
                </tbody>
                <tfoot className="bg-slate-100 font-bold border-t border-[#E7E5DE]">
                  <tr>
                    <td colSpan={3} className="py-3 px-3 uppercase tracking-wider text-right">Total:</td>
                    <td className="py-3 px-3 text-right font-mono text-purple-700">
                      ₹{(trialBalance?.total_debit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-purple-700">
                      ₹{(trialBalance?.total_credit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </Card>

      {/* ========================================================================= */}
      {/* 1. Modal: Create Sales Invoice (AR) */}
      {/* ========================================================================= */}
      <Dialog isOpen={isInvoiceModalOpen} onClose={() => setIsInvoiceModalOpen(false)} title="Create Customer Sales Invoice (AR)" maxWidth="lg">
        <form onSubmit={handleCreateInvoice} className="space-y-4 text-xs">
          {formError && <div className="p-2.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">{formError}</div>}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="font-semibold block mb-1">Customer *</label>
              <select
                required
                value={invoiceForm.customer_id}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, customer_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">Select Customer...</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold block mb-1">Link Lead / Project (Optional)</label>
              <select
                value={invoiceForm.project_id}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, project_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">No Project (General Invoice)</option>
                {leads.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} - {l.company_name} ({l.machine_interest || 'Project'})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold block mb-1">Facility Unit</label>
              <select
                value={invoiceForm.unit_id}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, unit_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="Unit_1">Unit 1 (Machining)</option>
                <option value="Unit_2">Unit 2 (Assembly & QC)</option>
                <option value="BOTH">Both Facilities</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold block mb-1">Invoice Date</label>
              <input
                type="date"
                required
                value={invoiceForm.invoice_date}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, invoice_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Due Date</label>
              <input
                type="date"
                required
                value={invoiceForm.due_date}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, due_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
          </div>

          {/* Line items */}
          <div className="border rounded-lg p-3 bg-slate-50 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-700">Line Items</span>
              <button
                type="button"
                onClick={() =>
                  setInvoiceForm({
                    ...invoiceForm,
                    lines: [...invoiceForm.lines, { item_code: '', description: '', quantity: 1, unit_price: 0, tax_percent: 18 }],
                  })
                }
                className="text-purple-600 hover:text-purple-800 font-semibold"
              >
                + Add Item
              </button>
            </div>
            {invoiceForm.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-white p-2 rounded border">
                <div className="col-span-3">
                  <select
                    value={line.item_code}
                    onChange={(e) => {
                      const selectedCode = e.target.value;
                      const prod = products.find((p) => p.code === selectedCode);
                      const mat = rawMaterials.find((r) => r.code === selectedCode);
                      const item = prod || mat;
                      const newLines = [...invoiceForm.lines];
                      newLines[idx].item_code = selectedCode;
                      if (item) {
                        newLines[idx].description = item.name;
                        const price = (item as any).selling_price ?? (item as any).standard_cost ?? 0;
                        if (price) newLines[idx].unit_price = price;
                      }
                      setInvoiceForm({ ...invoiceForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  >
                    <option value="">Select Item / SKU...</option>
                    <optgroup label="Finished Machinery & Equipment">
                      {products.map((p) => (
                        <option key={p.id || p.code} value={p.code}>
                          {p.code} - {p.name} {p.selling_price ? `(₹${p.selling_price.toLocaleString('en-IN')})` : ''}
                        </option>
                      ))}
                    </optgroup>
                    <optgroup label="Materials, Spares & Components">
                      {rawMaterials.map((r) => (
                        <option key={r.id || r.code} value={r.code}>
                          {r.code} - {r.name} {r.standard_cost ? `(₹${r.standard_cost.toLocaleString('en-IN')})` : ''}
                        </option>
                      ))}
                    </optgroup>
                  </select>
                </div>
                <div className="col-span-3">
                  <input
                    type="text"
                    placeholder="Description"
                    value={line.description}
                    onChange={(e) => {
                      const newLines = [...invoiceForm.lines];
                      newLines[idx].description = e.target.value;
                      setInvoiceForm({ ...invoiceForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    min="1"
                    placeholder="Qty"
                    value={line.quantity}
                    onChange={(e) => {
                      const newLines = [...invoiceForm.lines];
                      newLines[idx].quantity = Number(e.target.value);
                      setInvoiceForm({ ...invoiceForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    min="0"
                    placeholder="Price (₹)"
                    value={line.unit_price}
                    onChange={(e) => {
                      const newLines = [...invoiceForm.lines];
                      newLines[idx].unit_price = Number(e.target.value);
                      setInvoiceForm({ ...invoiceForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-1 text-right text-xs font-mono font-bold">
                  ₹{(line.quantity * line.unit_price * (1 + line.tax_percent / 100)).toFixed(0)}
                </div>
                <div className="col-span-1 text-center">
                  {invoiceForm.lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newLines = invoiceForm.lines.filter((_, i) => i !== idx);
                        setInvoiceForm({ ...invoiceForm, lines: newLines });
                      }}
                      className="text-rose-500 hover:text-rose-700"
                    >
                      <Trash2 className="w-3.5 h-3.5 mx-auto" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div className="text-right text-xs pt-2 space-y-0.5 font-mono">
              <div>Subtotal: ₹{invoiceSubtotal.toFixed(2)}</div>
              <div>GST (18%): ₹{invoiceTax.toFixed(2)}</div>
              <div className="font-bold text-sm text-purple-700">Total Invoice Amount: ₹{invoiceTotal.toFixed(2)}</div>
            </div>
          </div>

          <div>
            <label className="font-semibold block mb-1">Notes / Terms</label>
            <input
              type="text"
              placeholder="e.g. 50% advance received, balance upon dispatch"
              value={invoiceForm.notes}
              onChange={(e) => setInvoiceForm({ ...invoiceForm, notes: e.target.value })}
              className="w-full border rounded-lg p-2"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsInvoiceModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="bg-purple-600 hover:bg-purple-700 text-white">
              {submitting ? 'Posting...' : 'Create & Post Invoice'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ========================================================================= */}
      {/* 2. Modal: Create Supplier Bill (AP) */}
      {/* ========================================================================= */}
      <Dialog isOpen={isBillModalOpen} onClose={() => setIsBillModalOpen(false)} title="Record Supplier / Material Bill (AP)" maxWidth="lg">
        <form onSubmit={handleCreateBill} className="space-y-4 text-xs">
          {formError && <div className="p-2.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">{formError}</div>}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="font-semibold block mb-1">Supplier / Vendor *</label>
              <select
                required
                value={billForm.vendor_id}
                onChange={(e) => setBillForm({ ...billForm, vendor_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">Select Supplier...</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold block mb-1">Vendor Bill / Invoice # *</label>
              <input
                type="text"
                required
                placeholder="e.g. VEN-INV-2026-90"
                value={billForm.bill_number_vendor}
                onChange={(e) => setBillForm({ ...billForm, bill_number_vendor: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>

            <div>
              <label className="font-semibold block mb-1">Link Lead / Project (Optional)</label>
              <select
                value={billForm.project_id}
                onChange={(e) => setBillForm({ ...billForm, project_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">No Project (General Bill)</option>
                {leads.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} - {l.company_name} ({l.machine_interest || 'Project'})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="font-semibold block mb-1">Bill Date</label>
              <input
                type="date"
                required
                value={billForm.bill_date}
                onChange={(e) => setBillForm({ ...billForm, bill_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Due Date</label>
              <input
                type="date"
                required
                value={billForm.due_date}
                onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Facility Unit</label>
              <select
                value={billForm.unit_id}
                onChange={(e) => setBillForm({ ...billForm, unit_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="Unit_1">Unit 1</option>
                <option value="Unit_2">Unit 2</option>
                <option value="BOTH">Both</option>
              </select>
            </div>
          </div>

          {/* QC Hold Enforcement */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2">
            <label className="flex items-center gap-2 cursor-pointer font-semibold text-amber-900">
              <input
                type="checkbox"
                checked={billForm.has_qc_hold}
                onChange={(e) => setBillForm({ ...billForm, has_qc_hold: e.target.checked })}
                className="rounded text-amber-600"
              />
              Place under Quality Control (QC) Payment Hold
            </label>
            {billForm.has_qc_hold && (
              <input
                type="text"
                placeholder="Specify QC issue / reason for payment withholding..."
                value={billForm.qc_hold_reason}
                onChange={(e) => setBillForm({ ...billForm, qc_hold_reason: e.target.value })}
                className="w-full border rounded p-2 text-xs bg-white"
              />
            )}
          </div>

          {/* Line items */}
          <div className="border rounded-lg p-3 bg-slate-50 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-700">Material Items</span>
              <button
                type="button"
                onClick={() =>
                  setBillForm({
                    ...billForm,
                    lines: [...billForm.lines, { item_code: '', description: '', quantity: 1, unit_price: 0, tax_percent: 18 }],
                  })
                }
                className="text-amber-600 hover:text-amber-800 font-semibold"
              >
                + Add Material
              </button>
            </div>
            {billForm.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-white p-2 rounded border">
                <div className="col-span-3">
                  <select
                    value={line.item_code}
                    onChange={(e) => {
                      const selectedCode = e.target.value;
                      const mat = rawMaterials.find((r) => r.code === selectedCode);
                      const prod = products.find((p) => p.code === selectedCode);
                      const item = mat || prod;
                      const newLines = [...billForm.lines];
                      newLines[idx].item_code = selectedCode;
                      if (item) {
                        newLines[idx].description = item.name;
                        const cost = (item as any).standard_cost ?? (item as any).selling_price ?? 0;
                        if (cost) newLines[idx].unit_price = cost;
                      }
                      setBillForm({ ...billForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  >
                    <option value="">Select Raw Material / SKU...</option>
                    <optgroup label="Raw Materials & Consumables">
                      {rawMaterials.map((r) => (
                        <option key={r.id || r.code} value={r.code}>
                          {r.code} - {r.name} {r.standard_cost ? `(Cost: ₹${r.standard_cost.toLocaleString('en-IN')})` : ''}
                        </option>
                      ))}
                    </optgroup>
                    <optgroup label="Equipment & Machinery Sub-assemblies">
                      {products.map((p) => (
                        <option key={p.id || p.code} value={p.code}>
                          {p.code} - {p.name} {p.standard_cost ? `(Cost: ₹${p.standard_cost.toLocaleString('en-IN')})` : ''}
                        </option>
                      ))}
                    </optgroup>
                  </select>
                </div>
                <div className="col-span-3">
                  <input
                    type="text"
                    placeholder="Description"
                    value={line.description}
                    onChange={(e) => {
                      const newLines = [...billForm.lines];
                      newLines[idx].description = e.target.value;
                      setBillForm({ ...billForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    min="1"
                    placeholder="Qty"
                    value={line.quantity}
                    onChange={(e) => {
                      const newLines = [...billForm.lines];
                      newLines[idx].quantity = Number(e.target.value);
                      setBillForm({ ...billForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    min="0"
                    placeholder="Rate (₹)"
                    value={line.unit_price}
                    onChange={(e) => {
                      const newLines = [...billForm.lines];
                      newLines[idx].unit_price = Number(e.target.value);
                      setBillForm({ ...billForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  />
                </div>
                <div className="col-span-1 text-right text-xs font-mono font-bold">
                  ₹{(line.quantity * line.unit_price * (1 + line.tax_percent / 100)).toFixed(0)}
                </div>
                <div className="col-span-1 text-center">
                  {billForm.lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newLines = billForm.lines.filter((_, i) => i !== idx);
                        setBillForm({ ...billForm, lines: newLines });
                      }}
                      className="text-rose-500 hover:text-rose-700"
                    >
                      <Trash2 className="w-3.5 h-3.5 mx-auto" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div className="text-right text-xs pt-2 space-y-0.5 font-mono">
              <div>Subtotal: ₹{billSubtotal.toFixed(2)}</div>
              <div>Input GST (18%): ₹{billTax.toFixed(2)}</div>
              <div className="font-bold text-sm text-amber-700">Total Supplier Bill: ₹{billTotal.toFixed(2)}</div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsBillModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="bg-amber-600 hover:bg-amber-700 text-white">
              {submitting ? 'Recording...' : 'Record Supplier Bill'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ========================================================================= */}
      {/* 3. Modal: Record Payment / Receipt */}
      {/* ========================================================================= */}
      <Dialog isOpen={isPaymentModalOpen} onClose={() => setIsPaymentModalOpen(false)} title="Record Payment / Receipt Transaction" maxWidth="md">
        <form onSubmit={handleCreatePayment} className="space-y-4 text-xs">
          {formError && <div className="p-2.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">{formError}</div>}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold block mb-1">Transaction Type</label>
              <select
                value={paymentForm.payment_type}
                onChange={(e) =>
                  setPaymentForm({
                    ...paymentForm,
                    payment_type: e.target.value as any,
                    entity_id: '',
                  })
                }
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="CUSTOMER_RECEIPT">Customer Receipt (Inflow)</option>
                <option value="VENDOR_PAYMENT">Vendor Disbursement (Outflow)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold block mb-1">
                {paymentForm.payment_type === 'CUSTOMER_RECEIPT' ? 'Customer *' : 'Vendor *'}
              </label>
              <select
                required
                value={paymentForm.entity_id}
                onChange={(e) => setPaymentForm({ ...paymentForm, entity_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">Select Party...</option>
                {paymentForm.payment_type === 'CUSTOMER_RECEIPT'
                  ? customers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code})
                      </option>
                    ))
                  : vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.code})
                      </option>
                    ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold block mb-1">Link Lead / Project (Optional)</label>
              <select
                value={paymentForm.project_id}
                onChange={(e) => setPaymentForm({ ...paymentForm, project_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="">No Project</option>
                {leads.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} - {l.company_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="font-semibold block mb-1">Ref Document (Invoice # / Bill #)</label>
              <input
                type="text"
                placeholder="e.g. INV-202610-0001 or BILL-202610-0001"
                value={paymentForm.reference_doc_number}
                onChange={(e) => setPaymentForm({ ...paymentForm, reference_doc_number: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="font-semibold block mb-1">Payment Method</label>
              <select
                value={paymentForm.payment_method}
                onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="BANK_TRANSFER">Bank Transfer (NEFT/RTGS)</option>
                <option value="UPI">UPI</option>
                <option value="CHEQUE">Cheque</option>
                <option value="CASH">Cash</option>
              </select>
            </div>
            <div>
              <label className="font-semibold block mb-1">Payment Date</label>
              <input
                type="date"
                required
                value={paymentForm.payment_date}
                onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Bank / Cash Account</label>
              <select
                value={paymentForm.bank_account_code}
                onChange={(e) => setPaymentForm({ ...paymentForm, bank_account_code: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="1010-BANK-HDFC">1010 - HDFC Bank Account</option>
                <option value="1020-BANK-SBI">1020 - SBI Bank Account</option>
                <option value="1000-CASH">1000 - Petty Cash</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold block mb-1">Transaction Ref / UTR / Cheque #</label>
              <input
                type="text"
                placeholder="UTR No / Cheque No"
                value={paymentForm.payment_reference}
                onChange={(e) => setPaymentForm({ ...paymentForm, payment_reference: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Amount (₹) *</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                required
                placeholder="Amount in INR"
                value={paymentForm.amount || ''}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: Number(e.target.value) })}
                className="w-full border rounded-lg p-2 font-mono font-bold text-emerald-600"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsPaymentModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              {submitting ? 'Recording...' : 'Record Payment / Receipt'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ========================================================================= */}
      {/* 4. Modal: Create Journal Voucher (JV) */}
      {/* ========================================================================= */}
      <Dialog isOpen={isJournalModalOpen} onClose={() => setIsJournalModalOpen(false)} title="New Double-Entry Journal Voucher (JV)" maxWidth="lg">
        <form onSubmit={handleCreateJournal} className="space-y-4 text-xs">
          {formError && <div className="p-2.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">{formError}</div>}

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="font-semibold block mb-1">Voucher Date</label>
              <input
                type="date"
                required
                value={journalForm.entry_date}
                onChange={(e) => setJournalForm({ ...journalForm, entry_date: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Source / Voucher Ref</label>
              <input
                type="text"
                required
                value={journalForm.source_reference}
                onChange={(e) => setJournalForm({ ...journalForm, source_reference: e.target.value })}
                className="w-full border rounded-lg p-2"
              />
            </div>
            <div>
              <label className="font-semibold block mb-1">Facility Unit</label>
              <select
                value={journalForm.unit_id}
                onChange={(e) => setJournalForm({ ...journalForm, unit_id: e.target.value })}
                className="w-full border rounded-lg p-2 bg-white"
              >
                <option value="Unit_1">Unit 1</option>
                <option value="Unit_2">Unit 2</option>
                <option value="BOTH">Both Facilities</option>
              </select>
            </div>
          </div>

          <div>
            <label className="font-semibold block mb-1">Voucher Description / Narration *</label>
            <input
              type="text"
              required
              placeholder="e.g. Month-end depreciation adjustment, bank interest, payroll accrual"
              value={journalForm.description}
              onChange={(e) => setJournalForm({ ...journalForm, description: e.target.value })}
              className="w-full border rounded-lg p-2"
            />
          </div>

          {/* Double-entry lines */}
          <div className="border rounded-lg p-3 bg-slate-50 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-slate-700">Ledger Accounts (Double-Entry Debit & Credit)</span>
              <button
                type="button"
                onClick={() =>
                  setJournalForm({
                    ...journalForm,
                    lines: [...journalForm.lines, { account_code: '1000-CASH', debit: 0, credit: 0, description: '' }],
                  })
                }
                className="text-indigo-600 hover:text-indigo-800 font-semibold"
              >
                + Add Line
              </button>
            </div>
            {journalForm.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-white p-2 rounded border">
                <div className="col-span-5">
                  <select
                    value={line.account_code}
                    onChange={(e) => {
                      const newLines = [...journalForm.lines];
                      newLines[idx].account_code = e.target.value;
                      setJournalForm({ ...journalForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs"
                  >
                    {accounts.map((a) => (
                      <option key={a.id} value={a.account_code}>
                        {a.account_code} - {a.account_name} ({a.account_type})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-3">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Debit (₹)"
                    value={line.debit || ''}
                    onChange={(e) => {
                      const newLines = [...journalForm.lines];
                      newLines[idx].debit = Number(e.target.value);
                      if (Number(e.target.value) > 0) newLines[idx].credit = 0;
                      setJournalForm({ ...journalForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs font-mono font-semibold"
                  />
                </div>
                <div className="col-span-3">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Credit (₹)"
                    value={line.credit || ''}
                    onChange={(e) => {
                      const newLines = [...journalForm.lines];
                      newLines[idx].credit = Number(e.target.value);
                      if (Number(e.target.value) > 0) newLines[idx].debit = 0;
                      setJournalForm({ ...journalForm, lines: newLines });
                    }}
                    className="w-full border rounded p-1 text-xs font-mono font-semibold"
                  />
                </div>
                <div className="col-span-1 text-center">
                  {journalForm.lines.length > 2 && (
                    <button
                      type="button"
                      onClick={() => {
                        const newLines = journalForm.lines.filter((_, i) => i !== idx);
                        setJournalForm({ ...journalForm, lines: newLines });
                      }}
                      className="text-rose-500 hover:text-rose-700"
                    >
                      <Trash2 className="w-3.5 h-3.5 mx-auto" />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {/* Balancing status banner */}
            <div className="flex justify-between items-center pt-2 border-t text-xs">
              <div className="font-mono">
                Debit: <span className="font-bold">₹{jDeb.toFixed(2)}</span> | Credit:{' '}
                <span className="font-bold">₹{jCred.toFixed(2)}</span>
              </div>
              <div>
                {isJournalBalanced ? (
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> BALANCED
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Diff: ₹{Math.abs(jDeb - jCred).toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsJournalModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting || !isJournalBalanced}
              className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50"
            >
              {submitting ? 'Posting...' : 'Post Journal Voucher'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
