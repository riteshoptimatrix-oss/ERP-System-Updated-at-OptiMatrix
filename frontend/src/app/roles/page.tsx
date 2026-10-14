'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/services/api-client';
import { Shield, RefreshCw, Search, CheckCircle2, UserCheck, Briefcase, Key } from 'lucide-react';
import {
  ACCOUNT_TYPES,
  MANUFACTURING_DEPARTMENTS,
  DEPARTMENT_JOB_ROLES,
} from '@/lib/constants';

interface RoleRecord {
  name: string;
  permissions: Record<string, string[]> | string[];
  description?: string;
}

function groupPermissions(permissions: Record<string, string[]> | string[] | undefined): Record<string, string[]> {
  if (!permissions) return {};
  if (!Array.isArray(permissions)) {
    const grouped: Record<string, string[]> = {};
    for (const [mod, acts] of Object.entries(permissions)) {
      grouped[mod] = Array.isArray(acts) ? acts : [String(acts)];
    }
    return grouped;
  }

  const grouped: Record<string, string[]> = {};
  for (const perm of permissions) {
    if (typeof perm === 'string') {
      const parts = perm.split(':');
      const mod = parts[0] || 'general';
      const action = parts.slice(1).join(':') || 'access';
      if (!grouped[mod]) {
        grouped[mod] = [];
      }
      if (!grouped[mod].includes(action)) {
        grouped[mod].push(action);
      }
    }
  }
  return grouped;
}

export default function RolesPage() {
  const { hasPermission } = useAuth();
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ACCOUNT_TYPES' | 'JOB_ROLES' | 'RBAC_MATRIX'>('ACCOUNT_TYPES');
  const [selectedDept, setSelectedDept] = useState<string>(MANUFACTURING_DEPARTMENTS[0]);

  const fetchRoles = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get<RoleRecord[]>('/roles');
      if (res.data) {
        setRoles(res.data);
        if (!selectedRole && res.data.length > 0) {
          setSelectedRole(res.data[0].name);
        }
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [selectedRole]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  if (!hasPermission('roles', 'read')) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-neutral-200">
        <h3 className="text-lg font-bold text-slate-900">Access Restricted</h3>
        <p className="text-sm text-slate-500 mt-1">You do not have permission to view Roles and RBAC configuration.</p>
      </div>
    );
  }

  const filteredRoles = roles.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase().trim())
  );

  const activeRoleData = roles.find((r) => r.name === selectedRole) || roles[0];
  const activeGroupedPermissions = activeRoleData ? groupPermissions(activeRoleData.permissions) : {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Shield className="w-7 h-7 text-purple-600" />
            Roles, Account Types &amp; Permission Matrix
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manufacturing operations access architecture: 4 Account Types, 8 department job roles, and live module permissions.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchRoles}
          disabled={loading}
          className="flex items-center gap-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-neutral-200 pb-2">
        <button
          onClick={() => setActiveTab('ACCOUNT_TYPES')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${activeTab === 'ACCOUNT_TYPES'
              ? 'bg-[#0F172A] text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
            }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          1. Account Types (4 Categories)
        </button>
        <button
          onClick={() => setActiveTab('JOB_ROLES')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${activeTab === 'JOB_ROLES'
              ? 'bg-[#0F172A] text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
            }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          2. Employee Job Roles (8 Departments)
        </button>
        <button
          onClick={() => setActiveTab('RBAC_MATRIX')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${activeTab === 'RBAC_MATRIX'
              ? 'bg-[#0F172A] text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
            }`}
        >
          <Key className="w-3.5 h-3.5" />
          3. Live RBAC Matrix
        </button>
      </div>

      {/* View 1: 4 Account Types */}
      {activeTab === 'ACCOUNT_TYPES' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {ACCOUNT_TYPES.map((acc, idx) => (
            <Card key={acc.type} className="p-5 bg-white border-neutral-200 shadow-xs space-y-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-bold text-slate-400">
                  CATEGORY #{idx + 1}
                </span>
                <Badge variant={(acc.badgeVariant as 'success' | 'warning' | 'error' | 'neutral') || 'neutral'}>{acc.type}</Badge>
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">{acc.label}</h3>
                <p className="text-xs text-slate-600 font-medium mt-1">{acc.access}</p>
              </div>
              <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500">
                {acc.type === 'SUPER_ADMIN' && (
                  <p className="text-purple-800 bg-purple-50 p-2 rounded border border-purple-200/60">
                    Full executive access across Unit 1 &amp; 2. Complete administrative, operational, approval, and management authority across all ERP modules.
                  </p>
                )}
                {acc.type === 'ADMIN' && (
                  <p className="text-slate-700 bg-slate-50 p-2 rounded border border-slate-200/60">
                    Operational administrative control across modules, configurations, and plant operations.
                  </p>
                )}
                {acc.type === 'HR' && (
                  <p className="text-emerald-800 bg-emerald-50 p-2 rounded border border-emerald-200/60">
                    Full workforce lifecycle: provision employees, auto IDs, assign department job roles, shifts, attendance, and payroll records.
                  </p>
                )}
                {acc.type === 'EMPLOYEE' && (
                  <p className="text-blue-800 bg-blue-50 p-2 rounded border border-blue-200/60">
                    Operational access tailored to shop-floor, QC, inventory, dispatch, or finance tasks assigned by HR.
                  </p>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* View 2: 8 Manufacturing Department Job Roles */}
      {activeTab === 'JOB_ROLES' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Department List */}
          <Card className="p-4 bg-white border-neutral-200 shadow-xs md:col-span-1 space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 px-2 pb-1">
              Manufacturing Departments
            </h3>
            <div className="space-y-1">
              {MANUFACTURING_DEPARTMENTS.map((dept) => {
                const count = DEPARTMENT_JOB_ROLES[dept]?.length || 0;
                return (
                  <button
                    key={dept}
                    onClick={() => setSelectedDept(dept)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold transition-all flex items-center justify-between ${selectedDept === dept
                        ? 'bg-purple-50 text-purple-900 border border-purple-200 font-bold'
                        : 'text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <span>{dept}</span>
                    <Badge variant={selectedDept === dept ? 'success' : 'neutral'}>
                      {count} roles
                    </Badge>
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Department Roles Catalog */}
          <Card className="p-6 bg-white border-neutral-200 shadow-xs md:col-span-2 space-y-4">
            <div className="border-b border-neutral-100 pb-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">{selectedDept}</h2>
                <Badge variant="neutral">Department Catalog</Badge>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Authorized job roles available when provisioning employees in {selectedDept}.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(DEPARTMENT_JOB_ROLES[selectedDept] || []).map((role, idx) => (
                <div
                  key={role}
                  className="p-3.5 rounded-xl border border-neutral-200 bg-neutral-50/50 flex items-start justify-between"
                >
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-slate-400 font-bold">
                      ROLE #{idx + 1}
                    </span>
                    <h4 className="text-xs font-bold text-slate-900">{role}</h4>
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Briefcase className="w-3 h-3 text-slate-400" />
                      Assigned by HR Department
                    </span>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* View 3: Live RBAC Matrix */}
      {activeTab === 'RBAC_MATRIX' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Roles List */}
          <Card className="p-4 bg-white border-neutral-200 shadow-xs md:col-span-1 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search roles..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-neutral-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="space-y-1 max-h-[550px] overflow-y-auto">
              {filteredRoles.map((role) => {
                const grouped = groupPermissions(role.permissions);
                const moduleCount = Object.keys(grouped).length;
                return (
                  <button
                    key={role.name}
                    onClick={() => setSelectedRole(role.name)}
                    className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${selectedRole === role.name
                        ? 'bg-purple-50 text-purple-900 border border-purple-200 font-semibold'
                        : 'text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{role.name.replace(/_/g, ' ')}</span>
                      <Badge variant={selectedRole === role.name ? 'success' : 'neutral'}>
                        {moduleCount} modules
                      </Badge>
                    </div>
                  </button>
                );
              })}
              {filteredRoles.length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">No matching roles</p>
              )}
            </div>
          </Card>

          {/* Selected Role Permissions Detail */}
          <Card className="p-6 bg-white border-neutral-200 shadow-xs md:col-span-2 space-y-4">
            {activeRoleData ? (
              <>
                <div className="border-b border-neutral-100 pb-3">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900">
                      {activeRoleData.name.replace(/_/g, ' ')}
                    </h2>
                    <Badge variant="success">{activeRoleData.name}</Badge>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Configured module authorizations and action privileges for this role.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[500px] overflow-y-auto pr-1">
                  {Object.keys(activeGroupedPermissions).length === 0 ? (
                    <p className="text-sm text-slate-400 py-6 sm:col-span-2 text-center">
                      No permissions assigned to this role yet.
                    </p>
                  ) : (
                    Object.entries(activeGroupedPermissions).map(([moduleName, actions]) => (
                      <div
                        key={moduleName}
                        className="p-3 rounded-lg border border-neutral-100 bg-neutral-50/50 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                            {moduleName}
                          </span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {Array.isArray(actions) && actions.map((act) => (
                            <span
                              key={act}
                              className="px-2 py-0.5 text-[11px] font-mono rounded bg-white border border-neutral-200 text-slate-600"
                            >
                              {act}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400 text-center py-12">Select a role to inspect permissions</p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
