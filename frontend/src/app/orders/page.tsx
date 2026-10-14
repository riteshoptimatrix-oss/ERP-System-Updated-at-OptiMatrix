'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { ordersClient, ListOrdersParams } from '@/services/orders-client';
import { masterClient } from '@/services/master-client';
import {
  SalesOrder,
  OrderStatus,
  OrderDashboardSummary,
  OrderLineItem,
  OrderPlanningItem,
  OrderPlanningSummary,
} from '@/types/orders';
import { Customer, FinishedProduct } from '@/types/master';
import { ManufacturingUnit } from '@/types/auth';
import {
  ShoppingCart,
  TrendingUp,
  Truck,
  CheckCircle2,
  Clock,
  Plus,
  ArrowRight,
  ShieldAlert,
  AlertCircle,
  FileText,
  Trash2,
  Building2,
  ClipboardList,
  Edit,
  Download,
  Printer,
  RefreshCw,
  Check,
  Search,
} from 'lucide-react';

const ORDER_STATUS_OPTIONS: { label: string; value: OrderStatus | 'ALL' }[] = [
  { label: 'All Statuses', value: 'ALL' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Submitted', value: 'SUBMITTED' },
  { label: 'Confirmed', value: 'CONFIRMED' },
  { label: 'Partially Dispatched', value: 'PARTIALLY_DISPATCHED' },
  { label: 'Dispatched', value: 'DISPATCHED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

export default function SalesOrdersPage() {
  const { activeUnit, hasPermission, isLoading } = useAuth();
  const canRead = hasPermission('orders', 'read');
  const canCreate = hasPermission('orders', 'create');

  // Active Tab ('ORDERS' | 'PLANNING')
  const [activeTab, setActiveTab] = useState<'ORDERS' | 'PLANNING'>('ORDERS');

  // Sync tab with URL search params if navigated via ?tab=planning
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('tab') === 'planning') {
        setActiveTab('PLANNING');
      }
    }
  }, []);

  // Dashboard KPI state
  const [metrics, setMetrics] = useState<OrderDashboardSummary | null>(null);
  const [isMetricsLoading, setIsMetricsLoading] = useState(false);

  // Orders Table State
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [totalOrders, setTotalOrders] = useState(0);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Order Planning State
  const [planningLines, setPlanningLines] = useState<OrderPlanningItem[]>([]);
  const [planningSummary, setPlanningSummary] = useState<OrderPlanningSummary | null>(null);
  const [isPlanningLoading, setIsPlanningLoading] = useState(false);
  const [planningSearch, setPlanningSearch] = useState('');
  const [planningPriority, setPlanningPriority] = useState<string>('ALL');
  const [planningApproval, setPlanningApproval] = useState<string>('ALL');
  const [editingItem, setEditingItem] = useState<OrderPlanningItem | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSavingPlan, setIsSavingPlan] = useState(false);

  // Create Order Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Master records for dropdowns
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<FinishedProduct[]>([]);

  // Form State
  const [orderCustomer, setOrderCustomer] = useState('');
  const [orderPoNumber, setOrderPoNumber] = useState('');
  const [orderDeliveryDate, setOrderDeliveryDate] = useState('');
  const [orderNotes, setOrderNotes] = useState('');
  const [orderUnit, setOrderUnit] = useState<ManufacturingUnit>(activeUnit || 'Unit_1');
  const [orderItems, setOrderItems] = useState<
    {
      product_id: string;
      product_code: string;
      product_name: string;
      uom: string;
      quantity: number;
      unit_price: number;
      discount_percent: number;
      tax_percent: number;
    }[]
  >([]);

  // Load KPI Dashboard metrics
  const fetchDashboardMetrics = useCallback(async () => {
    if (!canRead || isLoading) return;
    try {
      setIsMetricsLoading(true);
      const data = await ordersClient.getDashboard(activeUnit || undefined);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load orders dashboard metrics:', err);
    } finally {
      setIsMetricsLoading(false);
    }
  }, [canRead, isLoading, activeUnit]);

  // Load Paginated Orders
  const fetchOrders = useCallback(async () => {
    if (!canRead || isLoading) return;
    try {
      setIsLoadingOrders(true);
      const params: ListOrdersParams = {
        search: searchQuery || undefined,
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        unit_id: activeUnit || undefined,
        page,
        page_size: pageSize,
      };
      const res = await ordersClient.listOrders(params);
      setOrders(res.items);
      setTotalOrders(res.total);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setIsLoadingOrders(false);
    }
  }, [canRead, isLoading, searchQuery, selectedStatus, activeUnit, page]);

  // Load Order Planning records
  const fetchPlanning = useCallback(async () => {
    if (!canRead || isLoading) return;
    try {
      setIsPlanningLoading(true);
      const [lines, sum] = await Promise.all([
        ordersClient.listPlanning({
          unit_id: activeUnit || undefined,
          priority: planningPriority !== 'ALL' ? planningPriority : undefined,
          final_approval: planningApproval !== 'ALL' ? planningApproval : undefined,
          search: planningSearch || undefined,
        }),
        ordersClient.getPlanningSummary(activeUnit || undefined),
      ]);
      setPlanningLines(lines);
      setPlanningSummary(sum);
    } catch (err) {
      console.error('Failed to load order planning data:', err);
    } finally {
      setIsPlanningLoading(false);
    }
  }, [canRead, isLoading, activeUnit, planningPriority, planningApproval, planningSearch]);

  // Load Master data for creation dropdowns
  const loadMasterData = useCallback(async () => {
    try {
      const [cRes, pRes] = await Promise.all([
        masterClient.list<Customer>('customers', { page: 1, page_size: 100 }),
        masterClient.list<FinishedProduct>('products', { page: 1, page_size: 100 }),
      ]);
      setCustomers(cRes.items);
      setProducts(pRes.items);
    } catch (err) {
      console.error('Failed to load customers or products:', err);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && canRead) {
      fetchDashboardMetrics();
    }
  }, [fetchDashboardMetrics, isLoading, canRead]);

  useEffect(() => {
    if (!isLoading && canRead && activeTab === 'ORDERS') {
      fetchOrders();
    }
  }, [fetchOrders, isLoading, canRead, activeTab]);

  useEffect(() => {
    if (!isLoading && canRead && activeTab === 'PLANNING') {
      fetchPlanning();
    }
  }, [fetchPlanning, isLoading, canRead, activeTab]);

  const handleSavePlanningItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem?.id) return;
    try {
      setIsSavingPlan(true);
      await ordersClient.updatePlanningItem(editingItem.id, {
        planned_qty: Number(editingItem.planned_qty),
        produced_qty: Number(editingItem.produced_qty),
        dispatch_qty: Number(editingItem.dispatch_qty),
        priority: editingItem.priority,
        final_approval: editingItem.final_approval,
        order_status: editingItem.order_status,
        remarks: editingItem.remarks,
        required_dispatch_date: editingItem.required_dispatch_date,
      });
      setIsEditModalOpen(false);
      setEditingItem(null);
      await fetchPlanning();
    } catch (err) {
      console.error('Failed to update planning line:', err);
      alert('Failed to save changes. Please try again.');
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleExportCSV = () => {
    if (!planningLines.length) return;
    const headers = [
      'Order No.',
      'Order Date',
      'Customer',
      'Brand',
      'Variant',
      'Length',
      'Order Qty',
      'Required Dispatch Date',
      'Priority',
      'Order Status',
      'Planned Qty',
      'Produced Qty',
      'Balance Qty',
      'Dispatch Qty',
      'Dispatch Balance',
      'Final Approval',
      'Remarks',
    ];
    const rows = planningLines.map((row) => [
      `"${row.order_number}"`,
      `"${row.order_date}"`,
      `"${row.customer.replace(/"/g, '""')}"`,
      `"${row.brand}"`,
      `"${row.variant.replace(/"/g, '""')}"`,
      `"${row.length}"`,
      row.order_qty,
      `"${row.required_dispatch_date || ''}"`,
      `"${row.priority}"`,
      `"${row.order_status}"`,
      row.planned_qty,
      row.produced_qty,
      row.balance_qty,
      row.dispatch_qty,
      row.dispatch_balance,
      `"${row.final_approval}"`,
      `"${(row.remarks || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Order_Planning_Taha_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    if (isCreateOpen) {
      loadMasterData();
    }
  }, [isCreateOpen, loadMasterData]);

  useEffect(() => {
    if (activeUnit) {
      setOrderUnit(activeUnit);
    }
  }, [activeUnit]);

  // Handle Add Line Item
  const handleAddLineItem = () => {
    if (products.length === 0) return;
    const defaultProduct = products[0];
    setOrderItems([
      ...orderItems,
      {
        product_id: defaultProduct.id,
        product_code: defaultProduct.code,
        product_name: defaultProduct.name,
        uom: defaultProduct.uom || 'PCS',
        quantity: 1,
        unit_price: defaultProduct.selling_price || 0,
        discount_percent: 0,
        tax_percent: 18,
      },
    ]);
  };

  const handleUpdateItem = (index: number, field: string, value: unknown) => {
    const updated = [...orderItems];
    if (field === 'product_id') {
      const selected = products.find((p) => p.id === value);
      if (selected) {
        updated[index].product_id = selected.id;
        updated[index].product_code = selected.code;
        updated[index].product_name = selected.name;
        updated[index].uom = selected.uom || 'PCS';
        updated[index].unit_price = selected.selling_price || 0;
      }
    } else {
      (updated[index] as Record<string, unknown>)[field] = value;
    }
    setOrderItems(updated);
  };

  const handleRemoveItem = (index: number) => {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  };

  // Handle Create Order Submit
  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!orderCustomer) {
      setFormError('Please select a customer.');
      return;
    }
    if (orderItems.length === 0) {
      setFormError('At least one finished product line item is required.');
      return;
    }

    try {
      setCreateSubmitting(true);
      await ordersClient.createOrder({
        customer_id: orderCustomer,
        customer_po_number: orderPoNumber || undefined,
        unit_id: orderUnit,
        delivery_due_date: orderDeliveryDate || undefined,
        items: orderItems.map((item) => ({
          ...item,
          quantity: Number(item.quantity) || 1,
          unit_price: Number(item.unit_price) || 0,
          discount_percent: Number(item.discount_percent) || 0,
          tax_percent: Number(item.tax_percent) || 18,
        })),
        notes: orderNotes || undefined,
      });

      setIsCreateOpen(false);
      setOrderCustomer('');
      setOrderPoNumber('');
      setOrderDeliveryDate('');
      setOrderNotes('');
      setOrderItems([]);
      fetchOrders();
      fetchDashboardMetrics();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create sales order';
      setFormError(msg);
    } finally {
      setCreateSubmitting(false);
    }
  };

  const getStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="neutral">DRAFT</Badge>;
      case 'SUBMITTED':
        return <Badge variant="warning">SUBMITTED</Badge>;
      case 'CONFIRMED':
        return <Badge variant="warning" className="font-semibold text-[#254936] bg-[#EAF0E9] border-[#315C45]/20">CONFIRMED</Badge>;
      case 'PARTIALLY_DISPATCHED':
        return <Badge variant="warning">PARTIAL DISPATCH</Badge>;
      case 'DISPATCHED':
        return <Badge variant="success">DISPATCHED</Badge>;
      case 'CANCELLED':
        return <Badge variant="error">CANCELLED</Badge>;
    }
  };

  const columns: Column<SalesOrder>[] = [
    {
      key: 'order_number',
      header: 'Order # & Date',
      render: (row) => (
        <div>
          <Link
            href={`/orders/${row.id}`}
            className="font-semibold text-[#315C45] hover:text-blue-800 hover:underline"
          >
            {row.order_number}
          </Link>
          <div className="text-[11px] text-slate-400">
            {new Date(row.order_date).toLocaleDateString()}
          </div>
        </div>
      ),
    },
    {
      key: 'customer',
      header: 'Customer',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900  flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            {row.customer_name}
          </div>
          <div className="text-[11px] text-slate-400">
            {row.customer_code} {row.customer_po_number ? `• PO: ${row.customer_po_number}` : ''}
          </div>
        </div>
      ),
    },
    {
      key: 'financials',
      header: 'Order Valuation',
      render: (row) => (
        <div>
          <div className="font-bold text-slate-900 ">
            ₹{Number(row.grand_total ?? 0).toLocaleString('en-IN')}
          </div>
          <div className="text-[10px] text-slate-400">
            {row.items?.length ?? 0} product line(s)
          </div>
        </div>
      ),
    },
    {
      key: 'dispatch_status',
      header: 'Dispatch Progress',
      render: (row) => (
        <div className="space-y-1 min-w-[130px]">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-medium text-slate-700 ">
              {row.total_dispatched_qty} / {row.total_ordered_qty}
            </span>
            <span className="font-bold text-[#315C45]">{row.dispatch_percent}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100  rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${row.status === 'DISPATCHED'
                ? 'bg-emerald-500'
                : row.dispatch_percent > 0
                  ? 'bg-amber-500'
                  : 'bg-slate-300 bg-slate-700'
                }`}
              style={{ width: `${row.dispatch_percent}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => getStatusBadge(row.status),
    },
    {
      key: 'unit_id',
      header: 'Plant',
      render: (row) => (
        <Badge variant={row.unit_id === 'Unit_1' ? 'neutral' : 'warning'} className="text-[10px]">
          {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : 'Unit 2 (Assembly & QC)'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (row) => (
        <Link
          href={`/orders/${row.id}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-[#315C45] hover:text-blue-800"
        >
          Manage
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      ),
    },
  ];

  if (!isLoading && !canRead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Access Restricted</h2>
        <p className="text-sm text-slate-600  mt-2">
          You do not possess the required <code>orders:read</code> permission to view Sales Orders.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white  border border-[#E7E5DE]  rounded-xl p-6 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900  tracking-tight">
            Sales Orders & Dispatch Management
          </h1>
          <p className="text-xs text-slate-500  mt-1">
            Track customer machine orders, verify stock availability, issue packing slips, and log dispatches for{' '}
            <span className="font-semibold text-[#315C45] text-blue-400">
              {activeUnit ? activeUnit.replace('_', ' ') : 'All Units'}
            </span>.
          </p>
        </div>
        {canCreate && (
          <Button
            onClick={() => {
              setIsCreateOpen(true);
              if (orderItems.length === 0) handleAddLineItem();
            }}
            className="flex items-center gap-2 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            Create Sales Order
          </Button>
        )}
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-[#E7E5DE] pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('ORDERS')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'ORDERS'
              ? 'bg-[#315C45] text-white shadow-sm'
              : 'bg-white text-slate-600 border border-[#E7E5DE] hover:bg-slate-50'
            }`}
        >
          <ShoppingCart className="w-3.5 h-3.5" />
          Sales Orders Master
          <span className="text-[10px] ml-1 px-1.5 py-0.5 rounded-full bg-slate-200/60 font-semibold">
            {metrics?.total_orders ?? orders.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('PLANNING')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'PLANNING'
              ? 'bg-[#315C45] text-white shadow-sm'
              : 'bg-white text-slate-600 border border-[#E7E5DE] hover:bg-slate-50'
            }`}
        >
          <ClipboardList className="w-3.5 h-3.5" />
          Order Planning (By Variant & Length)
          <span className="text-[10px] ml-1 px-1.5 py-0.5 rounded-full bg-slate-200/60 font-semibold">
            {planningSummary?.total_planning_lines ?? planningLines.length}
          </span>
        </button>
      </div>

      {/* TAB 1: SALES ORDERS MASTER */}
      {activeTab === 'ORDERS' && (
        <div className="space-y-6">
          {/* Dashboard KPI Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#EAF0E9] bg-blue-950/40 text-[#315C45] text-blue-400 flex items-center justify-center shrink-0">
                <ShoppingCart className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500">Total Orders</p>
                <h3 className="text-2xl font-bold text-slate-900 ">
                  {isMetricsLoading ? '—' : metrics?.total_orders ?? 0}
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {metrics?.confirmed_orders ?? 0} ready to pack & dispatch
                </p>
              </div>
            </Card>

            <Card className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-50 bg-amber-950/40 text-amber-600 text-amber-400 flex items-center justify-center shrink-0">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500">In Progress Dispatches</p>
                <h3 className="text-2xl font-bold text-slate-900 ">
                  {isMetricsLoading ? '—' : metrics?.partially_dispatched_orders ?? 0}
                </h3>
                <p className="text-[11px] text-amber-600 font-medium mt-0.5">Partial shipments out</p>
              </div>
            </Card>

            <Card className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 bg-emerald-950/40 text-emerald-600 text-emerald-400 flex items-center justify-center shrink-0">
                <Truck className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500">Fully Dispatched</p>
                <h3 className="text-2xl font-bold text-slate-900 ">
                  {isMetricsLoading ? '—' : metrics?.fully_dispatched_orders ?? 0}
                </h3>
                <p className="text-[11px] text-emerald-600 font-medium mt-0.5">100% fulfilled orders</p>
              </div>
            </Card>

            <Card className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-50 bg-purple-950/40 text-purple-600 text-purple-400 flex items-center justify-center shrink-0">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500">Active Order Value</p>
                <h3 className="text-2xl font-bold text-slate-900 ">
                  ₹{isMetricsLoading ? '—' : (metrics?.total_pipeline_value ?? 0).toLocaleString('en-IN')}
                </h3>
                <p className="text-[11px] text-purple-600 font-medium mt-0.5">Committed sales pipeline</p>
              </div>
            </Card>
          </div>

          {/* Filter and Search Bar */}
          <FilterBar
            searchQuery={searchQuery}
            onSearchChange={(q) => {
              setSearchQuery(q);
              setPage(1);
            }}
            placeholder="Search by order #, customer, code, or PO#..."
            onReset={() => {
              setSearchQuery('');
              setSelectedStatus('ALL');
              setPage(1);
            }}
          >
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700  focus:outline-none focus:ring-1 focus:ring-[#315C45]"
            >
              {ORDER_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </FilterBar>

          {/* Orders Table */}
          <DataTable
            columns={columns}
            data={orders}
            isLoading={isLoadingOrders}
            keyExtractor={(r) => r.id}
            emptyTitle="No sales orders found"
            emptyDescription="There are currently no sales orders matching your filter criteria."
          />

          {/* Pagination */}
          {totalOrders > pageSize && (
            <div className="flex items-center justify-between text-xs text-slate-500 px-2">
              <span>
                Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalOrders)} of {totalOrders} orders
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * pageSize >= totalOrders}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ORDER PLANNING (BY VARIANT AND LENGTH) */}
      {/* Updated by Taha; one line per variant and length */}
      {activeTab === 'PLANNING' && (
        <div className="space-y-6">
          {/* Order Planning Header Banner & Actions */}
          <div className="bg-[#FAF8F5] text-slate-800 rounded-xl p-5 shadow-xs border border-[#E7E5DE]">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Production Control Matrix
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    Updated by Taha; one line per variant and length
                  </span>
                </div>
                <h2 className="text-xl font-bold tracking-tight text-slate-900 mt-1.5 flex items-center gap-2">
                  <ClipboardList className="w-5 h-5 text-emerald-700" />
                  Order Planning
                </h2>
                <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                  Granular shop-floor manufacturing schedule per variant and cut length. Live dynamic balance tracking
                  for produced quantities and final dispatches across all client orders.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportCSV}
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
                  Print Matrix
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    await ordersClient.syncPlanning();
                    await fetchPlanning();
                  }}
                  className="bg-emerald-700 hover:bg-emerald-800 text-white border-transparent text-xs flex items-center gap-1.5 font-semibold shadow-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Sync From Orders
                </Button>
              </div>
            </div>
          </div>

          {/* Planning Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Planning Lines</p>
              <h3 className="text-xl font-bold text-slate-900 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_planning_lines ?? 0}
              </h3>
              <p className="text-[10px] text-slate-400 mt-0.5">Variant & Length Rows</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Order Qty</p>
              <h3 className="text-xl font-bold text-slate-900 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_order_qty ?? 0}
              </h3>
              <p className="text-[10px] text-blue-600 font-medium mt-0.5">Total booked units</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Planned Qty</p>
              <h3 className="text-xl font-bold text-indigo-700 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_planned_qty ?? 0}
              </h3>
              <p className="text-[10px] text-indigo-600 font-medium mt-0.5">Production scheduled</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Produced Qty</p>
              <h3 className="text-xl font-bold text-emerald-700 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_produced_qty ?? 0}
              </h3>
              <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Shop floor output</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Balance Qty</p>
              <h3 className="text-xl font-bold text-amber-700 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_balance_qty ?? 0}
              </h3>
              <p className="text-[10px] text-amber-600 font-medium mt-0.5">To be produced</p>
            </Card>

            <Card className="p-3.5 bg-white border border-[#E7E5DE]">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Dispatch Balance</p>
              <h3 className="text-xl font-bold text-rose-700 mt-1">
                {isPlanningLoading ? '—' : planningSummary?.total_dispatch_balance ?? 0}
              </h3>
              <p className="text-[10px] text-rose-600 font-medium mt-0.5">Pending dispatch</p>
            </Card>
          </div>

          {/* Planning Filter Bar */}
          <div className="bg-white border border-[#E7E5DE] rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-2 flex-1 min-w-[260px]">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter by Order No., Customer, Brand, Variant, or Length..."
                  value={planningSearch}
                  onChange={(e) => setPlanningSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={planningPriority}
                onChange={(e) => setPlanningPriority(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
              >
                <option value="ALL">All Priorities</option>
                <option value="URGENT">Urgent</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={planningApproval}
                onChange={(e) => setPlanningApproval(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-[#315C45]"
              >
                <option value="ALL">All Approvals</option>
                <option value="APPROVED">Approved</option>
                <option value="PENDING">Pending</option>
                <option value="ON_HOLD">On Hold</option>
              </select>

              {(planningSearch || planningPriority !== 'ALL' || planningApproval !== 'ALL') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPlanningSearch('');
                    setPlanningPriority('ALL');
                    setPlanningApproval('ALL');
                  }}
                  className="text-xs"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </div>

          {/* Planning Matrix Table (17 Columns Matching Requested Spreadsheet) */}
          <div className="bg-white border border-[#E7E5DE] rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100/90 text-slate-700 border-b border-[#E7E5DE] whitespace-nowrap text-[11px] font-semibold uppercase tracking-wider">
                    <th className="py-3 px-3">Order No.</th>
                    <th className="py-3 px-3">Order Date</th>
                    <th className="py-3 px-3 min-w-[160px]">Customer</th>
                    <th className="py-3 px-3">Brand</th>
                    <th className="py-3 px-3 min-w-[200px]">Variant</th>
                    <th className="py-3 px-3">Length</th>
                    <th className="py-3 px-3 text-right">Order Qty</th>
                    <th className="py-3 px-3">Req. Dispatch Date</th>
                    <th className="py-3 px-3">Priority</th>
                    <th className="py-3 px-3">Order Status</th>
                    <th className="py-3 px-3 text-right">Planned Qty</th>
                    <th className="py-3 px-3 text-right">Produced Qty</th>
                    <th className="py-3 px-3 text-right">Balance Qty</th>
                    <th className="py-3 px-3 text-right">Dispatch Qty</th>
                    <th className="py-3 px-3 text-right">Dispatch Balance</th>
                    <th className="py-3 px-3">Final Approval</th>
                    <th className="py-3 px-3 min-w-[220px]">Remarks</th>
                    <th className="py-3 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E7E5DE]">
                  {isPlanningLoading ? (
                    <tr>
                      <td colSpan={18} className="py-12 text-center text-slate-400">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#315C45]" />
                        Loading Order Planning lines...
                      </td>
                    </tr>
                  ) : planningLines.length === 0 ? (
                    <tr>
                      <td colSpan={18} className="py-12 text-center text-slate-500">
                        <ClipboardList className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                        No order planning records found. Click &quot;Sync From Orders&quot; to populate.
                      </td>
                    </tr>
                  ) : (
                    planningLines.map((row, idx) => (
                      <tr
                        key={row.id || idx}
                        className="hover:bg-emerald-50/40 transition-colors whitespace-nowrap"
                      >
                        <td className="py-2.5 px-3 font-bold text-slate-900">
                          {row.order_id ? (
                            <Link href={`/orders/${row.order_id}`} className="hover:text-[#315C45] hover:underline">
                              {row.order_number}
                            </Link>
                          ) : (
                            row.order_number
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">{row.order_date}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-800 max-w-[200px] truncate" title={row.customer}>
                          {row.customer}
                        </td>
                        <td className="py-2.5 px-3 text-slate-700">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                            {row.brand}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-900 max-w-[240px] truncate" title={row.variant}>
                          {row.variant}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">{row.length}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-slate-900">{row.order_qty}</td>
                        <td className="py-2.5 px-3 text-slate-600">{row.required_dispatch_date || '—'}</td>
                        <td className="py-2.5 px-3">
                          <Badge
                            variant={
                              row.priority === 'URGENT'
                                ? 'error'
                                : row.priority === 'HIGH'
                                  ? 'warning'
                                  : row.priority === 'LOW'
                                    ? 'neutral'
                                    : 'neutral'
                            }
                            className="text-[10px]"
                          >
                            {row.priority}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="text-[11px] font-medium text-slate-700">{row.order_status}</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-indigo-700">{row.planned_qty}</td>
                        <td className="py-2.5 px-3 text-right font-semibold text-emerald-700">{row.produced_qty}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-amber-700">
                          {row.balance_qty}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-blue-700">{row.dispatch_qty}</td>
                        <td className="py-2.5 px-3 text-right font-bold text-rose-700">
                          {row.dispatch_balance}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${row.final_approval === 'APPROVED'
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : row.final_approval === 'PENDING'
                                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                  : 'bg-rose-100 text-rose-800 border border-rose-300'
                              }`}
                          >
                            {row.final_approval === 'APPROVED' && <Check className="w-3 h-3" />}
                            {row.final_approval}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 text-[11px] max-w-[240px] truncate" title={row.remarks || ''}>
                          {row.remarks || '—'}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingItem({ ...row });
                              setIsEditModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-[#315C45] hover:bg-emerald-100 transition-colors"
                          >
                            <Edit className="w-3 h-3" />
                            Edit
                          </button>
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
                <span className="font-semibold text-slate-700">Order Planning Matrix:</span>
                <span>Updated by Taha; one line per variant and length.</span>
              </div>
              <div>
                Formula rules applied: <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">Balance Qty = Order Qty - Produced Qty</code> | <code className="bg-slate-200 px-1 py-0.5 rounded text-[10px]">Dispatch Balance = Order Qty - Dispatch Qty</code>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Planning Line Modal */}
      <Dialog
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingItem(null);
        }}
        title={`Update Order Planning: ${editingItem?.order_number || ''}`}
      >
        {editingItem && (
          <form onSubmit={handleSavePlanningItem} className="space-y-4 pt-2">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Customer:</span>
                <span className="font-semibold text-slate-800">{editingItem.customer}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Variant & Length:</span>
                <span className="font-semibold text-slate-800">
                  {editingItem.variant} ({editingItem.length})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Order Qty:</span>
                <span className="font-bold text-[#315C45]">{editingItem.order_qty} Units</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Planned Qty
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingItem.planned_qty}
                  onChange={(e) =>
                    setEditingItem({ ...editingItem, planned_qty: parseFloat(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Produced Qty
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingItem.produced_qty}
                  onChange={(e) => {
                    const pr = parseFloat(e.target.value) || 0;
                    setEditingItem({
                      ...editingItem,
                      produced_qty: pr,
                      balance_qty: Math.max(0, editingItem.order_qty - pr),
                    });
                  }}
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Dispatch Qty
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={editingItem.dispatch_qty}
                  onChange={(e) => {
                    const dq = parseFloat(e.target.value) || 0;
                    setEditingItem({
                      ...editingItem,
                      dispatch_qty: dq,
                      dispatch_balance: Math.max(0, editingItem.order_qty - dq),
                    });
                  }}
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Priority
                </label>
                <select
                  value={editingItem.priority}
                  onChange={(e) => setEditingItem({ ...editingItem, priority: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                >
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                  <option value="URGENT">URGENT</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Final Approval
                </label>
                <select
                  value={editingItem.final_approval}
                  onChange={(e) => setEditingItem({ ...editingItem, final_approval: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="PENDING">PENDING</option>
                  <option value="ON_HOLD">ON_HOLD</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Req. Dispatch Date
                </label>
                <input
                  type="date"
                  value={editingItem.required_dispatch_date || ''}
                  onChange={(e) =>
                    setEditingItem({ ...editingItem, required_dispatch_date: e.target.value })
                  }
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Remarks / Engineering & Shop-floor Notes
              </label>
              <textarea
                rows={2}
                value={editingItem.remarks || ''}
                onChange={(e) => setEditingItem({ ...editingItem, remarks: e.target.value })}
                placeholder="Shop floor progress, sub-assembly state, tooling or material delays..."
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE] bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8]">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingItem(null);
                }}
                disabled={isSavingPlan}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingPlan}>
                {isSavingPlan ? 'Saving Changes...' : 'Save Planning Line'}
              </Button>
            </div>
          </form>
        )}
      </Dialog>

      {/* Create Sales Order Modal */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Sales Order"
        description="Select customer, originating manufacturing facility, and finished product line items."
        maxWidth="xl"
      >
        <form onSubmit={handleCreateOrder} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Customer Master *
              </label>
              <select
                required
                value={orderCustomer}
                onChange={(e) => setOrderCustomer(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              >
                <option value="">Select customer...</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Customer PO #
              </label>
              <input
                type="text"
                value={orderPoNumber}
                onChange={(e) => setOrderPoNumber(e.target.value)}
                placeholder="e.g. PO-2026-904"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Committed Delivery Due Date
              </label>
              <input
                type="date"
                value={orderDeliveryDate}
                onChange={(e) => setOrderDeliveryDate(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>
          </div>

          {/* Line Items Builder */}
          <div className="border border-[#E7E5DE]  rounded-xl p-4 bg-slate-50 /40 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900  uppercase tracking-wider">
                Finished Product Items ({orderItems.length})
              </h4>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleAddLineItem}
                className="text-[11px] py-1 px-2.5"
              >
                + Add Item
              </Button>
            </div>

            {orderItems.map((item, idx) => (
              <div
                key={idx}
                className="grid grid-cols-12 gap-2 items-center bg-white  p-2.5 rounded-lg border border-[#E7E5DE]  text-xs"
              >
                <div className="col-span-5">
                  <label className="block text-[10px] text-slate-400 mb-0.5">Product</label>
                  <select
                    value={item.product_id}
                    onChange={(e) => handleUpdateItem(idx, 'product_id', e.target.value)}
                    className="w-full p-1.5 rounded border border-[#E7E5DE]  bg-white  text-xs"
                  >
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.code} — {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-span-2">
                  <label className="block text-[10px] text-slate-400 mb-0.5">Qty ({item.uom})</label>
                  <input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => handleUpdateItem(idx, 'quantity', Number(e.target.value))}
                    className="w-full p-1.5 rounded border border-[#E7E5DE]  bg-white  text-xs"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-[10px] text-slate-400 mb-0.5">Price (₹)</label>
                  <input
                    type="number"
                    min="0"
                    value={item.unit_price}
                    onChange={(e) => handleUpdateItem(idx, 'unit_price', Number(e.target.value))}
                    className="w-full p-1.5 rounded border border-[#E7E5DE]  bg-white  text-xs"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-[10px] text-slate-400 mb-0.5">Tax %</label>
                  <input
                    type="number"
                    min="0"
                    max="40"
                    value={item.tax_percent}
                    onChange={(e) => handleUpdateItem(idx, 'tax_percent', Number(e.target.value))}
                    className="w-full p-1.5 rounded border border-[#E7E5DE]  bg-white  text-xs"
                  />
                </div>

                <div className="col-span-1 flex justify-end pt-3">
                  <button
                    type="button"
                    onClick={() => handleRemoveItem(idx)}
                    className="text-slate-400 hover:text-rose-600 p-1 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Order Notes & Commercial Instructions
            </label>
            <textarea
              rows={2}
              value={orderNotes}
              onChange={(e) => setOrderNotes(e.target.value)}
              placeholder="Commercial terms, machine calibration notes, inspection certificates required..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
              disabled={createSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createSubmitting}>
              {createSubmitting ? 'Saving Order...' : 'Create Sales Order'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
