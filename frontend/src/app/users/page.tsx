'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { apiClient } from '@/services/api-client';
import { User, RoleName, ManufacturingUnit } from '@/types/auth';
import {
  MANUFACTURING_DEPARTMENTS,
  DEPARTMENT_JOB_ROLES,
  ACCOUNT_TYPES,
} from '@/lib/constants';
import {
  UserPlus,
  Shield,
  CheckCircle,
  XCircle,
  Briefcase,
  Building,
  Eye,
  EyeOff,
  Lock,
  KeyRound,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';

export default function UsersManagementPage() {
  const { user: currentUser, hasPermission } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    password: '',
    confirm_password: '',
    must_change_password: true,
    role: 'EMPLOYEE' as RoleName,
    account_type: 'EMPLOYEE',
    department: 'Production Department',
    job_role: 'Production Supervisor',
    employee_code: '',
    allowed_units: ['BOTH'] as ManufacturingUnit[],
  });
  const [formError, setFormError] = useState<string | null>(null);

  // Password reset modal state
  const [resetTargetUser, setResetTargetUser] = useState<User | null>(null);
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [resetMustChange, setResetMustChange] = useState(true);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [showResetNewPassword, setShowResetNewPassword] = useState(false);
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    const res = await apiClient.get<User[]>('/api/v1/users');
    if (res.data) {
      setUsers(res.data);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadUsers = async () => {
      setIsLoading(true);
      const res = await apiClient.get<User[]>('/api/v1/users');
      if (isMounted) {
        if (res.data) {
          setUsers(res.data);
        }
        setIsLoading(false);
      }
    };

    loadUsers();

    return () => {
      isMounted = false;
    };
  }, []);

  if (!hasPermission('users', 'read')) {
    return (
      <div className="p-8 text-center">
        <h3 className="text-lg font-bold text-slate-900">Access Denied</h3>
        <p className="text-sm text-slate-500 mt-1">
          You do not have permission to view the User Management module.
        </p>
      </div>
    );
  }

  const handleDepartmentChange = (dept: string) => {
    const roles = DEPARTMENT_JOB_ROLES[dept] || [];
    const defaultRole = roles[0] || 'Staff';
    setFormData((prev) => ({
      ...prev,
      department: dept,
      job_role: defaultRole,
    }));
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (formData.password.length < 12) {
      setFormError('Initial password must be at least 12 characters long.');
      return;
    }
    if (formData.password !== formData.confirm_password) {
      setFormError('Initial password and confirm password do not match.');
      return;
    }

    const res = await apiClient.post<User>('/api/v1/users', formData);
    if (res.data) {
      setShowCreateModal(false);
      setFormData({
        email: '',
        full_name: '',
        password: '',
        confirm_password: '',
        must_change_password: true,
        role: 'EMPLOYEE',
        account_type: 'EMPLOYEE',
        department: 'Production Department',
        job_role: 'Production Supervisor',
        employee_code: '',
        allowed_units: ['BOTH'],
      });
      fetchUsers();
    } else {
      setFormError(res.error?.message || 'Failed to provision user.');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTargetUser) return;
    setResetError(null);
    setResetSuccess(null);

    if (resetNewPassword.length < 12) {
      setResetError('New password must be at least 12 characters long.');
      return;
    }
    if (resetNewPassword !== resetConfirmPassword) {
      setResetError('New password and confirm password do not match.');
      return;
    }

    setIsResetting(true);
    const res = await apiClient.post('/api/v1/auth/reset-password', {
      user_id: resetTargetUser.id,
      new_password: resetNewPassword,
      confirm_password: resetConfirmPassword,
      must_change_password: resetMustChange,
    });

    if (res.status === 200) {
      setResetSuccess(`Password for ${resetTargetUser.full_name} has been reset. All active sessions revoked.`);
      setTimeout(() => {
        setResetTargetUser(null);
        setResetNewPassword('');
        setResetConfirmPassword('');
        setResetSuccess(null);
        fetchUsers();
      }, 1500);
    } else {
      setResetError(res.error?.message || 'Failed to reset employee password.');
    }
    setIsResetting(false);
  };

  const openResetModal = (u: User) => {
    setResetTargetUser(u);
    setResetNewPassword('');
    setResetConfirmPassword('');
    setResetMustChange(true);
    setResetError(null);
    setResetSuccess(null);
    setShowResetNewPassword(false);
    setShowResetConfirmPassword(false);
  };

  const toggleUserStatus = async (userToToggle: User) => {
    const updatedStatus = !userToToggle.is_active;
    const res = await apiClient.patch(`/api/v1/users/${userToToggle.id}`, {
      is_active: updatedStatus,
    });
    if (res.status === 200) {
      fetchUsers();
    }
  };

  const availableRoles = DEPARTMENT_JOB_ROLES[formData.department] || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            User, Account Type &amp; Access Administration
          </h2>
          <p className="text-xs text-slate-500">
            Provision employee ERP credentials with Account Type categories (Admin, HR, Employee), department job roles, and plant scoping.
          </p>
        </div>
        {hasPermission('users', 'create') && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5"
          >
            <UserPlus className="h-4 w-4" />
            Provision New Employee Account
          </Button>
        )}
      </div>

      {/* Users Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#E7E5DE] text-slate-500 font-semibold uppercase tracking-wider">
              <tr>
                <th className="pb-3 px-3">Employee Name &amp; ID</th>
                <th className="pb-3 px-3">Corporate Email</th>
                <th className="pb-3 px-3">Department &amp; Job Role</th>
                <th className="pb-3 px-3">Account Type</th>
                <th className="pb-3 px-3">Facility Scope</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading directory...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No users configured.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-900">{u.full_name}</div>
                      {u.employee_code && (
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                          {u.employee_code}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-600">{u.email}</td>
                    <td className="py-3 px-3">
                      <div className="font-medium text-slate-800">
                        {u.department || 'Operations'}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(u.job_roles && u.job_roles.length > 0
                          ? u.job_roles
                          : [u.job_role || u.role]
                        ).map((jr) => (
                          <span
                            key={jr}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-[#E8EEE7] text-[#315C45] rounded"
                          >
                            <Briefcase className="w-2.5 h-2.5" />
                            {jr}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <Badge
                        variant={
                          u.role === 'SUPER_ADMIN'
                            ? 'warning'
                            : u.role === 'HR'
                              ? 'success'
                              : 'neutral'
                        }
                      >
                        {u.role === 'SUPER_ADMIN'
                          ? 'Super Admin (Owner)'
                          : u.role === 'ADMIN'
                            ? 'Admin'
                            : u.role === 'HR'
                              ? 'HR'
                              : 'Employee'}
                      </Badge>
                    </td>
                    <td className="py-3 px-3">
                      {u.allowed_units.map((unit) => (
                        <span
                          key={unit}
                          className="inline-block mr-1 text-[11px] font-mono font-medium px-1.5 py-0.5 rounded bg-slate-100"
                        >
                          {unit === 'Unit_1'
                            ? 'Unit 1'
                            : unit === 'Unit_2'
                              ? 'Unit 2'
                              : 'Both'}
                        </span>
                      ))}
                    </td>
                    <td className="py-3 px-3">
                      <div className="space-y-1">
                        <Badge variant={u.is_active ? 'success' : 'error'}>
                          {u.is_active ? 'Active' : 'Deactivated'}
                        </Badge>
                        {u.must_change_password && (
                          <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
                            <KeyRound className="w-2.5 h-2.5" />
                            Change Required
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      {currentUser?.role === 'SUPER_ADMIN' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-500 border border-slate-200">
                          Read-only
                        </span>
                      ) : currentUser?.id !== u.id && hasPermission('users', 'update') ? (
                        <div className="flex items-center gap-1.5">
                          {/* HR can only reset EMPLOYEE passwords, Admin can reset non-super-admin */}
                          {(currentUser?.role === 'ADMIN' || (currentUser?.role === 'HR' && u.role === 'EMPLOYEE')) && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openResetModal(u)}
                              className="text-[11px] py-1 px-2 flex items-center gap-1 text-slate-700 hover:text-emerald-700"
                              title="Reset Employee Password"
                            >
                              <RotateCcw className="h-3 w-3" />
                              Reset
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleUserStatus(u)}
                            className="text-[11px] py-1 px-2"
                          >
                            {u.is_active ? (
                              <span className="flex items-center gap-1 text-rose-600">
                                <XCircle className="h-3 w-3" /> Deactivate
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-emerald-600">
                                <CheckCircle className="h-3 w-3" /> Activate
                              </span>
                            )}
                          </Button>
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[11px]">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Provision User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#E7E5DE] rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#EFEEE8] pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Shield className="h-4 w-4 text-[#315C45]" />
                Provision Employee Account
              </h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="p-2.5 rounded bg-rose-50 text-rose-700 text-xs border border-rose-200">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold block mb-1">Full Legal Name *</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="e.g. Ramesh Patil"
                  className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                />
              </div>

              <div>
                <label className="font-semibold block mb-1">Corporate Email Address *</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="ramesh.p@rgtech.com"
                  className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Initial Password (min 12 chars) *</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={12}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="Min 12 characters"
                      className="w-full pl-3 pr-8 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Confirm Initial Password *</label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      minLength={12}
                      value={formData.confirm_password}
                      onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                      placeholder="Re-type initial password"
                      className="w-full pl-3 pr-8 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600"
                      aria-label={showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'}
                    >
                      {showConfirmPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={formData.must_change_password}
                    onChange={(e) => setFormData({ ...formData, must_change_password: e.target.checked })}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-xs text-neutral-700 font-medium">
                    Require employee to change password on first login (Recommended)
                  </span>
                </label>
              </div>

              {/* Department & Job Role */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Department *</label>
                  <select
                    value={formData.department}
                    onChange={(e) => handleDepartmentChange(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  >
                    {MANUFACTURING_DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>
                        {dept}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Job Role *</label>
                  <select
                    value={formData.job_role}
                    onChange={(e) => setFormData({ ...formData, job_role: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  >
                    {availableRoles.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Account Type & Facility Scoping */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Account Type *</label>
                  <select
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        role: e.target.value as RoleName,
                        account_type: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  >
                    <option value="EMPLOYEE">Employee (Assigned operational permissions)</option>
                    {currentUser?.role !== 'HR' && (
                      <option value="ADMIN">Admin (Assigned administrative permissions)</option>
                    )}
                    <option value="HR">HR (Assigned HR permissions)</option>
                  </select>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    Super Admin (Owner) is strict read-only executive monitoring.
                  </p>
                </div>

                <div>
                  <label className="font-semibold block mb-1">Facility Access *</label>
                  <select
                    value={formData.allowed_units[0]}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        allowed_units: [e.target.value as ManufacturingUnit],
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  >
                    <option value="BOTH">Both Facilities (Unit 1 &amp; Unit 2)</option>
                    <option value="Unit_1">Unit 1 Only (Machining)</option>
                    <option value="Unit_2">Unit 2 Only (Assembly &amp; QC)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Employee ID / Badge (Optional)</label>
                <input
                  type="text"
                  value={formData.employee_code}
                  onChange={(e) =>
                    setFormData({ ...formData, employee_code: e.target.value.toUpperCase() })
                  }
                  placeholder="e.g. EMP-001"
                  className="w-full px-3 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs font-mono uppercase"
                />
              </div>

              <div className="pt-3 flex gap-2 justify-end border-t border-[#EFEEE8]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Provision Account
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetTargetUser && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#E7E5DE] rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#EFEEE8] pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <RotateCcw className="h-4 w-4 text-[#315C45]" />
                Reset Employee Password
              </h3>
              <button
                type="button"
                onClick={() => setResetTargetUser(null)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            <div className="p-3 bg-[#FAF9F5] border border-[#E6E4DC] rounded-lg text-xs space-y-1">
              <div className="font-semibold text-[#202722]">{resetTargetUser.full_name}</div>
              <div className="text-[#73786F] font-mono">{resetTargetUser.email}</div>
              <div className="text-[11px] text-slate-500 pt-1">
                This will set a new temporary password and revoke all active sessions for this account.
              </div>
            </div>

            {resetError && (
              <div className="p-2.5 rounded bg-rose-50 text-rose-700 text-xs border border-rose-200 flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{resetError}</span>
              </div>
            )}

            {resetSuccess && (
              <div className="p-2.5 rounded bg-emerald-50 text-emerald-700 text-xs border border-emerald-200 flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{resetSuccess}</span>
              </div>
            )}

            <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold block mb-1">New Temporary Password (min 12 chars) *</label>
                <div className="relative">
                  <input
                    type={showResetNewPassword ? 'text' : 'password'}
                    required
                    minLength={12}
                    value={resetNewPassword}
                    onChange={(e) => setResetNewPassword(e.target.value)}
                    placeholder="Min 12 characters"
                    disabled={isResetting}
                    className="w-full pl-3 pr-8 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => setShowResetNewPassword(!showResetNewPassword)}
                    className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600"
                    aria-label={showResetNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showResetNewPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Confirm Temporary Password *</label>
                <div className="relative">
                  <input
                    type={showResetConfirmPassword ? 'text' : 'password'}
                    required
                    minLength={12}
                    value={resetConfirmPassword}
                    onChange={(e) => setResetConfirmPassword(e.target.value)}
                    placeholder="Re-type temporary password"
                    disabled={isResetting}
                    className="w-full pl-3 pr-8 py-2 rounded-lg border border-[#E7E5DE] bg-white text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => setShowResetConfirmPassword(!showResetConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600"
                    aria-label={showResetConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'}
                  >
                    {showResetConfirmPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={resetMustChange}
                    onChange={(e) => setResetMustChange(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-xs text-neutral-700 font-medium">
                    Require employee to change password upon next login
                  </span>
                </label>
              </div>

              <div className="pt-3 flex gap-2 justify-end border-t border-[#EFEEE8]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setResetTargetUser(null)}
                  disabled={isResetting}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={isResetting}>
                  {isResetting ? 'Resetting...' : 'Confirm Reset Password'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
