'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { apiClient } from '@/services/api-client';
import { DashboardSummaryResponse, DashboardActivityResponse } from '@/types/dashboard';
import {
  ShoppingCart,
  Send,
  Boxes,
  Cog,
  CheckCircle2,
  Trash2,
  CalendarCheck,
  ShieldAlert,
  ShieldCheck,
  Building2,
  RefreshCw,
  Clock,
  Activity,
} from 'lucide-react';
import { getUnitDisplayName, getUnitDivision } from '@/lib/constants';
import { formatISTTime, formatISTDateTime, formatISTDate, formatRelativeTime } from '@/lib/date';

export function OperationsDashboardView() {
  const { user, activeUnit, setActiveUnit, canAccessUnit } = useAuth();

  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [activity, setActivity] = useState<DashboardActivityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshingFeed, setIsRefreshingFeed] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [liveClockIST, setLiveClockIST] = useState<string>('');

  // Live ticking IST clock (1-second precision)
  useEffect(() => {
    const updateClock = () => {
      setLiveClockIST(formatISTTime(new Date(), true, true));
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [summaryRes, activityRes] = await Promise.all([
        apiClient.get<DashboardSummaryResponse>(`/api/v1/dashboard/summary?unit_id=${activeUnit}`),
        apiClient.get<DashboardActivityResponse>(`/api/v1/dashboard/activity?unit_id=${activeUnit}`),
      ]);

      if (summaryRes.data) {
        setSummary(summaryRes.data);
      }
      if (activityRes.data) {
        setActivity(activityRes.data);
      }
      setLastUpdated(new Date());
    } finally {
      setIsLoading(false);
    }
  }, [activeUnit]);

  // Silent background fetch for real-time operations feed and live KPI summary
  const fetchActivityRealTime = useCallback(async () => {
    try {
      setIsRefreshingFeed(true);
      const [summaryRes, activityRes] = await Promise.all([
        apiClient.get<DashboardSummaryResponse>(`/api/v1/dashboard/summary?unit_id=${activeUnit}`),
        apiClient.get<DashboardActivityResponse>(`/api/v1/dashboard/activity?unit_id=${activeUnit}`),
      ]);
      if (summaryRes.data) {
        setSummary(summaryRes.data);
      }
      if (activityRes.data) {
        setActivity(activityRes.data);
      }
      setLastUpdated(new Date());
    } catch {
      // Silently catch background poll failures
    } finally {
      setIsRefreshingFeed(false);
    }
  }, [activeUnit]);

  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setIsLoading(true);
      try {
        const [summaryRes, activityRes] = await Promise.all([
          apiClient.get<DashboardSummaryResponse>(`/api/v1/dashboard/summary?unit_id=${activeUnit}`),
          apiClient.get<DashboardActivityResponse>(`/api/v1/dashboard/activity?unit_id=${activeUnit}`),
        ]);

        if (!isMounted) return;
        if (summaryRes.data) setSummary(summaryRes.data);
        if (activityRes.data) setActivity(activityRes.data);
        setLastUpdated(new Date());
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadData();

    // Real-time automatic polling every 6 seconds for operations feed
    const pollInterval = setInterval(() => {
      if (isMounted) {
        fetchActivityRealTime();
      }
    }, 6000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [activeUnit, fetchActivityRealTime]);

  const unitName = getUnitDisplayName(activeUnit);

  return (
    <div className="space-y-6">
      {/* Top Banner & Facility Control Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-[#FFFFFF] p-6 sm:p-7 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        {/* Subtle executive accent strip on left border */}
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />

        <div className="space-y-1.5 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A] font-mono">
              Operational Command Center
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A] border-[#E2E8F0]">
              {activeUnit === 'Unit_1'
                ? 'UNIT 1'
                : activeUnit === 'Unit_2'
                  ? 'UNIT 2'
                  : 'ALL UNITS'}
            </Badge>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            {unitName}
          </h2>
          <p className="text-xs text-[#64748B] max-w-xl">
            Live shop-floor telemetry, machine allocation, order queues, and quality metrics aggregated for {user?.full_name} ({user?.role}).
          </p>
        </div>

        {/* Facility Selector Buttons */}
        <div className="flex items-center gap-2 bg-[#F1F5F9] p-1.5 rounded-xl border border-[#E2E8F0]">
          <button
            type="button"
            onClick={() => setActiveUnit('Unit_1')}
            disabled={!canAccessUnit('Unit_1')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${activeUnit === 'Unit_1'
              ? 'bg-[#0F172A] text-white shadow-xs font-bold'
              : canAccessUnit('Unit_1')
                ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#FFFFFF]'
                : 'opacity-40 cursor-not-allowed text-[#94A3B8]'
              }`}
          >
            <Building2 className="h-3.5 w-3.5" />
            Unit 1 (Machining)
          </button>
          <button
            type="button"
            onClick={() => setActiveUnit('Unit_2')}
            disabled={!canAccessUnit('Unit_2')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${activeUnit === 'Unit_2'
              ? 'bg-[#0F172A] text-white shadow-xs font-bold'
              : canAccessUnit('Unit_2')
                ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#FFFFFF]'
                : 'opacity-40 cursor-not-allowed text-[#94A3B8]'
              }`}
          >
            <Building2 className="h-3.5 w-3.5" />
            Unit 2 (Assembly & QC)
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Orders */}
        <KpiCard
          kpi={summary?.kpis.orders}
          defaultTitle="Purchase Orders"
          defaultSubtitle="Active production jobs"
          icon={ShoppingCart}
          isLoading={isLoading}
        />

        {/* 2. Dispatch */}
        <KpiCard
          kpi={summary?.kpis.dispatch}
          defaultTitle="Sales & Dispatch"
          defaultSubtitle="Scheduled dispatches"
          icon={Send}
          isLoading={isLoading}
        />

        {/* 3. Stock */}
        <KpiCard
          kpi={summary?.kpis.stock}
          defaultTitle="Inventory Stock"
          defaultSubtitle="Tracked raw materials & parts"
          icon={Boxes}
          isLoading={isLoading}
        />

        {/* 4. Production */}
        <KpiCard
          kpi={summary?.kpis.production}
          defaultTitle="Shop-Floor Batches"
          defaultSubtitle="WIP machining & assembly"
          icon={Cog}
          isLoading={isLoading}
        />

        {/* 5. Quality Control */}
        <KpiCard
          kpi={summary?.kpis.qc}
          defaultTitle="QC Inspections"
          defaultSubtitle="Tolerances & dimensional checks"
          icon={CheckCircle2}
          isLoading={isLoading}
        />

        {/* 6. Wastage & Scrap */}
        <KpiCard
          kpi={summary?.kpis.wastage}
          defaultTitle="Wastage & Scrap"
          defaultSubtitle="Offcuts & melting reconciliation"
          icon={Trash2}
          isLoading={isLoading}
        />

        {/* 7. Attendance */}
        <KpiCard
          kpi={summary?.kpis.attendance}
          defaultTitle="Daily Attendance"
          defaultSubtitle="Active shift operators"
          icon={CalendarCheck}
          isLoading={isLoading}
        />

        {/* 8. Approvals */}
        <KpiCard
          kpi={summary?.kpis.approvals}
          defaultTitle="Pending Approvals"
          defaultSubtitle="PO sign-offs & leave requests"
          icon={ShieldAlert}
          isLoading={isLoading}
        />
      </div>

      {/* Split Section: Real Activity Feed & Status Diagnostics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Real Activity Feed (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-[#EFEEE8]">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-[#0F172A]">
                    Recent Manufacturing Operations & Audit Logs
                  </h3>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                    </span>
                    LIVE IST
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Chronological manufacturing and security events recorded in real-time Indian Standard Time (IST &bull; UTC+05:30)
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] font-mono text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                  {liveClockIST || 'IST Syncing...'}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchActivityRealTime}
                  disabled={isRefreshingFeed}
                  className="h-7 text-xs flex items-center gap-1 px-2.5"
                  title="Refresh activity logs now"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRefreshingFeed ? 'animate-spin text-emerald-600' : 'text-slate-500'}`} />
                  <span className="text-[11px]">Sync</span>
                </Button>
              </div>
            </div>

            {isLoading ? (
              <div className="py-12 flex flex-col items-center justify-center space-y-2">
                <div className="w-6 h-6 border-2 border-[#315C45] border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-[#73786F]">Loading real-time operations feed...</span>
              </div>
            ) : !activity || activity.activities.length === 0 ? (
              <EmptyState
                title="No operations recorded yet"
                description={`Transactions for ${activeUnit} will appear here in real time as operators execute batches, book inventory, or inspect tolerances.`}
                icon={Activity}
              />
            ) : (
              <div className="divide-y divide-[#EFEEE8] max-h-[520px] overflow-y-auto pr-1">
                {activity.activities.map((act) => {
                  const mod = (act.module || '').toLowerCase();
                  const isOrder = mod.includes('order');
                  const isProd = mod.includes('prod');
                  const isInv = mod.includes('inv');
                  const isWaste = mod.includes('waste') || mod.includes('scrap');
                  const isAuth = mod.includes('auth') || mod.includes('sec') || mod.includes('user');

                  return (
                    <div key={act.id} className="py-3 flex items-start justify-between gap-3 text-xs hover:bg-slate-50/60 transition-colors px-1 rounded-md">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className={`p-1.5 rounded-lg mt-0.5 shrink-0 ${isOrder ? 'bg-blue-50 text-blue-700' :
                          isProd ? 'bg-amber-50 text-amber-700' :
                            isInv ? 'bg-purple-50 text-purple-700' :
                              isWaste ? 'bg-rose-50 text-rose-700' :
                                isAuth ? 'bg-emerald-50 text-emerald-700' :
                                  'bg-[#EAF0E9] text-[#315C45]'
                          }`}>
                          {isOrder ? <ShoppingCart className="h-3.5 w-3.5" /> :
                            isProd ? <Cog className="h-3.5 w-3.5" /> :
                              isInv ? <Boxes className="h-3.5 w-3.5" /> :
                                isWaste ? <Trash2 className="h-3.5 w-3.5" /> :
                                  isAuth ? <ShieldCheck className="h-3.5 w-3.5" /> :
                                    <Activity className="h-3.5 w-3.5" />}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-[#202722] truncate">
                            {act.description}
                          </p>
                          <div className="flex items-center gap-2 text-[11px] text-[#73786F] mt-0.5">
                            <span>Operator: <span className="font-medium text-slate-700">{act.user_email || 'System'}</span></span>
                            <span>&bull;</span>
                            <span>Unit: <span className="font-medium text-slate-700">{act.unit_id === 'Unit_1' ? 'Unit 1' : act.unit_id === 'Unit_2' ? 'Unit 2' : (act.unit_id || activeUnit)}</span></span>
                          </div>
                        </div>
                      </div>

                      {/* IST Real-Time Timestamp Display */}
                      <div className="text-right shrink-0 pl-2">
                        <div className="flex items-center justify-end gap-1.5">
                          <span className="text-[11px] font-bold text-slate-800 font-mono">
                            {formatISTTime(act.timestamp, true, false)}
                          </span>
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase font-mono">
                            IST
                          </span>
                        </div>
                        <div className="flex items-center justify-end gap-1 text-[10px] text-slate-400 mt-0.5 font-medium" title={formatISTDateTime(act.timestamp)}>
                          <Clock className="w-2.5 h-2.5 text-slate-300" />
                          <span>{formatRelativeTime(act.timestamp)}</span>
                          <span>&bull;</span>
                          <span>{formatISTDate(act.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Plant Summary & Telemetry (1 Col) */}
        <div className="space-y-4">
          <Card
            title="Facility Overview"
            subtitle="Unit specifications and operational status"
          >
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-[#EFEEE8]">
                <span className="text-[#73786F]">Unit:</span>
                <span className="font-mono font-bold text-[#202722]">
                  {activeUnit === 'Unit_1' ? 'Unit 1 (Machining)' : 'Unit 2 (Assembly & QC)'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-[#EFEEE8]">
                <span className="text-[#73786F]">Facility Division:</span>
                <span className="font-medium text-[#202722]">
                  {getUnitDivision(activeUnit)}
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-[#EFEEE8]">
                <span className="text-[#73786F]">ERP Sync State:</span>
                <Badge variant="success">Online & Listening</Badge>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-[#EFEEE8]">
                <span className="text-[#73786F]">Active Operator:</span>
                <span className="font-medium text-[#202722] truncate max-w-[140px]">
                  {user?.full_name}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#73786F]">Assigned Role:</span>
                <Badge variant="neutral">{user?.role}</Badge>
              </div>

              <div className="pt-3 border-t border-[#EFEEE8] flex items-center justify-between text-[11px] text-[#73786F]">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Synced {lastUpdated.toLocaleTimeString()}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchDashboardData}
                  disabled={isLoading}
                  className="text-[11px] py-1 px-2.5 flex items-center gap-1.5 border-[#E7E5DE] text-[#202722] hover:bg-[#F1F0EA]"
                >
                  <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
