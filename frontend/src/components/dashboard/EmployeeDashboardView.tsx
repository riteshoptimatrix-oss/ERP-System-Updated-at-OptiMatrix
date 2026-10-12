'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { employeeClient } from '@/services/employee-client';
import {
  EmployeeDashboardResponse,
  LeaveBalanceItem,
  EmployeeTask,
  NotificationItem,
} from '@/types/employee';
import {
  Clock,
  CalendarCheck,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Bell,
  ArrowRight,
  Send,
  Building2,
  FileText,
  IndianRupee,
  ShieldCheck,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { formatISTTime } from '@/lib/date';

export const EmployeeDashboardView: React.FC = () => {
  const [data, setData] = useState<EmployeeDashboardResponse | null>(null);
  const [tasks, setTasks] = useState<EmployeeTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [liveClockIST, setLiveClockIST] = useState<string>('');

  // Modals
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [leaveForm, setLeaveForm] = useState({
    leave_type: 'CASUAL_LEAVE',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    days_count: 1,
    reason: '',
  });

  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
  const [correctionForm, setCorrectionForm] = useState({
    date: new Date().toISOString().split('T')[0],
    requested_check_in: '09:00',
    requested_check_out: '18:00',
    requested_status: 'PRESENT',
    reason: '',
  });

  // Live ticking IST Clock
  useEffect(() => {
    const update = () => setLiveClockIST(formatISTTime(new Date(), true, true));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setIsLoading(true);
      const [dashRes, taskRes] = await Promise.all([
        employeeClient.getDashboard(),
        employeeClient.listTasks('PENDING').catch(() => [] as EmployeeTask[]),
      ]);
      setData(dashRes);
      setTasks(taskRes);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to load employee dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Handle Check-In
  const handleCheckIn = async () => {
    try {
      setIsSubmitting(true);
      setActionError(null);
      await employeeClient.checkIn({ remarks: 'Manual web dashboard check-in' });
      setActionSuccess('Check-in logged successfully!');
      await loadDashboard();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Check-in failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Check-Out
  const handleCheckOut = async () => {
    try {
      setIsSubmitting(true);
      setActionError(null);
      await employeeClient.checkOut({ remarks: 'Shift completed' });
      setActionSuccess('Check-out logged successfully!');
      await loadDashboard();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Check-out failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Leave Submission
  const handleApplyLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setActionError(null);
      await employeeClient.applyLeave(leaveForm);
      setIsLeaveModalOpen(false);
      setActionSuccess('Leave application submitted for approval.');
      setLeaveForm({
        leave_type: 'CASUAL_LEAVE',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        days_count: 1,
        reason: '',
      });
      await loadDashboard();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to apply leave');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Attendance Correction Submission
  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setActionError(null);
      await employeeClient.submitAttendanceCorrection(correctionForm);
      setIsCorrectionModalOpen(false);
      setActionSuccess('Attendance correction request submitted to supervisor.');
      setCorrectionForm({
        date: new Date().toISOString().split('T')[0],
        requested_check_in: '09:00',
        requested_check_out: '18:00',
        requested_status: 'PRESENT',
        reason: '',
      });
      await loadDashboard();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to submit correction');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <RefreshCw className="h-8 w-8 text-[#0F172A] animate-spin" />
        <p className="text-sm font-medium text-[#64748B]">Loading your employee workspace...</p>
      </div>
    );
  }

  const todayAtt = data?.today_attendance;
  const currentShift = data?.current_shift;

  return (
    <div className="space-y-6">
      {/* Alert Messages */}
      {actionError && (
        <div className="flex items-center justify-between p-4 bg-[#FEF2F2] border border-[#FCA5A5] rounded-xl text-[#991B1B] text-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-[#991B1B] font-bold text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="flex items-center justify-between p-4 bg-[#F0FDF4] border border-[#86EFAC] rounded-xl text-[#166534] text-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-[#166534] font-bold text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Top Banner: Employee Workspace Command Bar */}
      <div className="bg-[#FFFFFF] p-6 sm:p-7 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />

        <div className="space-y-1.5 pl-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A] font-mono">
              Employee Self-Service Workspace
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A] border-[#CBD5E1]">
              {data?.employee_code}
            </Badge>
            <Badge variant="success" className="bg-[#DCFCE7] text-[#166534] border-[#86EFAC]">
              {data?.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : data?.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
            </Badge>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Welcome back, {data?.full_name}
          </h2>
          <p className="text-xs text-[#64748B] max-w-xl">
            {data?.designation} • {data?.department} • Assigned Roles: {data?.job_roles.join(', ') || 'Staff'}
          </p>
        </div>

        {/* Live IST Clock & Shift Status Pill */}
        <div className="flex flex-col items-end gap-1.5 self-stretch md:self-auto bg-[#F8FAFC] border border-[#E2E8F0] px-4 py-3 rounded-xl">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#0F172A]">
            <Clock className="h-4 w-4 text-[#0F172A]" />
            <span className="font-mono text-sm tracking-wider">{liveClockIST || 'Loading IST...'}</span>
          </div>
          <div className="text-[11px] text-[#64748B]">
            Shift: <span className="font-semibold text-[#0F172A]">{currentShift?.name} ({currentShift?.start_time} - {currentShift?.end_time})</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Attendance & Shift Widget + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Today's Shift & Attendance Control (Spans 2 cols) */}
        <Card className="lg:col-span-2 p-6 space-y-5 bg-[#FFFFFF] border-[#E2E8F0] shadow-card">
          <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-[#F1F5F9] rounded-lg text-[#0F172A]">
                <CalendarCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#0F172A]">Today&apos;s Attendance & Shift Log</h3>
                <p className="text-xs text-[#64748B]">{new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
              </div>
            </div>

            {todayAtt?.is_checked_in ? (
              <Badge variant={todayAtt.is_checked_out ? 'neutral' : 'success'}>
                {todayAtt.is_checked_out ? 'Shift Completed' : 'Checked In'}
              </Badge>
            ) : (
              <Badge variant="warning">Not Checked In</Badge>
            )}
          </div>

          {/* Real Telemetry Numbers */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-center">
              <span className="text-[11px] font-medium text-[#64748B]">Check-In Time</span>
              <p className="text-base font-bold font-mono text-[#0F172A] mt-1">
                {todayAtt?.check_in || '—:—'}
              </p>
            </div>
            <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-center">
              <span className="text-[11px] font-medium text-[#64748B]">Check-Out Time</span>
              <p className="text-base font-bold font-mono text-[#0F172A] mt-1">
                {todayAtt?.check_out || '—:—'}
              </p>
            </div>
            <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-center">
              <span className="text-[11px] font-medium text-[#64748B]">Worked Hours</span>
              <p className="text-base font-bold font-mono text-[#0F172A] mt-1">
                {todayAtt?.hours_worked ? `${todayAtt.hours_worked} hrs` : '0.0 hrs'}
              </p>
            </div>
            <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-center">
              <span className="text-[11px] font-medium text-[#64748B]">Overtime</span>
              <p className="text-base font-bold font-mono text-[#16A34A] mt-1">
                {todayAtt?.overtime_hours ? `+${todayAtt.overtime_hours} hrs` : '0.0 hrs'}
              </p>
            </div>
          </div>

          {/* Action Buttons Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2">
              {!todayAtt?.is_checked_in ? (
                <Button
                  variant="primary"
                  onClick={handleCheckIn}
                  disabled={isSubmitting}
                  className="bg-[#0F172A] hover:bg-[#1E293B] text-white flex items-center gap-2 shadow-xs"
                >
                  <CalendarCheck className="h-4 w-4" />
                  Record Daily Check-In
                </Button>
              ) : !todayAtt.is_checked_out ? (
                <Button
                  variant="primary"
                  onClick={handleCheckOut}
                  disabled={isSubmitting}
                  className="bg-[#DC2626] hover:bg-[#B91C1C] text-white flex items-center gap-2 shadow-xs"
                >
                  <CalendarCheck className="h-4 w-4" />
                  Record Shift Check-Out
                </Button>
              ) : (
                <div className="text-xs text-[#16A34A] font-semibold flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  Attendance complete for today
                </div>
              )}

              <Button
                variant="outline"
                onClick={() => setIsCorrectionModalOpen(true)}
                className="text-xs border-[#E2E8F0] text-[#0F172A] hover:bg-[#F8FAFC]"
              >
                Request Correction
              </Button>
            </div>

            <Link href="/employee/attendance">
              <Button variant="outline" size="sm" className="text-xs text-[#0F172A] hover:text-[#0F172A] flex items-center gap-1">
                View History <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </Card>

        {/* Card 2: Quick Links & Workspace Summary */}
        <Card className="p-6 space-y-4 bg-[#FFFFFF] border-[#E2E8F0] shadow-card flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
              <h3 className="text-base font-bold text-[#0F172A]">Quick Workspace Actions</h3>
              <Badge variant="neutral" className="bg-[#F1F5F9] text-[#64748B]">Self-Service</Badge>
            </div>

            <div className="space-y-2 mt-4">
              <Link href="/employee/leave" className="block">
                <div className="p-2.5 rounded-xl border border-[#E2E8F0] hover:border-[#0F172A] hover:bg-[#F8FAFC] transition-all flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Calendar className="h-4 w-4 text-[#0F172A]" />
                    <span className="text-xs font-semibold text-[#0F172A]">Apply Leave</span>
                  </div>
                  <Badge variant="neutral" className="text-[10px] bg-[#F1F5F9]">
                    {data?.pending_leaves_count || 0} Pending
                  </Badge>
                </div>
              </Link>

              <Link href="/employee/tasks" className="block">
                <div className="p-2.5 rounded-xl border border-[#E2E8F0] hover:border-[#0F172A] hover:bg-[#F8FAFC] transition-all flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Briefcase className="h-4 w-4 text-[#0F172A]" />
                    <span className="text-xs font-semibold text-[#0F172A]">My Operational Tasks</span>
                  </div>
                  <Badge variant="neutral" className="text-[10px] bg-[#F1F5F9]">
                    {data?.pending_tasks_count || 0} Active
                  </Badge>
                </div>
              </Link>

              <Link href="/employee/payroll" className="block">
                <div className="p-2.5 rounded-xl border border-[#E2E8F0] hover:border-[#0F172A] hover:bg-[#F8FAFC] transition-all flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <IndianRupee className="h-4 w-4 text-[#0F172A]" />
                    <span className="text-xs font-semibold text-[#0F172A]">Salary & Payslips</span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-[#94A3B8]" />
                </div>
              </Link>

              <Link href="/employee/profile" className="block">
                <div className="p-2.5 rounded-xl border border-[#E2E8F0] hover:border-[#0F172A] hover:bg-[#F8FAFC] transition-all flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="h-4 w-4 text-[#0F172A]" />
                    <span className="text-xs font-semibold text-[#0F172A]">My Employee Profile</span>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-[#94A3B8]" />
                </div>
              </Link>
            </div>
          </div>

          <Button
            variant="primary"
            onClick={() => setIsLeaveModalOpen(true)}
            className="w-full bg-[#0F172A] hover:bg-[#1E293B] text-white text-xs mt-3"
          >
            + New Leave Application
          </Button>
        </Card>
      </div>

      {/* Row 2: Leave Balances Grid (4 Cards) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-[#0F172A]">Configured Leave Balances & Quotas</h3>
          <span className="text-xs text-[#64748B]">Calendar Year {new Date().getFullYear()}</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data?.leave_balances.map((item) => (
            <Card key={item.leave_type} className="p-4 bg-[#FFFFFF] border-[#E2E8F0] shadow-card space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#0F172A]">{item.name}</span>
                <Badge variant={item.remaining_balance > 0 ? 'success' : 'neutral'}>
                  {item.remaining_balance} left
                </Badge>
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <div>
                  <span className="text-2xl font-extrabold text-[#0F172A] font-mono">
                    {item.remaining_balance}
                  </span>
                  <span className="text-xs text-[#64748B] ml-1">/ {item.quota_days} days</span>
                </div>
                <div className="text-[11px] text-[#64748B]">
                  Used: <span className="font-semibold text-[#0F172A]">{item.used_days}d</span>
                </div>
              </div>
              <div className="w-full bg-[#F1F5F9] rounded-full h-1.5 mt-2 overflow-hidden">
                <div
                  className="bg-[#0F172A] h-1.5 rounded-full transition-all"
                  style={{
                    width: `${item.quota_days > 0 ? Math.min(100, Math.round((item.used_days / item.quota_days) * 100)) : 0}%`,
                  }}
                />
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Row 3: Assigned Operational Work & Company Announcements */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Operational Tasks */}
        <Card className="p-6 bg-[#FFFFFF] border-[#E2E8F0] shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
            <div className="flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-[#0F172A]" />
              <h3 className="text-base font-bold text-[#0F172A]">Assigned Operational Tasks</h3>
            </div>
            <Link href="/employee/tasks">
              <Button variant="outline" size="sm" className="text-xs text-[#0F172A] hover:text-[#0F172A]">
                View All ({tasks.length})
              </Button>
            </Link>
          </div>

          {tasks.length === 0 ? (
            <div className="text-center py-8 text-[#64748B] text-xs">
              No pending tasks assigned for your job role and facility. You&apos;re all caught up!
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.slice(0, 4).map((task) => (
                <div
                  key={task.id}
                  className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] space-y-1.5 hover:border-[#CBD5E1] transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#0F172A] truncate max-w-[260px]">
                      {task.title}
                    </span>
                    <Badge
                      variant={
                        task.priority === 'HIGH' || task.priority === 'URGENT'
                          ? 'error'
                          : task.priority === 'MEDIUM'
                            ? 'warning'
                            : 'neutral'
                      }
                      className="text-[10px]"
                    >
                      {task.priority}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#64748B] line-clamp-2">{task.description}</p>
                  <div className="flex items-center justify-between text-[11px] text-[#94A3B8] pt-1">
                    <span>Module: <strong className="text-[#0F172A] uppercase">{task.source_module}</strong></span>
                    {task.due_date && <span>Due: <strong className="text-[#0F172A]">{task.due_date}</strong></span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Corporate Announcements & System Notifications */}
        <Card className="p-6 bg-[#FFFFFF] border-[#E2E8F0] shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-[#0F172A]" />
              <h3 className="text-base font-bold text-[#0F172A]">Announcements & Notifications</h3>
            </div>
            <Link href="/employee/notifications">
              <Button variant="outline" size="sm" className="text-xs text-[#0F172A] hover:text-[#0F172A]">
                View All
              </Button>
            </Link>
          </div>

          {/* Plant Broadcasts */}
          {data?.announcements && data.announcements.length > 0 && (
            <div className="space-y-2">
              {data.announcements.map((ann) => (
                <div
                  key={ann.id}
                  className="p-3.5 rounded-xl border border-[#FDE68A] bg-[#FEFCE8] text-[#854D0E] space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between font-bold">
                    <span>📢 {ann.title}</span>
                    <Badge variant="warning" className="text-[10px] bg-[#FEF08A] text-[#854D0E]">
                      {ann.priority}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-[#713F12] leading-relaxed">{ann.content}</p>
                </div>
              ))}
            </div>
          )}

          {/* Recent System Notifications */}
          <div className="space-y-2 mt-2">
            {data?.recent_notifications.length === 0 ? (
              <p className="text-xs text-[#64748B] text-center py-6">No recent notifications</p>
            ) : (
              data?.recent_notifications.map((notif) => (
                <div
                  key={notif.id}
                  className="p-2.5 rounded-lg border border-[#E2E8F0] hover:bg-[#F8FAFC] flex items-start gap-2.5 text-xs transition-all"
                >
                  <div className="h-2 w-2 rounded-full bg-[#0F172A] mt-1.5 shrink-0" />
                  <div className="flex-1 space-y-0.5">
                    <p className="font-semibold text-[#0F172A]">{notif.title}</p>
                    <p className="text-[11px] text-[#64748B]">{notif.message}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Apply Leave Modal */}
      <Dialog
        isOpen={isLeaveModalOpen}
        onClose={() => setIsLeaveModalOpen(false)}
        title="Submit Leave Application"
      >
        <form onSubmit={handleApplyLeave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Leave Type</label>
            <select
              value={leaveForm.leave_type}
              onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            >
              <option value="CASUAL_LEAVE">Casual Leave (CL)</option>
              <option value="SICK_LEAVE">Sick Leave (SL)</option>
              <option value="EARNED_LEAVE">Earned Leave (EL)</option>
              <option value="UNPAID_LEAVE">Unpaid Leave (LOP)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Start Date</label>
              <input
                type="date"
                required
                value={leaveForm.start_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">End Date</label>
              <input
                type="date"
                required
                value={leaveForm.end_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Total Days Count</label>
            <input
              type="number"
              min="0.5"
              step="0.5"
              required
              value={leaveForm.days_count}
              onChange={(e) => setLeaveForm({ ...leaveForm, days_count: parseFloat(e.target.value) || 1 })}
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Reason for Leave</label>
            <textarea
              required
              rows={3}
              value={leaveForm.reason}
              onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
              placeholder="State reason clearly for HR & supervisor approval..."
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[#F1F5F9]">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsLeaveModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="bg-[#0F172A] text-white text-xs"
            >
              Submit Application
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Attendance Correction Modal */}
      <Dialog
        isOpen={isCorrectionModalOpen}
        onClose={() => setIsCorrectionModalOpen(false)}
        title="Submit Attendance Correction Request"
      >
        <form onSubmit={handleCorrectionSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Date of Attendance</label>
            <input
              type="date"
              required
              value={correctionForm.date}
              onChange={(e) => setCorrectionForm({ ...correctionForm, date: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Requested Check-In</label>
              <input
                type="time"
                value={correctionForm.requested_check_in}
                onChange={(e) => setCorrectionForm({ ...correctionForm, requested_check_in: e.target.value })}
                className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Requested Check-Out</label>
              <input
                type="time"
                value={correctionForm.requested_check_out}
                onChange={(e) => setCorrectionForm({ ...correctionForm, requested_check_out: e.target.value })}
                className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Requested Status</label>
            <select
              value={correctionForm.requested_status}
              onChange={(e) => setCorrectionForm({ ...correctionForm, requested_status: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            >
              <option value="PRESENT">Present</option>
              <option value="HALF_DAY">Half Day</option>
              <option value="ON_LEAVE">On Leave</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">Reason for Correction</label>
            <textarea
              required
              rows={3}
              value={correctionForm.reason}
              onChange={(e) => setCorrectionForm({ ...correctionForm, reason: e.target.value })}
              placeholder="Explain why timing was missed (turnstile failure, offsite duty, biometric glitch)..."
              className="w-full px-3 py-2 text-xs border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#0F172A] bg-white text-[#0F172A]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[#F1F5F9]">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCorrectionModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="bg-[#0F172A] text-white text-xs"
            >
              Submit Request
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
};
