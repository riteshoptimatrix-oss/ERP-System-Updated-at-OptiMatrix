'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { employeeClient } from '@/services/employee-client';
import { LeaveApplication } from '@/types/hr';
import { EmployeeDashboardResponse } from '@/types/employee';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Calendar,
  Send,
  Plus,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { formatISTDate } from '@/lib/date';

export default function EmployeeLeavePage() {
  const [leaves, setLeaves] = useState<LeaveApplication[]>([]);
  const [dashboardData, setDashboardData] = useState<EmployeeDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isApplying, setIsApplying] = useState<boolean>(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const [errorMessage, setErrorMessage] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [showApplyModal, setShowApplyModal] = useState<boolean>(false);

  // Form state
  const [leaveType, setLeaveType] = useState<string>('CASUAL_LEAVE');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [daysCount, setDaysCount] = useState<number>(1);
  const [reason, setReason] = useState<string>('');

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const [leavesRes, dashRes] = await Promise.all([
        employeeClient.listLeaves(undefined, 1, 50),
        employeeClient.getDashboard(),
      ]);
      setLeaves(leavesRes.items || []);
      setDashboardData(dashRes);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to fetch leave history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDateChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
    if (start && end) {
      const d1 = new Date(start);
      const d2 = new Date(end);
      const diffTime = d2.getTime() - d1.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
      setDaysCount(diffDays > 0 ? diffDays : 1);
    }
  };

  const handleApplyLeave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!startDate || !endDate || !reason.trim() || daysCount <= 0) {
      setErrorMessage('Please fill in valid leave dates and an explanatory reason.');
      return;
    }

    setIsApplying(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      await employeeClient.applyLeave({
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        days_count: Number(daysCount),
        reason: reason.trim(),
      });
      setSuccessMessage('Leave application submitted for approval.');
      setShowApplyModal(false);
      setStartDate('');
      setEndDate('');
      setReason('');
      setDaysCount(1);
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Leave application failed');
    } finally {
      setIsApplying(false);
    }
  };

  const handleCancelLeave = async (leaveId: string) => {
    if (!confirm('Are you sure you want to cancel this pending leave request?')) {
      return;
    }

    setCancellingId(leaveId);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      await employeeClient.cancelLeave(leaveId);
      setSuccessMessage('Leave application cancelled successfully.');
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to cancel leave application');
    } finally {
      setCancellingId(null);
    }
  };

  const balances = dashboardData?.leave_balances || [];
  const casualBal = balances.find((b) => b.leave_type.includes('CASUAL'));
  const sickBal = balances.find((b) => b.leave_type.includes('SICK'));
  const earnedBal = balances.find((b) => b.leave_type.includes('EARNED'));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] p-6 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
              Time Off & Attendance Quotas
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Leave Management & Entitlements
          </h1>
          <p className="text-xs text-[#64748B]">
            Annual leave entitlements, statutory sick leaves, application tracking, and cancellation controls.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={isLoading}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setShowApplyModal(true)}
            className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" />
            Apply for Leave
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Quota Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Casual Leave */}
        <Card className="p-5">
          <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
            <span className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Casual Leave (CL)
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A]">
              Annual
            </Badge>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div>
              <span className="text-3xl font-mono font-bold text-[#0F172A]">
                {casualBal?.remaining_balance ?? 12}
              </span>
              <span className="text-xs text-[#64748B] ml-1">days left</span>
            </div>
            <div className="text-right text-xs text-[#64748B]">
              <span className="block">Used: <span className="font-semibold text-[#0F172A]">{casualBal?.used_days ?? 0}</span></span>
              <span className="block">Quota: <span className="font-semibold text-[#0F172A]">{casualBal?.quota_days ?? 12}</span></span>
            </div>
          </div>
        </Card>

        {/* Sick Leave */}
        <Card className="p-5">
          <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
            <span className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Sick Leave (SL)
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A]">
              Medical
            </Badge>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div>
              <span className="text-3xl font-mono font-bold text-[#0F172A]">
                {sickBal?.remaining_balance ?? 10}
              </span>
              <span className="text-xs text-[#64748B] ml-1">days left</span>
            </div>
            <div className="text-right text-xs text-[#64748B]">
              <span className="block">Used: <span className="font-semibold text-[#0F172A]">{sickBal?.used_days ?? 0}</span></span>
              <span className="block">Quota: <span className="font-semibold text-[#0F172A]">{sickBal?.quota_days ?? 10}</span></span>
            </div>
          </div>
        </Card>

        {/* Earned Leave */}
        <Card className="p-5">
          <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
            <span className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Earned Leave (EL)
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A]">
              Privilege
            </Badge>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <div>
              <span className="text-3xl font-mono font-bold text-[#0F172A]">
                {earnedBal?.remaining_balance ?? 15}
              </span>
              <span className="text-xs text-[#64748B] ml-1">days left</span>
            </div>
            <div className="text-right text-xs text-[#64748B]">
              <span className="block">Used: <span className="font-semibold text-[#0F172A]">{earnedBal?.used_days ?? 0}</span></span>
              <span className="block">Quota: <span className="font-semibold text-[#0F172A]">{earnedBal?.quota_days ?? 15}</span></span>
            </div>
          </div>
        </Card>
      </div>

      {/* Applications Table */}
      <Card title="My Leave History & Active Requests">
        {leaves.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#64748B]">
            No leave requests submitted yet. Click &quot;Apply for Leave&quot; above to request time off.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0]">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Leave Type</th>
                  <th className="py-2.5 px-3 font-semibold">Start Date</th>
                  <th className="py-2.5 px-3 font-semibold">End Date</th>
                  <th className="py-2.5 px-3 font-semibold">Days</th>
                  <th className="py-2.5 px-3 font-semibold">Reason</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {leaves.map((leave) => (
                  <tr key={leave.id} className="hover:bg-[#F8FAFC]/80">
                    <td className="py-2.5 px-3 font-semibold text-[#0F172A]">
                      {leave.leave_type}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {formatISTDate(leave.start_date)}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {formatISTDate(leave.end_date)}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-[#0F172A]">
                      {leave.days_count} {leave.days_count === 1 ? 'day' : 'days'}
                    </td>
                    <td className="py-2.5 px-3 text-[#64748B] max-w-xs truncate">
                      {leave.reason}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge
                        variant={
                          leave.status === 'APPROVED' ? 'success' :
                          leave.status === 'REJECTED' ? 'error' :
                          leave.status === 'CANCELLED' ? 'neutral' : 'warning'
                        }
                        className="text-[10px]"
                      >
                        {leave.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {leave.status === 'PENDING' ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelLeave(leave.id)}
                          disabled={cancellingId === leave.id}
                          className="h-6 text-[10px] text-rose-700 hover:text-rose-800 border-rose-200 hover:bg-rose-50"
                        >
                          {cancellingId === leave.id ? 'Cancelling...' : 'Cancel'}
                        </Button>
                      ) : (
                        <span className="text-[#94A3B8] text-[11px]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Apply Leave Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#FFFFFF] rounded-2xl shadow-xl border border-[#E2E8F0] max-w-lg w-full p-6 animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-[#0F172A]" />
                <h3 className="text-base font-bold text-[#0F172A]">
                  Apply for Leave
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowApplyModal(false)}
                className="text-xs text-[#64748B] hover:text-[#0F172A] px-2 py-1 rounded"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleApplyLeave} className="space-y-4 mt-4 text-xs">
              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Leave Type
                </label>
                <select
                  value={leaveType}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLeaveType(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                >
                  <option value="CASUAL_LEAVE">Casual Leave (CL) - Remaining: {casualBal?.remaining_balance ?? 12}</option>
                  <option value="SICK_LEAVE">Sick Leave (SL) - Remaining: {sickBal?.remaining_balance ?? 10}</option>
                  <option value="EARNED_LEAVE">Earned Leave (EL) - Remaining: {earnedBal?.remaining_balance ?? 15}</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-[#0F172A] mb-1">
                    Start Date
                  </label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleDateChange(e.target.value, endDate)}
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-[#0F172A] mb-1">
                    End Date
                  </label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleDateChange(startDate, e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Calculated Working Days
                </label>
                <Input
                  type="number"
                  min="1"
                  value={daysCount}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDaysCount(Number(e.target.value))}
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Reason for Absence
                </label>
                <textarea
                  value={reason}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReason(e.target.value)}
                  rows={3}
                  placeholder="State the purpose of leave and handover plan..."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowApplyModal(false)}
                  disabled={isApplying}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isApplying}
                  className="bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  {isApplying ? 'Submitting...' : 'Submit Application'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
