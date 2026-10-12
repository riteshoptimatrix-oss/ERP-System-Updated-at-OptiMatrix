'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { hrClient } from '@/services/hr-client';
import { masterClient } from '@/services/master-client';
import {
  ShiftConfig,
  ShiftConfigCreate,
  ShiftType,
  HRAttendanceSummary,
} from '@/types/hr';
import { Employee } from '@/types/master';
import {
  Users,
  Clock,
  Briefcase,
  Building,
  Plus,
  Search,
  CheckCircle2,
  Calendar,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function HRPage() {
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
        router.replace('/employee/profile');
      } else {
        router.replace('/unauthorized');
      }
    }
  }, [user, isHRUser, router]);

  const canCreate = hasPermission('hr', 'create');

  // Summary Metrics
  const [summary, setSummary] = useState<HRAttendanceSummary | null>(null);

  // Shifts state
  const [shifts, setShifts] = useState<ShiftConfig[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [searchEmployee, setSearchEmployee] = useState('');
  const [deptFilter, setDeptFilter] = useState('');

  // Shift Modal
  const [isShiftModalOpen, setIsShiftModalOpen] = useState(false);
  const [shiftForm, setShiftForm] = useState<ShiftConfigCreate>({
    shift_code: '',
    name: '',
    shift_type: 'GENERAL',
    start_time: '09:00',
    end_time: '18:00',
    break_duration_minutes: 60,
    grace_period_minutes: 15,
    standard_work_hours: 8.0,
    unit_id: 'BOTH',
    is_active: true,
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch summary & shifts
  const fetchData = useCallback(async () => {
    try {
      const sum = await hrClient.getSummary(activeUnit);
      setSummary(sum);
      const shiftList = await hrClient.listShifts(activeUnit);
      setShifts(shiftList);
      const empRes = await masterClient.list<Employee>('employees', { page_size: 100 });
      setEmployees(empRes.items || []);
    } catch {
      // ignore
    }
  }, [activeUnit]);

  useEffect(() => {
    if (!isHRUser) return;
    fetchData();
  }, [isHRUser, fetchData]);

  // Create Shift handler
  const handleCreateShift = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!shiftForm.shift_code || !shiftForm.name) {
      setFormError('Shift code and name are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      await hrClient.createShift(shiftForm);
      setIsShiftModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create shift');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filtered employees
  const filteredEmployees = employees.filter((emp) => {
    const matchesSearch =
      !searchEmployee ||
      emp.full_name.toLowerCase().includes(searchEmployee.toLowerCase()) ||
      emp.code.toLowerCase().includes(searchEmployee.toLowerCase());
    const matchesDept = !deptFilter || emp.department === deptFilter;
    return matchesSearch && matchesDept;
  });

  const departments = Array.from(new Set(employees.map((e) => e.department).filter(Boolean)));

  const employeeColumns: Column<Employee>[] = [
    {
      key: 'code',
      header: 'Employee Code',
      render: (row) => <span className="font-mono font-semibold text-slate-900">{row.code}</span>,
    },
    {
      key: 'name',
      header: 'Full Name & Designation',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-900">{row.full_name}</div>
          <div className="text-xs text-slate-500">{row.designation || 'Staff'}</div>
        </div>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (row) => <span className="text-sm text-slate-700">{row.department || 'Operations'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge variant={row.is_active ? 'success' : 'neutral'}>
          {row.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
  ];

  const shiftColumns: Column<ShiftConfig>[] = [
    {
      key: 'shift_code',
      header: 'Shift Code',
      render: (row) => <span className="font-mono font-semibold text-slate-900">{row.shift_code}</span>,
    },
    {
      key: 'name',
      header: 'Shift Name & Type',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-900">{row.name}</div>
          <div className="text-xs text-slate-500">{row.shift_type}</div>
        </div>
      ),
    },
    {
      key: 'timing',
      header: 'Hours & Timing',
      render: (row) => (
        <div className="text-sm">
          <div className="font-mono text-slate-800">{row.start_time} - {row.end_time}</div>
          <div className="text-xs text-slate-500">
            {row.standard_work_hours}h work • {row.break_duration_minutes}m break
          </div>
        </div>
      ),
    },
    {
      key: 'unit_id',
      header: 'Facility Unit',
      render: (row) => (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border">
          {row.unit_id === 'Unit_1'
            ? 'Unit 1 (Machining)'
            : row.unit_id === 'Unit_2'
              ? 'Unit 2 (Assembly & QC)'
              : 'All Units'}
        </span>
      ),
    },
  ];

  if (user && !isHRUser) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">
            Human Resources & Staff
          </h1>
          <p className="text-sm text-slate-600">
            Workforce directory, plant shift scheduling, department allocations, and facility assignments.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/master/employees">
            <Button variant="outline">
              <Users className="w-4 h-4 mr-1.5" />
              Employee Directory
            </Button>
          </Link>
          <Link href="/attendance">
            <Button variant="outline">
              <Calendar className="w-4 h-4 mr-1.5" />
              Attendance &amp; Punch Logs
            </Button>
          </Link>
          <Link href="/attendance?tab=leaves">
            <Button
              variant="outline"
              className={summary?.pending_leave_requests ? 'border-amber-400 text-amber-900 bg-amber-50/70 font-medium' : ''}
            >
              <Clock className="w-4 h-4 mr-1.5 text-amber-600" />
              Leave Applications {Boolean(summary?.pending_leave_requests) && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-xs bg-amber-200 text-amber-900 font-bold">
                  {summary?.pending_leave_requests}
                </span>
              )}
            </Button>
          </Link>
          <Link href="/payroll">
            <Button variant="outline">
              <Briefcase className="w-4 h-4 mr-1.5" />
              Payroll Management
            </Button>
          </Link>
          {canCreate && (
            <Button variant="primary" onClick={() => setIsShiftModalOpen(true)}>
              <Plus className="w-4 h-4 mr-1.5" />
              Configure Shift
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Active Staff</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {summary?.total_active_employees ?? employees.length}
              </p>
            </div>
            <Users className="w-8 h-8 text-blue-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Present On Floor</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {summary?.present_today ?? '--'}
              </p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-emerald-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-purple-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Configured Shifts</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{shifts.length}</p>
            </div>
            <Clock className="w-8 h-8 text-purple-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Departments</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{departments.length}</p>
            </div>
            <Building className="w-8 h-8 text-amber-500 opacity-80" />
          </div>
        </Card>
      </div>

      {/* Facility Shifts */}
      <Card className="p-4 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold text-slate-900">Plant Shift Timings</h2>
            <p className="text-xs text-slate-500">Configured shift schedules for manufacturing & office operations</p>
          </div>
        </div>

        <DataTable
          columns={shiftColumns}
          data={shifts}
          keyExtractor={(row) => row.id}
          emptyDescription="No facility shifts configured yet."
        />
      </Card>

      {/* Employee Directory */}
      <Card className="p-4 space-y-4">
        <div className="flex flex-wrap gap-3 items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Employee Master Directory</h2>
            <p className="text-xs text-slate-500">Active workforce with department and facility mapping</p>
          </div>

          <div className="flex gap-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Search staff by name or code..."
                className="pl-8 pr-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                value={searchEmployee}
                onChange={(e) => setSearchEmployee(e.target.value)}
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            </div>

            <select
              className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        <DataTable
          columns={employeeColumns}
          data={filteredEmployees}
          keyExtractor={(row) => row.id}
          emptyDescription="No employees found matching the selected filter."
        />
      </Card>

      {/* Dialog: Create Shift */}
      <Dialog
        isOpen={isShiftModalOpen}
        onClose={() => setIsShiftModalOpen(false)}
        title="Configure Plant Shift"
      >
        <form onSubmit={handleCreateShift} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Shift Code *
              </label>
              <input
                type="text"
                placeholder="e.g. SHIFT-MORN-01"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.shift_code}
                onChange={(e) => setShiftForm({ ...shiftForm, shift_code: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Shift Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Morning Shift"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.name}
                onChange={(e) => setShiftForm({ ...shiftForm, name: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Shift Type
              </label>
              <select
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.shift_type}
                onChange={(e) => setShiftForm({ ...shiftForm, shift_type: e.target.value as ShiftType })}
              >
                <option value="GENERAL">General Office</option>
                <option value="SHIFT_1">Shift 1 (Morning)</option>
                <option value="SHIFT_2">Shift 2 (Evening)</option>
                <option value="NIGHT">Night Shift</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Facility Unit
              </label>
              <select
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.unit_id}
                onChange={(e) => setShiftForm({ ...shiftForm, unit_id: e.target.value })}
              >
                <option value="BOTH">Both Facilities (Unit 1 &amp; Unit 2)</option>
                <option value="Unit_1">Unit 1 — Heavy Machining</option>
                <option value="Unit_2">Unit 2 — Assembly &amp; QC</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Start Time (HH:MM) *
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.start_time}
                onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                End Time (HH:MM) *
              </label>
              <input
                type="time"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.end_time}
                onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Standard Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.standard_work_hours}
                onChange={(e) => setShiftForm({ ...shiftForm, standard_work_hours: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Break (Mins)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.break_duration_minutes}
                onChange={(e) => setShiftForm({ ...shiftForm, break_duration_minutes: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Grace (Mins)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={shiftForm.grace_period_minutes}
                onChange={(e) => setShiftForm({ ...shiftForm, grace_period_minutes: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsShiftModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Shift'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
