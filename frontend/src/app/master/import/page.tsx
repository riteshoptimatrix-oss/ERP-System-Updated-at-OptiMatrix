'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/context/AuthContext';
import { reportsClient } from '@/services/reports-client';
import {
  ImportEntityType,
  ImportDryRunResponse,
  ImportBatchSummary,
} from '@/types/reports';
import {
  FileSpreadsheet,
  Upload,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  History,
  FileCheck2,
  RefreshCw,
  Building2,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

const ENTITY_OPTIONS: { id: ImportEntityType; label: string; description: string }[] = [
  { id: 'customers', label: 'Customer Master', description: 'Client billing, GSTIN, credit limits, and contact profiles' },
  { id: 'vendors', label: 'Supplier & Vendor Master', description: 'Vendor GSTIN, payment terms, and procurement addresses' },
  { id: 'raw_materials', label: 'Raw Material Master', description: 'Material codes, UoM, reorder limits, and cost prices' },
  { id: 'finished_products', label: 'Finished Product Master', description: 'Product codes, selling prices, UoM, and categories' },
  { id: 'employees', label: 'Employee Master', description: 'Workforce records, designations, departments, and payroll base' },
  { id: 'warehouses', label: 'Warehouse & Storage Locations', description: 'Storage sheds, racks, and facility associations' },
  { id: 'categories', label: 'Product & Material Categories', description: 'Item groupings and taxonomy codes' },
  { id: 'uoms', label: 'Units of Measure', description: 'Measurement units (KG, NOS, MTR, SET)' },
  { id: 'opening_stock', label: 'Opening Stock Balances', description: 'Initial stock ledger quantities and valuations' },
];

export default function ExcelMigrationStudioPage() {
  const { user, activeUnit, hasPermission } = useAuth();
  const canImport = hasPermission('master', 'create');
  const isHRUser = user && (user.role === 'HR' || user.account_type === 'HR' || user.department?.toUpperCase() === 'HR' || user.department?.toLowerCase() === 'human resources') && user.role !== 'SUPER_ADMIN' && user.role !== 'ADMIN';
  const isSalesDispatchUser = user && (user.role === 'SALES_DISPATCH' || user.account_type === 'SALES_DISPATCH') && user.role !== 'SUPER_ADMIN' && user.role !== 'ADMIN';
  const isQCUser = user && (user.role === 'QC_INSPECTOR' || user.account_type === 'QC_INSPECTOR' || user.designation === 'QC Inspector') && user.role !== 'SUPER_ADMIN' && user.role !== 'ADMIN';
  const isInventoryManagerUser = user && (user.role === 'INVENTORY_MANAGER' || user.account_type === 'INVENTORY_MANAGER' || user.designation === 'Inventory Manager') && user.role !== 'SUPER_ADMIN' && user.role !== 'ADMIN';

  const [selectedEntity, setSelectedEntity] = useState<ImportEntityType>('customers');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<ImportDryRunResponse | null>(null);
  const [commitMessage, setCommitMessage] = useState<string | null>(null);
  const [commitLoading, setCommitLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [batches, setBatches] = useState<ImportBatchSummary[]>([]);
  const [loadingBatches, setLoadingBatches] = useState(false);

  const loadBatchHistory = async () => {
    try {
      setLoadingBatches(true);
      const res = await reportsClient.listBatches(1, 10);
      setBatches(res.items);
    } catch {
      // Ignored
    } finally {
      setLoadingBatches(false);
    }
  };

  useEffect(() => {
    loadBatchHistory();
  }, []);

  const handleDownloadTemplate = () => {
    const url = reportsClient.getTemplateUrl(selectedEntity);
    window.open(url, '_blank');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setDryRunResult(null);
      setCommitMessage(null);
    }
  };

  const handleDryRun = async () => {
    if (!selectedFile) return;
    try {
      setIsUploading(true);
      setCommitMessage(null);
      const res = await reportsClient.dryRunImport(selectedEntity, selectedFile);
      setDryRunResult(res);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Dry-run validation failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCommit = async () => {
    if (!dryRunResult || !dryRunResult.can_commit) return;
    try {
      setCommitLoading(true);
      const res = await reportsClient.commitBatch({
        batch_token: dryRunResult.batch_token,
        unit_id: activeUnit === 'BOTH' ? 'Unit_1' : activeUnit,
        notes: notes || undefined,
      });
      setCommitMessage(res.message);
      setDryRunResult(null);
      setSelectedFile(null);
      loadBatchHistory();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to commit batch to database.');
    } finally {
      setCommitLoading(false);
    }
  };

  if (!canImport || isHRUser || isSalesDispatchUser || isQCUser || isInventoryManagerUser) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white rounded-xl shadow-sm border border-neutral-200">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-neutral-900">Access Restricted</h2>
        <p className="text-sm text-neutral-600 mt-2">
          {isHRUser || isSalesDispatchUser || isQCUser || isInventoryManagerUser
            ? 'Excel Migration & Bulk Import Studio is reserved for Administrators and Operations Managers.'
            : 'You do not possess the required master:create permission to import master datasets.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900  flex items-center gap-2">
            <FileSpreadsheet className="w-7 h-7 text-emerald-600" />
            Excel Migration & Bulk Import Studio
          </h1>
          <p className="text-sm text-slate-500  mt-1">
            Safely validate legacy Excel workbooks, detect duplicates, preview row errors, and commit with zero overwrites.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadTemplate}
            className="flex items-center gap-1.5 bg-[#EAF0E9] border-[#315C45]/20 text-[#254936] hover:bg-blue-100"
          >
            <Download className="w-4 h-4 text-[#315C45]" />
            Download Standard Template (.xlsx)
          </Button>
        </div>
      </div>

      {/* Multi-step workflow banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-lg border border-[#E7E5DE]  bg-white  flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-full bg-blue-100 text-[#254936] font-bold flex items-center justify-center shrink-0">1</span>
          <div>
            <p className="font-semibold text-slate-800 ">Select Entity</p>
            <p className="text-[11px] text-slate-400">Master or Stock data</p>
          </div>
        </div>
        <div className="p-3 rounded-lg border border-[#E7E5DE]  bg-white  flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-full bg-blue-100 text-[#254936] font-bold flex items-center justify-center shrink-0">2</span>
          <div>
            <p className="font-semibold text-slate-800 ">Upload & Dry-Run</p>
            <p className="text-[11px] text-slate-400">Schema & duplicate checks</p>
          </div>
        </div>
        <div className="p-3 rounded-lg border border-[#E7E5DE]  bg-white  flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-full bg-blue-100 text-[#254936] font-bold flex items-center justify-center shrink-0">3</span>
          <div>
            <p className="font-semibold text-slate-800 ">Review Discrepancies</p>
            <p className="text-[11px] text-slate-400">Row-level error breakdown</p>
          </div>
        </div>
        <div className="p-3 rounded-lg border border-[#E7E5DE]  bg-white  flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center shrink-0">4</span>
          <div>
            <p className="font-semibold text-slate-800 ">Authorized Commit</p>
            <p className="text-[11px] text-slate-400">Atomic database insertion</p>
          </div>
        </div>
      </div>

      {/* Step 1 & 2: Entity Selection & File Upload Card */}
      <Card className="p-6 border-[#E7E5DE] ">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Entity Selection */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
              1. Select Target Collection
            </label>
            <select
              value={selectedEntity}
              onChange={(e) => {
                setSelectedEntity(e.target.value as ImportEntityType);
                setDryRunResult(null);
                setSelectedFile(null);
              }}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            >
              {ENTITY_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-2">
              {ENTITY_OPTIONS.find((o) => o.id === selectedEntity)?.description}
            </p>
          </div>

          {/* File Drag and Drop */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
              2. Choose Workbook File (.xlsx, .csv)
            </label>
            <div className="border-2 border-dashed border-[#E7E5DE]  rounded-lg p-4 text-center hover:border-[#315C45] transition-colors bg-slate-50/50 /40">
              <input
                type="file"
                accept=".xlsx,.csv"
                onChange={handleFileChange}
                className="hidden"
                id="import-file-input"
              />
              <label
                htmlFor="import-file-input"
                className="cursor-pointer flex flex-col items-center justify-center gap-1.5"
              >
                <Upload className="w-6 h-6 text-slate-400" />
                <span className="text-xs font-medium text-slate-700 ">
                  {selectedFile ? selectedFile.name : 'Click to browse Excel or CSV file'}
                </span>
                <span className="text-[11px] text-slate-400">
                  Max file size 25MB • UTF-8 or standard Excel formatting
                </span>
              </label>
            </div>

            {selectedFile && (
              <div className="mt-3 flex justify-end">
                <Button
                  size="sm"
                  onClick={handleDryRun}
                  disabled={isUploading || !canImport}
                  className="flex items-center gap-2 bg-[#315C45] hover:bg-[#254936] text-white"
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Validating Schema & Duplicates...
                    </>
                  ) : (
                    <>
                      <FileCheck2 className="w-4 h-4" />
                      Run Dry-Run Validation
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Success Alert */}
      {commitMessage && (
        <div className="p-4 rounded-lg bg-emerald-50 bg-emerald-950/40 border border-emerald-200 border-emerald-800 flex items-center gap-3 text-emerald-800 text-emerald-300 text-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <div>
            <p className="font-semibold">{commitMessage}</p>
            <p className="text-xs mt-0.5">Records are now active and queryable across master tables and analytical reports.</p>
          </div>
        </div>
      )}

      {/* Dry-Run Results Section */}
      {dryRunResult && (
        <Card className="p-6 border-[#E7E5DE]  space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-[#EFEEE8] ">
            <div>
              <h3 className="text-base font-bold text-slate-900  flex items-center gap-2">
                Dry-Run Validation Report
                {dryRunResult.can_commit ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">
                    PASSED
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800">
                    ERRORS DETECTED
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-500 mt-1">{dryRunResult.validation_summary}</p>
            </div>

            {/* Commit Button */}
            {dryRunResult.can_commit && (
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  placeholder="Optional commit notes..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="px-3 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900 "
                />
                <Button
                  size="sm"
                  onClick={handleCommit}
                  disabled={commitLoading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-sm"
                >
                  {commitLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Authorize & Commit ({dryRunResult.valid_rows_count} Rows)
                </Button>
              </div>
            )}
          </div>

          {/* Validation Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg bg-slate-50 /60 border border-[#E7E5DE] ">
              <span className="text-[11px] font-medium text-slate-500 block">Total Processed Rows</span>
              <span className="text-xl font-bold text-slate-900  mt-0.5 block">{dryRunResult.total_rows}</span>
            </div>
            <div className="p-3 rounded-lg bg-emerald-50/70 bg-emerald-950/30 border border-emerald-200 border-emerald-800/50">
              <span className="text-[11px] font-medium text-emerald-700 text-emerald-400 block">Clean & Valid Rows</span>
              <span className="text-xl font-bold text-emerald-700 text-emerald-400 mt-0.5 block">{dryRunResult.valid_rows_count}</span>
            </div>
            <div className="p-3 rounded-lg bg-rose-50/70 bg-rose-950/30 border border-rose-200 border-rose-800/50">
              <span className="text-[11px] font-medium text-rose-700 text-rose-400 block">Invalid Row Count</span>
              <span className="text-xl font-bold text-rose-700 text-rose-400 mt-0.5 block">{dryRunResult.error_rows_count}</span>
            </div>
            <div className="p-3 rounded-lg bg-amber-50/70 bg-amber-950/30 border border-amber-200 border-amber-800/50">
              <span className="text-[11px] font-medium text-amber-700 text-amber-400 block">Detected Duplicates</span>
              <span className="text-xl font-bold text-amber-700 text-amber-400 mt-0.5 block">{dryRunResult.duplicate_rows_count}</span>
            </div>
          </div>

          {/* Error Breakdown Table (If Any) */}
          {dryRunResult.errors.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-rose-600 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                Row-Level Discrepancy Breakdown
              </h4>
              <div className="max-h-60 overflow-y-auto border border-rose-200 border-rose-900 rounded-lg">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-rose-50 bg-rose-950/60 text-rose-800 text-rose-300 font-semibold sticky top-0">
                    <tr>
                      <th className="py-2 px-3 border-b border-rose-200 border-rose-900">Row #</th>
                      <th className="py-2 px-3 border-b border-rose-200 border-rose-900">Column</th>
                      <th className="py-2 px-3 border-b border-rose-200 border-rose-900">Provided Value</th>
                      <th className="py-2 px-3 border-b border-rose-200 border-rose-900">Error Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rose-100 divide-rose-900/50 text-slate-800 ">
                    {dryRunResult.errors.map((err, idx) => (
                      <tr key={idx} className="hover:bg-rose-50/40">
                        <td className="py-1.5 px-3 font-bold text-rose-700">{err.row_number}</td>
                        <td className="py-1.5 px-3 font-medium">{err.column || '-'}</td>
                        <td className="py-1.5 px-3 font-mono text-slate-600 ">{String(err.value || '-')}</td>
                        <td className="py-1.5 px-3 text-rose-600 text-rose-400">{err.error_message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Batch History Section */}
      <Card className="p-6 border-[#E7E5DE] ">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-slate-900  flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            Past Import Batches & Audit Trail
          </h3>
          <Button
            variant="outline"
            size="sm"
            onClick={loadBatchHistory}
            disabled={loadingBatches}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingBatches ? 'animate-spin' : ''}`} />
            Refresh Log
          </Button>
        </div>

        <div className="overflow-x-auto border border-[#E7E5DE]  rounded-lg">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-50  text-slate-500 font-semibold">
              <tr>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Filename</th>
                <th className="py-2.5 px-3">Target Entity</th>
                <th className="py-2.5 px-3">Rows</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Committed By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 divide-slate-800">
              {batches.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No import batches recorded yet.
                  </td>
                </tr>
              ) : (
                batches.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-50/50 /40">
                    <td className="py-2 px-3 text-slate-600 ">
                      {new Date(b.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 px-3 font-medium text-slate-900 ">{b.filename}</td>
                    <td className="py-2 px-3 uppercase text-[11px] font-semibold text-[#315C45]">{b.entity_type}</td>
                    <td className="py-2 px-3">
                      <span className="text-emerald-600 font-semibold">{b.valid_rows_count} valid</span> / {b.total_rows}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${b.status === 'COMMITTED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : b.status === 'DRY_RUN_PASSED'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                      >
                        {b.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-500">{b.committed_by || b.created_by}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
