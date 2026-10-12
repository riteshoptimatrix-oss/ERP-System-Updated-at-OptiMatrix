'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { ordersClient } from '@/services/orders-client';
import {
  SalesOrder,
  OrderStatus,
  PackingSlip,
  DispatchRecord,
  StockAvailabilityResult,
} from '@/types/orders';
import {
  ArrowLeft,
  Building2,
  Calendar,
  Truck,
  CheckCircle2,
  Clock,
  ShieldAlert,
  AlertCircle,
  FileText,
  Send,
  Boxes,
  PackageCheck,
  Ban,
  Printer,
  ChevronRight,
  Info,
} from 'lucide-react';
import { formatISTDateTime } from '@/lib/date';

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;

  const { hasPermission, user } = useAuth();
  const canRead = hasPermission('orders', 'read');
  const canUpdate = hasPermission('orders', 'update');
  const canCreateSales = hasPermission('sales', 'create');
  const canPostSales = hasPermission('sales', 'post');

  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [packingSlips, setPackingSlips] = useState<PackingSlip[]>([]);
  const [dispatches, setDispatches] = useState<DispatchRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Packing Slip Modal State
  const [isPackingModalOpen, setIsPackingModalOpen] = useState(false);
  const [packingSubmitting, setPackingSubmitting] = useState(false);
  const [packingError, setPackingError] = useState<string | null>(null);
  const [packagesCount, setPackagesCount] = useState(1);
  const [grossWeight, setGrossWeight] = useState<number | undefined>(undefined);
  const [handlingNotes, setHandlingNotes] = useState('');
  const [packItems, setPackItems] = useState<{ [productCode: string]: number }>({});

  // Dispatch Modal State
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  const [dispatchSubmitting, setDispatchSubmitting] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [selectedPackingSlipId, setSelectedPackingSlipId] = useState('');
  const [carrierName, setCarrierName] = useState('');
  const [vehicleNumber, setVehicleNumber] = useState('');
  const [lrNumber, setLrNumber] = useState('');
  const [driverName, setDriverName] = useState('');
  const [driverPhone, setDriverPhone] = useState('');
  const [dispatchRemarks, setDispatchRemarks] = useState('');
  const [dispatchItems, setDispatchItems] = useState<{ [productCode: string]: number }>({});

  // Cancel Modal State
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  // Stock check state
  const [stockCheckMap, setStockCheckMap] = useState<{ [productId: string]: StockAvailabilityResult }>({});

  // Load Order, Packing Slips & Dispatches
  const loadOrderData = useCallback(async () => {
    if (!orderId || !canRead) return;
    try {
      setIsLoading(true);
      setError(null);
      const [oData, psData, dspData] = await Promise.all([
        ordersClient.getOrder(orderId),
        ordersClient.listPackingSlips(orderId),
        ordersClient.listDispatches(orderId),
      ]);
      setOrder(oData);
      setPackingSlips(psData);
      setDispatches(dspData);

      // Pre-fill pack quantities with remaining quantities
      const initialPack: { [k: string]: number } = {};
      const initialDsp: { [k: string]: number } = {};
      oData.items.forEach((item) => {
        const rem = Math.max(0, item.quantity - item.dispatched_quantity);
        initialPack[item.product_code] = rem;
        initialDsp[item.product_code] = rem;
      });
      setPackItems(initialPack);
      setDispatchItems(initialDsp);

      // Check stock contract for all products
      const stockResults: { [productId: string]: StockAvailabilityResult } = {};
      for (const it of oData.items) {
        try {
          const res = await ordersClient.checkStock(it.product_id, oData.unit_id, it.quantity);
          stockResults[it.product_id] = res;
        } catch {
          // Handled gracefully
        }
      }
      setStockCheckMap(stockResults);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load order details');
    } finally {
      setIsLoading(false);
    }
  }, [orderId, canRead]);

  useEffect(() => {
    loadOrderData();
  }, [loadOrderData]);

  // Stage Transitions
  const handleSubmitOrder = async () => {
    if (!order) return;
    try {
      await ordersClient.submitOrder(order.id);
      await loadOrderData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Submission failed');
    }
  };

  const handleConfirmOrder = async () => {
    if (!order) return;
    try {
      await ordersClient.confirmOrder(order.id);
      await loadOrderData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Confirmation failed');
    }
  };

  const handleCancelOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order || !cancelReason.trim()) return;
    try {
      setCancelSubmitting(true);
      await ordersClient.cancelOrder(order.id, cancelReason);
      setIsCancelModalOpen(false);
      await loadOrderData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Cancellation failed');
    } finally {
      setCancelSubmitting(false);
    }
  };

  // Generate Packing Slip
  const handleGeneratePackingSlip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setPackingError(null);

    const itemsToPack = order.items
      .filter((it) => (packItems[it.product_code] || 0) > 0)
      .map((it) => ({
        product_id: it.product_id,
        product_code: it.product_code,
        product_name: it.product_name,
        ordered_quantity: it.quantity,
        pack_quantity: Number(packItems[it.product_code]),
        package_type: 'WOODEN_CRATE',
      }));

    if (itemsToPack.length === 0) {
      setPackingError('Please specify pack quantity for at least one item.');
      return;
    }

    try {
      setPackingSubmitting(true);
      await ordersClient.createPackingSlip(order.id, {
        items: itemsToPack,
        packages_count: packagesCount,
        gross_weight_kg: grossWeight,
        special_handling_notes: handlingNotes || undefined,
      });
      setIsPackingModalOpen(false);
      await loadOrderData();
    } catch (err: unknown) {
      setPackingError(err instanceof Error ? err.message : 'Failed to generate packing slip');
    } finally {
      setPackingSubmitting(false);
    }
  };

  // Post Dispatch Record
  const handlePostDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setDispatchError(null);

    const itemsToDispatch = order.items
      .filter((it) => (dispatchItems[it.product_code] || 0) > 0)
      .map((it) => ({
        product_id: it.product_id,
        product_code: it.product_code,
        product_name: it.product_name,
        quantity: Number(dispatchItems[it.product_code]),
      }));

    if (itemsToDispatch.length === 0) {
      setDispatchError('Please specify dispatch quantity for at least one item.');
      return;
    }

    try {
      setDispatchSubmitting(true);
      await ordersClient.postDispatch(order.id, {
        packing_slip_id: selectedPackingSlipId || undefined,
        carrier_name: carrierName,
        vehicle_number: vehicleNumber,
        lr_number: lrNumber || undefined,
        driver_name: driverName || undefined,
        driver_phone: driverPhone || undefined,
        items: itemsToDispatch,
        remarks: dispatchRemarks || undefined,
      });
      setIsDispatchModalOpen(false);
      setCarrierName('');
      setVehicleNumber('');
      setLrNumber('');
      setDriverName('');
      setDriverPhone('');
      await loadOrderData();
    } catch (err: unknown) {
      setDispatchError(err instanceof Error ? err.message : 'Dispatch posting failed');
    } finally {
      setDispatchSubmitting(false);
    }
  };

  if (!canRead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Access Restricted</h2>
        <p className="text-sm text-slate-600  mt-2">
          You do not possess the required <code>orders:read</code> permission to view this order.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="w-8 h-8 border-2 border-[#315C45] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading order tracking telemetry and dispatch records...</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <AlertCircle className="w-12 h-12 text-rose-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Order Not Found</h2>
        <p className="text-sm text-slate-600  mt-2">{error || 'Order record missing.'}</p>
        <div className="mt-6">
          <Button onClick={() => router.push('/orders')}>Return to Orders Hub</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Status Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/orders"
            className="p-2 rounded-lg border border-[#E7E5DE]  hover:bg-slate-50  text-slate-600  transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900  tracking-tight">
                {order.order_number}
              </h1>
              <Badge
                variant={
                  order.status === 'DISPATCHED'
                    ? 'success'
                    : order.status === 'CANCELLED'
                      ? 'error'
                      : 'warning'
                }
              >
                {order.status.replace('_', ' ')}
              </Badge>
              <Badge variant={order.unit_id === 'Unit_1' ? 'neutral' : 'warning'}>
                {order.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : order.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Customer: <span className="font-semibold text-slate-800 ">{order.customer_name}</span> ({order.customer_code}) • Placed {new Date(order.order_date).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Action Buttons depending on status */}
        <div className="flex items-center gap-2 flex-wrap">
          {order.status === 'DRAFT' && canUpdate && (
            <Button onClick={handleSubmitOrder} className="bg-[#315C45] hover:bg-[#254936] text-white">
              <Send className="w-4 h-4 mr-1.5" />
              Submit Order
            </Button>
          )}

          {order.status === 'SUBMITTED' && canUpdate && (
            <Button onClick={handleConfirmOrder} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <CheckCircle2 className="w-4 h-4 mr-1.5" />
              Confirm & Authorize
            </Button>
          )}

          {(order.status === 'CONFIRMED' || order.status === 'PARTIALLY_DISPATCHED') && (
            <>
              {canCreateSales && (
                <Button variant="outline" onClick={() => setIsPackingModalOpen(true)}>
                  <FileText className="w-4 h-4 mr-1.5" />
                  Generate Packing Slip
                </Button>
              )}

              {canPostSales && (
                <Button
                  onClick={() => setIsDispatchModalOpen(true)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  <Truck className="w-4 h-4 mr-1.5" />
                  Post Dispatch
                </Button>
              )}
            </>
          )}

          {order.status !== 'DISPATCHED' &&
            order.status !== 'PARTIALLY_DISPATCHED' &&
            order.status !== 'CANCELLED' &&
            canUpdate && (
              <Button
                variant="outline"
                onClick={() => setIsCancelModalOpen(true)}
                className="text-rose-600 hover:bg-rose-50 border-rose-200"
              >
                <Ban className="w-4 h-4 mr-1.5" />
                Cancel Order
              </Button>
            )}
        </div>
      </div>

      {/* Dispatch Reconciliation Progress Card */}
      <Card className="p-4 bg-white ">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2 text-xs">
          <div>
            <span className="font-semibold text-slate-700 ">
              Fulfillment & Dispatch Progress:
            </span>{' '}
            <span className="font-mono text-slate-500">
              {order.total_dispatched_qty} of {order.total_ordered_qty} units shipped
            </span>
          </div>
          <div className="font-bold text-[#315C45] text-sm">{order.dispatch_percent}% Fulfilled</div>
        </div>
        <div className="w-full h-2.5 bg-slate-100  rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${order.status === 'DISPATCHED'
              ? 'bg-emerald-500'
              : order.dispatch_percent > 0
                ? 'bg-amber-500'
                : 'bg-slate-300'
              }`}
            style={{ width: `${order.dispatch_percent}%` }}
          />
        </div>
      </Card>

      {/* Main Grid: Line Items & Commercial Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left (2 cols): Ordered Finished Products Table */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="flex items-center justify-between border-b border-[#EFEEE8]  pb-3 mb-4">
              <h3 className="text-sm font-bold text-slate-900  flex items-center gap-2">
                <PackageCheck className="w-4 h-4 text-[#315C45]" />
                Ordered Machinery & Finished Products ({order.items.length})
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 /60 border-b border-[#E7E5DE]  text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">Item / SKU</th>
                    <th className="py-2.5 px-3 text-right">Ordered</th>
                    <th className="py-2.5 px-3 text-right">Dispatched</th>
                    <th className="py-2.5 px-3 text-right">Remaining</th>
                    <th className="py-2.5 px-3 text-right">Unit Price</th>
                    <th className="py-2.5 px-3 text-right">Total</th>
                    <th className="py-2.5 px-3 text-center">Stock Check</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 divide-slate-800">
                  {order.items.map((it, idx) => {
                    const rem = Math.max(0, it.quantity - it.dispatched_quantity);
                    const stockResult = stockCheckMap[it.product_id];
                    const unitPrice = Number(it.unit_price || 0);
                    const lineTotal = Number(it.total_amount ?? (it.quantity * unitPrice));
                    return (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-3 px-3">
                          <div className="font-semibold text-slate-900 ">
                            {it.product_name}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">
                            {it.product_code} • {it.uom}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right font-medium">{it.quantity}</td>
                        <td className="py-3 px-3 text-right font-medium text-emerald-600">
                          {it.dispatched_quantity}
                        </td>
                        <td className="py-3 px-3 text-right font-bold text-amber-600">{rem}</td>
                        <td className="py-3 px-3 text-right font-mono">
                          ₹{unitPrice.toLocaleString('en-IN')}
                        </td>
                        <td className="py-3 px-3 text-right font-bold font-mono">
                          ₹{lineTotal.toLocaleString('en-IN')}
                        </td>
                        <td className="py-3 px-3 text-center">
                          {stockResult ? (
                            <Badge
                              variant={
                                stockResult.status === 'VERIFIED'
                                  ? 'success'
                                  : stockResult.status === 'INSUFFICIENT'
                                    ? 'error'
                                    : 'neutral'
                              }
                              className="text-[10px]"
                              title={stockResult.message}
                            >
                              {stockResult.status}
                            </Badge>
                          ) : (
                            <span className="text-[10px] text-slate-400">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Financial Totals */}
            <div className="mt-4 pt-4 border-t border-[#EFEEE8]  flex justify-end">
              <div className="w-64 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-500">
                  <span>Subtotal:</span>
                  <span className="font-mono">₹{Number(order.subtotal ?? 0).toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between text-slate-500">
                  <span>Taxes (GST):</span>
                  <span className="font-mono">₹{Number(order.tax_total ?? 0).toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between font-bold text-slate-900  text-sm pt-1.5 border-t border-[#E7E5DE] ">
                  <span>Grand Total:</span>
                  <span className="font-mono text-[#315C45]">
                    ₹{Number(order.grand_total ?? 0).toLocaleString('en-IN')}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Packing Slips & Dispatches Tabs / Accordions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Packing Slips Card */}
            <Card>
              <div className="flex items-center justify-between border-b border-[#EFEEE8]  pb-2 mb-3">
                <h4 className="text-xs font-bold text-slate-900  flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#315C45]" />
                  Packing Slips ({packingSlips.length})
                </h4>
              </div>
              {packingSlips.length === 0 ? (
                <p className="text-[11px] text-slate-400 py-4 text-center">
                  No packing slips generated yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {packingSlips.map((ps) => (
                    <div
                      key={ps.id}
                      className="p-2.5 rounded-lg border border-[#EFEEE8]  bg-slate-50 /40 text-xs"
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="text-[#315C45]">{ps.slip_number}</span>
                        <span className="text-slate-400 text-[10px]">
                          {new Date(ps.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">
                        {ps.packages_count} package(s) • {ps.items.length} item line(s)
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Dispatches Card */}
            <Card>
              <div className="flex items-center justify-between border-b border-[#EFEEE8]  pb-2 mb-3">
                <h4 className="text-xs font-bold text-slate-900  flex items-center gap-1.5">
                  <Truck className="w-3.5 h-3.5 text-emerald-600" />
                  Dispatch Shipments ({dispatches.length})
                </h4>
              </div>
              {dispatches.length === 0 ? (
                <p className="text-[11px] text-slate-400 py-4 text-center">
                  No dispatches posted yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {dispatches.map((dsp) => (
                    <div
                      key={dsp.id}
                      className="p-2.5 rounded-lg border border-[#EFEEE8]  bg-slate-50 /40 text-xs"
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span className="text-emerald-600">{dsp.dispatch_number}</span>
                        <span className="text-slate-400 text-[10px]">
                          {new Date(dsp.dispatched_date).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">
                        Vehicle: {dsp.vehicle_number} ({dsp.carrier_name}) • {dsp.total_quantity} unit(s)
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* Right (1 col): Commercial Details & Audit Timeline */}
        <div className="space-y-6">
          <Card className="space-y-3 text-xs">
            <h3 className="text-sm font-bold text-slate-900  border-b border-[#EFEEE8]  pb-2">
              Commercial & Delivery Profile
            </h3>

            <div>
              <span className="text-slate-400 block mb-0.5">Client PO Number</span>
              <div className="font-semibold text-slate-800 ">
                {order.customer_po_number || 'Direct Order (No PO Number)'}
              </div>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">Committed Due Date</span>
              <div className="font-semibold text-slate-800  flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                {order.delivery_due_date || 'Standard Lead Time'}
              </div>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">Shipping Address</span>
              <div className="text-slate-700  leading-relaxed">
                {order.shipping_address || 'Same as client billing location'}
              </div>
            </div>

            {order.notes && (
              <div>
                <span className="text-slate-400 block mb-0.5">Instructions & Notes</span>
                <p className="bg-slate-50 /40 p-2.5 rounded-lg text-slate-600  leading-relaxed">
                  {order.notes}
                </p>
              </div>
            )}
          </Card>

          {/* Audit Timeline */}
          <Card>
            <div className="flex items-center gap-2 border-b border-[#EFEEE8]  pb-2 mb-3">
              <Clock className="w-4 h-4 text-[#315C45]" />
              <h3 className="text-sm font-bold text-slate-900 ">
                Order Activity Audit Log
              </h3>
            </div>

            {!order.activities || order.activities.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No audit logs recorded.</p>
            ) : (
              <div className="relative pl-5 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 before:bg-slate-800 text-xs">
                {order.activities.map((act) => (
                  <div key={act.id} className="relative">
                    <div className="absolute -left-5 top-1 w-2.5 h-2.5 rounded-full bg-[#EAF0E9]0 ring-4 ring-white ring-slate-900" />
                    <div>
                      <p className="font-semibold text-slate-800 ">
                        {act.description}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        By {act.performed_by} • {formatISTDateTime(act.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Generate Packing Slip Modal */}
      <Dialog
        isOpen={isPackingModalOpen}
        onClose={() => setIsPackingModalOpen(false)}
        title="Generate Packing Slip"
        description="Verify product quantities packed into shipping crates or pallets."
        maxWidth="lg"
      >
        <form onSubmit={handleGeneratePackingSlip} className="space-y-4">
          {packingError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{packingError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold mb-1">Total Packages Count *</label>
              <input
                type="number"
                min="1"
                required
                value={packagesCount}
                onChange={(e) => setPackagesCount(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white "
              />
            </div>

            <div>
              <label className="block font-semibold mb-1">Gross Weight (Kg)</label>
              <input
                type="number"
                min="0"
                value={grossWeight ?? ''}
                onChange={(e) => setGrossWeight(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="e.g. 4500"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white "
              />
            </div>
          </div>

          <div className="border border-[#E7E5DE]  rounded-xl p-3 bg-slate-50  space-y-2">
            <h4 className="text-xs font-bold text-slate-700 ">
              Quantities to Pack for this Slip
            </h4>
            {order.items.map((item) => {
              const rem = Math.max(0, item.quantity - item.dispatched_quantity);
              return (
                <div
                  key={item.product_code}
                  className="flex items-center justify-between text-xs py-1.5 border-b border-[#EFEEE8]  last:border-0"
                >
                  <div>
                    <span className="font-semibold text-slate-800 ">
                      {item.product_name}
                    </span>
                    <span className="text-[11px] text-slate-400 block">
                      Remaining balance: {rem} {item.uom}
                    </span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    max={rem}
                    value={packItems[item.product_code] ?? 0}
                    onChange={(e) =>
                      setPackItems({
                        ...packItems,
                        [item.product_code]: Number(e.target.value),
                      })
                    }
                    className="w-24 px-2.5 py-1 text-xs rounded border border-[#E7E5DE]  bg-white  text-right"
                  />
                </div>
              );
            })}
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">Handling / Marking Notes</label>
            <input
              type="text"
              value={handlingNotes}
              onChange={(e) => setHandlingNotes(e.target.value)}
              placeholder="e.g. Top Heavy; Do Not Stack"
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white "
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsPackingModalOpen(false)}
              disabled={packingSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={packingSubmitting}>
              {packingSubmitting ? 'Generating...' : 'Confirm Packing Slip'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Post Dispatch Record Modal */}
      <Dialog
        isOpen={isDispatchModalOpen}
        onClose={() => setIsDispatchModalOpen(false)}
        title="Post Goods Dispatch & Transporter Details"
        description="Verify carrier information, vehicle number, and quantities loaded for transport."
        maxWidth="lg"
      >
        <form onSubmit={handlePostDispatch} className="space-y-4">
          {dispatchError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{dispatchError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold mb-1">Carrier / Transporter Name *</label>
              <input
                type="text"
                required
                value={carrierName}
                onChange={(e) => setCarrierName(e.target.value)}
                placeholder="e.g. VRL Logistics, GATI, Self-Pickup"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white "
              />
            </div>

            <div>
              <label className="block font-semibold mb-1">Vehicle Registration # *</label>
              <input
                type="text"
                required
                value={vehicleNumber}
                onChange={(e) => setVehicleNumber(e.target.value)}
                placeholder="e.g. MH-12-PQ-9874"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white  uppercase"
              />
            </div>

            <div>
              <label className="block font-semibold mb-1">LR / Consignment Note #</label>
              <input
                type="text"
                value={lrNumber}
                onChange={(e) => setLrNumber(e.target.value)}
                placeholder="LR-789456"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white "
              />
            </div>

            <div>
              <label className="block font-semibold mb-1">Driver Phone Number</label>
              <input
                type="tel"
                value={driverPhone}
                onChange={(e) => setDriverPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE]  bg-white "
              />
            </div>
          </div>

          <div className="border border-[#E7E5DE]  rounded-xl p-3 bg-slate-50  space-y-2">
            <h4 className="text-xs font-bold text-slate-700 ">
              Quantities Dispatched in this Shipment
            </h4>
            {order.items.map((item) => {
              const rem = Math.max(0, item.quantity - item.dispatched_quantity);
              return (
                <div
                  key={item.product_code}
                  className="flex items-center justify-between text-xs py-1.5 border-b border-[#EFEEE8]  last:border-0"
                >
                  <div>
                    <span className="font-semibold text-slate-800 ">
                      {item.product_name}
                    </span>
                    <span className="text-[11px] text-slate-400 block">
                      Max dispatchable: {rem} {item.uom}
                    </span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    max={rem}
                    value={dispatchItems[item.product_code] ?? 0}
                    onChange={(e) =>
                      setDispatchItems({
                        ...dispatchItems,
                        [item.product_code]: Number(e.target.value),
                      })
                    }
                    className="w-24 px-2.5 py-1 text-xs rounded border border-[#E7E5DE]  bg-white  text-right font-bold"
                  />
                </div>
              );
            })}
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDispatchModalOpen(false)}
              disabled={dispatchSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={dispatchSubmitting}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {dispatchSubmitting ? 'Posting...' : 'Record Dispatch'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Cancel Order Modal */}
      <Dialog
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        title="Cancel Sales Order"
        description="Provide a mandatory commercial reason for cancelling this sales order."
        maxWidth="md"
      >
        <form onSubmit={handleCancelOrder} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Cancellation Reason *
            </label>
            <textarea
              required
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="e.g. Customer cancelled project tender; renegotiating terms..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900 "
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCancelModalOpen(false)}
              disabled={cancelSubmitting}
            >
              Dismiss
            </Button>
            <Button
              type="submit"
              disabled={cancelSubmitting}
              className="bg-rose-600 hover:bg-rose-700 text-white"
            >
              {cancelSubmitting ? 'Cancelling...' : 'Confirm Cancellation'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
