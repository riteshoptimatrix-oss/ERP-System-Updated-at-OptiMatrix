'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { wastageClient } from '@/services/wastage-client';
import { masterClient } from '@/services/master-client';
import { productionClient } from '@/services/production-client';
import {
  ScrapEntry,
  ScrapCategory,
  ScrapDisposition,
  PlannedVsActualWastage,
  WastageSummary,
} from '@/types/wastage';
import { RawMaterial } from '@/types/master';
import { ProductionOrder } from '@/types/production';
import {
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Plus,
  BarChart2,
  IndianRupee,
  Layers,
  Search,
  Check,
  X,
} from 'lucide-react';

const CATEGORY_LABELS: Record<ScrapCategory, string> = {
  CUTTING_OFFCUT: 'Cutting Offcut',
  MACHINING_SWARF: 'Machining Swarf',
  REJECTED_DEFECTIVE: 'Rejected Defective',
  TOOLING_SETUP: 'Tooling / Setup',
  DAMAGE_IN_HANDLING: 'Handling Damage',
  CONTAMINATION: 'Contamination',
  OBSOLETE_MATERIAL: 'Obsolete Material',
  OTHER: 'Other Scrap',
};

const DISPOSITION_LABELS: Record<ScrapDisposition, string> = {
  DISPOSAL: 'Scrap Disposal',
  RECYCLE_INTERNAL: 'Internal Recycle',
  SCRAP_YARD_SALE: 'Scrap Yard Sale',
  HOLD_REVIEW: 'Hold for Review',
};

export default function WastageScrapPage() {
  const { activeUnit, hasPermission } = useAuth();
  const canCreate = hasPermission('wastage', 'create');
  const canApprove = hasPermission('wastage', 'approve');

  // KPI Metrics
  const [metrics, setMetrics] = useState<WastageSummary | null>(null);

  // Entries State
  const [entries, setEntries] = useState<ScrapEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  // Master & Reference Data
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [productionOrders, setProductionOrders] = useState<ProductionOrder[]>([]);

  // Modals State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);

  const [selectedEntry, setSelectedEntry] = useState<ScrapEntry | null>(null);
  const [comparisonData, setComparisonData] = useState<PlannedVsActualWastage | null>(null);

  const [approvalNotes, setApprovalNotes] = useState('');
  const [approvalDisposition, setApprovalDisposition] = useState<ScrapDisposition>('SCRAP_YARD_SALE');
  const [rejectionReason, setRejectionReason] = useState('');

  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [form, setForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    unit_id: (activeUnit === 'Unit_2' ? 'Unit_2' : 'Unit_1') as 'Unit_1' | 'Unit_2',
    production_order_id: '',
    item_id: '',
    scrap_category: 'MACHINING_SWARF' as ScrapCategory,
    quantity: 1,
    uom: 'KG',
    reason: '',
    disposition: 'HOLD_REVIEW' as ScrapDisposition,
    operator_name: '',
    machine_id: '',
    notes: '',
  });

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setActionError(null);
    try {
      const unitParam = activeUnit && activeUnit !== 'BOTH' ? activeUnit : undefined;
      const [metricsRes, entriesRes, rawRes, ordersRes] = await Promise.all([
        wastageClient.getSummary(unitParam),
        wastageClient.listEntries({
          unit_id: unitParam,
          scrap_category: selectedCategory !== 'ALL' ? selectedCategory : undefined,
          status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
          search: searchQuery || undefined,
          page_size: 100,
        }),
        masterClient.list<RawMaterial>('materials', { page_size: 100 }).catch(() => ({ items: [] })),
        productionClient.listOrders({ unit_id: unitParam, page_size: 100 }).catch(() => ({ items: [] })),
      ]);

      setMetrics(metricsRes);
      setEntries(entriesRes.items || []);
      setMaterials(rawRes?.items || []);
      setProductionOrders(ordersRes?.items || []);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to load wastage data');
    } finally {
      setIsLoading(false);
    }
  }, [activeUnit, selectedCategory, selectedStatus, searchQuery]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Create Scrap
  const handleCreateScrap = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.item_id || !form.reason) {
      setActionError('Item selection and reason are required.');
      return;
    }

    const selectedMat = materials.find((m) => m.id === form.item_id || m.code === form.item_id);
    const selectedPo = productionOrders.find((p) => p.id === form.production_order_id || p.order_number === form.production_order_id);

    setIsSubmitting(true);
    setActionError(null);
    try {
      await wastageClient.createEntry({
        entry_date: form.entry_date,
        unit_id: form.unit_id,
        production_order_id: selectedPo?.id || (form.production_order_id || undefined),
        production_order_number: selectedPo?.order_number || undefined,
        item_id: selectedMat?.id || form.item_id,
        item_code: selectedMat?.code || form.item_id,
        item_name: selectedMat?.name || 'Item',
        item_type: 'RAW_MATERIAL',
        scrap_category: form.scrap_category,
        quantity: Number(form.quantity),
        uom: form.uom,
        reason: form.reason,
        disposition: form.disposition,
        operator_name: form.operator_name || undefined,
        machine_id: form.machine_id || undefined,
        notes: form.notes || undefined,
      });

      setActionSuccess('Scrap entry recorded successfully.');
      setShowCreateModal(false);
      setForm({
        entry_date: new Date().toISOString().split('T')[0],
        unit_id: (activeUnit === 'Unit_2' ? 'Unit_2' : 'Unit_1') as 'Unit_1' | 'Unit_2',
        production_order_id: '',
        item_id: '',
        scrap_category: 'MACHINING_SWARF',
        quantity: 1,
        uom: 'KG',
        reason: '',
        disposition: 'HOLD_REVIEW',
        operator_name: '',
        machine_id: '',
        notes: '',
      });
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to record scrap entry');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Approve
  const handleApprove = async () => {
    if (!selectedEntry) return;
    setIsSubmitting(true);
    setActionError(null);
    try {
      await wastageClient.approveEntry(selectedEntry.id, approvalNotes, approvalDisposition);
      setActionSuccess(`Scrap entry ${selectedEntry.entry_number} approved.`);
      setShowApproveModal(false);
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Approval failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Reject
  const handleReject = async () => {
    if (!selectedEntry || !rejectionReason) {
      setActionError('Rejection reason is required.');
      return;
    }
    setIsSubmitting(true);
    setActionError(null);
    try {
      await wastageClient.rejectEntry(selectedEntry.id, rejectionReason);
      setActionSuccess(`Scrap entry ${selectedEntry.entry_number} rejected.`);
      setShowRejectModal(false);
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Rejection failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Load Comparison Data
  const handleFetchComparison = async (orderId: string) => {
    if (!orderId) return;
    setActionError(null);
    try {
      const data = await wastageClient.getPlannedVsActual(orderId);
      setComparisonData(data);
      setShowComparisonModal(true);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to calculate comparison');
    }
  };

  const columns: Column<ScrapEntry>[] = [
    {
      key: 'entry_number',
      header: 'Entry #',
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-[#315C45] text-blue-400">
          {row.entry_number}
        </span>
      ),
    },
    {
      key: 'entry_date',
      header: 'Date',
      render: (row) => <span>{row.entry_date}</span>,
    },
    {
      key: 'unit_id',
      header: 'Unit',
      render: (row) => (
        <Badge variant={row.unit_id === 'Unit_1' ? 'neutral' : 'warning'}>
          {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : row.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
        </Badge>
      ),
    },
    {
      key: 'production_order_number',
      header: 'Order #',
      render: (row) => (
        row.production_order_number ? (
          <button
            onClick={() => handleFetchComparison(row.production_order_id || row.production_order_number || '')}
            className="text-xs text-[#315C45] hover:underline flex items-center gap-1 font-mono"
            title="View planned vs actual comparison"
          >
            {row.production_order_number}
            <BarChart2 className="w-3 h-3" />
          </button>
        ) : (
          <span className="text-slate-400 text-xs italic">Independent</span>
        )
      ),
    },
    {
      key: 'item_code',
      header: 'Material / Scrap',
      render: (row) => (
        <div>
          <div className="font-medium text-xs text-slate-900 ">{row.item_name}</div>
          <div className="font-mono text-[11px] text-slate-400">{row.item_code}</div>
        </div>
      ),
    },
    {
      key: 'scrap_category',
      header: 'Category',
      render: (row) => (
        <span className="text-xs font-medium text-slate-700 ">
          {CATEGORY_LABELS[row.scrap_category as ScrapCategory] || row.scrap_category}
        </span>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      render: (row) => (
        <span className="font-semibold text-xs text-slate-800 ">
          {row.quantity} {row.uom}
        </span>
      ),
    },
    {
      key: 'total_cost',
      header: 'Financial Loss',
      render: (row) => (
        <span className="text-xs font-semibold text-rose-600 text-rose-400">
          ₹{row.total_cost.toLocaleString()}
        </span>
      ),
    },
    {
      key: 'disposition',
      header: 'Disposition',
      render: (row) => (
        <span className="text-[11px] text-slate-600 ">
          {DISPOSITION_LABELS[row.disposition as ScrapDisposition] || row.disposition}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => {
        let variant: 'neutral' | 'success' | 'warning' | 'error' = 'neutral';
        if (row.status === 'APPROVED') variant = 'success';
        if (row.status === 'SUBMITTED') variant = 'warning';
        if (row.status === 'REJECTED') variant = 'error';
        return <Badge variant={variant}>{row.status}</Badge>;
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex items-center gap-1">
          {canApprove && row.status === 'SUBMITTED' && (
            <>
              <button
                onClick={() => {
                  setSelectedEntry(row);
                  setShowApproveModal(true);
                }}
                className="p-1 text-emerald-600 hover:bg-emerald-50 hover:bg-emerald-950/30 rounded"
                title="Approve Scrap"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setSelectedEntry(row);
                  setShowRejectModal(true);
                }}
                className="p-1 text-rose-600 hover:bg-rose-50 hover:bg-rose-950/30 rounded"
                title="Reject Scrap"
              >
                <X className="w-4 h-4" />
              </button>
            </>
          )}
          {row.production_order_id && (
            <button
              onClick={() => handleFetchComparison(row.production_order_id || '')}
              className="p-1 text-[#315C45] hover:bg-[#EAF0E9] hover:bg-blue-950/30 rounded"
              title="Compare with BOM allowance"
            >
              <BarChart2 className="w-4 h-4" />
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900  flex items-center gap-2">
            <Trash2 className="w-7 h-7 text-amber-500" />
            Wastage & Scrap Tracking
          </h1>
          <p className="text-sm text-slate-500 ">
            Shop-floor scrap logs, material costing, and planned vs. actual wastage reconciliation
          </p>
        </div>

        <div className="flex gap-2">
          {canCreate && (
            <Button
              variant="primary"
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Log Scrap Entry
            </Button>
          )}
        </div>
      </div>

      {/* Feedback Alerts */}
      {actionSuccess && (
        <div className="p-3 bg-emerald-50 bg-emerald-950/30 border border-emerald-200 border-emerald-800 rounded-lg text-xs text-emerald-800 text-emerald-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            {actionSuccess}
          </span>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-3 bg-rose-50 bg-rose-950/30 border border-rose-200 border-rose-800 rounded-lg text-xs text-rose-800 text-rose-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {actionError}
          </span>
          <button onClick={() => setActionError(null)} className="text-rose-600 hover:text-rose-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Total Entries</span>
            <Layers className="w-5 h-5 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900 ">
            {metrics?.total_scrap_entries || 0}
          </div>
          <span className="text-xs text-slate-500">Across recorded batches</span>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Pending Approvals</span>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-600 text-amber-400">
            {metrics?.pending_approvals || 0}
          </div>
          <span className="text-xs text-slate-500">Awaiting supervisor sign-off</span>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Approved Scrap</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-600 text-emerald-400">
            {metrics?.approved_entries || 0}
          </div>
          <span className="text-xs text-slate-500">Authorized disposal/recycling</span>
        </Card>

        <Card className="p-4 border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Total Financial Loss</span>
            <IndianRupee className="w-5 h-5 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-600 text-rose-400">
            ₹{(metrics?.total_scrap_cost || 0).toLocaleString()}
          </div>
          <span className="text-xs text-slate-500">At standard component valuation</span>
        </Card>
      </div>

      {/* Category Breakdown Bar */}
      {metrics?.category_breakdown && metrics.category_breakdown.length > 0 && (
        <Card className="p-4">
          <h3 className="text-xs font-bold text-slate-400 uppercase mb-3">Scrap Distribution by Category</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {metrics.category_breakdown.map((cat) => (
              <div key={cat.category} className="p-3 bg-slate-50 /50 rounded-lg">
                <span className="text-xs font-medium text-slate-600  block truncate">
                  {CATEGORY_LABELS[cat.category as ScrapCategory] || cat.category}
                </span>
                <div className="text-sm font-bold text-slate-900  mt-1">
                  {cat.total_quantity} units
                </div>
                <div className="text-[11px] text-rose-500 font-semibold">
                  ₹{cat.total_cost.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Filters & Scrap Table */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-3 mb-4 justify-between">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by entry #, material, order #..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg focus:outline-hidden focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div className="flex gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="py-1.5 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              <option value="ALL">All Scrap Categories</option>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="py-1.5 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>

        <DataTable
          columns={columns}
          data={entries}
          isLoading={isLoading}
          keyExtractor={(row) => row.id}
        />
      </Card>

      {/* ------------------------------------------------------------- */}
      {/* Log Scrap Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Log Daily Scrap / Wastage Entry"
      >
        <form onSubmit={handleCreateScrap} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Entry Date
              </label>
              <input
                type="date"
                value={form.entry_date}
                onChange={(e) => setForm({ ...form, entry_date: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Manufacturing Unit
              </label>
              <select
                value={form.unit_id}
                onChange={(e) => setForm({ ...form, unit_id: e.target.value as 'Unit_1' | 'Unit_2' })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                <option value="Unit_1">Unit 1 — Heavy Machining</option>
                <option value="Unit_2">Unit 2 — Assembly &amp; QC</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Production Order (Optional)
            </label>
            <select
              value={form.production_order_id}
              onChange={(e) => setForm({ ...form, production_order_id: e.target.value })}
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              <option value="">-- No Production Order (Independent Floor Scrap) --</option>
              {productionOrders.map((po) => (
                <option key={po.id} value={po.id}>
                  {po.order_number} - {po.product_name} ({po.unit_id === 'Unit_1' ? 'Unit 1' : po.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Raw Material / Component *
            </label>
            <select
              value={form.item_id}
              onChange={(e) => {
                const mat = materials.find((m) => m.id === e.target.value);
                setForm({
                  ...form,
                  item_id: e.target.value,
                  uom: mat?.uom || 'KG',
                });
              }}
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              required
            >
              <option value="">-- Select Material --</option>
              {materials.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.code} - {m.name} ({m.uom})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Category
              </label>
              <select
                value={form.scrap_category}
                onChange={(e) => setForm({ ...form, scrap_category: e.target.value as ScrapCategory })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Quantity *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                UoM
              </label>
              <input
                type="text"
                value={form.uom}
                readOnly
                className="w-full py-2 px-3 text-xs bg-slate-100  border border-[#E7E5DE]  rounded-lg text-slate-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Reason / Defect Description *
            </label>
            <textarea
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              placeholder="e.g. Dimensions out of tolerance, cutting swarf, tooling chatter..."
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg h-16"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Operator Name
              </label>
              <input
                type="text"
                value={form.operator_name}
                onChange={(e) => setForm({ ...form, operator_name: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Machine / Workstation
              </label>
              <input
                type="text"
                value={form.machine_id}
                onChange={(e) => setForm({ ...form, machine_id: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? 'Recording...' : 'Submit Scrap Entry'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* Planned vs Actual Comparison Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showComparisonModal}
        onClose={() => setShowComparisonModal(false)}
        title={`Planned vs Actual Wastage: ${comparisonData?.order_number || ''}`}
      >
        {comparisonData && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2 p-3 bg-slate-50  rounded-lg text-xs">
              <div>
                <span className="text-slate-400 block">Product:</span>
                <span className="font-semibold">{comparisonData.product_name}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Production Plan / Actual:</span>
                <span className="font-semibold">{comparisonData.planned_production_qty} planned / {comparisonData.actual_produced_qty} produced</span>
              </div>
              <div>
                <span className="text-slate-400 block">Net Cost Variance:</span>
                <span className={`font-bold ${comparisonData.total_cost_variance > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                  {comparisonData.total_cost_variance > 0 ? '+' : ''}₹{comparisonData.total_cost_variance.toLocaleString()}
                </span>
              </div>
            </div>

            <div className="overflow-x-auto border border-[#E7E5DE]  rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100  text-slate-600 ">
                  <tr>
                    <th className="p-2">Component</th>
                    <th className="p-2">BOM Scrap %</th>
                    <th className="p-2">Planned Scrap</th>
                    <th className="p-2">Actual Scrap</th>
                    <th className="p-2">Variance</th>
                    <th className="p-2">Cost Variance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 divide-slate-800">
                  {comparisonData.components.map((comp) => (
                    <tr key={comp.material_id}>
                      <td className="p-2">
                        <div className="font-medium">{comp.material_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{comp.material_code}</div>
                      </td>
                      <td className="p-2">{comp.planned_scrap_percentage}%</td>
                      <td className="p-2">{comp.planned_scrap_quantity} {comp.uom}</td>
                      <td className="p-2 font-semibold">{comp.actual_scrap_quantity} {comp.uom}</td>
                      <td className="p-2">
                        <span className={`font-semibold ${comp.scrap_variance > 0 ? 'text-rose-500' : comp.scrap_variance < 0 ? 'text-emerald-500' : ''}`}>
                          {comp.scrap_variance > 0 ? `+${comp.scrap_variance}` : comp.scrap_variance} {comp.uom}
                        </span>
                      </td>
                      <td className="p-2 font-semibold">
                        <span className={comp.cost_variance > 0 ? 'text-rose-500' : comp.cost_variance < 0 ? 'text-emerald-500' : ''}>
                          {comp.cost_variance > 0 ? '+' : ''}₹{comp.cost_variance.toLocaleString()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end">
              <Button variant="primary" onClick={() => setShowComparisonModal(false)}>Close</Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* Approve Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        title={`Authorize Scrap Entry: ${selectedEntry?.entry_number || ''}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 ">
            Confirming authorization for {selectedEntry?.quantity} {selectedEntry?.uom} of {selectedEntry?.item_name}. Total financial loss: ₹{selectedEntry?.total_cost.toLocaleString()}.
          </p>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Final Disposition
            </label>
            <select
              value={approvalDisposition}
              onChange={(e) => setApprovalDisposition(e.target.value as ScrapDisposition)}
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              {Object.entries(DISPOSITION_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Approval Notes
            </label>
            <input
              type="text"
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="e.g. Weighbridge verified, transferred to yard"
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#EFEEE8] ">
            <Button variant="outline" onClick={() => setShowApproveModal(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleApprove} disabled={isSubmitting}>
              {isSubmitting ? 'Approving...' : 'Confirm Approval'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* Reject Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        title={`Reject Scrap Entry: ${selectedEntry?.entry_number || ''}`}
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Rejection Reason *
            </label>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Explain why this scrap record is rejected..."
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg h-20"
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#EFEEE8] ">
            <Button variant="outline" onClick={() => setShowRejectModal(false)}>Cancel</Button>
            <Button variant="danger" onClick={handleReject} disabled={isSubmitting}>
              {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
