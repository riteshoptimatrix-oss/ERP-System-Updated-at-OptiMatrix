'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { inventoryClient } from '@/services/inventory-client';
import { masterClient } from '@/services/master-client';
import {
  StockBalance,
  StockMovementLedger,
  LowStockAlert,
  InventoryDashboardSummary,
  ItemType,
  AdjustmentReason,
} from '@/types/inventory';
import { RawMaterial, FinishedProduct, Warehouse } from '@/types/master';
import {
  Boxes,
  Layers,
  AlertTriangle,
  History,
  ArrowUpRight,
  ArrowDownRight,
  ArrowLeftRight,
  SlidersHorizontal,
  Upload,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export default function InventoryHubPage() {
  const { activeUnit, hasPermission } = useAuth();
  const canCreate = hasPermission('inventory', 'create');
  const canUpdate = hasPermission('inventory', 'update');
  const canPost = hasPermission('inventory', 'post');

  // Active Tab: 'BALANCES' | 'LEDGER' | 'ALERTS'
  const [activeTab, setActiveTab] = useState<'BALANCES' | 'LEDGER' | 'ALERTS'>('BALANCES');

  // KPI Metrics
  const [metrics, setMetrics] = useState<InventoryDashboardSummary | null>(null);

  // Stock Balances State
  const [balances, setBalances] = useState<StockBalance[]>([]);
  const [isLoadingBalances, setIsLoadingBalances] = useState(false);
  const [balanceSearch, setBalanceSearch] = useState('');
  const [selectedItemType, setSelectedItemType] = useState<string>('ALL');
  const [belowReorderOnly, setBelowReorderOnly] = useState(false);

  // Movement Ledger State
  const [ledger, setLedger] = useState<StockMovementLedger[]>([]);
  const [isLoadingLedger, setIsLoadingLedger] = useState(false);
  const [ledgerMovementType, setLedgerMovementType] = useState<string>('ALL');

  // Low Stock Alerts State
  const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);

  // Master Data Options for Modals
  const [rawMaterials, setRawMaterials] = useState<RawMaterial[]>([]);
  const [finishedProducts, setFinishedProducts] = useState<FinishedProduct[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);

  // Modal Dialog States
  const [showInwardModal, setShowInwardModal] = useState(false);
  const [showOutwardModal, setShowOutwardModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [showOpeningModal, setShowOpeningModal] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form States
  const [inwardForm, setInwardForm] = useState({
    item_id: '',
    item_type: 'RAW_MATERIAL' as ItemType,
    warehouse_id: '',
    quantity: 1,
    unit_cost: 0,
    batch_no: 'BATCH-01',
    supplier_id: '',
    invoice_no: '',
    po_number: '',
    notes: '',
  });

  const [outwardForm, setOutwardForm] = useState({
    item_id: '',
    warehouse_id: '',
    quantity: 1,
    destination: 'Machine Line 1',
    department: 'Assembly',
    batch_no: 'DEFAULT',
    notes: '',
  });

  const [transferForm, setTransferForm] = useState({
    source_warehouse_id: '',
    target_warehouse_id: '',
    item_id: '',
    quantity: 1,
    batch_no: 'DEFAULT',
    transfer_reason: 'INTER_FACILITY_TRANSFER',
    vehicle_number: '',
    notes: '',
  });

  const [adjustForm, setAdjustForm] = useState({
    item_id: '',
    warehouse_id: '',
    quantity_delta: 0,
    reason: 'PHYSICAL_COUNT_DISCREPANCY' as AdjustmentReason,
    batch_no: 'DEFAULT',
    notes: '',
  });

  const [openingRawCsv, setOpeningRawCsv] = useState(
    'ITEM_CODE,ITEM_TYPE,WH_CODE,QUANTITY,UNIT_COST,BATCH_NO\n'
  );

  // -------------------------------------------------------------
  // Data Fetching Handlers
  // -------------------------------------------------------------
  const fetchDashboard = useCallback(async () => {
    try {
      const data = await inventoryClient.getDashboard(activeUnit === 'BOTH' ? undefined : activeUnit);
      setMetrics(data);
    } catch (err: unknown) {
      console.error('Error fetching inventory summary:', err);
    }
  }, [activeUnit]);

  const fetchBalances = useCallback(async () => {
    try {
      setIsLoadingBalances(true);
      const res = await inventoryClient.listBalances({
        search: balanceSearch || undefined,
        item_type: selectedItemType === 'ALL' ? undefined : selectedItemType,
        below_reorder_only: belowReorderOnly,
        unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        page: 1,
        page_size: 50,
      });
      setBalances(res.items);
    } catch (err: unknown) {
      console.error('Error fetching stock balances:', err);
    } finally {
      setIsLoadingBalances(false);
    }
  }, [activeUnit, balanceSearch, selectedItemType, belowReorderOnly]);

  const fetchLedger = useCallback(async () => {
    try {
      setIsLoadingLedger(true);
      const res = await inventoryClient.listLedger({
        movement_type: ledgerMovementType === 'ALL' ? undefined : ledgerMovementType,
        unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        page: 1,
        page_size: 50,
      });
      setLedger(res.items);
    } catch (err: unknown) {
      console.error('Error fetching inventory ledger:', err);
    } finally {
      setIsLoadingLedger(false);
    }
  }, [activeUnit, ledgerMovementType]);

  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoadingAlerts(true);
      const data = await inventoryClient.getLowStockAlerts(activeUnit === 'BOTH' ? undefined : activeUnit);
      setAlerts(data);
    } catch (err: unknown) {
      console.error('Error fetching low stock alerts:', err);
    } finally {
      setIsLoadingAlerts(false);
    }
  }, [activeUnit]);

  const fetchMasterData = useCallback(async () => {
    try {
      const [rmRes, fgRes, whRes] = await Promise.all([
        masterClient.list('materials', { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
        masterClient.list('products', { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
        masterClient.list('warehouses', { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 })),
      ]);
      setRawMaterials((rmRes?.items || []) as RawMaterial[]);
      setFinishedProducts((fgRes?.items || []) as FinishedProduct[]);
      setWarehouses((whRes?.items || []) as Warehouse[]);
    } catch (err) {
      console.warn('Master metadata for inventory currently unavailable:', err);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchMasterData();
  }, [fetchDashboard, fetchMasterData]);

  useEffect(() => {
    if (activeTab === 'BALANCES') fetchBalances();
    else if (activeTab === 'LEDGER') fetchLedger();
    else if (activeTab === 'ALERTS') fetchAlerts();
  }, [activeTab, fetchBalances, fetchLedger, fetchAlerts]);

  // -------------------------------------------------------------
  // Action Handlers
  // -------------------------------------------------------------
  const handleInwardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      await inventoryClient.materialInward({
        item_id: inwardForm.item_id,
        item_type: inwardForm.item_type,
        warehouse_id: inwardForm.warehouse_id,
        quantity: Number(inwardForm.quantity),
        unit_cost: Number(inwardForm.unit_cost),
        batch_no: inwardForm.batch_no,
        supplier_id: inwardForm.supplier_id || undefined,
        invoice_no: inwardForm.invoice_no || undefined,
        po_number: inwardForm.po_number || undefined,
        notes: inwardForm.notes || undefined,
      });
      setActionSuccess('Material inward recorded successfully.');
      setShowInwardModal(false);
      fetchDashboard();
      fetchBalances();
      fetchLedger();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record material inward';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOutwardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      await inventoryClient.materialOutward({
        item_id: outwardForm.item_id,
        warehouse_id: outwardForm.warehouse_id,
        quantity: Number(outwardForm.quantity),
        destination: outwardForm.destination || undefined,
        department: outwardForm.department || undefined,
        batch_no: outwardForm.batch_no || 'DEFAULT',
        notes: outwardForm.notes || undefined,
      });
      setActionSuccess('Material issued to floor successfully.');
      setShowOutwardModal(false);
      fetchDashboard();
      fetchBalances();
      fetchLedger();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to issue material';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      await inventoryClient.stockTransfer({
        source_warehouse_id: transferForm.source_warehouse_id,
        target_warehouse_id: transferForm.target_warehouse_id,
        item_id: transferForm.item_id,
        quantity: Number(transferForm.quantity),
        batch_no: transferForm.batch_no || 'DEFAULT',
        transfer_reason: transferForm.transfer_reason,
        vehicle_number: transferForm.vehicle_number || undefined,
        notes: transferForm.notes || undefined,
      });
      setActionSuccess('Inter-warehouse transfer posted successfully.');
      setShowTransferModal(false);
      fetchDashboard();
      fetchBalances();
      fetchLedger();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to transfer stock';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      await inventoryClient.stockAdjustment({
        item_id: adjustForm.item_id,
        warehouse_id: adjustForm.warehouse_id,
        quantity_delta: Number(adjustForm.quantity_delta),
        reason: adjustForm.reason,
        batch_no: adjustForm.batch_no || 'DEFAULT',
        notes: adjustForm.notes,
      });
      setActionSuccess('Stock adjustment logged successfully.');
      setShowAdjustModal(false);
      fetchDashboard();
      fetchBalances();
      fetchLedger();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record stock adjustment';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpeningStockImport = async () => {
    setActionError(null);
    setIsSubmitting(true);
    try {
      const lines = openingRawCsv.trim().split('\n').slice(1);
      const items = lines.map((l) => {
        const [code, type, wh, qty, cost, batch] = l.split(',').map((s) => s.trim());
        return {
          item_code: code,
          item_type: type as ItemType,
          warehouse_code: wh,
          quantity: parseFloat(qty),
          unit_cost: parseFloat(cost || '0'),
          batch_no: batch || 'DEFAULT',
        };
      });

      const res = await inventoryClient.importOpeningStock({
        items,
        notes: 'Bulk opening balance import',
      });
      setActionSuccess(`Processed ${res.processed_count} opening balances (${res.skipped_count} skipped duplicates).`);
      setShowOpeningModal(false);
      fetchDashboard();
      fetchBalances();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to import opening stock';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // Data Table Columns
  // -------------------------------------------------------------
  const balanceColumns: Column<StockBalance>[] = [
    {
      key: 'item',
      header: 'Item',
      render: (b) => (
        <div>
          <div className="font-semibold text-slate-900 ">{b.item_code}</div>
          <div className="text-xs text-slate-500">{b.item_name}</div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      render: (b) => (
        <Badge variant={b.item_type === 'RAW_MATERIAL' ? 'neutral' : 'success'}>
          {b.item_type === 'RAW_MATERIAL' ? 'Raw Material' : 'Finished Good'}
        </Badge>
      ),
    },
    {
      key: 'warehouse',
      header: 'Warehouse & Facility',
      render: (b) => (
        <div>
          <div className="font-medium text-slate-800 ">{b.warehouse_name}</div>
          <div className="text-xs text-slate-500">
            {b.warehouse_code} • {b.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : b.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
          </div>
        </div>
      ),
    },
    {
      key: 'batch',
      header: 'Batch',
      render: (b) => <span className="font-mono text-xs text-slate-600 ">{b.batch_no}</span>,
    },
    {
      key: 'on_hand',
      header: 'On Hand',
      render: (b) => (
        <span className="font-bold text-slate-900 ">
          {b.quantity_on_hand.toLocaleString()} <span className="text-xs font-normal text-slate-500">{b.uom}</span>
        </span>
      ),
    },
    {
      key: 'available',
      header: 'Available',
      render: (b) => (
        <span className={`font-semibold ${b.is_below_reorder ? 'text-rose-600' : 'text-emerald-600'}`}>
          {b.quantity_available.toLocaleString()} {b.uom}
        </span>
      ),
    },
    {
      key: 'valuation',
      header: 'Valuation (INR)',
      render: (b) => (
        <div>
          <div className="font-semibold text-slate-900 ">₹{b.total_valuation.toLocaleString()}</div>
          <div className="text-xs text-slate-500">₹{b.valuation_rate}/unit</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (b) => (
        b.is_below_reorder ? (
          <Badge variant="error">Below Reorder ({b.reorder_level})</Badge>
        ) : (
          <Badge variant="success">Optimal</Badge>
        )
      ),
    },
  ];

  const ledgerColumns: Column<StockMovementLedger>[] = [
    {
      key: 'transaction_number',
      header: 'TXN Number',
      render: (l) => <span className="font-mono font-medium text-slate-900 ">{l.transaction_number}</span>,
    },
    {
      key: 'movement',
      header: 'Movement',
      render: (l) => {
        let variant: 'success' | 'error' | 'warning' | 'neutral' = 'neutral';
        if (l.quantity_change > 0) variant = 'success';
        else if (l.quantity_change < 0) variant = 'error';

        return <Badge variant={variant}>{l.movement_type.replace(/_/g, ' ')}</Badge>;
      },
    },
    {
      key: 'item',
      header: 'Item',
      render: (l) => (
        <div>
          <div className="font-semibold text-slate-900 ">{l.item_code}</div>
          <div className="text-xs text-slate-500">{l.item_name}</div>
        </div>
      ),
    },
    {
      key: 'warehouse',
      header: 'Warehouse',
      render: (l) => (
        <span className="text-xs text-slate-700 ">{l.warehouse_code} ({l.unit_id === 'Unit_1' ? 'Unit 1' : l.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})</span>
      ),
    },
    {
      key: 'change',
      header: 'Change',
      render: (l) => (
        <span className={`font-bold ${l.quantity_change > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
          {l.quantity_change > 0 ? `+${l.quantity_change}` : l.quantity_change} {l.uom}
        </span>
      ),
    },
    {
      key: 'balance_after',
      header: 'Balance After',
      render: (l) => <span className="font-semibold text-slate-800 ">{l.balance_after} {l.uom}</span>,
    },
    {
      key: 'created_at',
      header: 'Date & By',
      render: (l) => (
        <div>
          <div className="text-xs text-slate-700 ">{new Date(l.created_at).toLocaleString()}</div>
          <div className="text-xs text-slate-500">{l.created_by}</div>
        </div>
      ),
    },
  ];

  const alertColumns: Column<LowStockAlert>[] = [
    {
      key: 'item',
      header: 'Item Code & Name',
      render: (a) => (
        <div>
          <div className="font-bold text-slate-900 ">{a.item_code}</div>
          <div className="text-xs text-slate-500">{a.item_name}</div>
        </div>
      ),
    },
    {
      key: 'unit_id',
      header: 'Facility',
      render: (a) => (
        <span className="font-medium text-slate-800 ">
          {a.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : a.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
        </span>
      ),
    },
    {
      key: 'available',
      header: 'Available Stock',
      render: (a) => (
        <span className="font-bold text-rose-600">
          {a.total_available} {a.uom}
        </span>
      ),
    },
    {
      key: 'reorder',
      header: 'Reorder Level',
      render: (a) => <span className="font-semibold text-slate-800 ">{a.reorder_level} {a.uom}</span>,
    },
    {
      key: 'shortage',
      header: 'Shortage',
      render: (a) => (
        <Badge variant="error">-{a.shortage_quantity} {a.uom} Deficit</Badge>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (a) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setInwardForm((prev) => ({ ...prev, item_id: a.item_id, item_type: a.item_type }));
            setShowInwardModal(true);
          }}
        >
          Replenish Inward
        </Button>
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

      {/* Header & Quick Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 ">Inventory & Warehouse Management</h1>
          <p className="text-sm text-slate-500">
            Multi-facility stock balances, immutable transaction ledger, and controlled shop-floor movements.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canCreate && (
            <Button onClick={() => setShowInwardModal(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <ArrowDownRight className="mr-1.5 h-4 w-4" /> Material Inward (GRN)
            </Button>
          )}
          {canUpdate && (
            <Button onClick={() => setShowOutwardModal(true)} variant="secondary">
              <ArrowUpRight className="mr-1.5 h-4 w-4" /> Issue to Floor
            </Button>
          )}
          {canUpdate && (
            <Button onClick={() => setShowTransferModal(true)} variant="outline">
              <ArrowLeftRight className="mr-1.5 h-4 w-4" /> Transfer
            </Button>
          )}
          {canPost && (
            <Button onClick={() => setShowAdjustModal(true)} variant="outline">
              <SlidersHorizontal className="mr-1.5 h-4 w-4" /> Adjust
            </Button>
          )}
          {canCreate && (
            <Button onClick={() => setShowOpeningModal(true)} variant="outline">
              <Upload className="mr-1.5 h-4 w-4" /> Import Opening
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-blue-500 shadow-sm">
          <div className="p-3 bg-[#EAF0E9] bg-blue-950/40 rounded-lg text-[#315C45]">
            <Boxes className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Total Items Tracked</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.total_items_tracked ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              RM: {metrics?.raw_material_items ?? 0} | FG: {metrics?.finished_goods_items ?? 0}
            </p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-emerald-500 shadow-sm">
          <div className="p-3 bg-emerald-50 bg-emerald-950/40 rounded-lg text-emerald-600">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Inventory Valuation</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              ₹{(metrics?.total_valuation_inr ?? 0).toLocaleString()}
            </h3>
            <p className="text-xs text-emerald-600 mt-0.5 font-medium">Reconciled moving avg</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-amber-500 shadow-sm">
          <div className="p-3 bg-amber-50 bg-amber-950/40 rounded-lg text-amber-600">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Low Stock Alerts</p>
            <h3 className="text-2xl font-bold text-amber-600">{metrics?.low_stock_alerts_count ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Requires replenishment</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-purple-500 shadow-sm">
          <div className="p-3 bg-purple-50 bg-purple-950/40 rounded-lg text-purple-600">
            <History className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Movements Today</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.movements_today_count ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Across {metrics?.warehouses_count ?? 0} warehouses</p>
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-[#E7E5DE] ">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('BALANCES')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'BALANCES'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <Boxes className="h-4 w-4" /> Stock Balances
          </button>
          <button
            onClick={() => setActiveTab('LEDGER')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'LEDGER'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <History className="h-4 w-4" /> Movement Ledger
          </button>
          <button
            onClick={() => setActiveTab('ALERTS')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'ALERTS'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <AlertTriangle className="h-4 w-4" /> Low Stock Alerts
            {(metrics?.low_stock_alerts_count ?? 0) > 0 && (
              <span className="bg-rose-100 text-rose-700 rounded-full text-xs px-2 py-0.5 font-bold">
                {metrics?.low_stock_alerts_count}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* TAB CONTENT: STOCK BALANCES */}
      {activeTab === 'BALANCES' && (
        <div className="space-y-4">
          <FilterBar
            searchQuery={balanceSearch}
            onSearchChange={setBalanceSearch}
            placeholder="Search by item code, name, warehouse, batch..."
            onReset={() => {
              setBalanceSearch('');
              setSelectedItemType('ALL');
              setBelowReorderOnly(false);
            }}
          >
            <select
              value={selectedItemType}
              onChange={(e) => setSelectedItemType(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700 "
            >
              <option value="ALL">All Item Types</option>
              <option value="RAW_MATERIAL">Raw Materials</option>
              <option value="FINISHED_GOOD">Finished Goods</option>
            </select>
            <div className="flex items-center gap-1.5 pl-2">
              <input
                type="checkbox"
                id="reorder_filter"
                checked={belowReorderOnly}
                onChange={(e) => setBelowReorderOnly(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-[#E7E5DE] text-[#315C45] focus:ring-[#315C45]"
              />
              <label htmlFor="reorder_filter" className="text-xs text-slate-600  cursor-pointer">
                Below Reorder Only
              </label>
            </div>
          </FilterBar>

          <DataTable
            columns={balanceColumns}
            data={balances}
            isLoading={isLoadingBalances}
            keyExtractor={(b) => b.id}
            emptyTitle="No stock balance records found"
            emptyDescription="There are currently no tracked stock balances in this unit."
          />
        </div>
      )}

      {/* TAB CONTENT: MOVEMENT LEDGER */}
      {activeTab === 'LEDGER' && (
        <div className="space-y-4">
          <FilterBar
            searchQuery=""
            onSearchChange={() => { }}
            placeholder="Filter movements..."
            onReset={() => setLedgerMovementType('ALL')}
          >
            <select
              value={ledgerMovementType}
              onChange={(e) => setLedgerMovementType(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700 "
            >
              <option value="ALL">All Movement Types</option>
              <option value="MATERIAL_INWARD">Material Inward (GRN)</option>
              <option value="MATERIAL_OUTWARD">Material Outward (Floor)</option>
              <option value="TRANSFER_IN">Transfer In</option>
              <option value="TRANSFER_OUT">Transfer Out</option>
              <option value="ADJUSTMENT_IN">Adjustment In</option>
              <option value="ADJUSTMENT_OUT">Adjustment Out</option>
              <option value="SALES_DISPATCH">Sales Dispatch</option>
              <option value="OPENING_STOCK">Opening Stock</option>
            </select>
          </FilterBar>

          <DataTable
            columns={ledgerColumns}
            data={ledger}
            isLoading={isLoadingLedger}
            keyExtractor={(l) => l.id}
            emptyTitle="No ledger transactions found"
            emptyDescription="No immutable stock movement records match the selected criteria."
          />
        </div>
      )}

      {/* TAB CONTENT: LOW STOCK ALERTS */}
      {activeTab === 'ALERTS' && (
        <div className="space-y-4">
          <DataTable
            columns={alertColumns}
            data={alerts}
            isLoading={isLoadingAlerts}
            keyExtractor={(a) => `${a.item_id}-${a.unit_id}`}
            emptyTitle="All tracked items optimal"
            emptyDescription="No inventory items are currently below their configured reorder thresholds."
          />
        </div>
      )}

      {/* MODAL: MATERIAL INWARD */}
      {showInwardModal && (
        <Dialog
          isOpen={showInwardModal}
          onClose={() => setShowInwardModal(false)}
          title="Record Material Inward (GRN / Production Receipt)"
        >
          <form onSubmit={handleInwardSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Item Type</label>
                <select
                  value={inwardForm.item_type}
                  onChange={(e) => setInwardForm({ ...inwardForm, item_type: e.target.value as ItemType, item_id: '' })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="RAW_MATERIAL">Raw Material</option>
                  <option value="FINISHED_GOOD">Finished Good</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Select Item</label>
                <select
                  value={inwardForm.item_id}
                  onChange={(e) => setInwardForm({ ...inwardForm, item_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Choose Item --</option>
                  {inwardForm.item_type === 'RAW_MATERIAL'
                    ? rawMaterials.map((rm) => (
                      <option key={rm.id} value={rm.id}>{rm.code} - {rm.name}</option>
                    ))
                    : finishedProducts.map((fg) => (
                      <option key={fg.id} value={fg.id}>{fg.code} - {fg.name}</option>
                    ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Target Warehouse</label>
                <select
                  value={inwardForm.warehouse_id}
                  onChange={(e) => setInwardForm({ ...inwardForm, warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Choose Warehouse --</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.code} - {wh.name} ({wh.unit_id === 'Unit_1' ? 'Unit 1' : wh.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Quantity</label>
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={inwardForm.quantity}
                  onChange={(e) => setInwardForm({ ...inwardForm, quantity: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Unit Cost (INR)</label>
                <input
                  type="number"
                  step="0.01"
                  value={inwardForm.unit_cost}
                  onChange={(e) => setInwardForm({ ...inwardForm, unit_cost: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Batch / Lot Number</label>
                <input
                  type="text"
                  value={inwardForm.batch_no}
                  onChange={(e) => setInwardForm({ ...inwardForm, batch_no: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Invoice Number</label>
                <input
                  type="text"
                  value={inwardForm.invoice_no}
                  onChange={(e) => setInwardForm({ ...inwardForm, invoice_no: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">PO Number</label>
                <input
                  type="text"
                  value={inwardForm.po_number}
                  onChange={(e) => setInwardForm({ ...inwardForm, po_number: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Notes / Remarks</label>
              <textarea
                value={inwardForm.notes}
                onChange={(e) => setInwardForm({ ...inwardForm, notes: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowInwardModal(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {isSubmitting ? 'Recording...' : 'Confirm Inward'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: MATERIAL OUTWARD */}
      {showOutwardModal && (
        <Dialog
          isOpen={showOutwardModal}
          onClose={() => setShowOutwardModal(false)}
          title="Issue Materials to Production Floor"
        >
          <form onSubmit={handleOutwardSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Select Raw Material</label>
              <select
                value={outwardForm.item_id}
                onChange={(e) => setOutwardForm({ ...outwardForm, item_id: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                required
              >
                <option value="">-- Choose Raw Material --</option>
                {rawMaterials.map((rm) => (
                  <option key={rm.id} value={rm.id}>{rm.code} - {rm.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Source Warehouse</label>
                <select
                  value={outwardForm.warehouse_id}
                  onChange={(e) => setOutwardForm({ ...outwardForm, warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Choose Source Warehouse --</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>{wh.code} - {wh.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Quantity</label>
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={outwardForm.quantity}
                  onChange={(e) => setOutwardForm({ ...outwardForm, quantity: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Destination / Machine Line</label>
                <input
                  type="text"
                  value={outwardForm.destination}
                  onChange={(e) => setOutwardForm({ ...outwardForm, destination: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Batch / Lot</label>
                <input
                  type="text"
                  value={outwardForm.batch_no}
                  onChange={(e) => setOutwardForm({ ...outwardForm, batch_no: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Notes</label>
              <textarea
                value={outwardForm.notes}
                onChange={(e) => setOutwardForm({ ...outwardForm, notes: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowOutwardModal(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting} variant="primary">
                {isSubmitting ? 'Issuing...' : 'Issue to Floor'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: STOCK TRANSFER */}
      {showTransferModal && (
        <Dialog
          isOpen={showTransferModal}
          onClose={() => setShowTransferModal(false)}
          title="Inter-Warehouse / Inter-Facility Stock Transfer"
        >
          <form onSubmit={handleTransferSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Select Item to Transfer</label>
              <select
                value={transferForm.item_id}
                onChange={(e) => setTransferForm({ ...transferForm, item_id: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                required
              >
                <option value="">-- Choose Item --</option>
                <optgroup label="Raw Materials">
                  {rawMaterials.map((rm) => (
                    <option key={rm.id} value={rm.id}>[RM] {rm.code} - {rm.name}</option>
                  ))}
                </optgroup>
                <optgroup label="Finished Products">
                  {finishedProducts.map((fg) => (
                    <option key={fg.id} value={fg.id}>[FG] {fg.code} - {fg.name}</option>
                  ))}
                </optgroup>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Source Warehouse</label>
                <select
                  value={transferForm.source_warehouse_id}
                  onChange={(e) => setTransferForm({ ...transferForm, source_warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Origin Warehouse --</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.code} - {wh.name} ({wh.unit_id === 'Unit_1' ? 'Unit 1' : wh.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Destination Warehouse</label>
                <select
                  value={transferForm.target_warehouse_id}
                  onChange={(e) => setTransferForm({ ...transferForm, target_warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Target Warehouse --</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.code} - {wh.name} ({wh.unit_id === 'Unit_1' ? 'Unit 1' : wh.unit_id === 'Unit_2' ? 'Unit 2' : 'All'})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Transfer Quantity</label>
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={transferForm.quantity}
                  onChange={(e) => setTransferForm({ ...transferForm, quantity: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Vehicle Number</label>
                <input
                  type="text"
                  placeholder="e.g. MH-14-GH-1234"
                  value={transferForm.vehicle_number}
                  onChange={(e) => setTransferForm({ ...transferForm, vehicle_number: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowTransferModal(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting} variant="primary">
                {isSubmitting ? 'Transferring...' : 'Execute Transfer'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: STOCK ADJUSTMENT */}
      {showAdjustModal && (
        <Dialog
          isOpen={showAdjustModal}
          onClose={() => setShowAdjustModal(false)}
          title="Stock Adjustment (Audit Authorization Required)"
        >
          <form onSubmit={handleAdjustSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Select Item</label>
              <select
                value={adjustForm.item_id}
                onChange={(e) => setAdjustForm({ ...adjustForm, item_id: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                required
              >
                <option value="">-- Choose Item --</option>
                <optgroup label="Raw Materials">
                  {rawMaterials.map((rm) => (
                    <option key={rm.id} value={rm.id}>[RM] {rm.code} - {rm.name}</option>
                  ))}
                </optgroup>
                <optgroup label="Finished Products">
                  {finishedProducts.map((fg) => (
                    <option key={fg.id} value={fg.id}>[FG] {fg.code} - {fg.name}</option>
                  ))}
                </optgroup>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">Warehouse</label>
                <select
                  value={adjustForm.warehouse_id}
                  onChange={(e) => setAdjustForm({ ...adjustForm, warehouse_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                >
                  <option value="">-- Choose Warehouse --</option>
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>{wh.code} - {wh.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Quantity Delta (+ for surplus, - for deficit)
                </label>
                <input
                  type="number"
                  step="any"
                  value={adjustForm.quantity_delta}
                  onChange={(e) => setAdjustForm({ ...adjustForm, quantity_delta: parseFloat(e.target.value) || 0 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">Adjustment Reason</label>
              <select
                value={adjustForm.reason}
                onChange={(e) => setAdjustForm({ ...adjustForm, reason: e.target.value as AdjustmentReason })}
                className="w-full border rounded-md p-2 text-xs"
                required
              >
                <option value="PHYSICAL_COUNT_DISCREPANCY">Physical Count Discrepancy</option>
                <option value="DAMAGED_GOODS">Damaged Goods</option>
                <option value="OBSOLETE_SCRAP">Obsolete / Scrap</option>
                <option value="QUALITY_REJECT">Quality Reject</option>
                <option value="SAMPLE_TESTING">Sample Testing</option>
                <option value="CORRECTION">Correction</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Mandatory Audit Justification (Minimum 3 characters)
              </label>
              <textarea
                value={adjustForm.notes}
                onChange={(e) => setAdjustForm({ ...adjustForm, notes: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
                required
                minLength={3}
                placeholder="Explain the discrepancy observed during stock audit..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowAdjustModal(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting} variant="primary">
                {isSubmitting ? 'Posting...' : 'Post Adjustment'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: OPENING STOCK IMPORT */}
      {showOpeningModal && (
        <Dialog
          isOpen={showOpeningModal}
          onClose={() => setShowOpeningModal(false)}
          title="Import Opening Stock Balances"
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-600 ">
              Paste CSV records below. Format: <code className="bg-slate-100  p-1 rounded">ITEM_CODE,ITEM_TYPE,WH_CODE,QUANTITY,UNIT_COST,BATCH_NO</code>.
              Existing balances for the same batch will be skipped safely without creating duplicate balances.
            </p>
            <textarea
              value={openingRawCsv}
              onChange={(e) => setOpeningRawCsv(e.target.value)}
              className="w-full font-mono text-xs border rounded-md p-2 h-48 bg-slate-50 "
            />
            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowOpeningModal(false)}>Cancel</Button>
              <Button onClick={handleOpeningStockImport} disabled={isSubmitting} variant="primary">
                {isSubmitting ? 'Importing...' : 'Run Import'}
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
