'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { HRDashboardView } from '@/components/dashboard/HRDashboardView';
import { EmployeeDashboardView } from '@/components/dashboard/EmployeeDashboardView';
import { OperationsDashboardView } from '@/components/dashboard/OperationsDashboardView';

export function DashboardRouter() {
  const { user } = useAuth();

  // Route directly based on user's identity & account type:
  // 1. HR staff: HR Workforce Command Center
  if (user?.role === 'HR' || user?.account_type === 'HR') {
    return <HRDashboardView />;
  }

  // 2. Regular Employees: Personal Self-Service Workspace
  if (user?.role === 'EMPLOYEE' || user?.account_type === 'EMPLOYEE') {
    return <EmployeeDashboardView />;
  }

  // 3. Operational Roles (SUPER_ADMIN, PLANT_HEAD, PRODUCTION_MANAGER, QC_MANAGER, etc.): Operational Telemetry
  return <OperationsDashboardView />;
}
