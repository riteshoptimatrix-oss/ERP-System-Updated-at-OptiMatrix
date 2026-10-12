'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { apiClient } from '@/services/api-client';
import { HRAttendanceSummary, AttendanceEntry, LeaveApplication } from '@/types/hr';
import { Employee, PaginatedResponse } from '@/types/master';
import { DashboardActivityResponse } from '@/types/dashboard';
import {
  Users,
  CalendarCheck,
  UserCheck,
  UserX,
  Clock,
  Briefcase,
  AlertCircle,
  TrendingUp,
  Plus,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Building2,
  Calendar,
  Layers,
  Activity,
  Check,
  X,
} from 'lucide-react';
import { formatISTTime, formatISTDate, formatISTDateTime, formatRelativeTime } from '@/lib/date';
import { useAuth } from '@/context/AuthContext';

export function HRDashboardView() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<HRAttendanceSummary | null>(null);
  const [todayAttendance, setTodayAttendance] = useState<AttendanceEntry[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [activity, setActivity] = useState<DashboardActivityResponse | null>(null);
  const [pendingLeavesList, setPendingLeavesList] = useState<LeaveApplication[]>([]);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [liveClockIST, setLiveClockIST] = useState<string>('');
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // Live ticking IST clock (1-second precision)
  useEffect(() => {
    const updateClock = () => {
      setLiveClockIST(formatISTTime(new Date(), true, true));
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  const loadHRData = useCallback(async () => {
    try {
      const todayStr = new Date().toISOString().split('T')[0];
      const [sumRes, attRes, empRes, actRes, leavesRes] = await Promise.allSettled([
        apiClient.get<HRAttendanceSummary>('/api/v1/hr/summary'),
        apiClient.get<PaginatedResponse<AttendanceEntry>>(`/api/v1/hr/attendance?date=${todayStr}&page=1&page_size=10`),
        apiClient.get<PaginatedResponse<Employee>>('/api/v1/master/employees?page=1&page_size=100'),
        apiClient.get<DashboardActivityResponse>('/api/v1/dashboard/activity?unit_id=BOTH'),
        apiClient.get<PaginatedResponse<LeaveApplication>>('/api/v1/hr/leaves?status=PENDING&page=1&page_size=20'),
      ]);

      if (sumRes.status === 'fulfilled' && sumRes.value.data) {
        setSummary(sumRes.value.data);
      }
      if (attRes.status === 'fulfilled' && attRes.value.data) {
        setTodayAttendance(attRes.value.data.items || []);
      }
      if (empRes.status === 'fulfilled' && empRes.value.data) {
        setEmployees(empRes.value.data.items || []);
      }
      if (actRes.status === 'fulfilled' && actRes.value.data) {
        setActivity(actRes.value.data);
      }
      if (leavesRes.status === 'fulfilled' && leavesRes.value.data) {
        setPendingLeavesList(leavesRes.value.data.items || []);
      }
      setLastUpdated(new Date());
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const handleReviewLeave = async (leaveId: string, status: 'APPROVED' | 'REJECTED') => {
    let rejectionReason: string | undefined = undefined;
    if (status === 'REJECTED') {
      const promptRes = window.prompt('Please enter the reason for rejecting this leave:');
      if (promptRes === null) return;
      if (!promptRes.trim()) {
        alert('A rejection reason is mandatory.');
        return;
      }
      rejectionReason = promptRes.trim();
    }

    setActionLoadingId(leaveId);
    try {
      const res = await apiClient.put(`/api/v1/hr/leaves/${leaveId}/review`, {
        status,
        notes: rejectionReason ? `Rejected by HR: ${rejectionReason}` : 'Approved by HR Administrator',
        rejection_reason: rejectionReason,
      });
      if (res.error) {
        alert(res.error.message || `Failed to ${status.toLowerCase()} leave`);
      } else {
        await loadHRData();
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update leave');
    } finally {
      setActionLoadingId(null);
    }
  };

  useEffect(() => {
    setIsLoading(true);
    loadHRData();
    const interval = setInterval(loadHRData, 15000);
    return () => clearInterval(interval);
  }, [loadHRData]);

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    loadHRData();
  };

  const totalEmployees = summary?.total_active_employees ?? employees.length;
  const presentToday = summary?.present_today ?? 0;
  const onLeaveToday = summary?.on_leave_today ?? 0;
  const absentToday = summary?.absent_today ?? 0;
  const pendingLeaves = summary?.pending_leave_requests ?? 0;
  const totalOt = summary?.total_overtime_hours_month ?? 0;
  const attendanceRate = totalEmployees > 0 ? Math.round((presentToday / totalEmployees) * 100) : 0;

  // Department distribution calculation
  const deptCounts: Record<string, number> = {};
  employees.forEach((emp) => {
    const dept = emp.department || 'Operations';
    deptCounts[dept] = (deptCounts[dept] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Executive HR Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-white p-6 sm:p-7 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />

        <div className="space-y-1.5 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A] font-mono">
              Human Resources & Workforce Administration
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A] border-[#E2E8F0]">
              ENTERPRISE-WIDE
            </Badge>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Corporate Workforce & Attendance Operations
          </h2>
          <p className="text-xs text-[#64748B] max-w-xl">
            Live personnel register, biometric shift attendance, leave requests, and payroll disbursement aggregated for {user?.full_name} ({user?.role}).
          </p>
        </div>

        {/* Quick HR Navigation Shortcuts */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Link href="/attendance">
            <Button variant="outline" size="sm" className="text-xs flex items-center gap-1.5">
              <CalendarCheck className="w-3.5 h-3.5 text-blue-600" />
              Daily Attendance
            </Button>
          </Link>
          <Link href="/hr">
            <Button variant="outline" size="sm" className="text-xs flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-emerald-600" />
              Staff Directory
            </Button>
          </Link>
          <Link href="/payroll">
            <Button variant="outline" size="sm" className="text-xs flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-purple-600" />
              Payroll & Salaries
            </Button>
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="text-xs flex items-center gap-1.5 border-slate-200"
            title="Refresh HR metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
            Sync
          </Button>
        </div>
      </div>

      {/* 8 Real HR KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Total Workforce */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Total Workforce
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
                  {isLoading ? '...' : totalEmployees}
                </span>
                <span className="text-[11px] text-[#64748B]">Active Staff</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-700">
              <Users className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Across both units</span>
            <Link href="/hr" className="text-blue-600 hover:underline flex items-center gap-0.5">
              Directory &rarr;
            </Link>
          </div>
        </Card>

        {/* 2. Present Today */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Present Today
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-emerald-700">
                  {isLoading ? '...' : presentToday}
                </span>
                <span className="text-[11px] text-emerald-600 font-medium">Clocked In</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-700">
              <UserCheck className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Current shift punch-ins</span>
            <Link href="/attendance" className="text-emerald-600 hover:underline flex items-center gap-0.5">
              Logs &rarr;
            </Link>
          </div>
        </Card>

        {/* 3. On Leave Today */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                On Leave Today
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-amber-600">
                  {isLoading ? '...' : onLeaveToday}
                </span>
                <span className="text-[11px] text-amber-600 font-medium">Approved</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700">
              <Calendar className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Casual & paid leaves</span>
            <Link href="/attendance" className="text-amber-600 hover:underline flex items-center gap-0.5">
              Leaves &rarr;
            </Link>
          </div>
        </Card>

        {/* 4. Absent Today */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Absent Today
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-rose-600">
                  {isLoading ? '...' : absentToday}
                </span>
                <span className="text-[11px] text-rose-500 font-medium">Unexcused</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-rose-50 text-rose-700">
              <UserX className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>LOP calculated</span>
            <span className="text-[10px] text-slate-400">Auto-tracked</span>
          </div>
        </Card>

        {/* 5. Attendance Rate */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Attendance Rate
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
                  {isLoading ? '...' : `${attendanceRate}%`}
                </span>
                <Badge variant={attendanceRate >= 85 ? 'success' : 'warning'} className="text-[10px] px-1.5 py-0.5">
                  {attendanceRate >= 85 ? 'Healthy' : 'Below Target'}
                </Badge>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-cyan-50 text-cyan-700">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Target: 95% threshold</span>
            <span className="font-mono text-[10px]">Today</span>
          </div>
        </Card>

        {/* 6. Pending Leave Requests */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Pending Leaves
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-amber-600">
                  {isLoading ? '...' : pendingLeaves}
                </span>
                {pendingLeaves > 0 && (
                  <Badge variant="warning" className="text-[10px] px-1.5 py-0.5">
                    Needs Action
                  </Badge>
                )}
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700">
              <AlertCircle className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Requires HR review</span>
            <Link href="/attendance?tab=leaves" className="text-amber-600 hover:underline flex items-center gap-0.5 font-medium">
              Review Applications &rarr;
            </Link>
          </div>
        </Card>

        {/* 7. Monthly Overtime */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Monthly Overtime
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
                  {isLoading ? '...' : `${totalOt} hrs`}
                </span>
                <span className="text-[11px] text-[#64748B]">Accumulated</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-violet-50 text-violet-700">
              <Clock className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Current calendar month</span>
            <span className="font-mono text-[10px]">Overtime</span>
          </div>
        </Card>

        {/* 8. Payroll & Salary Cycle */}
        <Card className="p-5 border-[#E2E8F0] bg-white hover:shadow-card-elevated transition-all">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
                Salary Processing
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold tracking-tight text-purple-700">
                  Ready
                </span>
                <Badge variant="neutral" className="text-[10px] px-1.5 py-0.5 bg-purple-50 text-purple-700 border-purple-200">
                  Cycle 26 Days
                </Badge>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-purple-50 text-purple-700">
              <Briefcase className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
            <span>Gross & net computation</span>
            <Link href="/payroll" className="text-purple-600 hover:underline flex items-center gap-0.5">
              Payroll &rarr;
            </Link>
          </div>
        </Card>
      </div>

      {/* Pending Employee Leave Approvals Queue */}
      <div className={`rounded-2xl p-5 shadow-sm relative overflow-hidden transition-all ${
        pendingLeavesList.length > 0
          ? 'bg-amber-50/40 border-2 border-amber-300'
          : 'bg-white border border-[#E2E8F0]'
      }`}>
        <div className={`absolute top-0 left-0 bottom-0 w-2 ${
          pendingLeavesList.length > 0 ? 'bg-amber-500' : 'bg-slate-300'
        }`} />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-200/80 pl-2">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl ${
              pendingLeavesList.length > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
            }`}>
              <Calendar className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">
                  Employee Leave Applications &amp; Approvals Queue
                </h3>
                {pendingLeavesList.length > 0 ? (
                  <Badge variant="warning" className="text-xs px-2 py-0.5 font-bold animate-pulse">
                    {pendingLeavesList.length} Action Required
                  </Badge>
                ) : (
                  <Badge variant="success" className="text-xs px-2 py-0.5 font-medium">
                    All Clear (0 Pending)
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time queue of staff leave requests submitted from the Employee Self-Service portal.
              </p>
            </div>
          </div>
          <Link href="/attendance?tab=leaves">
            <Button variant="outline" size="sm" className="text-xs flex items-center gap-1 bg-white hover:bg-slate-50">
              Open Full Leaves Register
              <ArrowRight className="w-3 h-3 ml-0.5" />
            </Button>
          </Link>
        </div>

        {pendingLeavesList.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500 pl-2">
            No pending leave applications. When an employee requests leave, it will appear here immediately for HR approval.
          </div>
        ) : (
          <div className="space-y-3 pl-2">
            {pendingLeavesList.map((leave) => (
              <div
                key={leave.id}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl border border-amber-200/90 bg-white hover:border-amber-400 transition-all shadow-xs"
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-amber-100 border border-amber-200 flex items-center justify-center font-bold text-amber-800 text-xs shrink-0 mt-0.5">
                    {leave.employee_name?.slice(0, 2).toUpperCase() || 'EM'}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm text-slate-900">{leave.employee_name}</span>
                      <span className="text-xs font-mono font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                        {leave.employee_code}
                      </span>
                      <Badge variant="neutral" className="text-[11px]">
                        {leave.department || 'Operations'}
                      </Badge>
                      <span className="text-xs font-semibold text-amber-800 bg-amber-100/70 px-2 py-0.5 rounded border border-amber-200">
                        {leave.leave_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-bold text-slate-700 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                        {leave.days_count} {leave.days_count === 1 ? 'Day' : 'Days'}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-600 mt-2 flex-wrap">
                      <span className="flex items-center gap-1.5 font-medium text-slate-800 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {leave.start_date} &rarr; {leave.end_date}
                      </span>
                      {leave.application_number && (
                        <span className="text-slate-400 font-mono text-[11px]">
                          Ref: {leave.application_number}
                        </span>
                      )}
                    </div>

                    {leave.reason && (
                      <div className="text-xs text-slate-800 mt-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">
                        <span className="font-semibold text-slate-600 mr-1.5">Reason:</span>
                        &ldquo;{leave.reason}&rdquo;
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                  <Button
                    size="sm"
                    variant="primary"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-9 px-3.5 flex items-center gap-1.5 shadow-sm font-semibold"
                    disabled={actionLoadingId === leave.id}
                    onClick={() => handleReviewLeave(leave.id, 'APPROVED')}
                  >
                    <Check className="w-4 h-4" />
                    Approve Leave
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-rose-600 border-rose-300 hover:bg-rose-50 text-xs h-9 px-3.5 flex items-center gap-1.5 font-medium"
                    disabled={actionLoadingId === leave.id}
                    onClick={() => handleReviewLeave(leave.id, 'REJECTED')}
                  >
                    <X className="w-4 h-4" />
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Split Section: Today's Attendance Register + Activity Log vs Workforce Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols wide) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Today's Live Attendance Sheet */}
          <Card className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-[#EFEEE8]">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-[#0F172A]">
                    Today&apos;s Live Workforce Attendance Sheet
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
                  Real-time biometric punch logs and presence verification across corporate and plant shifts
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Link href="/attendance">
                  <Button variant="outline" size="sm" className="h-7 text-xs flex items-center gap-1 px-2.5">
                    View Register
                    <ArrowRight className="w-3 h-3 ml-0.5" />
                  </Button>
                </Link>
              </div>
            </div>

            {/* Attendance Status Bar */}
            <div className="mb-4 p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center justify-between text-xs mb-1.5 font-medium">
                <span className="text-slate-600">Attendance Distribution</span>
                <span className="text-slate-900 font-semibold">{presentToday} / {totalEmployees} present</span>
              </div>
              <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full transition-all"
                  style={{ width: `${totalEmployees > 0 ? (presentToday / totalEmployees) * 100 : 0}%` }}
                  title={`Present: ${presentToday}`}
                />
                <div
                  className="bg-amber-400 h-full transition-all"
                  style={{ width: `${totalEmployees > 0 ? (onLeaveToday / totalEmployees) * 100 : 0}%` }}
                  title={`On Leave: ${onLeaveToday}`}
                />
                <div
                  className="bg-rose-500 h-full transition-all"
                  style={{ width: `${totalEmployees > 0 ? (absentToday / totalEmployees) * 100 : 0}%` }}
                  title={`Absent: ${absentToday}`}
                />
              </div>
              <div className="flex items-center gap-4 text-[11px] text-slate-500 mt-2">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Present ({presentToday})
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  On Leave ({onLeaveToday})
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  Absent ({absentToday})
                </span>
              </div>
            </div>

            {/* Attendance List Table */}
            {isLoading ? (
              <div className="py-8 text-center text-xs text-slate-400">Loading attendance data...</div>
            ) : todayAttendance.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-xs text-slate-500">No shift attendance logged yet for today.</p>
                <Link href="/attendance">
                  <Button variant="primary" size="sm" className="mt-3 text-xs">
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Register Attendance
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-[300px] overflow-y-auto">
                {todayAttendance.map((record) => (
                  <div key={record.id} className="py-2.5 flex items-center justify-between text-xs hover:bg-slate-50 px-2 rounded-md">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-700 text-[10px]">
                        {record.employee_name.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900">{record.employee_name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {record.employee_code} &bull; {record.department}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right text-[11px] text-slate-500">
                        <div>Punch: {record.check_in || '--:--'}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{record.shift_code}</div>
                      </div>
                      <Badge
                        variant={
                          record.status === 'PRESENT'
                            ? 'success'
                            : record.status === 'ON_LEAVE'
                            ? 'warning'
                            : 'error'
                        }
                        className="text-[10px]"
                      >
                        {record.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* HR & Personnel Activity Audit Feed */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#EFEEE8]">
              <div>
                <h3 className="text-base font-bold text-[#0F172A]">
                  Human Resources & Operational Event Log
                </h3>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Chronological HR, employee onboarding, attendance, and administrative events in real-time IST
                </p>
              </div>
              <span className="text-[11px] font-mono text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                {liveClockIST || 'IST Syncing...'}
              </span>
            </div>

            {isLoading ? (
              <div className="py-6 text-center text-xs text-slate-400">Loading activity feed...</div>
            ) : !activity || activity.activities.length === 0 ? (
              <EmptyState
                title="No HR logs recorded"
                description="Events relating to employee accounts, salary structures, or attendance will appear here."
                icon={Activity}
              />
            ) : (
              <div className="divide-y divide-[#EFEEE8] max-h-[380px] overflow-y-auto">
                {activity.activities.map((act) => (
                  <div key={act.id} className="py-2.5 flex items-start justify-between gap-3 text-xs hover:bg-slate-50 px-1 rounded-md">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div className="p-1.5 rounded-lg mt-0.5 shrink-0 bg-blue-50 text-blue-700">
                        <ShieldCheck className="h-3.5 w-3.5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900 truncate">{act.description}</p>
                        <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                          <span>User: <span className="font-medium text-slate-700">{act.user_email || 'System'}</span></span>
                          <span>&bull;</span>
                          <span>Module: <span className="font-medium text-slate-700">{act.module}</span></span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="font-mono font-bold text-slate-700 text-[11px]">
                        {formatISTTime(act.timestamp, true, false)}
                      </div>
                      <div className="text-[10px] text-slate-400">{formatISTDate(act.timestamp)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column (1 Col wide) */}
        <div className="space-y-6">
          {/* Department Headcount Breakdown */}
          <Card
            title="Department Headcount"
            subtitle="Personnel distribution across corporate units"
          >
            <div className="space-y-3 pt-1">
              {Object.keys(deptCounts).length === 0 ? (
                <p className="text-xs text-slate-500">No departments configured yet.</p>
              ) : (
                Object.entries(deptCounts).map(([dept, count]) => {
                  const pct = totalEmployees > 0 ? Math.round((count / totalEmployees) * 100) : 0;
                  return (
                    <div key={dept} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-800">{dept}</span>
                        <span className="text-slate-500 font-mono">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="bg-[#0F172A] h-full rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })
              )}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">Total Active Staff</span>
                <span className="font-bold text-slate-900 font-mono">{totalEmployees}</span>
              </div>
            </div>
          </Card>

          {/* Plant Work Shifts Schedule */}
          <Card
            title="Active Facility Shifts"
            subtitle="Configured standard operational timings"
          >
            <div className="space-y-3 text-xs">
              <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between font-semibold text-slate-900">
                  <span>General Shift</span>
                  <Badge variant="neutral" className="text-[10px]">ALL UNITS</Badge>
                </div>
                <div className="flex items-center justify-between text-slate-500 mt-1 font-mono text-[11px]">
                  <span>09:00 - 18:00</span>
                  <span>8.0h &bull; 60m Break</span>
                </div>
              </div>

              <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between font-semibold text-slate-900">
                  <span>Shift 1 (Machining)</span>
                  <Badge variant="neutral" className="text-[10px]">Unit 1 (Machining)</Badge>
                </div>
                <div className="flex items-center justify-between text-slate-500 mt-1 font-mono text-[11px]">
                  <span>07:00 - 15:30</span>
                  <span>8.0h &bull; 30m Break</span>
                </div>
              </div>

              <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50">
                <div className="flex items-center justify-between font-semibold text-slate-900">
                  <span>Shift 2 (Assembly &amp; QC)</span>
                  <Badge variant="neutral" className="text-[10px]">Unit 2 (Assembly &amp; QC)</Badge>
                </div>
                <div className="flex items-center justify-between text-slate-500 mt-1 font-mono text-[11px]">
                  <span>15:30 - 00:00</span>
                  <span>8.0h &bull; 30m Break</span>
                </div>
              </div>
            </div>
          </Card>

          {/* Quick HR Actions Card */}
          <Card
            title="Management Actions"
            subtitle="Quick personnel transactions"
          >
            <div className="space-y-2 pt-1">
              <Link href="/master/employees">
                <Button variant="outline" className="w-full justify-start text-xs h-9">
                  <Plus className="w-3.5 h-3.5 mr-2 text-blue-600" />
                  Add New Employee Record
                </Button>
              </Link>
              <Link href="/attendance">
                <Button variant="outline" className="w-full justify-start text-xs h-9">
                  <CalendarCheck className="w-3.5 h-3.5 mr-2 text-emerald-600" />
                  Biometric Attendance &amp; Punch
                </Button>
              </Link>
              <Link href="/payroll">
                <Button variant="outline" className="w-full justify-start text-xs h-9">
                  <Briefcase className="w-3.5 h-3.5 mr-2 text-purple-600" />
                  Process Monthly Payroll
                </Button>
              </Link>
              <Link href="/reports?tab=attendance">
                <Button variant="outline" className="w-full justify-start text-xs h-9">
                  <Layers className="w-3.5 h-3.5 mr-2 text-amber-600" />
                  Export Attendance Reports
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
