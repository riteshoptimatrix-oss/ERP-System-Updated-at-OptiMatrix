'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { bomClient } from '@/services/bom-client';
import { masterClient } from '@/services/master-client';
import {
  BOM,
  BOMStatus,
  BOMDashboardSummary,
  MaterialRequirementCalculation,
  BOMComponentInput,
} from '@/types/bom';
import { FinishedProduct, RawMaterial } from '@/types/master';
import {
  Scroll,
  Layers,
  CheckCircle2,
  AlertCircle,
  Plus,
  Calculator,
  GitBranch,
  ShieldCheck,
  Send,
  Upload,
  AlertTriangle,
  Boxes,
  Download,
} from 'lucide-react';
import { printBOMToPdf, printExplosionToPdf } from '@/utils/bom-pdf';

export default function BOMHubPage() {
  const { activeUnit, hasPermission } = useAuth();
  const canCreate = hasPermission('bom', 'create');
  const canUpdate = hasPermission('bom', 'update');
  const canApprove = hasPermission('bom', 'approve');

  // Active Tab: 'LIST' | 'CALCULATOR'
  const [activeTab, setActiveTab] = useState<'LIST' | 'CALCULATOR'>('LIST');

  // KPI Metrics
  const [metrics, setMetrics] = useState<BOMDashboardSummary | null>(null);

  // BOM List State
  const [boms, setBoms] = useState<BOM[]>([]);
  const [isLoadingBoms, setIsLoadingBoms] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  // Master Data Options
  const [products, setProducts] = useState<FinishedProduct[]>([]);
  const [rawMaterials, setRawMaterials] = useState<RawMaterial[]>([]);

  // Calculator State
  const [calcSelectedBomId, setCalcSelectedBomId] = useState<string>('');
  const [calcBatchQuantity, setCalcBatchQuantity] = useState<number>(10);
  const [calcResult, setCalcResult] = useState<MaterialRequirementCalculation | null>(null);
  const [isCalculating, setIsCalculating] = useState<boolean>(false);

  // Modal Dialog States
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [selectedBomForModal, setSelectedBomForModal] = useState<BOM | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create BOM Form State
  const [createForm, setCreateForm] = useState({
    product_id: '',
    revision_no: 'R1',
    base_quantity: 1.0,
    description: '',
    components: [] as (BOMComponentInput & { material_code?: string; material_name?: string })[],
  });

  // Revision Form State
  const [newRevisionNo, setNewRevisionNo] = useState('R2');
  const [revisionDescription, setRevisionDescription] = useState('');

  // Approval Form State
  const [approvalAction, setApprovalAction] = useState({
    approved: true,
    set_as_active: true,
    remarks: 'Approved for manufacturing line production',
  });

  // -------------------------------------------------------------
  // Data Fetching Handlers
  // -------------------------------------------------------------
  const fetchDashboard = useCallback(async () => {
    try {
      const data = await bomClient.getDashboard(activeUnit === 'BOTH' ? undefined : activeUnit);
      setMetrics(data);
    } catch (err) {
      console.error('Error fetching BOM dashboard:', err);
    }
  }, [activeUnit]);

  const fetchBOMs = useCallback(async () => {
    try {
      setIsLoadingBoms(true);
      const res = await bomClient.listBOMs({
        search: searchQuery || undefined,
        status: selectedStatus === 'ALL' ? undefined : selectedStatus,
        unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        page: 1,
        page_size: 50,
      });
      setBoms(res.items);
    } catch (err) {
      console.error('Error fetching BOMs:', err);
    } finally {
      setIsLoadingBoms(false);
    }
  }, [activeUnit, searchQuery, selectedStatus]);

  const fetchMasterData = useCallback(async () => {
    try {
      const [prodRes, matRes] = await Promise.all([
        masterClient.list('products', { page_size: 100 }),
        masterClient.list('materials', { page_size: 100 }),
      ]);
      setProducts(prodRes.items as FinishedProduct[]);
      setRawMaterials(matRes.items as RawMaterial[]);
    } catch (err) {
      console.error('Failed to load products/materials for BOM:', err);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchBOMs();
    fetchMasterData();
  }, [fetchDashboard, fetchBOMs, fetchMasterData]);

  // -------------------------------------------------------------
  // Action Handlers
  // -------------------------------------------------------------
  const handleAddComponentLine = () => {
    if (rawMaterials.length === 0) return;
    const defaultMat = rawMaterials[0];
    setCreateForm((prev) => ({
      ...prev,
      components: [
        ...prev.components,
        {
          material_id: defaultMat.id,
          material_code: defaultMat.code,
          material_name: defaultMat.name,
          uom: defaultMat.uom || 'KGS',
          net_quantity: 1.0,
          scrap_percentage: 0.0,
          notes: '',
        },
      ],
    }));
  };

  const handleRemoveComponentLine = (index: number) => {
    setCreateForm((prev) => ({
      ...prev,
      components: prev.components.filter((_, i) => i !== index),
    }));
  };

  const handleComponentChange = (index: number, field: string, value: string | number) => {
    setCreateForm((prev) => {
      const updated = [...prev.components];
      if (field === 'material_id') {
        const found = rawMaterials.find((m) => m.id === value);
        if (found) {
          updated[index] = {
            ...updated[index],
            material_id: found.id,
            material_code: found.code,
            material_name: found.name,
            uom: found.uom || 'KGS',
          };
        }
      } else {
        updated[index] = {
          ...updated[index],
          [field]: value,
        };
      }
      return { ...prev, components: updated };
    });
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setIsSubmitting(true);
    try {
      if (!createForm.product_id) throw new Error('Please select a finished product.');
      if (createForm.components.length === 0) throw new Error('Add at least one raw material component.');

      await bomClient.createBOM({
        product_id: createForm.product_id,
        unit_id: (activeUnit === 'BOTH' || !activeUnit) ? 'Unit_1' : activeUnit,
        base_quantity: Number(createForm.base_quantity),
        revision_no: createForm.revision_no,
        description: createForm.description || undefined,
        components: createForm.components.map((c) => ({
          material_id: c.material_id,
          net_quantity: Number(c.net_quantity),
          uom: c.uom,
          scrap_percentage: Number(c.scrap_percentage),
          notes: c.notes || undefined,
        })),
      });

      setActionSuccess('Bill of Materials created successfully.');
      setShowCreateModal(false);
      setCreateForm({
        product_id: '',
        revision_no: 'R1',
        base_quantity: 1.0,
        description: '',
        components: [],
      });
      fetchDashboard();
      fetchBOMs();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create BOM';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitForApproval = async (bom: BOM) => {
    setActionError(null);
    try {
      await bomClient.submitForApproval(bom.id);
      setActionSuccess(`BOM ${bom.bom_number} submitted for review.`);
      fetchBOMs();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit BOM';
      setActionError(msg);
    }
  };

  const handleApproveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBomForModal) return;
    setActionError(null);
    setIsSubmitting(true);
    try {
      await bomClient.approveBOM(selectedBomForModal.id, approvalAction);
      setActionSuccess(`BOM ${selectedBomForModal.bom_number} status updated.`);
      setShowApproveModal(false);
      fetchBOMs();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve BOM';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBomForModal) return;
    setActionError(null);
    setIsSubmitting(true);
    try {
      await bomClient.createRevision(selectedBomForModal.id, {
        new_revision_no: newRevisionNo,
        description: revisionDescription,
      });
      setActionSuccess(`New revision ${newRevisionNo} cloned successfully.`);
      setShowRevisionModal(false);
      fetchBOMs();
      fetchDashboard();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create revision';
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunRequirementsCalculation = async () => {
    if (!calcSelectedBomId) return;
    setIsCalculating(true);
    setActionError(null);
    try {
      const result = await bomClient.calculateRequirements(
        calcSelectedBomId,
        Number(calcBatchQuantity)
      );
      setCalcResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to calculate requirements';
      setActionError(msg);
    } finally {
      setIsCalculating(false);
    }
  };

  // -------------------------------------------------------------
  // Data Table Columns
  // -------------------------------------------------------------
  const getStatusBadge = (status: BOMStatus) => {
    switch (status) {
      case 'DRAFT':
        return <Badge variant="neutral">DRAFT</Badge>;
      case 'PENDING_APPROVAL':
        return <Badge variant="warning">PENDING APPROVAL</Badge>;
      case 'APPROVED':
        return <Badge variant="success">APPROVED</Badge>;
      case 'OBSOLETE':
        return <Badge variant="error">OBSOLETE</Badge>;
    }
  };

  const bomColumns: Column<BOM>[] = [
    {
      key: 'bom_number',
      header: 'BOM # & Rev',
      render: (b) => (
        <div>
          <span className="font-semibold text-[#315C45] text-blue-400 font-mono">{b.bom_number}</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[11px] font-bold bg-slate-100  px-1.5 py-0.5 rounded text-slate-700 ">
              {b.revision_no}
            </span>
            {b.is_active && (
              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-200 border-emerald-800">
                ACTIVE
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'product',
      header: 'Finished Product',
      render: (b) => (
        <div>
          <div className="font-semibold text-slate-900 ">{b.product_code}</div>
          <div className="text-xs text-slate-500">{b.product_name}</div>
        </div>
      ),
    },
    {
      key: 'facility',
      header: 'Facility & Base',
      render: (b) => (
        <div>
          <div className="font-medium text-slate-800 ">
            {b.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : b.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
          </div>
          <div className="text-xs text-slate-500">Yield: {b.base_quantity} {b.product_uom}</div>
        </div>
      ),
    },
    {
      key: 'components_count',
      header: 'Components',
      render: (b) => (
        <span className="font-semibold text-slate-700 ">
          {b.components?.length || 0} material(s)
        </span>
      ),
    },
    {
      key: 'estimated_cost',
      header: 'Est. Unit Cost',
      render: (b) => (
        <span className="font-bold text-slate-900 ">
          ₹{(b.total_estimated_cost || 0).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (b) => getStatusBadge(b.status),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (b) => (
        <div className="flex items-center gap-1.5">
          {b.status === 'DRAFT' && canUpdate && (
            <Button size="sm" variant="outline" onClick={() => handleSubmitForApproval(b)}>
              <Send className="w-3.5 h-3.5 mr-1" /> Submit
            </Button>
          )}
          {b.status === 'PENDING_APPROVAL' && canApprove && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                setSelectedBomForModal(b);
                setShowApproveModal(true);
              }}
            >
              <ShieldCheck className="w-3.5 h-3.5 mr-1" /> Review
            </Button>
          )}
          {b.status === 'APPROVED' && canCreate && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSelectedBomForModal(b);
                setNewRevisionNo(`R${parseInt(b.revision_no.replace('R', '') || '1', 10) + 1}`);
                setShowRevisionModal(true);
              }}
            >
              <GitBranch className="w-3.5 h-3.5 mr-1" /> New Rev
            </Button>
          )}
          {b.status === 'APPROVED' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setCalcSelectedBomId(b.id);
                setActiveTab('CALCULATOR');
              }}
            >
              <Calculator className="w-3.5 h-3.5 mr-1" /> Explode
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => printBOMToPdf(b)}
            title="Download / Print Bill of Materials as PDF"
            className="text-slate-700 hover:text-slate-900 border-slate-300 bg-white hover:bg-slate-50"
          >
            <Download className="w-3.5 h-3.5 mr-1 text-[#315C45]" /> PDF
          </Button>
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
            Bill of Materials (BOM) & Engineering Recipes
          </h1>
          <p className="text-sm text-slate-500">
            Multi-level component engineering, approved revision control, scrap allowances, and material requirement forecasting.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canCreate && (
            <Button
              onClick={() => {
                if (createForm.components.length === 0) handleAddComponentLine();
                setShowCreateModal(true);
              }}
              className="bg-[#315C45] hover:bg-[#254936] text-white"
            >
              <Plus className="mr-1.5 h-4 w-4" /> Create BOM
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-blue-500 shadow-sm">
          <div className="p-3 bg-[#EAF0E9] bg-blue-950/40 rounded-lg text-[#315C45]">
            <Scroll className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Total BOMs</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.total_boms ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Across {metrics?.products_with_bom_count ?? 0} machines</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-emerald-500 shadow-sm">
          <div className="p-3 bg-emerald-50 bg-emerald-950/40 rounded-lg text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Approved Revisions</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.approved_boms ?? 0}</h3>
            <p className="text-xs text-emerald-600 font-medium mt-0.5">{metrics?.active_boms ?? 0} active in production</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-amber-500 shadow-sm">
          <div className="p-3 bg-amber-50 bg-amber-950/40 rounded-lg text-amber-600">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Pending Review</p>
            <h3 className="text-2xl font-bold text-amber-700">{metrics?.pending_approval_boms ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">Awaiting manager sign-off</p>
          </div>
        </Card>

        <Card className="p-5 flex items-center space-x-4 border-l-4 border-l-purple-500 shadow-sm">
          <div className="p-3 bg-purple-50 bg-purple-950/40 rounded-lg text-purple-600">
            <Calculator className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Draft Recipes</p>
            <h3 className="text-2xl font-bold text-slate-900 ">{metrics?.draft_boms ?? 0}</h3>
            <p className="text-xs text-slate-500 mt-0.5">In engineering formulation</p>
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-[#E7E5DE] ">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('LIST')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'LIST'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <Scroll className="h-4 w-4" /> Bill of Materials Master
          </button>
          <button
            onClick={() => setActiveTab('CALCULATOR')}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${activeTab === 'CALCULATOR'
              ? 'border-[#315C45] text-[#315C45]'
              : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-[#E7E5DE]'
              }`}
          >
            <Calculator className="h-4 w-4" /> Material Requirements Explosion
          </button>
        </nav>
      </div>

      {/* TAB 1: BOM LIST */}
      {activeTab === 'LIST' && (
        <div className="space-y-4">
          <FilterBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            placeholder="Search by BOM #, product code, name..."
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
              <option value="APPROVED">Approved</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="DRAFT">Draft</option>
              <option value="OBSOLETE">Obsolete</option>
            </select>
          </FilterBar>

          <DataTable
            columns={bomColumns}
            data={boms}
            isLoading={isLoadingBoms}
            keyExtractor={(b) => b.id}
            emptyTitle="No Bill of Materials configured"
            emptyDescription="Create your first BOM recipe to link finished machines with component raw materials."
          />
        </div>
      )}

      {/* TAB 2: MATERIAL REQUIREMENTS CALCULATOR */}
      {activeTab === 'CALCULATOR' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-base font-bold text-slate-900  mb-2 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-[#315C45]" />
              Batch Material Explosion & Shortage Forecast
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Select an approved Bill of Materials and target production quantity to compute net/gross raw material requirements,
              accounting for approved scrap allowances and live on-hand inventory availability.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Select Approved BOM
                </label>
                <select
                  value={calcSelectedBomId}
                  onChange={(e) => setCalcSelectedBomId(e.target.value)}
                  className="w-full border rounded-md p-2 text-xs bg-white "
                >
                  <option value="">-- Choose BOM --</option>
                  {boms
                    .filter((b) => b.status === 'APPROVED')
                    .map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.bom_number} ({b.revision_no}) - {b.product_code} ({b.product_name})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Target Production Batch Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  step="any"
                  value={calcBatchQuantity}
                  onChange={(e) => setCalcBatchQuantity(parseFloat(e.target.value) || 1)}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>

              <div className="flex items-end">
                <Button
                  onClick={handleRunRequirementsCalculation}
                  disabled={!calcSelectedBomId || isCalculating}
                  className="w-full bg-[#315C45] hover:bg-[#254936] text-white"
                >
                  {isCalculating ? 'Computing Requirements...' : 'Explode Requirements'}
                </Button>
              </div>
            </div>
          </Card>

          {/* Calculation Output Table */}
          {calcResult && (
            <div className="space-y-4">
              {/* Shortage Summary Banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${calcResult.has_sufficient_stock
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
                  }`}
              >
                <div className="flex items-center gap-3">
                  {calcResult.has_sufficient_stock ? (
                    <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-rose-600" />
                  )}
                  <div>
                    <h4 className="font-bold text-sm">
                      {calcResult.has_sufficient_stock
                        ? 'Inventory Sufficient for Production Batch'
                        : `Material Shortages Detected: ${calcResult.total_shortages_count} item(s) deficit`}
                    </h4>
                    <p className="text-xs">
                      Target batch: {calcResult.production_quantity} unit(s) of {calcResult.product_code}. Total material cost: ₹
                      {calcResult.total_estimated_material_cost.toLocaleString()}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => printExplosionToPdf(calcResult)}
                  className="bg-white text-slate-800 border-slate-300 hover:bg-slate-50 shadow-sm flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5 text-[#315C45]" />
                  Download PDF
                </Button>
              </div>

              <Card className="overflow-hidden p-0">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 /60 border-b border-[#E7E5DE]  text-slate-500 font-semibold uppercase">
                    <tr>
                      <th className="py-3 px-4">Component Material</th>
                      <th className="py-3 px-4">Net Qty</th>
                      <th className="py-3 px-4">Scrap %</th>
                      <th className="py-3 px-4">Gross Required</th>
                      <th className="py-3 px-4">Available In Stock</th>
                      <th className="py-3 px-4">Shortage / Deficit</th>
                      <th className="py-3 px-4">Est. Cost (INR)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 divide-slate-800">
                    {calcResult.requirements.map((req) => (
                      <tr key={req.material_id} className="hover:bg-slate-50/50 /40">
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-slate-900 ">{req.material_code}</div>
                          <div className="text-[11px] text-slate-500">{req.material_name}</div>
                        </td>
                        <td className="py-3.5 px-4 font-medium">
                          {req.net_required_quantity} {req.uom}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">
                          {req.scrap_percentage}%
                        </td>
                        <td className="py-3.5 px-4 font-bold text-slate-900 ">
                          {req.gross_required_quantity} {req.uom}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-700 ">
                          {req.quantity_available} {req.uom}
                        </td>
                        <td className="py-3.5 px-4">
                          {req.is_shortage ? (
                            <Badge variant="error">-{req.shortage_quantity} {req.uom} Deficit</Badge>
                          ) : (
                            <Badge variant="success">Covered</Badge>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-slate-900 ">
                          ₹{req.total_estimated_cost.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* MODAL: CREATE BOM */}
      {showCreateModal && (
        <Dialog
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create Bill of Materials (Engineering Recipe)"
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Finished Product
                </label>
                <select
                  value={createForm.product_id}
                  onChange={(e) => setCreateForm({ ...createForm, product_id: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs bg-white "
                  required
                >
                  <option value="">-- Choose Finished Product --</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.code} - {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Revision Code
                </label>
                <input
                  type="text"
                  value={createForm.revision_no}
                  onChange={(e) => setCreateForm({ ...createForm, revision_no: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs uppercase"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Base Production Yield
                </label>
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  value={createForm.base_quantity}
                  onChange={(e) => setCreateForm({ ...createForm, base_quantity: parseFloat(e.target.value) || 1 })}
                  className="w-full border rounded-md p-2 text-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700  mb-1">
                  Recipe Description
                </label>
                <input
                  type="text"
                  placeholder="e.g. Standard BOM with hardened gears"
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full border rounded-md p-2 text-xs"
                />
              </div>
            </div>

            {/* Dynamic Component Lines */}
            <div className="space-y-2 pt-2 border-t">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800  uppercase">
                  Raw Material Components ({createForm.components.length})
                </h4>
                <Button type="button" size="sm" variant="outline" onClick={handleAddComponentLine}>
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add Component
                </Button>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {createForm.components.map((comp, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 p-2 bg-slate-50  rounded-lg border items-center">
                    <div className="col-span-5">
                      <select
                        value={comp.material_id}
                        onChange={(e) => handleComponentChange(idx, 'material_id', e.target.value)}
                        className="w-full border rounded p-1.5 text-xs bg-white "
                        required
                      >
                        {rawMaterials.map((rm) => (
                          <option key={rm.id} value={rm.id}>
                            {rm.code} - {rm.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-span-2">
                      <input
                        type="number"
                        min="0.001"
                        step="any"
                        placeholder="Net Qty"
                        value={comp.net_quantity}
                        onChange={(e) => handleComponentChange(idx, 'net_quantity', parseFloat(e.target.value) || 0)}
                        className="w-full border rounded p-1.5 text-xs"
                        required
                      />
                    </div>

                    <div className="col-span-2">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="any"
                        placeholder="Scrap %"
                        value={comp.scrap_percentage}
                        onChange={(e) => handleComponentChange(idx, 'scrap_percentage', parseFloat(e.target.value) || 0)}
                        className="w-full border rounded p-1.5 text-xs"
                      />
                    </div>

                    <div className="col-span-2">
                      <span className="text-xs font-bold text-slate-500 uppercase">{comp.uom}</span>
                    </div>

                    <div className="col-span-1 text-right">
                      <button
                        type="button"
                        onClick={() => handleRemoveComponentLine(idx)}
                        className="text-rose-500 hover:text-rose-700 text-xs font-bold"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-[#315C45] hover:bg-[#254936] text-white">
                {isSubmitting ? 'Saving...' : 'Save Draft BOM'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: CLONE REVISION */}
      {showRevisionModal && selectedBomForModal && (
        <Dialog
          isOpen={showRevisionModal}
          onClose={() => setShowRevisionModal(false)}
          title={`Generate New Revision for ${selectedBomForModal.bom_number}`}
        >
          <form onSubmit={handleRevisionSubmit} className="space-y-4">
            <p className="text-xs text-slate-600 ">
              Approved revisions are locked for engineering trace. This clones BOM components from{' '}
              <span className="font-bold">{selectedBomForModal.revision_no}</span> into a new draft revision.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                New Revision Code
              </label>
              <input
                type="text"
                value={newRevisionNo}
                onChange={(e) => setNewRevisionNo(e.target.value)}
                className="w-full border rounded-md p-2 text-xs uppercase"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Reason for Engineering Revision
              </label>
              <textarea
                value={revisionDescription}
                onChange={(e) => setRevisionDescription(e.target.value)}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
                required
                placeholder="e.g. Component vendor cost reduction or specification upgrade"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowRevisionModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-[#315C45] hover:bg-[#254936] text-white">
                {isSubmitting ? 'Cloning...' : 'Generate Revision'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}

      {/* MODAL: APPROVE BOM */}
      {showApproveModal && selectedBomForModal && (
        <Dialog
          isOpen={showApproveModal}
          onClose={() => setShowApproveModal(false)}
          title={`BOM Approval Review: ${selectedBomForModal.bom_number}`}
        >
          <form onSubmit={handleApproveSubmit} className="space-y-4">
            <div className="p-3 bg-slate-50  rounded-lg border text-xs space-y-1">
              <div><span className="font-semibold">Product:</span> {selectedBomForModal.product_code} ({selectedBomForModal.product_name})</div>
              <div><span className="font-semibold">Revision:</span> {selectedBomForModal.revision_no}</div>
              <div><span className="font-semibold">Component Count:</span> {selectedBomForModal.components?.length}</div>
              <div><span className="font-semibold">Estimated Unit Cost:</span> ₹{selectedBomForModal.total_estimated_cost.toLocaleString()}</div>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                <input
                  type="radio"
                  name="approval"
                  checked={approvalAction.approved}
                  onChange={() => setApprovalAction({ ...approvalAction, approved: true })}
                />
                Approve Revision
              </label>
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer text-rose-600">
                <input
                  type="radio"
                  name="approval"
                  checked={!approvalAction.approved}
                  onChange={() => setApprovalAction({ ...approvalAction, approved: false })}
                />
                Reject Revision
              </label>
            </div>

            {approvalAction.approved && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="set_active"
                  checked={approvalAction.set_as_active}
                  onChange={(e) => setApprovalAction({ ...approvalAction, set_as_active: e.target.checked })}
                  className="h-3.5 w-3.5 rounded border-[#E7E5DE] text-[#315C45]"
                />
                <label htmlFor="set_active" className="text-xs text-slate-700  cursor-pointer">
                  Set as Active Production BOM for this product in {selectedBomForModal.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : selectedBomForModal.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
                </label>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Review Remarks
              </label>
              <textarea
                value={approvalAction.remarks}
                onChange={(e) => setApprovalAction({ ...approvalAction, remarks: e.target.value })}
                className="w-full border rounded-md p-2 text-xs"
                rows={2}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setShowApproveModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {isSubmitting ? 'Recording...' : 'Submit Decision'}
              </Button>
            </div>
          </form>
        </Dialog>
      )}
    </div>
  );
}
