'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { useAuth } from '@/context/AuthContext';
import { reportsClient } from '@/services/reports-client';
import { ReportType, GenericReportResponse } from '@/types/reports';
import {
  LineChart,
  FileSpreadsheet,
  Download,
  Calendar,
  Building2,
  Filter,
  RefreshCw,
  Search,
  ShoppingCart,
  Boxes,
  Scroll,
  Cog,
  CheckCircle2,
  Trash2,
  Zap,
  CalendarCheck,
  IndianRupee,
  Send,
  Layers,
  ArrowUpRight,
  ShieldAlert
} from 'lucide-react';

interface ReportTab {
  id: ReportType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  module: string;
}

const ALL_REPORT_TABS: ReportTab[] = [
  { id: 'sales', label: 'Sales & Invoices', icon: Send, color: 'text-[#315C45]', module: 'sales' },
  { id: 'orders', label: 'Sales Orders', icon: ShoppingCart, color: 'text-indigo-600', module: 'orders' },
  { id: 'dispatch', label: 'Dispatches & Slips', icon: ArrowUpRight, color: 'text-cyan-600', module: 'sales' },
  { id: 'inventory', label: 'Inventory & Balances', icon: Boxes, color: 'text-emerald-600', module: 'inventory' },
  { id: 'bom', label: 'Bill of Materials', icon: Scroll, color: 'text-amber-600', module: 'bom' },
  { id: 'production', label: 'Production & WIP', icon: Cog, color: 'text-violet-600', module: 'production' },
  { id: 'qc', label: 'Quality Control', icon: CheckCircle2, color: 'text-teal-600', module: 'qc' },
  { id: 'wastage', label: 'Wastage & Scrap', icon: Trash2, color: 'text-rose-600', module: 'wastage' },
  { id: 'downtime', label: 'Downtime & Outages', icon: Zap, color: 'text-yellow-600', module: 'power' },
  { id: 'attendance', label: 'HR & Attendance', icon: CalendarCheck, color: 'text-pink-600', module: 'attendance' },
  { id: 'payroll', label: 'Payroll Runs', icon: IndianRupee, color: 'text-green-600', module: 'payroll' },
  { id: 'finance', label: 'General Ledger', icon: Layers, color: 'text-purple-600', module: 'finance' },
];

export default function ReportsPage() {
  const { user, activeUnit, hasPermission } = useAuth();
  const canExport = hasPermission('reports', 'export');

  // Filter tabs strictly: if user lacks permission for module, do not render tab at all
  const availableTabs = React.useMemo(() => {
    if (!user) return [];
    if (user.role === 'SUPER_ADMIN') return ALL_REPORT_TABS;
    return ALL_REPORT_TABS.filter((tab) => hasPermission(tab.module, 'read'));
  }, [user, hasPermission]);

  const [activeTab, setActiveTab] = useState<ReportType>('attendance');

  // Sync activeTab when availableTabs load
  useEffect(() => {
    if (availableTabs.length > 0 && !availableTabs.some((t) => t.id === activeTab)) {
      setActiveTab(availableTabs[0].id);
    }
  }, [availableTabs, activeTab]);

  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState<GenericReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await reportsClient.getReport(activeTab, {
        unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: search || undefined,
        page,
        page_size: pageSize,
      });
      setReportData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch report data.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, activeUnit, startDate, endDate, search, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [activeTab, activeUnit, startDate, endDate, search]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleExport = (format: 'csv' | 'xlsx') => {
    const url = reportsClient.getExportUrl(activeTab, format, {
      unit_id: activeUnit === 'BOTH' ? undefined : activeUnit,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      search: search || undefined,
    });
    window.open(url, '_blank');
  };

  const isRestrictedRole =
    user &&
    user.role !== 'SUPER_ADMIN' &&
    user.role !== 'ADMIN' &&
    (user.role === 'SALES_DISPATCH' ||
      user.account_type === 'SALES_DISPATCH' ||
      user.role === 'QC_INSPECTOR' ||
      user.account_type === 'QC_INSPECTOR' ||
      user.designation === 'QC Inspector' ||
      user.role === 'INVENTORY_MANAGER' ||
      user.account_type === 'INVENTORY_MANAGER' ||
      user.designation === 'Inventory Manager');

  if (isRestrictedRole || !hasPermission('reports', 'read')) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white rounded-xl shadow-sm border border-neutral-200">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-neutral-900">Access Restricted</h2>
        <p className="text-sm text-neutral-600 mt-2">
          Reports & Analytics is reserved for Executives and Administrators.
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
              <LineChart className="w-7 h-7 text-[#315C45]" />
              Reports & Cross-Module Analytics
            </h1>
            <p className="text-sm text-slate-500  mt-1">
              Live enterprise analytics, transaction reconciliations, and auditable data exports.
            </p>
          </div>

          {/* Export Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={!canExport || loading}
              className="flex items-center gap-1.5"
            >
              <Download className="w-4 h-4 text-emerald-600" />
              Export CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('xlsx')}
              disabled={!canExport || loading}
              className="flex items-center gap-1.5 bg-emerald-50 hover:bg-emerald-100 bg-emerald-950/40 border-emerald-200"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-700 text-emerald-400" />
              Export Excel (.xlsx)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={loadReport}
              disabled={loading}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Tab Selection - only authorized tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-[#E7E5DE]  scrollbar-thin">
          {availableTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-[#315C45] text-white shadow-sm'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700  '
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : tab.color}`} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Filter Bar */}
        <Card className="p-4 bg-slate-50/50 /50 border-[#E7E5DE] ">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
            {/* Search */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search report entries..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            {/* Start Date */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500  whitespace-nowrap">From:</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            {/* End Date */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500  whitespace-nowrap">To:</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            {/* Facility Status Info */}
            <div className="flex items-center justify-end text-xs text-slate-500  gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-blue-500" />
              <span>Facility: <strong className="text-slate-700 ">{activeUnit}</strong></span>
              {(startDate || endDate || search) && (
                <button
                  onClick={() => { setStartDate(''); setEndDate(''); setSearch(''); }}
                  className="ml-2 text-xs text-[#315C45] hover:underline cursor-pointer"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>
        </Card>

        {/* Period KPIs */}
        {reportData?.kpis && reportData.kpis.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {reportData.kpis.map((kpi, idx) => (
              <Card key={idx} className="p-4 bg-white  border-[#E7E5DE]  shadow-xs">
                <span className="text-xs font-medium text-slate-500  block truncate">
                  {kpi.metric_name}
                </span>
                <span className="text-xl font-bold text-slate-900  mt-1 block">
                  {kpi.formatted_value}
                </span>
              </Card>
            ))}
          </div>
        )}

        {/* Report Data Table */}
        <Card className="p-0 overflow-hidden border-[#E7E5DE]  shadow-xs">
          {error ? (
            <div className="p-8 text-center text-rose-600 text-sm">
              {error}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 /80 border-b border-[#E7E5DE]  text-slate-500  font-semibold">
                    {reportData?.columns.map((col) => (
                      <th key={col.key} className="py-3 px-4 uppercase tracking-wider text-[11px]">
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 divide-slate-800">
                  {loading ? (
                    <tr>
                      <td colSpan={reportData?.columns.length || 5} className="py-12 text-center text-slate-400">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-500" />
                        Aggregating analytical ledger...
                      </td>
                    </tr>
                  ) : reportData?.items.length === 0 ? (
                    <tr>
                      <td colSpan={reportData?.columns.length || 5} className="py-12 text-center text-slate-400">
                        No transactions recorded for the selected filter criteria.
                      </td>
                    </tr>
                  ) : (
                    reportData?.items.map((row, rIdx) => (
                      <tr
                        key={String(row.id ?? rIdx)}
                        className="hover:bg-slate-50/60 /40 transition-colors"
                      >
                        {reportData.columns.map((col) => {
                          const val = row[col.key];
                          const isCurrency = col.label.includes('(₹)');
                          return (
                            <td key={col.key} className="py-3 px-4 font-medium text-slate-800 ">
                              {isCurrency && typeof val === 'number'
                                ? `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                                : val !== undefined && val !== null
                                ? String(val)
                                : '-'}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {reportData && reportData.total_pages > 1 && (
            <div className="p-3 border-t border-[#E7E5DE]  flex items-center justify-between text-xs text-slate-500">
              <span>
                Showing page {reportData.page} of {reportData.total_pages} ({reportData.total} records)
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={reportData.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={reportData.page >= reportData.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
  );
}
