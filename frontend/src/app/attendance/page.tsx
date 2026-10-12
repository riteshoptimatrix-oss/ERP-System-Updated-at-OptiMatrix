'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { hrClient } from '@/services/hr-client';
import { masterClient } from '@/services/master-client';
import {
  AttendanceEntry,
  AttendanceStatus,
  AttendanceEntryCreate,
  AttendanceCorrectionRequest,
  LeaveApplication,
  LeaveType,
  LeaveApplicationCreate,
  LeaveApprovalRequest,
  HRAttendanceSummary,
  ShiftConfig,
} from '@/types/hr';
import { Employee } from '@/types/master';
import {
  Users,
  CheckCircle,
  AlertCircle,
  Clock,
  Calendar,
  FileText,
  Plus,
  Edit2,
  Check,
  X,
  Search,
} from 'lucide-react';

const STATUS_VARIANTS: Record<AttendanceStatus, 'success' | 'warning' | 'error' | 'neutral'> = {
  PRESENT: 'success',
  HALF_DAY: 'warning',
  ABSENT: 'error',
  ON_LEAVE: 'neutral',
  HOLIDAY: 'neutral',
};

const LEAVE_STATUS_VARIANTS: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  PENDING: 'warning',
  APPROVED: 'success',
  REJECTED: 'error',
  CANCELLED: 'neutral',
};

export default function AttendancePage() {
  const { user, activeUnit, hasPermission } = useAuth();
  const router = useRouter();

  const isHRUser = Boolean(
    user && (
      user.role === 'HR' ||
      user.account_type === 'HR' ||
      user.role === 'ADMIN' ||
      user.role === 'SUPER_ADMIN' ||
      user.department?.toUpperCase() === 'HR' ||
      user.department?.toLowerCase() === 'human resources' ||
      hasPermission('hr', 'read')
    )
  );

  useEffect(() => {
    if (user && !isHRUser) {
      if (user.role === 'EMPLOYEE' || user.account_type === 'EMPLOYEE') {
        router.replace('/employee/attendance');
      } else {
        router.replace('/unauthorized');
      }
    }
  }, [user, isHRUser, router]);

  const canCreate = hasPermission('attendance', 'create');
  const canUpdate = hasPermission('attendance', 'update');
  const canApprove = hasPermission('attendance', 'approve');

  // Active Tab
  const [activeTab, setActiveTab] = useState<'attendance' | 'leaves'>('attendance');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('tab') === 'leaves') {
        setActiveTab('leaves');
      }
    }
  }, []);

  // KPI Metrics
  const [metrics, setMetrics] = useState<HRAttendanceSummary | null>(null);

  // Attendance State
  const [attendanceList, setAttendanceList] = useState<AttendanceEntry[]>([]);
  const [totalAttendance, setTotalAttendance] = useState(0);
  const [page, setPage] = useState(1);
  const [filterDate, setFilterDate] = useState(new Date().toISOString().split('T')[0]);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [searchEmp, setSearchEmp] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Leaves State
  const [leavesList, setLeavesList] = useState<LeaveApplication[]>([]);
  const [totalLeaves, setTotalLeaves] = useState(0);
  const [leavesPage, setLeavesPage] = useState(1);
  const [leaveStatusFilter, setLeaveStatusFilter] = useState('');

  // Dropdown reference data
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [shifts, setShifts] = useState<ShiftConfig[]>([]);

  // Dialogs
  const [isRecordOpen, setIsRecordOpen] = useState(false);
  const [isCorrectOpen, setIsCorrectOpen] = useState(false);
  const [isLeaveOpen, setIsLeaveOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<AttendanceEntry | null>(null);
  const [selectedLeave, setSelectedLeave] = useState<LeaveApplication | null>(null);

  // Form states
  const [attForm, setAttForm] = useState<Partial<AttendanceEntryCreate>>({
    date: new Date().toISOString().split('T')[0],
    status: 'PRESENT',
    hours_worked: 8.0,
    overtime_hours: 0.0,
    check_in: '09:00',
    check_out: '18:00',
  });

  const [correctForm, setCorrectForm] = useState<AttendanceCorrectionRequest>({
    hours_worked: 8.0,
    overtime_hours: 0.0,
    check_in: '09:00',
    check_out: '18:00',
    correction_reason: '',
  });

  const [leaveForm, setLeaveForm] = useState<Partial<LeaveApplicationCreate>>({
    leave_type: 'CASUAL_LEAVE',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    days_count: 1.0,
    reason: '',
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load KPI metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const summary = await hrClient.getSummary(activeUnit);
      setMetrics(summary);
    } catch {
      // ignore
    }
  }, [activeUnit]);

  // Load Reference Masters
  const fetchMasters = useCallback(async () => {
    try {
      const empRes = await masterClient.list<Employee>('employees', { page_size: 100 });
      setEmployees(empRes.items || []);
      const shiftRes = await hrClient.listShifts(activeUnit);
      setShifts(shiftRes || []);
    } catch {
      // ignore
    }
  }, [activeUnit]);

  // Load Attendance Records
  const fetchAttendance = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await hrClient.listAttendance({
        date: filterDate || undefined,
        employee_id: searchEmp || undefined,
        unit_id: activeUnit !== 'BOTH' ? activeUnit : undefined,
        status: filterStatus || undefined,
        page,
        page_size: 20,
      });
      setAttendanceList(res.items);
      setTotalAttendance(res.total);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [activeUnit, filterDate, searchEmp, filterStatus, page]);

  // Load Leaves
  const fetchLeaves = useCallback(async () => {
    try {
      const res = await hrClient.listLeaves({
        unit_id: activeUnit !== 'BOTH' ? activeUnit : undefined,
        status: leaveStatusFilter || undefined,
        page: leavesPage,
        page_size: 20,
      });
      setLeavesList(res.items);
      setTotalLeaves(res.total);
    } catch {
      // ignore
    }
  }, [activeUnit, leaveStatusFilter, leavesPage]);

  useEffect(() => {
    if (!isHRUser) return;
    fetchMetrics();
    fetchMasters();
  }, [isHRUser, fetchMetrics, fetchMasters]);

  useEffect(() => {
    if (!isHRUser) return;
    if (activeTab === 'attendance') {
      fetchAttendance();
    } else {
      fetchLeaves();
    }
  }, [isHRUser, activeTab, fetchAttendance, fetchLeaves]);

  // Handle Record Attendance Submit
  const handleRecordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!attForm.employee_id) {
      setFormError('Please select an employee.');
      return;
    }
    const emp = employees.find((x) => x.id === attForm.employee_id || x.code === attForm.employee_id);

    setIsSubmitting(true);
    try {
      await hrClient.recordAttendance({
        employee_id: attForm.employee_id,
        employee_code: emp?.code || attForm.employee_id,
        date: attForm.date || new Date().toISOString().split('T')[0],
        unit_id: (activeUnit !== 'BOTH' ? activeUnit : emp?.unit_id || 'Unit_1') as string,
        shift_code: attForm.shift_code || 'SHIFT-GEN',
        check_in: attForm.check_in,
        check_out: attForm.check_out,
        status: (attForm.status || 'PRESENT') as AttendanceStatus,
        hours_worked: Number(attForm.hours_worked || 8.0),
        overtime_hours: Number(attForm.overtime_hours || 0.0),
        remarks: attForm.remarks,
      });
      setIsRecordOpen(false);
      fetchAttendance();
      fetchMetrics();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to record attendance');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Correction Submit
  const handleCorrectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    setFormError(null);
    if (!correctForm.correction_reason.trim()) {
      setFormError('Reason for supervisor correction is mandatory.');
      return;
    }

    setIsSubmitting(true);
    try {
      await hrClient.correctAttendance(selectedRecord.id, correctForm);
      setIsCorrectOpen(false);
      setSelectedRecord(null);
      fetchAttendance();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Correction failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Leave Apply
  const handleLeaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!leaveForm.employee_id) {
      setFormError('Please select an employee.');
      return;
    }
    if (!leaveForm.reason?.trim()) {
      setFormError('Please provide a reason for the leave.');
      return;
    }

    setIsSubmitting(true);
    try {
      await hrClient.applyLeave({
        employee_id: leaveForm.employee_id,
        leave_type: (leaveForm.leave_type || 'CASUAL_LEAVE') as LeaveType,
        start_date: leaveForm.start_date || new Date().toISOString().split('T')[0],
        end_date: leaveForm.end_date || new Date().toISOString().split('T')[0],
        days_count: Number(leaveForm.days_count || 1.0),
        reason: leaveForm.reason,
      });
      setIsLeaveOpen(false);
      fetchLeaves();
      fetchMetrics();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to apply leave');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Leave Review
  const handleLeaveReview = async (leaveId: string, status: 'APPROVED' | 'REJECTED') => {
    try {
      await hrClient.reviewLeave(leaveId, {
        status,
        notes: `Processed by supervisor`,
      });
      fetchLeaves();
      fetchMetrics();
    } catch {
      // ignore
    }
  };

  // Attendance Columns
  const attendanceColumns: Column<AttendanceEntry>[] = [
    {
      key: 'employee',
      header: 'Employee',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-900">{row.employee_name}</div>
          <div className="text-xs text-slate-500">{row.employee_code} • {row.department}</div>
        </div>
      ),
    },
    {
      key: 'date',
      header: 'Date & Unit',
      render: (row) => (
        <div>
          <div className="text-sm text-slate-800">{row.date}</div>
          <div className="text-xs text-slate-500">
            {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : row.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'} ({row.shift_code})
          </div>
        </div>
      ),
    },
    {
      key: 'timing',
      header: 'Check In / Out',
      render: (row) => (
        <div className="text-xs font-mono text-slate-700">
          {row.check_in || '--:--'} → {row.check_out || '--:--'}
        </div>
      ),
    },
    {
      key: 'hours',
      header: 'Hours / OT',
      render: (row) => (
        <div className="text-sm">
          <span className="font-semibold text-slate-800">{row.hours_worked}h</span>
          {row.overtime_hours > 0 && (
            <span className="ml-1.5 text-xs font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
              +{row.overtime_hours}h OT
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex flex-col gap-1 items-start">
          <Badge variant={STATUS_VARIANTS[row.status] || 'neutral'}>
            {row.status.replace('_', ' ')}
          </Badge>
          {row.is_corrected && (
            <span className="text-[11px] text-amber-600 italic">
              Corrected: {row.correction_reason}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div>
          {canUpdate && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSelectedRecord(row);
                setCorrectForm({
                  check_in: row.check_in || '09:00',
                  check_out: row.check_out || '18:00',
                  hours_worked: row.hours_worked,
                  overtime_hours: row.overtime_hours,
                  status: row.status,
                  correction_reason: row.correction_reason || '',
                });
                setIsCorrectOpen(true);
              }}
            >
              <Edit2 className="w-3.5 h-3.5 mr-1" />
              Correct
            </Button>
          )}
        </div>
      ),
    },
  ];

  // Leave Columns
  const leaveColumns: Column<LeaveApplication>[] = [
    {
      key: 'application_number',
      header: 'Application No',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900">{row.application_number}</div>
          <div className="text-xs text-slate-500">{row.created_at?.slice(0, 10)}</div>
        </div>
      ),
    },
    {
      key: 'employee',
      header: 'Employee',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-900">{row.employee_name}</div>
          <div className="text-xs text-slate-500">{row.employee_code} • {row.department}</div>
        </div>
      ),
    },
    {
      key: 'leave_details',
      header: 'Leave Details',
      render: (row) => (
        <div>
          <div className="text-sm font-medium text-slate-800">
            {row.leave_type.replace('_', ' ')} ({row.days_count} {row.days_count === 1 ? 'day' : 'days'})
          </div>
          <div className="text-xs text-slate-500">
            {row.start_date} to {row.end_date}
          </div>
          <div className="text-xs text-slate-600 italic mt-0.5">&ldquo;{row.reason}&rdquo;</div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge variant={LEAVE_STATUS_VARIANTS[row.status] || 'neutral'}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-1.5">
          {row.status === 'PENDING' && canApprove && (
            <>
              <Button
                size="sm"
                variant="primary"
                onClick={() => handleLeaveReview(row.id, 'APPROVED')}
              >
                <Check className="w-3.5 h-3.5 mr-1" />
                Approve
              </Button>
              <Button
                size="sm"
                variant="danger"
                onClick={() => handleLeaveReview(row.id, 'REJECTED')}
              >
                <X className="w-3.5 h-3.5 mr-1" />
                Reject
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  if (user && !isHRUser) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">
            Attendance & Leaves
          </h1>
          <p className="text-sm text-slate-600">
            Plant shift tracking, daily punch logs, loss-of-pay verification, and leave requests.
          </p>
        </div>
        <div className="flex gap-2">
          {canCreate && (
            <>
              <Button variant="outline" onClick={() => setIsLeaveOpen(true)}>
                <FileText className="w-4 h-4 mr-1.5" />
                Apply Leave
              </Button>
              <Button variant="primary" onClick={() => setIsRecordOpen(true)}>
                <Plus className="w-4 h-4 mr-1.5" />
                Record Punch
              </Button>
            </>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Employees</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.total_active_employees ?? '--'}
              </p>
            </div>
            <Users className="w-8 h-8 text-blue-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Present Today</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.present_today ?? '--'}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-emerald-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-rose-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Absent Today</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.absent_today ?? '--'}
              </p>
            </div>
            <AlertCircle className="w-8 h-8 text-rose-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Month Overtime</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.total_overtime_hours_month ? `${metrics.total_overtime_hours_month}h` : '0h'}
              </p>
            </div>
            <Clock className="w-8 h-8 text-amber-500 opacity-80" />
          </div>
        </Card>

        <Card
          className={`p-4 border-l-4 border-l-purple-600 bg-white cursor-pointer hover:shadow-md transition-all ${
            activeTab === 'leaves' ? 'ring-2 ring-purple-400 bg-purple-50/20' : ''
          }`}
          onClick={() => setActiveTab('leaves')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Leaves</p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="text-2xl font-bold text-slate-900">
                  {metrics?.pending_leave_requests ?? '--'}
                </p>
                <span className="text-[11px] text-purple-600 font-medium hover:underline">View queue &rarr;</span>
              </div>
            </div>
            <Calendar className="w-8 h-8 text-purple-500 opacity-80" />
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-[#E7E5DE]">
        <button
          className={`py-2.5 px-5 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'attendance'
            ? 'border-[#315C45] text-[#315C45]'
            : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          onClick={() => setActiveTab('attendance')}
        >
          Daily Attendance Logs ({totalAttendance})
        </button>
        <button
          className={`py-2.5 px-5 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'leaves'
            ? 'border-[#315C45] text-[#315C45]'
            : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          onClick={() => setActiveTab('leaves')}
        >
          Leave Applications ({totalLeaves})
        </button>
      </div>

      {/* Tab 1: Daily Attendance */}
      {activeTab === 'attendance' && (
        <Card className="p-4 space-y-4">
          <div className="flex flex-wrap gap-3 items-center justify-between">
            <div className="flex flex-wrap gap-2 items-center">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Date</label>
                <input
                  type="date"
                  className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                  value={filterDate}
                  onChange={(e) => setFilterDate(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Status</label>
                <select
                  className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="PRESENT">Present</option>
                  <option value="HALF_DAY">Half Day</option>
                  <option value="ABSENT">Absent</option>
                  <option value="ON_LEAVE">On Leave</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Employee Search</label>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Code or Name..."
                    className="pl-8 pr-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                    value={searchEmp}
                    onChange={(e) => setSearchEmp(e.target.value)}
                  />
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilterDate(new Date().toISOString().split('T')[0]);
                setFilterStatus('');
                setSearchEmp('');
              }}
            >
              Reset Filters
            </Button>
          </div>

          <DataTable
            columns={attendanceColumns}
            data={attendanceList}
            isLoading={isLoading}
            keyExtractor={(row) => row.id}
            emptyDescription="No attendance records found for this date or criteria."
          />
        </Card>
      )}

      {/* Tab 2: Leave Applications */}
      {activeTab === 'leaves' && (
        <Card className="p-4 space-y-4">
          <div className="flex gap-2 items-center">
            <select
              className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
              value={leaveStatusFilter}
              onChange={(e) => setLeaveStatusFilter(e.target.value)}
            >
              <option value="">All Leave Statuses</option>
              <option value="PENDING">Pending Review</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <DataTable
            columns={leaveColumns}
            data={leavesList}
            keyExtractor={(row) => row.id}
            emptyDescription="No leave applications on record."
          />
        </Card>
      )}

      {/* Dialog: Record Punch */}
      <Dialog
        isOpen={isRecordOpen}
        onClose={() => setIsRecordOpen(false)}
        title="Record Daily Attendance"
      >
        <form onSubmit={handleRecordSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Employee *
            </label>
            <select
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm focus:ring-1 focus:ring-[#315C45]"
              value={attForm.employee_id || ''}
              onChange={(e) => setAttForm({ ...attForm, employee_id: e.target.value })}
              required
            >
              <option value="">Select Employee</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.code} - {emp.full_name} ({emp.department})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Date *
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.date}
                onChange={(e) => setAttForm({ ...attForm, date: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Shift
              </label>
              <select
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.shift_code}
                onChange={(e) => setAttForm({ ...attForm, shift_code: e.target.value })}
              >
                {shifts.map((s) => (
                  <option key={s.id} value={s.shift_code}>
                    {s.name} ({s.start_time}-{s.end_time})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Status *
              </label>
              <select
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.status}
                onChange={(e) => setAttForm({ ...attForm, status: e.target.value as AttendanceStatus })}
              >
                <option value="PRESENT">Present</option>
                <option value="HALF_DAY">Half Day</option>
                <option value="ABSENT">Absent</option>
                <option value="ON_LEAVE">On Leave</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Check In
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.check_in}
                onChange={(e) => setAttForm({ ...attForm, check_in: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Check Out
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.check_out}
                onChange={(e) => setAttForm({ ...attForm, check_out: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Work Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.hours_worked}
                onChange={(e) => setAttForm({ ...attForm, hours_worked: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Overtime Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={attForm.overtime_hours}
                onChange={(e) => setAttForm({ ...attForm, overtime_hours: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Remarks
            </label>
            <input
              type="text"
              placeholder="Optional notes or remarks"
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
              value={attForm.remarks || ''}
              onChange={(e) => setAttForm({ ...attForm, remarks: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsRecordOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Recording...' : 'Save Attendance'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Dialog: Supervisor Correction */}
      <Dialog
        isOpen={isCorrectOpen}
        onClose={() => setIsCorrectOpen(false)}
        title={`Correct Attendance - ${selectedRecord?.employee_name}`}
      >
        <form onSubmit={handleCorrectSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Check In
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={correctForm.check_in || ''}
                onChange={(e) => setCorrectForm({ ...correctForm, check_in: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Check Out
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={correctForm.check_out || ''}
                onChange={(e) => setCorrectForm({ ...correctForm, check_out: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Work Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={correctForm.hours_worked ?? 8.0}
                onChange={(e) => setCorrectForm({ ...correctForm, hours_worked: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Overtime Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={correctForm.overtime_hours ?? 0.0}
                onChange={(e) => setCorrectForm({ ...correctForm, overtime_hours: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Supervisor Correction Reason *
            </label>
            <textarea
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm focus:ring-1 focus:ring-[#315C45]"
              rows={3}
              placeholder="State the reason e.g. Biometric network offline, verified by plant supervisor"
              value={correctForm.correction_reason}
              onChange={(e) => setCorrectForm({ ...correctForm, correction_reason: e.target.value })}
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsCorrectOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Apply Correction'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Dialog: Apply Leave */}
      <Dialog
        isOpen={isLeaveOpen}
        onClose={() => setIsLeaveOpen(false)}
        title="Submit Leave Application"
      >
        <form onSubmit={handleLeaveSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Employee *
            </label>
            <select
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
              value={leaveForm.employee_id || ''}
              onChange={(e) => setLeaveForm({ ...leaveForm, employee_id: e.target.value })}
              required
            >
              <option value="">Select Employee</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.code} - {emp.full_name} ({emp.department})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Leave Type *
              </label>
              <select
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={leaveForm.leave_type}
                onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value as LeaveType })}
              >
                <option value="CASUAL_LEAVE">Casual Leave</option>
                <option value="SICK_LEAVE">Sick Leave</option>
                <option value="EARNED_LEAVE">Earned Leave</option>
                <option value="UNPAID_LEAVE">Unpaid Leave (LOP)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Total Days *
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={leaveForm.days_count}
                onChange={(e) => setLeaveForm({ ...leaveForm, days_count: parseFloat(e.target.value) })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Start Date *
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={leaveForm.start_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                End Date *
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={leaveForm.end_date}
                onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Reason *
            </label>
            <textarea
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
              rows={3}
              placeholder="Provide reason for absence..."
              value={leaveForm.reason}
              onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsLeaveOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit Application'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
