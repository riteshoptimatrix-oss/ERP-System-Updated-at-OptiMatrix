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
    if (!isLoading && canRead) {
      fetchOrders();
    }
  }, [fetchOrders, isLoading, canRead]);

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
