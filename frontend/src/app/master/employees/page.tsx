'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Employee } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/services/api-client';
import {
  ACCOUNT_TYPES,
  MANUFACTURING_DEPARTMENTS,
  DEPARTMENT_JOB_ROLES,
} from '@/lib/constants';
import {
  Plus,
  Download,
  Edit2,
  Ban,
  CheckCircle2,
  Sparkles,
  KeyRound,
  Shield,
  Briefcase,
  Eye,
  EyeOff,
  Lock,
} from 'lucide-react';

export default function EmployeesPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [autoNextCode, setAutoNextCode] = useState<string>('EMP-001');

  const [showInitialPassword, setShowInitialPassword] = useState(false);
  const [showConfirmInitialPassword, setShowConfirmInitialPassword] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    full_name: '',
    email: '',
    phone: '',
    department: 'Production Department',
    designation: 'Production Supervisor',
    account_type: 'EMPLOYEE',
    job_role: 'Production Supervisor',
    joining_date: '',
    unit_id: 'BOTH',
    status: 'ACTIVE',
    emergency_contact: '',
    create_user_account: false,
    user_password: '',
    confirm_user_password: '',
    must_change_password: true,
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<Employee>('employees', {
        page,
        page_size: pageSize,
        search: search || undefined,
        department: departmentFilter || undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
      });
      setEmployees(res.items);
      setTotal(res.total);
    } catch {
      // Empty state
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, departmentFilter, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const fetchNextCode = async () => {
    try {
      const res = await apiClient.get<{ next_code: string }>('/api/v1/master/employees/next-code');
      if (res.data?.next_code) {
        setAutoNextCode(res.data.next_code);
        return res.data.next_code;
      }
    } catch {
      // Fallback
    }
    return 'EMP-001';
  };

  const handleOpenCreate = async () => {
    setEditingEmployee(null);
    setShowInitialPassword(false);
    setShowConfirmInitialPassword(false);
    const nextCode = await fetchNextCode();
    setFormData({
      code: nextCode,
      full_name: '',
      email: '',
      phone: '',
      department: 'Production Department',
      designation: 'Production Supervisor',
      account_type: 'EMPLOYEE',
      job_role: 'Production Supervisor',
      joining_date: new Date().toISOString().split('T')[0],
      unit_id: 'BOTH',
      status: 'ACTIVE',
      emergency_contact: '',
      create_user_account: true,
      user_password: 'admin123',
      confirm_user_password: 'admin123',
      must_change_password: true,
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (emp: Employee) => {
    setEditingEmployee(emp);
    setShowInitialPassword(false);
    setShowConfirmInitialPassword(false);
    setFormData({
      code: emp.code,
      full_name: emp.full_name,
      email: emp.email || '',
      phone: emp.phone || '',
      department: emp.department || 'Production Department',
      designation: emp.designation || 'Staff',
      account_type: emp.account_type || 'EMPLOYEE',
      job_role: emp.job_role || emp.designation || 'Staff',
      joining_date: emp.joining_date || '',
      unit_id: emp.unit_id,
      status: emp.status || 'ACTIVE',
      emergency_contact: emp.emergency_contact || '',
      create_user_account: false,
      user_password: '',
      confirm_user_password: '',
      must_change_password: true,
      is_active: emp.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleDepartmentChange = (dept: string) => {
    const roles = DEPARTMENT_JOB_ROLES[dept] || [];
    const defaultRole = roles[0] || 'Staff';
    setFormData((prev) => ({
      ...prev,
      department: dept,
      designation: defaultRole,
      job_role: defaultRole,
    }));
  };

  const handleJobRoleChange = (role: string) => {
    setFormData((prev) => ({
      ...prev,
      designation: role,
      job_role: role,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Front-end validation for account provisioning
    if (!editingEmployee && formData.create_user_account) {
      if (!formData.email) {
        setFormError('Corporate email address is required to provision an ERP login account.');
        return;
      }
      if (!formData.user_password || formData.user_password.length < 6) {
        setFormError('Initial password must be at least 6 characters long (default: admin123).');
        return;
      }
      if (formData.user_password !== formData.confirm_user_password) {
        setFormError('Initial password and confirm password do not match.');
        return;
      }
    }

    setIsSubmitting(true);

    try {
      if (editingEmployee) {
        await masterClient.update<Employee>('employees', editingEmployee.id, {
          full_name: formData.full_name,
          email: formData.email || undefined,
          phone: formData.phone || undefined,
          department: formData.department,
          designation: formData.designation,
          account_type: formData.account_type,
          job_role: formData.job_role,
          joining_date: formData.joining_date || undefined,
          unit_id: formData.unit_id,
          status: formData.status,
          emergency_contact: formData.emergency_contact || undefined,
          is_active: formData.is_active,
        });
      } else {
        const payload = {
          ...formData,
          email: formData.email?.trim() || undefined,
          phone: formData.phone?.trim() || undefined,
          emergency_contact: formData.emergency_contact?.trim() || undefined,
          joining_date: formData.joining_date || undefined,
          user_password: formData.create_user_account ? (formData.user_password || undefined) : undefined,
          confirm_user_password: formData.create_user_account ? (formData.confirm_user_password || undefined) : undefined,
        };
        await masterClient.create<Employee>('employees', payload);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save employee record.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (emp: Employee) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('employees', emp.id, false);
      loadData();
    } catch {
      // error handled
    }
  };

  const availableJobRoles = DEPARTMENT_JOB_ROLES[formData.department] || [];

  const columns: Column<Employee>[] = [
    {
      key: 'code',
      header: 'Employee ID',
      render: (e: Employee) => (
        <span className="font-mono font-bold text-neutral-900 bg-neutral-100 px-2 py-0.5 rounded text-xs">
          {e.code}
        </span>
      ),
    },
    {
      key: 'name',
      header: 'Employee Name & Job Role',
      render: (e: Employee) => (
        <div>
          <div className="font-medium text-neutral-900">{e.full_name}</div>
          <div className="text-xs text-slate-500 font-medium flex items-center gap-1 mt-0.5">
            <Briefcase className="w-3 h-3 text-slate-400" />
            {e.designation}
          </div>
        </div>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (e: Employee) => (
        <span className="text-xs font-semibold text-neutral-800 bg-slate-50 border border-neutral-200 px-2 py-0.5 rounded">
          {e.department}
        </span>
      ),
    },
    {
      key: 'account_type',
      header: 'Account Type',
      render: (e: Employee) => {
        const accType = e.account_type || 'EMPLOYEE';
        return (
          <Badge
            variant={
              accType === 'SUPER_ADMIN'
                ? 'warning'
                : accType === 'HR'
                  ? 'success'
                  : 'neutral'
            }
            className="text-[11px] font-mono uppercase"
          >
            {accType}
          </Badge>
        );
      },
    },
    {
      key: 'unit_id',
      header: 'Assigned Unit',
      render: (e: Employee) => (
        <Badge
          variant={
            e.unit_id === 'Unit_1'
              ? 'neutral'
              : e.unit_id === 'Unit_2'
                ? 'warning'
                : 'success'
          }
          className="text-xs"
        >
          {e.unit_id === 'Unit_1'
            ? 'Unit 1 (Machining)'
            : e.unit_id === 'Unit_2'
              ? 'Unit 2 (Assembly & QC)'
              : 'Both Units'}
        </Badge>
      ),
    },
    {
      key: 'contact',
      header: 'Contact',
      render: (e: Employee) => (
        <div className="text-xs">
          <div>{e.phone || 'No phone'}</div>
          <div className="text-neutral-500 font-mono">{e.email || 'No email'}</div>
        </div>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (e: Employee) => (
        <Badge variant={e.is_active ? 'success' : 'neutral'} className="text-xs">
          {e.is_active ? (e.status || 'Active') : 'Deactivated'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (e: Employee) => (
        <div className="flex items-center gap-2">
          {!canUpdate ? (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
              Read-only
            </span>
          ) : (
            <>
              <button
                onClick={() => handleOpenEdit(e)}
                className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
                title="Edit Employee"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleToggleStatus(e)}
                className={`p-1 rounded transition-colors ${e.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
                  }`}
                title={e.is_active ? 'Deactivate' : 'Activate'}
              >
                {e.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">
            Employee &amp; Workforce Master
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manufacturing workforce directory with automated employee ID generation, department job roles, and account types across Unit 1 and Unit 2.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={masterClient.getTemplateUrl('employees')}
            download
            className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            <span>Import Template</span>
          </a>

          {canCreate && (
            <Button onClick={handleOpenCreate} className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              <span>Add Employee</span>
            </Button>
          )}
        </div>
      </div>

      <FilterBar
        searchQuery={search}
        onSearchChange={setSearch}
        placeholder="Search employee ID, name, or phone..."
      >
        <select
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
          className="text-xs border border-[#E7E5DE] rounded-lg px-2.5 py-2 bg-white"
        >
          <option value="">All Departments</option>
          {MANUFACTURING_DEPARTMENTS.map((dept) => (
            <option key={dept} value={dept}>
              {dept}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs border border-[#E7E5DE] rounded-lg px-2.5 py-2 bg-white"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active Only</option>
          <option value="INACTIVE">Deactivated Only</option>
        </select>
      </FilterBar>

      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-sm">
        <DataTable
          columns={columns}
          data={employees}
          isLoading={isLoading}
          emptyTitle="No employees found"
          emptyDescription="Click 'Add Employee' to register workforce personnel with automatic ID generation."
          keyExtractor={(e) => e.id}
        />

        {total > pageSize && (
          <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
            <div>Total: {total} employees</div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span>
                Page {page} of {Math.ceil(total / pageSize)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      <Dialog
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingEmployee ? `Edit Employee (${editingEmployee.code})` : 'Register New Employee'}
      >
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[80vh] overflow-y-auto px-1">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {formError}
            </div>
          )}

          {/* Employee ID & Full Name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-neutral-700">
                  Employee ID *
                </label>
                {!editingEmployee && (
                  <span className="text-[11px] text-emerald-700 font-mono font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Auto-generated
                  </span>
                )}
              </div>
              <input
                type="text"
                required
                disabled={!!editingEmployee}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="e.g. EMP-001"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase font-mono font-bold disabled:bg-neutral-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="e.g. Rajesh Sharma"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Department & Job Role */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Department *
              </label>
              <select
                value={formData.department}
                onChange={(e) => handleDepartmentChange(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                {MANUFACTURING_DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Employee Job Role *
              </label>
              <select
                value={formData.designation}
                onChange={(e) => handleJobRoleChange(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                {availableJobRoles.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Account Type & Facility Scoping */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Account Type *
              </label>
              <select
                value={formData.account_type}
                onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                <option value="EMPLOYEE">Employee (Assigned operational permissions)</option>
                <option value="ADMIN">Admin (Assigned administrative permissions)</option>
                <option value="HR">HR (Assigned HR permissions)</option>
              </select>
              <p className="text-[11px] text-slate-500 mt-1">
                Super Admin (Owner) is reserved for strict read-only executive monitoring.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Facility Assignment *
              </label>
              <select
                value={formData.unit_id}
                onChange={(e) => setFormData({ ...formData, unit_id: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                <option value="Unit_1">Unit 1 (Heavy Machining &amp; Fabrication)</option>
                <option value="Unit_2">Unit 2 (Precision Assembly &amp; QC)</option>
                <option value="BOTH">Both Facilities (Unit 1 &amp; Unit 2)</option>
              </select>
            </div>
          </div>

          {/* Phone & Email */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Phone Number
              </label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Corporate Email Address
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="rajesh.s@rgtech.com"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Joining Date & Emergency Contact */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Joining Date
              </label>
              <input
                type="date"
                value={formData.joining_date}
                onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Emergency Contact
              </label>
              <input
                type="text"
                value={formData.emergency_contact}
                onChange={(e) => setFormData({ ...formData, emergency_contact: e.target.value })}
                placeholder="Contact name &amp; phone"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Provision ERP Login Account (New Registrations Only) */}
          {!editingEmployee && (
            <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.create_user_account}
                  onChange={(e) =>
                    setFormData({ ...formData, create_user_account: e.target.checked })
                  }
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-xs font-semibold text-neutral-900 flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5 text-slate-700" />
                  Provision ERP Login Credentials for this Employee
                </span>
              </label>

              {formData.create_user_account && (
                <div className="pt-2 border-t border-neutral-200 space-y-3">
                  <p className="text-[11px] text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                    Default initial password is set to <strong className="font-mono text-emerald-950 bg-emerald-100/80 px-1 py-0.5 rounded">admin123</strong>. The employee will be able to log in immediately with their corporate email and can change their password later.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-neutral-700 mb-1">
                        Initial Password *
                      </label>
                      <div className="relative">
                        <input
                          type={showInitialPassword ? 'text' : 'password'}
                          required={formData.create_user_account}
                          value={formData.user_password}
                          onChange={(e) => setFormData({ ...formData, user_password: e.target.value })}
                          placeholder="Default: admin123"
                          className="w-full pl-3 pr-9 py-2 border border-neutral-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                        />
                        <button
                          type="button"
                          onClick={() => setShowInitialPassword(!showInitialPassword)}
                          className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600"
                          aria-label={showInitialPassword ? 'Hide password' : 'Show password'}
                        >
                          {showInitialPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-neutral-700 mb-1">
                        Confirm Initial Password *
                      </label>
                      <div className="relative">
                        <input
                          type={showConfirmInitialPassword ? 'text' : 'password'}
                          required={formData.create_user_account}
                          value={formData.confirm_user_password}
                          onChange={(e) => setFormData({ ...formData, confirm_user_password: e.target.value })}
                          placeholder="Re-type password"
                          className="w-full pl-3 pr-9 py-2 border border-neutral-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmInitialPassword(!showConfirmInitialPassword)}
                          className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600"
                          aria-label={showConfirmInitialPassword ? 'Hide confirmation password' : 'Show confirmation password'}
                        >
                          {showConfirmInitialPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.must_change_password}
                        onChange={(e) =>
                          setFormData({ ...formData, must_change_password: e.target.checked })
                        }
                        className="rounded text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="text-xs text-neutral-700 font-medium">
                        Require password change on first login (Recommended)
                      </span>
                    </label>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Min length: 12 chars
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : editingEmployee ? 'Update Employee' : 'Add Employee'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
