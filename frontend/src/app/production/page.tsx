'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { productionClient } from '@/services/production-client';
import { masterClient } from '@/services/master-client';
import { bomClient } from '@/services/bom-client';
import {
  ProductionOrder,
  ProductionOrderStatus,
  ProductionDashboardSummary,
  ProductionVarianceReport,
  DailyProductionEntry,
  DailyProductionSummary,
} from '@/types/production';
import { FinishedProduct, Warehouse } from '@/types/master';
import { BOM } from '@/types/bom';
import {
  Cog,
  Layers,
  CheckCircle2,
  AlertCircle,
  Plus,
  Play,
  CheckCheck,
  BarChart3,
  Flame,
  Boxes,
  Truck,
  ArrowRight,
  ClipboardList,
  Download,
  Printer,
  Edit,
  RefreshCw,
  Calendar,
  Users,
  IndianRupee,
  Trash2,
  Search,
} from 'lucide-react';

export default function ProductionHubPage() {
  const { user, isLoading: authLoading, activeUnit, hasPermission } = useAuth();
  const canRead = hasPermission('production', 'read');
  const canCreate = hasPermission('production', 'create');
  const canUpdate = hasPermission('production', 'update');
  const canPost = hasPermission('production', 'post');

  // Active Tab: 'ORDERS' | 'DAILY'
  const [activeTab, setActiveTab] = useState<'ORDERS' | 'DAILY'>('ORDERS');

  // Sync tab with URL search params if navigated via ?tab=daily
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('tab') === 'daily') {
        setActiveTab('DAILY');
      }
    }
  }, []);

  // KPI Metrics
  const [metrics, setMetrics] = useState<ProductionDashboardSummary | null>(null);

  // Daily Production Planning & Actual State
  const [dailyLines, setDailyLines] = useState<DailyProductionEntry[]>([]);
  const [dailySummary, setDailySummary] = useState<DailyProductionSummary | null>(null);
  const [isLoadingDaily, setIsLoadingDaily] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('ALL');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [dailySearch, setDailySearch] = useState('');
  const [editingDaily, setEditingDaily] = useState<DailyProductionEntry | null>(null);
  const [showDailyEditModal, setShowDailyEditModal] = useState(false);
  const [showDailyCreateModal, setShowDailyCreateModal] = useState(false);
  const [isSavingDaily, setIsSavingDaily] = useState(false);

  // New Daily Entry Form
  const [newDailyForm, setNewDailyForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    order_no: '',
    customer: '',
    variant: '',
    length: 'Standard',
    labour: '',
    machine: '',
    department: 'Machining',
    planned_qty: 10,
    actual_qty: 10,
    rework_qty: 0,
    scrap_qty: 0,
    work_type: 'REGULAR',
    standard_target: 10,
    rate_per_unit: 50,
    daily_earned_inr: 500,
    start_time: '08:30 AM',
    end_time: '05:00 PM',
    supervisor_remarks: '',
    priority_change: 'NORMAL',
  });

  // Orders State
  const [orders, setOrders] = useState<ProductionOrder[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  // Master Data
  const [products, setProducts] = useState<FinishedProduct[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [boms, setBoms] = useState<BOM[]>([]);

  // Modals State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showIssueModal, setShowIssueModal] = useState(false);
  const [showOutputModal, setShowOutputModal] = useState(false);
  const [showVarianceModal, setShowVarianceModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<ProductionOrder | null>(null);
  const [varianceReport, setVarianceReport] = useState<ProductionVarianceReport | null>(null);

  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create Form State
  const [createForm, setCreateForm] = useState({
    product_id: '',
    bom_id: '',
    target_warehouse_id: '',
    planned_quantity: 1,
    notes: '',
  });

  // Issue Form State
  const [issueWarehouseId, setIssueWarehouseId] = useState('');
  const [issueItems, setIssueItems] = useState<{ material_id: string; material_code: string; quantity: number }[]>([]);

  // Output Form State
  const [outputForm, setOutputForm] = useState({
    produced_quantity: 1,
    rejected_quantity: 0,
    warehouse_id: '',
    batch_no: '',
    operator_name: '',
    notes: '',
  });

  // -------------------------------------------------------------
  // Data Fetching Handlers
  // -------------------------------------------------------------
  const fetchDashboard = useCallback(async () => {
    if (!canRead) return;
    try {
      const data = await productionClient.getDashboard(activeUnit === 'BOTH' ? undefined : activeUnit);
      setMetrics(data);
    } catch (err) {
      console.error('Error fetching production dashboard:', err);
    }
  }, [activeUnit, canRead]);

  const fetchOrders = useCallback(async () => {
    if (!canRead) return;
    try {
      setIsLoadingOrders(true);
      const res = await productionClient.listOrders({
        search: searchQuery || undefined,
        status: selectedStatus === 'ALL' ? undefined : selectedStatus,
        unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        page: 1,
        page_size: 50,
      });
      setOrders(res.items);
    } catch (err) {
      console.error('Error fetching production orders:', err);
    } finally {
      setIsLoadingOrders(false);
    }
  }, [activeUnit, searchQuery, selectedStatus, canRead]);

  const fetchDaily = useCallback(async () => {
    if (!canRead) return;
    try {
      setIsLoadingDaily(true);
      const [lines, sum] = await Promise.all([
        productionClient.listDaily({
          date: selectedDate || undefined,
          department: selectedDepartment !== 'ALL' ? selectedDepartment : undefined,
          unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
          search: dailySearch || undefined,
        }),
        productionClient.getDailySummary({
          date: selectedDate || undefined,
          department: selectedDepartment !== 'ALL' ? selectedDepartment : undefined,
          unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        }),
      ]);
      setDailyLines(lines);
      setDailySummary(sum);
    } catch (err) {
      console.error('Error fetching daily production:', err);
    } finally {
      setIsLoadingDaily(false);
    }
  }, [selectedDate, selectedDepartment, activeUnit, dailySearch, canRead]);

  const fetchMasterData = useCallback(async () => {
    try {
      const [prodRes, whRes, bomRes] = await Promise.all([
        masterClient.list('products', { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
        masterClient.list('warehouses', { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
        bomClient.listBOMs({ is_active: true, page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
      ]);
      setProducts((prodRes?.items || []) as FinishedProduct[]);
      setWarehouses((whRes?.items || []) as Warehouse[]);
      setBoms((bomRes?.items || []) as BOM[]);
    } catch (err) {
      console.warn('Master metadata for production currently unavailable:', err);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !canRead) return;
    fetchDashboard();
    if (activeTab === 'ORDERS') {
      fetchOrders();
    } else if (activeTab === 'DAILY') {
      fetchDaily();
    }
    fetchMasterData();
  }, [fetchDashboard, fetchOrders, fetchDaily, fetchMasterData, activeTab, canRead, authLoading]);

  const handleSaveDaily = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDaily?.id) return;
    try {
      setIsSavingDaily(true);
      await productionClient.updateDaily(editingDaily.id, {
        planned_qty: Number(editingDaily.planned_qty),
        actual_qty: Number(editingDaily.actual_qty),
        rework_qty: Number(editingDaily.rework_qty),
        scrap_qty: Number(editingDaily.scrap_qty),
        work_type: editingDaily.work_type,
        standard_target: Number(editingDaily.standard_target),
        rate_per_unit: Number(editingDaily.rate_per_unit || 0),
        daily_earned_inr: Number(editingDaily.daily_earned_inr || 0),
        start_time: editingDaily.start_time,
        end_time: editingDaily.end_time,
        supervisor_remarks: editingDaily.supervisor_remarks,
        priority_change: editingDaily.priority_change,
        department: editingDaily.department,
        labour: editingDaily.labour,
        machine: editingDaily.machine,
      });
      setShowDailyEditModal(false);
      setEditingDaily(null);
      setActionSuccess('Daily production record updated successfully.');
      await fetchDaily();
    } catch (err) {
      console.error('Failed to update daily entry:', err);
      setActionError('Failed to save changes to daily production line.');
    } finally {
      setIsSavingDaily(false);
    }
  };

  const handleCreateDaily = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSavingDaily(true);
      await productionClient.createDaily({
        ...newDailyForm,
        planned_qty: Number(newDailyForm.planned_qty),
        actual_qty: Number(newDailyForm.actual_qty),
        rework_qty: Number(newDailyForm.rework_qty),
        scrap_qty: Number(newDailyForm.scrap_qty),
        standard_target: Number(newDailyForm.standard_target),
        rate_per_unit: Number(newDailyForm.rate_per_unit),
        unit_id: activeUnit === 'BOTH' ? 'Unit_1' : activeUnit || 'Unit_1',
      });
      setShowDailyCreateModal(false);
      setActionSuccess('New daily production record logged successfully.');
      await fetchDaily();
    } catch (err) {
      console.error('Failed to create daily entry:', err);
      setActionError('Failed to create new daily production entry.');
    } finally {
      setIsSavingDaily(false);
    }
  };

  const handleDeleteDaily = async (id: string) => {
    if (!confirm('Are you sure you want to remove this daily production entry?')) return;
    try {
      await productionClient.deleteDaily(id);
      setActionSuccess('Daily production record deleted.');
      await fetchDaily();
    } catch (err) {
      console.error('Failed to delete daily entry:', err);
      setActionError('Failed to delete record.');
    }
  };

  const handleExportDailyCSV = () => {
    if (!dailyLines.length) return;
    const headers = [
      'Date',
      'Order No.',
      'Customer',
      'Variant',
      'Length',
      'Labour',
      'Machine',
      'Department',
      'Planned Qty',
      'Actual Qty',
      'Rework Qty',
      'Scrap Qty',
      'Good Qty',
      'Completion %',
      'Work Type',
      'Standard Target',
      'Performance %',
      'Daily Earned INR',
      'Start Time',
      'End Time',
      'Supervisor Remarks',
      'Priority Change',
    ];
    const rows = dailyLines.map((row) => [
      `"${row.date}"`,
      `"${row.order_no}"`,
      `"${row.customer.replace(/"/g, '""')}"`,
      `"${row.variant.replace(/"/g, '""')}"`,
      `"${row.length}"`,
      `"${row.labour.replace(/"/g, '""')}"`,
      `"${row.machine.replace(/"/g, '""')}"`,
      `"${row.department}"`,
      row.planned_qty,
      row.actual_qty,
      row.rework_qty,
      row.scrap_qty,
      row.good_qty,
      `"${row.completion_pct}%"`,
      `"${row.work_type}"`,
      row.standard_target,
      `"${row.performance_pct}%"`,
      `"₹${row.daily_earned_inr.toFixed(2)}"`,
      `"${row.start_time || ''}"`,
      `"${row.end_time || ''}"`,
      `"${(row.supervisor_remarks || '').replace(/"/g, '""')}"`,
      `"${row.priority_change || ''}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Daily_Production_Shivakumar_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // -------------------------------------------------------------
  // Action Handlers
  // -------------------------------------------------------------
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      await productionClient.createOrder({
        product_id: createForm.product_id,
        bom_id: createForm.bom_id || undefined,
        unit_id: (activeUnit === 'BOTH' || !activeUnit) ? 'Unit_1' : activeUnit,
        target_warehouse_id: createForm.target_warehouse_id,
        planned_quantity: Number(createForm.planned_quantity),
        notes: createForm.notes || undefined,
      });

      setActionSuccess('Production order created in DRAFT state.');
      setShowCreateModal(false);
      setCreateForm({ product_id: '', bom_id: '', target_warehouse_id: '', planned_quantity: 1, notes: '' });
      fetchDashboard();
      fetchOrders();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create order';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReleaseOrder = async (order: ProductionOrder) => {
    setActionError(null);
    try {
      await productionClient.releaseOrder(order.id);
      setActionSuccess(`Order ${order.order_number} RELEASED & materials reserved.`);
      fetchOrders();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to release order';
      setActionError(msg);
    }
  };

  const openIssueModal = (order: ProductionOrder) => {
    setSelectedOrder(order);
    const defaultWh = warehouses[0]?.id || '';
    setIssueWarehouseId(defaultWh);
    setIssueItems(
      order.materials.map((m) => ({
        material_id: m.material_id,
        material_code: m.material_code,
        quantity: Math.max(0, m.total_standard_required - m.total_issued),
      }))
    );
    setShowIssueModal(true);
  };

  const handleIssueSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setActionError(null);
    setIsSubmitting(true);
    try {
      const validItems = issueItems
        .filter((it) => it.quantity > 0)
        .map((it) => ({
          material_id: it.material_id,
          warehouse_id: issueWarehouseId,
          quantity: Number(it.quantity),
        }));

      if (validItems.length === 0) throw new Error('Specify at least one material quantity to issue.');

      await productionClient.issueMaterials(selectedOrder.id, validItems);
      setActionSuccess(`Raw materials issued to ${selectedOrder.order_number}.`);
      setShowIssueModal(false);
      fetchOrders();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to issue materials';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openOutputModal = (order: ProductionOrder) => {
    setSelectedOrder(order);
    setOutputForm({
      produced_quantity: order.remaining_quantity || 1,
      rejected_quantity: 0,
      warehouse_id: order.target_warehouse_id || warehouses[0]?.id || '',
      batch_no: `LOT-${order.order_number}`,
      operator_name: '',
      notes: '',
    });
    setShowOutputModal(true);
  };

  const handleOutputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setActionError(null);
    setIsSubmitting(true);
    try {
      await productionClient.recordOutput(selectedOrder.id, {
        produced_quantity: Number(outputForm.produced_quantity),
        rejected_quantity: Number(outputForm.rejected_quantity),
        warehouse_id: outputForm.warehouse_id,
        batch_no: outputForm.batch_no || undefined,
        operator_name: outputForm.operator_name || undefined,
        notes: outputForm.notes || undefined,
      });

      setActionSuccess(`Output recorded for ${selectedOrder.order_number} and receipted into FG stock.`);
      setShowOutputModal(false);
      fetchOrders();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record output';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openVarianceReport = async (order: ProductionOrder) => {
    setSelectedOrder(order);
    setActionError(null);
    try {
      const rep = await productionClient.getVarianceReport(order.id);
      setVarianceReport(rep);
      setShowVarianceModal(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load variance report';
      setActionError(msg);
    }
  };

  // -------------------------------------------------------------
  // Data Table Columns
  // -------------------------------------------------------------
  const getStatusBadge = (status: ProductionOrderStatus) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="neutral">DRAFT</Badge>;
      case 'RELEASED':
        return <Badge variant="warning">RELEASED</Badge>;
      case 'IN_PROGRESS':
        return <Badge variant="warning" className="font-semibold text-[#254936] bg-[#EAF0E9] border-[#315C45]/20">IN PROGRESS</Badge>;
      case 'COMPLETED':
        return <Badge variant="success">COMPLETED</Badge>;
      case 'CANCELLED':
        return <Badge variant="error">CANCELLED</Badge>;
    }
  };

  const orderColumns: Column<ProductionOrder>[] = [
    {
      key: 'order_number',
      header: 'Order # & Recipe',
      render: (o) => (
        <div>
          <span className="font-semibold text-[#315C45] text-blue-400 font-mono">{o.order_number}</span>
          <div className="text-[11px] text-slate-500">
            {o.bom_number} (Rev: {o.bom_revision_no})
          </div>
        </div>
      ),
    },
    {
      key: 'product',
      header: 'Finished Good',
      render: (o) => (
        <div>
          <div className="font-semibold text-slate-900 ">{o.product_code}</div>
          <div className="text-xs text-slate-500">{o.product_name}</div>
        </div>
      ),
    },
    {
      key: 'facility',
      header: 'Facility & Yard',
      render: (o) => (
        <div>
          <div className="font-medium text-slate-800 ">
            {o.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : o.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
          </div>
          <div className="text-xs text-slate-500">{o.target_warehouse_code}</div>
        </div>
      ),
    },
    {
      key: 'progress',
      header: 'Yield & Progress',
      render: (o) => (
        <div className="space-y-1 min-w-[130px]">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-medium text-slate-700 ">
              {o.produced_quantity} / {o.planned_quantity} {o.product_uom}
            </span>
            <span className="font-bold text-[#315C45]">{o.completion_percentage}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100  rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${o.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-[#315C45]'
                }`}
              style={{ width: `${o.completion_percentage}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (o) => getStatusBadge(o.status),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (o) => (
        <div className="flex items-center gap-1.5">
          {o.status === 'DRAFT' && canUpdate && (
            <Button size="sm" variant="outline" onClick={() => handleReleaseOrder(o)}>
              <Play className="w-3.5 h-3.5 mr-1" /> Release
            </Button>
          )}
          {(o.status === 'RELEASED' || o.status === 'IN_PROGRESS') && canPost && (
            <>
              <Button size="sm" variant="outline" onClick={() => openIssueModal(o)}>
                <Boxes className="w-3.5 h-3.5 mr-1" /> Issue Mat.
              </Button>
              <Button size="sm" variant="primary" onClick={() => openOutputModal(o)}>
                <CheckCheck className="w-3.5 h-3.5 mr-1" /> Record Output
              </Button>
            </>
          )}
          {o.status !== 'DRAFT' && (
            <Button size="sm" variant="secondary" onClick={() => openVarianceReport(o)}>
              <BarChart3 className="w-3.5 h-3.5 mr-1" /> Variance
            </Button>
          )}
        </div>
      ),
    },
  ];

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <RefreshCw className="w-4 h-4 animate-spin text-[#315C45]" />
          <span>Authenticating production credentials...</span>
        </div>
      </div>
    );
  }

  if (!canRead) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#E7E5DE] max-w-lg mx-auto mt-12 space-y-4">
        <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-800">Production Access Restricted</h2>
        <p className="text-xs text-slate-500 leading-relaxed">
          Your account role does not have authorization to view shop-floor production orders or KPI metrics. Please contact your administrator or HR department if you require access.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {actionSuccess && (
        <div className="flex items-center justify-between rounded-lg bg-emerald-50 p-4 border border-emerald-200 text-emerald-800">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <span className="font-medium text-sm">{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-xs font-semibold hover:underline">Dismiss</button>
        </div>
      )}

      {actionError && (
        <div className="flex items-center justify-between rounded-lg bg-rose-50 p-4 border border-rose-200 text-rose-800">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-rose-600" />
            <span className="font-medium text-sm">{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-xs font-semibold hover:underline">Dismiss</button>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 ">
            Production Planning & Shop-Floor Execution (WIP)
          </h1>
          <p className="text-sm text-slate-500">
            Work order execution, material reservation and issue, work-in-progress, and finished goods receipts.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canCreate && (
            <Button
              onClick={() => {
                if (products.length > 0) setCreateForm((f) => ({ ...f, product_id: products[0].id }));
                if (warehouses.length > 0) setCreateForm((f) => ({ ...f, target_warehouse_id: warehouses[0].id }));
                setShowCreateModal(true);
              }}
              className="bg-[#315C45] hover:bg-[#254936] text-white"
            >
              <Plus className="mr-1.5 h-4 w-4" /> Create Production Order
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-blue-500 shadow-sm">
          <div className="p-3 bg-[#EAF0E9] bg-blue-950/40 rounded-lg text-[#315C45]">
            <Cog className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Total Work Orders</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.total_orders ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Active: {(metrics?.released_orders ?? 0) + (metrics?.in_progress_orders ?? 0)} in floor
            </p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-amber-500 shadow-sm">
          <div className="p-3 bg-amber-50 bg-amber-950/40 rounded-lg text-amber-600">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Units in WIP</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {((metrics?.total_planned_units ?? 0) - (metrics?.total_produced_units ?? 0)).toLocaleString()}
            </h3>
            <p className="text-xs text-amber-600 font-medium mt-0.5">{metrics?.in_progress_orders ?? 0} orders running</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-emerald-500 shadow-sm">
          <div className="p-3 bg-emerald-50 bg-emerald-950/40 rounded-lg text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Completed Output</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {(metrics?.total_produced_units ?? 0).toLocaleString()}
            </h3>
            <p className="text-xs text-emerald-600 font-medium mt-0.5">Yield: {metrics?.overall_yield_percentage ?? 100}%</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-purple-500 shadow-sm">
          <div className="p-3 bg-purple-50 bg-purple-950/40 rounded-lg text-purple-600">
            <Flame className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Rejections / Scrap</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {(metrics?.total_rejected_units ?? 0).toLocaleString()}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">Reported shop floor waste</p>
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-[#E7E5DE] pb-2">
        <button
          onClick={() => setActiveTab('ORDERS')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'ORDERS'
            ? 'bg-[#315C45] text-white shadow-sm'
            : 'bg-white text-slate-600 border border-[#E7E5DE] hover:bg-slate-50'
            }`}
        >
          <Cog className="h-3.5 w-3.5" />
          Production Work Orders (WIP)
          <span className="text-[10px] ml-1 px-1.5 py-0.5 rounded-full bg-slate-200/60 font-semibold">
            {metrics?.total_orders ?? orders.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('DAILY')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'DAILY'
            ? 'bg-[#315C45] text-white shadow-sm'
            : 'bg-white text-slate-600 border border-[#E7E5DE] hover:bg-slate-50'
            }`}
        >
          <ClipboardList className="h-3.5 w-3.5" />
          Daily Production Planning & Actual
          <span className="text-[10px] ml-1 px-1.5 py-0.5 rounded-full bg-slate-200/60 font-semibold">
            {dailySummary?.total_entries ?? dailyLines.length}
          </span>
        </button>
      </div>

      {/* TAB 1: PRODUCTION ORDERS */}
      {activeTab === 'ORDERS' && (
        <div className="space-y-4">
          <FilterBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            placeholder="Search by Order #, product, or BOM..."
            onReset={() => {
              setSearchQuery('');
              setSelectedStatus('ALL');
            }}
          >
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700 "
            >
              <option value="ALL">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="RELEASED">Released</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </FilterBar>

          <DataTable
            columns={orderColumns}
            data={orders}
            isLoading={isLoadingOrders}
            keyExtractor={(o) => o.id}
            emptyTitle="No production orders found"
            emptyDescription="Create a production order to plan and issue materials for manufacturing batches."
          />
        </div>
      )}

      {/* TAB 2: DAILY PRODUCTION PLANNING & ACTUAL */}
      {/* Main daily entry screen for Shivakumar (department-wise) */}
      {activeTab === 'DAILY' && (
        <div className="space-y-6">
          {/* Header Banner & Action Buttons */}
          <div className="bg-[#FAF8F5] text-slate-800 rounded-xl p-5 shadow-xs border border-[#E7E5DE]">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Department-Wise Floor Control
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    Main daily entry screen for Shivakumar
                  </span>
                </div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900 mt-1.5 flex items-center gap-2">
                  <ClipboardList className="w-5 h-5 text-emerald-700" />
                  Daily Production Planning & Actual
                </h2>
                <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                  Log and monitor machine operators, planned vs actual output, rework, scrap, standard targets,
                  and performance piece-rates across all manufacturing departments.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportDailyCSV}
                  className="bg-white hover:bg-slate-50 text-slate-700 border-[#E7E5DE] text-xs flex items-center gap-1.5 shadow-xs"
                >
                  <Download className="w-3.5 h-3.5 text-slate-500" />
                  Export Sheet (CSV)
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.print()}
                  className="bg-white hover:bg-slate-50 text-slate-700 border-[#E7E5DE] text-xs flex items-center gap-1.5 shadow-xs"
                >
                  <Printer className="w-3.5 h-3.5 text-slate-500" />
                  Print Daily Matrix
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDailyCreateModal(true)}
                  className="bg-emerald-700 hover:bg-emerald-800 text-white border-transparent text-xs flex items-center gap-1.5 font-semibold shadow-xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  + Log Production Entry
                </Button>
              </div>
            </div>
          </div>

          {/* Department Quick Tabs */}
          <div className="bg-white p-2.5 rounded-xl border border-[#E7E5DE] shadow-sm flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold text-slate-500 mr-2">Department:</span>
              {['ALL', 'Machining', 'Assembly', 'Fabrication', 'Welding', 'Quality Control', 'Grinding'].map((dept) => (
                <button
                  key={dept}
                  type="button"
                  onClick={() => setSelectedDepartment(dept)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${selectedDepartment === dept
                    ? 'bg-[#315C45] text-white shadow-xs font-semibold'
                    : 'bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200'
                    }`}
                >
                  {dept === 'ALL' ? 'All Departments' : dept}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Date:</span>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-2.5 py-1 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
              />
              {selectedDate && (
                <button
                  type="button"
                  onClick={() => setSelectedDate('')}
                  className="text-xs text-slate-400 hover:text-slate-600 underline"
                >
                  Clear Date
                </button>
              )}
            </div>
          </div>

          {/* Daily KPI Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Entries</p>
              <h3 className="text-xl font-bold text-slate-900 mt-1">
                {isLoadingDaily ? '—' : dailySummary?.total_entries ?? 0}
              </h3>
              <p className="text-[10px] text-slate-400 mt-0.5">Floor Entry Records</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Planned Qty</p>
              <h3 className="text-xl font-bold text-indigo-700 mt-1">
                {isLoadingDaily ? '—' : dailySummary?.total_planned_qty ?? 0}
              </h3>
              <p className="text-[10px] text-indigo-600 font-medium mt-0.5">Target production</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Actual Output</p>
              <h3 className="text-xl font-bold text-slate-900 mt-1">
                {isLoadingDaily ? '—' : dailySummary?.total_actual_qty ?? 0}
              </h3>
              <p className="text-[10px] text-slate-500 font-medium mt-0.5">Total machine units</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Good Output</p>
              <h3 className="text-xl font-bold text-emerald-700 mt-1">
                {isLoadingDaily ? '—' : dailySummary?.total_good_qty ?? 0}
              </h3>
              <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Passed inspection</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Rework / Scrap</p>
              <h3 className="text-xl font-bold text-rose-700 mt-1">
                {isLoadingDaily ? '—' : `${dailySummary?.total_rework_qty ?? 0} / ${dailySummary?.total_scrap_qty ?? 0}`}
              </h3>
              <p className="text-[10px] text-rose-600 font-medium mt-0.5">Defects logged</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Daily Earned</p>
              <h3 className="text-xl font-bold text-emerald-800 mt-1">
                ₹{isLoadingDaily ? '—' : (dailySummary?.total_daily_earned_inr ?? 0).toLocaleString('en-IN')}
              </h3>
              <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Piece-rate / wages</p>
            </Card>
          </div>

          {/* Department Breakdown Overview Cards */}
          {dailySummary?.department_breakdown && dailySummary.department_breakdown.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                Department Performance Summary
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {dailySummary.department_breakdown.map((dep) => (
                  <div
                    key={dep.department}
                    className="bg-white p-3 rounded-lg border border-slate-200 shadow-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-slate-900">{dep.department}</span>
                      <span className="text-[11px] font-semibold text-emerald-700">{dep.completion_pct}% Met</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-emerald-600 h-1.5 rounded-full"
                        style={{ width: `${Math.min(100, dep.completion_pct)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>Good: <strong className="text-slate-800">{dep.good_qty}</strong> / {dep.planned_qty}</span>
                      <span>Earned: <strong className="text-[#315C45]">₹{dep.earned_inr.toLocaleString('en-IN')}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search Bar for Daily Lines */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Order No., Customer, Variant, Labour, Machine, or Remarks..."
              value={dailySearch}
              onChange={(e) => setDailySearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
            />
          </div>

          {/* Complete 21-Column Daily Production Table */}
          <div className="bg-white border border-[#E7E5DE] rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100/90 text-slate-700 border-b border-[#E7E5DE] whitespace-nowrap text-[11px] font-semibold uppercase tracking-wider">
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">Order No.</th>
                    <th className="py-3 px-3 min-w-[150px]">Customer</th>
                    <th className="py-3 px-3 min-w-[180px]">Variant</th>
                    <th className="py-3 px-3">Length</th>
                    <th className="py-3 px-3 min-w-[130px]">Labour</th>
                    <th className="py-3 px-3 min-w-[160px]">Machine</th>
                    <th className="py-3 px-3">Department</th>
                    <th className="py-3 px-3 text-right">Planned Qty</th>
                    <th className="py-3 px-3 text-right">Actual Qty</th>
                    <th className="py-3 px-3 text-right">Rework Qty</th>
                    <th className="py-3 px-3 text-right">Scrap Qty</th>
                    <th className="py-3 px-3 text-right">Good Qty</th>
                    <th className="py-3 px-3 text-right">Completion %</th>
                    <th className="py-3 px-3">Work Type</th>
                    <th className="py-3 px-3 text-right">Standard Target</th>
                    <th className="py-3 px-3 text-right">Performance %</th>
                    <th className="py-3 px-3 text-right">Daily Earned ₹</th>
                    <th className="py-3 px-3">Start Time</th>
                    <th className="py-3 px-3">End Time</th>
                    <th className="py-3 px-3 min-w-[200px]">Supervisor Remarks</th>
                    <th className="py-3 px-3">Priority Change</th>
                    <th className="py-3 px-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E7E5DE]">
                  {isLoadingDaily ? (
                    <tr>
                      <td colSpan={23} className="py-12 text-center text-slate-400">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#315C45]" />
                        Loading daily production entries...
                      </td>
                    </tr>
                  ) : dailyLines.length === 0 ? (
                    <tr>
                      <td colSpan={23} className="py-12 text-center text-slate-500">
                        <ClipboardList className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        No daily production entries found for the selected department/date criteria.
                      </td>
                    </tr>
                  ) : (
                    dailyLines.map((row) => (
                      <tr
                        key={row.id}
                        className="hover:bg-emerald-50/40 transition-colors whitespace-nowrap"
                      >
                        <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">{row.date}</td>
                        <td className="py-2.5 px-3 font-bold text-slate-900">{row.order_no}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-800 max-w-[180px] truncate" title={row.customer}>
                          {row.customer}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-900 max-w-[200px] truncate" title={row.variant}>
                          {row.variant}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">{row.length}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-800">{row.labour}</td>
                        <td className="py-2.5 px-3 text-slate-700 max-w-[180px] truncate" title={row.machine}>
                          {row.machine}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                            {row.department}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-indigo-700">{row.planned_qty}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-slate-900">{row.actual_qty}</td>
                        <td className="py-2.5 px-3 text-right text-amber-700">{row.rework_qty}</td>
                        <td className="py-2.5 px-3 text-right text-rose-700">{row.scrap_qty}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-emerald-700">{row.good_qty}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-emerald-800">{row.completion_pct}%</td>
                        <td className="py-2.5 px-3">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700">
                            {row.work_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-700">{row.standard_target}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-[#315C45]">{row.performance_pct}%</td>
                        <td className="py-2.5 px-3 text-right font-bold text-emerald-700">
                          ₹{row.daily_earned_inr.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 font-mono text-[10px]">{row.start_time || '—'}</td>
                        <td className="py-2.5 px-3 text-slate-500 font-mono text-[10px]">{row.end_time || '—'}</td>
                        <td className="py-2.5 px-3 text-slate-600 text-[11px] max-w-[220px] truncate" title={row.supervisor_remarks || ''}>
                          {row.supervisor_remarks || '—'}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${row.priority_change === 'URGENT'
                              ? 'bg-rose-100 text-rose-800'
                              : row.priority_change === 'HIGH'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-100 text-slate-700'
                              }`}
                          >
                            {row.priority_change || 'NORMAL'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingDaily({ ...row });
                                setShowDailyEditModal(true);
                              }}
                              className="p-1 rounded text-[#315C45] hover:bg-emerald-100 transition-colors"
                              title="Edit Entry"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => row.id && handleDeleteDaily(row.id)}
                              className="p-1 rounded text-rose-500 hover:bg-rose-50 transition-colors"
                              title="Delete Entry"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Matrix Footer Note */}
            <div className="p-3 bg-slate-50 border-t border-[#E7E5DE] text-[11px] text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-slate-700">Daily Production Planning & Actual:</span>
                <span>Main daily entry screen for Shivakumar. Department-wise floor tracking.</span>
              </div>
              <div>
                Formula rules applied: <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">Good Qty = Actual - Rework - Scrap</code> | <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">Completion % = Good / Planned * 100</code> | <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">Performance % = Actual / Standard Target * 100</code>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT DAILY PRODUCTION ENTRY */}
      <Dialog
        isOpen={showDailyEditModal}
        onClose={() => {
          setShowDailyEditModal(false);
          setEditingDaily(null);
        }}
        title={`Update Daily Production: ${editingDaily?.order_no || ''} (${editingDaily?.machine || ''})`}
      >
        {editingDaily && (
          <form onSubmit={handleSaveDaily} className="space-y-4 pt-2">
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <span className="text-slate-500">Customer:</span>{' '}
                <strong className="text-slate-800">{editingDaily.customer}</strong>
              </div>
              <div>
                <span className="text-slate-500">Operator:</span>{' '}
                <strong className="text-slate-800">{editingDaily.labour}</strong>
              </div>
              <div>
                <span className="text-slate-500">Variant & Length:</span>{' '}
                <strong className="text-slate-800">{editingDaily.variant} ({editingDaily.length})</strong>
              </div>
              <div>
                <span className="text-slate-500">Department:</span>{' '}
                <strong className="text-slate-800">{editingDaily.department}</strong>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Planned Qty</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingDaily.planned_qty}
                  onChange={(e) => setEditingDaily({ ...editingDaily, planned_qty: parseFloat(e.target.value) || 0 })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Actual Qty</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingDaily.actual_qty}
                  onChange={(e) => {
                    const aq = parseFloat(e.target.value) || 0;
                    const gq = Math.max(0, aq - editingDaily.rework_qty - editingDaily.scrap_qty);
                    const rate = editingDaily.rate_per_unit || 50;
                    setEditingDaily({
                      ...editingDaily,
                      actual_qty: aq,
                      good_qty: gq,
                      completion_pct: editingDaily.planned_qty > 0 ? Math.round((gq / editingDaily.planned_qty) * 1000) / 10 : 0,
                      daily_earned_inr: gq * rate,
                    });
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Rework Qty</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingDaily.rework_qty}
                  onChange={(e) => {
                    const rq = parseFloat(e.target.value) || 0;
                    const gq = Math.max(0, editingDaily.actual_qty - rq - editingDaily.scrap_qty);
                    const rate = editingDaily.rate_per_unit || 50;
                    setEditingDaily({
                      ...editingDaily,
                      rework_qty: rq,
                      good_qty: gq,
                      daily_earned_inr: gq * rate,
                    });
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Scrap Qty</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingDaily.scrap_qty}
                  onChange={(e) => {
                    const sq = parseFloat(e.target.value) || 0;
                    const gq = Math.max(0, editingDaily.actual_qty - editingDaily.rework_qty - sq);
                    const rate = editingDaily.rate_per_unit || 50;
                    setEditingDaily({
                      ...editingDaily,
                      scrap_qty: sq,
                      good_qty: gq,
                      daily_earned_inr: gq * rate,
                    });
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Work Type</label>
                <select
                  value={editingDaily.work_type}
                  onChange={(e) => setEditingDaily({ ...editingDaily, work_type: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                >
                  <option value="REGULAR">REGULAR</option>
                  <option value="OVERTIME">OVERTIME</option>
                  <option value="REWORK">REWORK</option>
                  <option value="URGENT">URGENT</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Standard Target</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingDaily.standard_target}
                  onChange={(e) => setEditingDaily({ ...editingDaily, standard_target: parseFloat(e.target.value) || 0 })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Rate per Unit (₹)</label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={editingDaily.rate_per_unit || 0}
                  onChange={(e) => {
                    const r = parseFloat(e.target.value) || 0;
                    setEditingDaily({
                      ...editingDaily,
                      rate_per_unit: r,
                      daily_earned_inr: (editingDaily.good_qty || 0) * r,
                    });
                  }}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Priority Change</label>
                <select
                  value={editingDaily.priority_change || 'NORMAL'}
                  onChange={(e) => setEditingDaily({ ...editingDaily, priority_change: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
                >
                  <option value="NORMAL">NORMAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="URGENT">URGENT</option>
                  <option value="HOLD">HOLD</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Supervisor Remarks</label>
              <textarea
                rows={2}
                value={editingDaily.supervisor_remarks || ''}
                onChange={(e) => setEditingDaily({ ...editingDaily, supervisor_remarks: e.target.value })}
                placeholder="Calibration notes, tool wear, scrap reasons, quality notes..."
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8]">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowDailyEditModal(false);
                  setEditingDaily(null);
                }}
                disabled={isSavingDaily}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingDaily}>
                {isSavingDaily ? 'Saving Changes...' : 'Save Daily Entry'}
              </Button>
            </div>
          </form>
        )}
      </Dialog>

      {/* MODAL: CREATE NEW DAILY PRODUCTION ENTRY */}
      <Dialog
        isOpen={showDailyCreateModal}
        onClose={() => setShowDailyCreateModal(false)}
        title="Log New Daily Production Entry (Shivakumar)"
      >
        <form onSubmit={handleCreateDaily} className="space-y-4 pt-2">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Date</label>
              <input
                type="date"
                required
                value={newDailyForm.date}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, date: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Order No.</label>
              <input
                type="text"
                required
                placeholder="e.g. SO-2026-0001"
                value={newDailyForm.order_no}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, order_no: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Department</label>
              <select
                value={newDailyForm.department}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, department: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              >
                <option value="Machining">Machining</option>
                <option value="Assembly">Assembly</option>
                <option value="Fabrication">Fabrication</option>
                <option value="Welding">Welding</option>
                <option value="Quality Control">Quality Control</option>
                <option value="Grinding">Grinding</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Customer</label>
              <input
                type="text"
                required
                placeholder="Customer Name"
                value={newDailyForm.customer}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, customer: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Variant</label>
              <input
                type="text"
                required
                placeholder="e.g. Semi-Automatic Envelope Machine"
                value={newDailyForm.variant}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, variant: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Length</label>
              <input
                type="text"
                placeholder="e.g. 100 mm"
                value={newDailyForm.length}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, length: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Labour / Operator Name</label>
              <input
                type="text"
                required
                placeholder="Operator Name"
                value={newDailyForm.labour}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, labour: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Machine</label>
              <input
                type="text"
                required
                placeholder="e.g. CNC VMC-01"
                value={newDailyForm.machine}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, machine: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Planned Qty</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={newDailyForm.planned_qty}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, planned_qty: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Actual Qty</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={newDailyForm.actual_qty}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, actual_qty: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 font-bold"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Rework Qty</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={newDailyForm.rework_qty}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, rework_qty: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Scrap Qty</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={newDailyForm.scrap_qty}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, scrap_qty: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Work Type</label>
              <select
                value={newDailyForm.work_type}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, work_type: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              >
                <option value="REGULAR">REGULAR</option>
                <option value="OVERTIME">OVERTIME</option>
                <option value="REWORK">REWORK</option>
                <option value="URGENT">URGENT</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Standard Target</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={newDailyForm.standard_target}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, standard_target: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Rate / Unit (₹)</label>
              <input
                type="number"
                step="1"
                min="0"
                value={newDailyForm.rate_per_unit}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, rate_per_unit: parseFloat(e.target.value) || 0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Priority</label>
              <select
                value={newDailyForm.priority_change}
                onChange={(e) => setNewDailyForm({ ...newDailyForm, priority_change: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
              >
                <option value="NORMAL">NORMAL</option>
                <option value="HIGH">HIGH</option>
                <option value="URGENT">URGENT</option>
                <option value="HOLD">HOLD</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Supervisor Remarks</label>
            <textarea
              rows={2}
              value={newDailyForm.supervisor_remarks}
              onChange={(e) => setNewDailyForm({ ...newDailyForm, supervisor_remarks: e.target.value })}
              placeholder="Notes on operations, tool wear, shifts, machine calibration..."
              className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8]">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowDailyCreateModal(false)}
              disabled={isSavingDaily}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSavingDaily}>
              {isSavingDaily ? 'Saving Entry...' : 'Submit Daily Production'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* MODAL: CREATE PRODUCTION ORDER */}
      {showCreateModal && (
        <Dialog
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create Production Work Order"
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Finished Product
              </label>
              <select
                value={createForm.product_id}
                onChange={(e) => setCreateForm({ ...createForm, product_id: e.target.value })}
                className="w-full border rounded-md p-2 text-xs bg-white "
                required
              >
                <option value="">-- Choose Product --</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} - {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Approved BOM (Optional)
                </label>
                <select
                  value={createForm.bom_id}
                  onChange={(e) => setCreateForm({ ...createForm, bom_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs bg-white "
                >
                  <option value="">-- Auto-Select Active Approved BOM --</option>
                  {boms.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.bom_number} ({b.revision_no}) - {b.product_code}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Target Finished Goods Warehouse
                </label>
                <select
                  value={createForm.target_warehouse_id}
                  onChange={(e) => setCreateForm({ ...createForm, target_warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs bg-white "
                  required
                >
                  <option value="">-- Choose Destination --</option>
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} - {w.name} ({w.unit_id === 'Unit_1' ? 'Unit 1' : w.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Planned Batch Quantity
              </label>
              <input
                type="number"
                min="1"
                step="any"
                value={createForm.planned_quantity}
                onChange={(e) => setCreateForm({ ...createForm, planned_quantity: parseFloat(e.target.value) || 1 })}
                className="w-full border rounded-md p-2 text-xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Order Notes / Customer References
              </label>
              <textarea
                value={createForm.notes}
                onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-[#315C45] hover:bg-[#254936] text-white">
                {isSubmitting ? 'Creating...' : 'Create Order (Draft)'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: ISSUE MATERIALS */}
      {showIssueModal && selectedOrder && (
        <Dialog
          isOpen={showIssueModal}
          onClose={() => setShowIssueModal(false)}
          title={`Issue Materials: ${selectedOrder.order_number}`}
        >
          <form onSubmit={handleIssueSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Source Raw Material Warehouse
              </label>
              <select
                value={issueWarehouseId}
                onChange={(e) => setIssueWarehouseId(e.target.value)}
                className="w-full border rounded-md p-2 text-xs bg-white "
                required
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} - {w.name} ({w.unit_id === 'Unit_1' ? 'Unit 1' : w.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-700  uppercase">
                Component Issue Quantities
              </h4>
              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {issueItems.map((it, idx) => (
                  <div key={it.material_id} className="flex items-center justify-between p-2 rounded border bg-slate-50 ">
                    <span className="text-xs font-medium">{it.material_code}</span>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={it.quantity}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0;
                        setIssueItems((prev) => {
                          const updated = [...prev];
                          updated[idx].quantity = val;
                          return updated;
                        });
                      }}
                      className="w-28 border rounded p-1 text-xs text-right"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowIssueModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} variant="primary">
                {isSubmitting ? 'Issuing...' : 'Confirm Material Issue'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: RECORD OUTPUT */}
      {showOutputModal && selectedOrder && (
        <Dialog
          isOpen={showOutputModal}
          onClose={() => setShowOutputModal(false)}
          title={`Record Output & FG Receipt: ${selectedOrder.order_number}`}
        >
          <form onSubmit={handleOutputSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Good Finished Machines Produced
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={outputForm.produced_quantity}
                  onChange={(e) => setOutputForm({ ...outputForm, produced_quantity: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Scrapped / Rejected Units
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={outputForm.rejected_quantity}
                  onChange={(e) => setOutputForm({ ...outputForm, rejected_quantity: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  FG Receipt Warehouse
                </label>
                <select
                  value={outputForm.warehouse_id}
                  onChange={(e) => setOutputForm({ ...outputForm, warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs bg-white "
                  required
                >
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} - {w.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Lot / Batch Serial
                </label>
                <input
                  type="text"
                  value={outputForm.batch_no}
                  onChange={(e) => setOutputForm({ ...outputForm, batch_no: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Operator / Line Notes
              </label>
              <textarea
                value={outputForm.notes}
                onChange={(e) => setOutputForm({ ...outputForm, notes: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowOutputModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {isSubmitting ? 'Posting Receipt...' : 'Receipt into Finished Goods'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: VARIANCE REPORT */}
      {showVarianceModal && varianceReport && (
        <Dialog
          isOpen={showVarianceModal}
          onClose={() => setShowVarianceModal(false)}
          title={`Material Consumption Variance: ${varianceReport.order_number}`}
        >
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2 p-3 bg-slate-50  rounded-lg text-xs">
              <div><span className="font-semibold">Yield Efficiency:</span> {varianceReport.yield_efficiency_percentage}%</div>
              <div><span className="font-semibold">Total Std Cost:</span> ₹{varianceReport.total_standard_cost.toLocaleString()}</div>
              <div>
                <span className="font-semibold">Net Cost Variance:</span>{' '}
                <span className={varianceReport.net_cost_variance > 0 ? 'text-rose-600 font-bold' : 'text-emerald-600 font-bold'}>
                  ₹{varianceReport.net_cost_variance.toLocaleString()}
                </span>
              </div>
            </div>

            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100  border-b text-slate-600 uppercase font-semibold">
                <tr>
                  <th className="p-2">Material</th>
                  <th className="p-2">BOM Standard</th>
                  <th className="p-2">Actual Consumed</th>
                  <th className="p-2">Variance</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {varianceReport.material_variances.map((mv) => (
                  <tr key={mv.material_id}>
                    <td className="p-2 font-medium">{mv.material_code}</td>
                    <td className="p-2">{mv.standard_required} {mv.uom}</td>
                    <td className="p-2">{mv.actual_issued} {mv.uom}</td>
                    <td className="p-2">
                      {mv.variance_quantity > 0 ? (
                        <span className="text-rose-600 font-bold">+{mv.variance_quantity} {mv.uom}</span>
                      ) : (
                        <span className="text-emerald-600 font-bold">{mv.variance_quantity} {mv.uom}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="flex justify-end pt-2 border-t">
              <Button variant="outline" onClick={() => setShowVarianceModal(false)}>Close</Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
