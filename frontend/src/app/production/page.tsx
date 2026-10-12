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
} from 'lucide-react';

export default function ProductionHubPage() {
  const { activeUnit, hasPermission } = useAuth();
  const canCreate = hasPermission('production', 'create');
  const canUpdate = hasPermission('production', 'update');
  const canPost = hasPermission('production', 'post');

  // Active Tab: 'ORDERS' | 'WIP'
  const [activeTab, setActiveTab] = useState<'ORDERS' | 'WIP'>('ORDERS');

  // KPI Metrics
  const [metrics, setMetrics] = useState<ProductionDashboardSummary | null>(null);

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
    try {
      const data = await productionClient.getDashboard(activeUnit === 'BOTH' ? undefined : activeUnit);
      setMetrics(data);
    } catch (err) {
      console.error('Error fetching production dashboard:', err);
    }
  }, [activeUnit]);

  const fetchOrders = useCallback(async () => {
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
  }, [activeUnit, searchQuery, selectedStatus]);

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
    fetchDashboard();
    fetchOrders();
    fetchMasterData();
  }, [fetchDashboard, fetchOrders, fetchMasterData]);

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
      <div className="border-b border-[#E7E5DE] ">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('ORDERS')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'ORDERS'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <Cog className="h-4 w-4" /> Production Orders
          </button>
        </nav>
      </div>

      {/* Orders Table */}
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
