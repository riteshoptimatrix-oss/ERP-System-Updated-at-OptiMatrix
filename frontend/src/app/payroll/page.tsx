'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { payrollClient } from '@/services/payroll-client';
import { masterClient } from '@/services/master-client';
import {
  PayrollRun,
  PayrollRunStatus,
  PayrollRunCreate,
  PayrollItem,
  Payslip,
  PayrollJournalEntry,
  PayrollSummary,
  SalaryStructure,
  SalaryStructureInput,
} from '@/types/hr';
import { Employee } from '@/types/master';
import {
  CreditCard,
  CheckCircle,
  FileText,
  IndianRupee,
  Plus,
  Eye,
  Check,
  Send,
  Lock,
  Download,
  Calendar,
  Layers,
} from 'lucide-react';

const RUN_STATUS_VARIANTS: Record<PayrollRunStatus, 'neutral' | 'warning' | 'success' | 'error'> = {
  DRAFT: 'neutral',
  UNDER_REVIEW: 'warning',
  APPROVED: 'success',
  POSTED: 'neutral',
};

export default function PayrollPage() {
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
        router.replace('/employee/payroll');
      } else {
        router.replace('/unauthorized');
      }
    }
  }, [user, isHRUser, router]);

  const canRead = hasPermission('payroll', 'read');
  const canCreate = hasPermission('payroll', 'create');
  const canUpdate = hasPermission('payroll', 'update');
  const canApprove = hasPermission('payroll', 'approve');
  const canPost = hasPermission('payroll', 'post');
  const canExport = hasPermission('payroll', 'export');

  // Active Tab
  const [activeTab, setActiveTab] = useState<'runs' | 'structures'>('runs');

  // KPI Metrics
  const [metrics, setMetrics] = useState<PayrollSummary | null>(null);

  // Runs State
  const [runsList, setRunsList] = useState<PayrollRun[]>([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [periodFilter, setPeriodFilter] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Salary Structures State
  const [structuresList, setStructuresList] = useState<SalaryStructure[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);

  // Detailed Run Line Items modal
  const [selectedRun, setSelectedRun] = useState<PayrollRun | null>(null);
  const [runItems, setRunItems] = useState<PayrollItem[]>([]);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  // Payslip Modal
  const [selectedPayslip, setSelectedPayslip] = useState<Payslip | null>(null);
  const [isSlipOpen, setIsSlipOpen] = useState(false);

  // Journal Entry Modal
  const [journalEntry, setJournalEntry] = useState<PayrollJournalEntry | null>(null);
  const [isJournalOpen, setIsJournalOpen] = useState(false);

  // Create Run Modal
  const [isCreateRunOpen, setIsCreateRunOpen] = useState(false);
  const [runForm, setRunForm] = useState<PayrollRunCreate>({
    period: new Date().toISOString().slice(0, 7),
    unit_id: 'Unit_1',
    working_days_in_month: 26,
    notes: '',
  });

  // Salary Structure Modal
  const [isStructOpen, setIsStructOpen] = useState(false);
  const [structForm, setStructForm] = useState<SalaryStructureInput>({
    employee_id: '',
    unit_id: 'Unit_1',
    base_monthly_salary: 25000,
    basic_salary: 15000,
    hra: 5000,
    conveyance_allowance: 2000,
    special_allowance: 3000,
    overtime_hourly_rate: 150,
    pf_applicable: true,
    pf_percentage: 12.0,
    esi_applicable: true,
    esi_percentage: 0.75,
    professional_tax: 200,
    tds_monthly: 0,
    bank_name: 'State Bank of India',
    bank_account_number: '',
    bank_ifsc: '',
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load KPI metrics
  const fetchMetrics = useCallback(async () => {
    try {
      const res = await payrollClient.getSummary(activeUnit);
      setMetrics(res);
    } catch {
      // ignore
    }
  }, [activeUnit]);

  // Load Reference Masters
  const fetchEmployees = useCallback(async () => {
    try {
      const res = await masterClient.list<Employee>('employees', { page_size: 100 });
      setEmployees(res.items || []);
    } catch {
      // ignore
    }
  }, []);

  // Load Runs
  const fetchRuns = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await payrollClient.listRuns({
        unit_id: activeUnit !== 'BOTH' ? activeUnit : undefined,
        status: statusFilter || undefined,
        period: periodFilter || undefined,
        page,
        page_size: 20,
      });
      setRunsList(res.items);
      setTotalRuns(res.total);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [activeUnit, statusFilter, periodFilter, page]);

  // Load Structures
  const fetchStructures = useCallback(async () => {
    try {
      const res = await payrollClient.listStructures(activeUnit);
      setStructuresList(res);
    } catch {
      // ignore
    }
  }, [activeUnit]);

  useEffect(() => {
    if (!isHRUser) return;
    fetchMetrics();
    fetchEmployees();
  }, [isHRUser, fetchMetrics, fetchEmployees]);

  useEffect(() => {
    if (!isHRUser) return;
    if (activeTab === 'runs') {
      fetchRuns();
    } else {
      fetchStructures();
    }
  }, [isHRUser, activeTab, fetchRuns, fetchStructures]);

  // Open Run Details
  const handleViewDetails = async (run: PayrollRun) => {
    setSelectedRun(run);
    try {
      const items = await payrollClient.listItems(run.id);
      setRunItems(items);
      setIsDetailsOpen(true);
    } catch {
      // ignore
    }
  };

  // View Payslip
  const handleViewPayslip = async (employeeId: string, period: string) => {
    try {
      const slip = await payrollClient.getPayslip(employeeId, period);
      setSelectedPayslip(slip);
      setIsSlipOpen(true);
    } catch {
      // ignore
    }
  };

  // View Accounting Export
  const handleViewJournal = async (runId: string) => {
    try {
      const jv = await payrollClient.getAccountingExport(runId);
      setJournalEntry(jv);
      setIsJournalOpen(true);
    } catch {
      // ignore
    }
  };

  // State transitions: Review, Approve, Post
  const handleRunAction = async (action: 'review' | 'approve' | 'post', runId: string) => {
    try {
      if (action === 'review') await payrollClient.reviewRun(runId);
      if (action === 'approve') await payrollClient.approveRun(runId);
      if (action === 'post') await payrollClient.postRun(runId);
      fetchRuns();
      fetchMetrics();
      if (selectedRun?.id === runId) {
        const updated = await payrollClient.getRun(runId);
        setSelectedRun(updated);
      }
    } catch {
      // ignore
    }
  };

  // Create Run submit
  const handleCreateRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await payrollClient.createRun({
        period: runForm.period,
        unit_id: (activeUnit !== 'BOTH' ? activeUnit : runForm.unit_id) as string,
        working_days_in_month: Number(runForm.working_days_in_month || 26),
        notes: runForm.notes,
      });
      setIsCreateRunOpen(false);
      fetchRuns();
      fetchMetrics();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create payroll run');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Save Structure submit
  const handleSaveStructure = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!structForm.employee_id) {
      setFormError('Please select an employee.');
      return;
    }

    setIsSubmitting(true);
    try {
      await payrollClient.upsertStructure({
        ...structForm,
        unit_id: (activeUnit !== 'BOTH' ? activeUnit : structForm.unit_id) as string,
        base_monthly_salary: Number(structForm.base_monthly_salary),
        basic_salary: Number(structForm.basic_salary),
        hra: Number(structForm.hra),
        conveyance_allowance: Number(structForm.conveyance_allowance),
        special_allowance: Number(structForm.special_allowance),
        overtime_hourly_rate: Number(structForm.overtime_hourly_rate),
        pf_percentage: Number(structForm.pf_percentage),
        esi_percentage: Number(structForm.esi_percentage),
        professional_tax: Number(structForm.professional_tax),
        tds_monthly: Number(structForm.tds_monthly),
      });
      setIsStructOpen(false);
      fetchStructures();
      fetchMetrics();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to save salary structure');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Run Columns
  const runColumns: Column<PayrollRun>[] = [
    {
      key: 'run_number',
      header: 'Run Number & Period',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900">{row.run_number}</div>
          <div className="text-xs text-slate-500 font-mono">
            Period: {row.period} • {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : row.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
          </div>
        </div>
      ),
    },
    {
      key: 'employees',
      header: 'Headcount',
      render: (row) => (
        <div className="text-sm">
          <span className="font-semibold text-slate-800">{row.total_employees}</span> employees
          <div className="text-xs text-slate-500">{row.working_days_in_month} working days</div>
        </div>
      ),
    },
    {
      key: 'gross_net',
      header: 'Gross / Deductions / Net',
      render: (row) => (
        <div className="text-sm">
          <div className="font-medium text-slate-800">
            Net: ₹{row.total_net_payout.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-slate-500">
            Gross: ₹{row.total_gross_payout.toLocaleString('en-IN')} | Ded: ₹{row.total_deductions.toLocaleString('en-IN')}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <Badge variant={RUN_STATUS_VARIANTS[row.status] || 'neutral'}>
            {row.status}
          </Badge>
          {row.status === 'POSTED' && (
            <span title="Locked & Immutable">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-1.5 items-center">
          <Button size="sm" variant="outline" onClick={() => handleViewDetails(row)}>
            <Eye className="w-3.5 h-3.5 mr-1" />
            Inspect
          </Button>

          {row.status === 'DRAFT' && canUpdate && (
            <Button size="sm" variant="outline" onClick={() => handleRunAction('review', row.id)}>
              <Send className="w-3.5 h-3.5 mr-1" />
              Review
            </Button>
          )}

          {row.status === 'UNDER_REVIEW' && canApprove && (
            <Button size="sm" variant="primary" onClick={() => handleRunAction('approve', row.id)}>
              <Check className="w-3.5 h-3.5 mr-1" />
              Approve
            </Button>
          )}

          {row.status === 'APPROVED' && canPost && (
            <Button size="sm" variant="danger" onClick={() => handleRunAction('post', row.id)}>
              <Lock className="w-3.5 h-3.5 mr-1" />
              Post Run
            </Button>
          )}

          {row.status === 'POSTED' && canExport && (
            <Button size="sm" variant="outline" onClick={() => handleViewJournal(row.id)}>
              <FileText className="w-3.5 h-3.5 mr-1" />
              Journal JV
            </Button>
          )}
        </div>
      ),
    },
  ];

  // Structure Columns
  const structureColumns: Column<SalaryStructure>[] = [
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
      key: 'base_gross',
      header: 'Monthly CTC / Gross',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900">
            ₹{row.gross_monthly_standard.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-slate-500">Base: ₹{row.base_monthly_salary.toLocaleString('en-IN')}</div>
        </div>
      ),
    },
    {
      key: 'breakdown',
      header: 'Components',
      render: (row) => (
        <div className="text-xs text-slate-600">
          Basic: ₹{row.basic_salary} | HRA: ₹{row.hra} | Conv: ₹{row.conveyance_allowance}
        </div>
      ),
    },
    {
      key: 'statutory',
      header: 'PF / ESI / PT',
      render: (row) => (
        <div className="text-xs text-slate-600">
          PF: {row.pf_applicable ? `${row.pf_percentage}%` : 'No'} | ESI: {row.esi_applicable ? `${row.esi_percentage}%` : 'No'} | PT: ₹{row.professional_tax}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setStructForm({
              employee_id: row.employee_id,
              unit_id: row.unit_id,
              base_monthly_salary: row.base_monthly_salary,
              basic_salary: row.basic_salary,
              hra: row.hra,
              conveyance_allowance: row.conveyance_allowance,
              special_allowance: row.special_allowance,
              overtime_hourly_rate: row.overtime_hourly_rate,
              pf_applicable: row.pf_applicable,
              pf_percentage: row.pf_percentage,
              esi_applicable: row.esi_applicable,
              esi_percentage: row.esi_percentage,
              professional_tax: row.professional_tax,
              tds_monthly: row.tds_monthly,
              bank_name: row.bank_name || '',
              bank_account_number: row.bank_account_number || '',
              bank_ifsc: row.bank_ifsc || '',
            });
            setIsStructOpen(true);
          }}
        >
          Edit Package
        </Button>
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
            Payroll & Compensation
          </h1>
          <p className="text-sm text-slate-600">
            Attendance-backed payroll calculation, statutory deductions (PF, ESI, PT), and payslip generation.
          </p>
        </div>
        <div className="flex gap-2">
          {canUpdate && (
            <Button variant="outline" onClick={() => setIsStructOpen(true)}>
              <CreditCard className="w-4 h-4 mr-1.5" />
              Salary Structure
            </Button>
          )}
          {canCreate && (
            <Button variant="primary" onClick={() => setIsCreateRunOpen(true)}>
              <Plus className="w-4 h-4 mr-1.5" />
              Process Monthly Payroll
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-blue-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Configured Salaries</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.configured_salary_structures_count ?? '--'}
              </p>
            </div>
            <Layers className="w-8 h-8 text-blue-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Latest Net Payout</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                ₹{metrics?.total_net_payout?.toLocaleString('en-IN') ?? '0'}
              </p>
            </div>
            <IndianRupee className="w-8 h-8 text-emerald-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-purple-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Statutory Deductions</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                ₹{metrics?.total_statutory_deductions?.toLocaleString('en-IN') ?? '0'}
              </p>
            </div>
            <FileText className="w-8 h-8 text-purple-500 opacity-80" />
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-600 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Payroll Runs Count</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {metrics?.active_payroll_runs ?? '--'}
              </p>
            </div>
            <Calendar className="w-8 h-8 text-amber-500 opacity-80" />
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#E7E5DE]">
        <button
          className={`py-2.5 px-5 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'runs'
            ? 'border-[#315C45] text-[#315C45]'
            : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          onClick={() => setActiveTab('runs')}
        >
          Payroll Runs ({totalRuns})
        </button>
        <button
          className={`py-2.5 px-5 text-sm font-semibold border-b-2 transition-colors ${activeTab === 'structures'
            ? 'border-[#315C45] text-[#315C45]'
            : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          onClick={() => setActiveTab('structures')}
        >
          Salary Structure Master ({structuresList.length})
        </button>
      </div>

      {/* Tab 1: Runs */}
      {activeTab === 'runs' && (
        <Card className="p-4 space-y-4">
          <div className="flex flex-wrap gap-3 items-center justify-between">
            <div className="flex gap-2">
              <select
                className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="DRAFT">Draft</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="APPROVED">Approved</option>
                <option value="POSTED">Posted (Locked)</option>
              </select>

              <input
                type="month"
                className="px-3 py-1.5 text-sm border border-[#E7E5DE] rounded-md focus:outline-none focus:ring-1 focus:ring-[#315C45]"
                value={periodFilter}
                onChange={(e) => setPeriodFilter(e.target.value)}
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setStatusFilter('');
                setPeriodFilter('');
              }}
            >
              Reset Filters
            </Button>
          </div>

          <DataTable
            columns={runColumns}
            data={runsList}
            isLoading={isLoading}
            keyExtractor={(row) => row.id}
            emptyDescription="No payroll runs on record. Click 'Process Monthly Payroll' to compute your first run."
          />
        </Card>
      )}

      {/* Tab 2: Salary Structures */}
      {activeTab === 'structures' && (
        <Card className="p-4 space-y-4">
          <DataTable
            columns={structureColumns}
            data={structuresList}
            keyExtractor={(row) => row.id}
            emptyDescription="No salary structures defined. Click 'Salary Structure' to configure compensation packages."
          />
        </Card>
      )}

      {/* Dialog: Process Monthly Payroll */}
      <Dialog
        isOpen={isCreateRunOpen}
        onClose={() => setIsCreateRunOpen(false)}
        title="Compute Monthly Payroll Run"
      >
        <form onSubmit={handleCreateRun} className="space-y-4">
          {formError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-md">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Payroll Period (YYYY-MM) *
              </label>
              <input
                type="month"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={runForm.period}
                onChange={(e) => setRunForm({ ...runForm, period: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Working Days in Month *
              </label>
              <input
                type="number"
                min="20"
                max="31"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={runForm.working_days_in_month}
                onChange={(e) => setRunForm({ ...runForm, working_days_in_month: parseInt(e.target.value) })}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Notes
            </label>
            <input
              type="text"
              placeholder="e.g. October 2026 Production & Quality Staff Payout"
              className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
              value={runForm.notes || ''}
              onChange={(e) => setRunForm({ ...runForm, notes: e.target.value })}
            />
          </div>

          <div className="p-3 bg-[#EAF0E9] border border-[#315C45]/20 text-blue-800 text-xs rounded-md">
            The system will pull actual attendance records for the selected month, prorate loss-of-pay (unpaid absences), compute approved overtime hours, and apply statutory deductions (PF, ESI, PT).
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsCreateRunOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Calculating...' : 'Compute & Generate Run'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Dialog: Configure Salary Structure */}
      <Dialog
        isOpen={isStructOpen}
        onClose={() => setIsStructOpen(false)}
        title="Configure Salary Structure Package"
      >
        <form onSubmit={handleSaveStructure} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
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
              value={structForm.employee_id}
              onChange={(e) => setStructForm({ ...structForm, employee_id: e.target.value })}
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
                Base Monthly CTC (₹) *
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.base_monthly_salary}
                onChange={(e) => setStructForm({ ...structForm, base_monthly_salary: parseFloat(e.target.value) })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Basic Salary (₹) *
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.basic_salary}
                onChange={(e) => setStructForm({ ...structForm, basic_salary: parseFloat(e.target.value) })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                HRA (₹)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.hra}
                onChange={(e) => setStructForm({ ...structForm, hra: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Conveyance (₹)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.conveyance_allowance}
                onChange={(e) => setStructForm({ ...structForm, conveyance_allowance: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Special Allow (₹)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.special_allowance}
                onChange={(e) => setStructForm({ ...structForm, special_allowance: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Overtime Rate (₹/hr)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.overtime_hourly_rate}
                onChange={(e) => setStructForm({ ...structForm, overtime_hourly_rate: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Professional Tax (₹)
              </label>
              <input
                type="number"
                min="0"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.professional_tax}
                onChange={(e) => setStructForm({ ...structForm, professional_tax: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 border p-3 rounded-md bg-slate-50">
            <div>
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={structForm.pf_applicable}
                  onChange={(e) => setStructForm({ ...structForm, pf_applicable: e.target.checked })}
                />
                Deduct PF (12%)
              </label>
            </div>
            <div>
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={structForm.esi_applicable}
                  onChange={(e) => setStructForm({ ...structForm, esi_applicable: e.target.checked })}
                />
                Deduct ESI (0.75%)
              </label>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Bank Name
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.bank_name || ''}
                onChange={(e) => setStructForm({ ...structForm, bank_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Account Number
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.bank_account_number || ''}
                onChange={(e) => setStructForm({ ...structForm, bank_account_number: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                IFSC Code
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-[#E7E5DE] rounded-md text-sm"
                value={structForm.bank_ifsc || ''}
                onChange={(e) => setStructForm({ ...structForm, bank_ifsc: e.target.value })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" type="button" onClick={() => setIsStructOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Package'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Dialog: Inspect Run Items */}
      <Dialog
        isOpen={isDetailsOpen}
        onClose={() => setIsDetailsOpen(false)}
        title={`Payroll Run: ${selectedRun?.run_number} (${selectedRun?.period})`}
      >
        <div className="space-y-4 max-h-[75vh] overflow-y-auto">
          <div className="flex justify-between items-center bg-slate-50 p-3 rounded border">
            <div>
              <p className="text-xs text-slate-500">Status</p>
              <Badge variant={RUN_STATUS_VARIANTS[selectedRun?.status || 'DRAFT'] || 'neutral'}>
                {selectedRun?.status}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-slate-500">Gross Payout</p>
              <p className="font-semibold text-slate-800">₹{selectedRun?.total_gross_payout.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Total Deductions</p>
              <p className="font-semibold text-rose-700">-₹{selectedRun?.total_deductions.toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Net Payable</p>
              <p className="font-bold text-emerald-700 text-lg">₹{selectedRun?.total_net_payout.toLocaleString('en-IN')}</p>
            </div>
          </div>

          <div className="divide-y border rounded-md">
            {runItems.map((item) => (
              <div key={item.id} className="p-3 flex justify-between items-center text-sm">
                <div>
                  <div className="font-semibold text-slate-900">{item.employee_name} ({item.employee_code})</div>
                  <div className="text-xs text-slate-500">
                    Present: {item.present_days}d • LOP: {item.unpaid_leave_days}d • OT: {item.overtime_hours}h
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-slate-900">
                    Net: ₹{item.net_pay.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-slate-500">
                    Gross ₹{item.gross_earnings} - Ded ₹{item.total_deductions}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleViewPayslip(item.employee_id, item.period)}
                >
                  View Payslip
                </Button>
              </div>
            ))}
          </div>
        </div>
      </Dialog>

      {/* Dialog: Payslip */}
      <Dialog
        isOpen={isSlipOpen}
        onClose={() => setIsSlipOpen(false)}
        title={`Payslip: ${selectedPayslip?.payslip_number}`}
      >
        {selectedPayslip && (
          <div className="space-y-4 text-sm max-h-[75vh] overflow-y-auto">
            <div className="border-b pb-3 flex justify-between">
              <div>
                <h3 className="font-bold text-base text-slate-900">Opti Matrix PVT LTD</h3>
                <p className="text-xs text-slate-500">
                  Manufacturing Unit: {selectedPayslip.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : selectedPayslip.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
                </p>
              </div>
              <div className="text-right">
                <p className="font-semibold text-slate-800">Salary Slip - {selectedPayslip.period}</p>
                <p className="text-xs text-slate-500">{selectedPayslip.payslip_number}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 bg-slate-50 p-2.5 rounded text-xs">
              <div><span className="text-slate-500">Employee:</span> <span className="font-medium text-slate-800">{selectedPayslip.employee_name}</span></div>
              <div><span className="text-slate-500">Employee Code:</span> <span className="font-medium text-slate-800">{selectedPayslip.employee_code}</span></div>
              <div><span className="text-slate-500">Department:</span> <span className="font-medium text-slate-800">{selectedPayslip.department}</span></div>
              <div><span className="text-slate-500">Designation:</span> <span className="font-medium text-slate-800">{selectedPayslip.designation}</span></div>
              <div><span className="text-slate-500">Working Days:</span> <span className="font-medium text-slate-800">{selectedPayslip.standard_working_days}</span></div>
              <div><span className="text-slate-500">Present / LOP:</span> <span className="font-medium text-slate-800">{selectedPayslip.present_days} / {selectedPayslip.lop_days} days</span></div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Earnings */}
              <div className="border rounded p-3 space-y-1.5 text-xs">
                <div className="font-bold text-slate-800 border-b pb-1 text-sm">Earnings</div>
                <div className="flex justify-between"><span>Basic Salary</span><span>₹{selectedPayslip.basic.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>HRA</span><span>₹{selectedPayslip.hra.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Conveyance</span><span>₹{selectedPayslip.conveyance.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Special Allowance</span><span>₹{selectedPayslip.special_allowance.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Overtime Pay ({selectedPayslip.overtime_hours}h)</span><span>₹{selectedPayslip.overtime_pay.toFixed(2)}</span></div>
                <div className="flex justify-between font-bold border-t pt-1.5 text-slate-900">
                  <span>Gross Earnings</span><span>₹{selectedPayslip.total_earnings.toFixed(2)}</span>
                </div>
              </div>

              {/* Deductions */}
              <div className="border rounded p-3 space-y-1.5 text-xs">
                <div className="font-bold text-slate-800 border-b pb-1 text-sm">Deductions</div>
                <div className="flex justify-between"><span>Loss of Pay (LOP)</span><span className="text-rose-700">₹{selectedPayslip.lop_deduction.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Provident Fund (PF)</span><span className="text-rose-700">₹{selectedPayslip.pf_deduction.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>ESI</span><span className="text-rose-700">₹{selectedPayslip.esi_deduction.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Professional Tax (PT)</span><span className="text-rose-700">₹{selectedPayslip.professional_tax.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>TDS / Income Tax</span><span className="text-rose-700">₹{selectedPayslip.tds_deduction.toFixed(2)}</span></div>
                <div className="flex justify-between font-bold border-t pt-1.5 text-slate-900">
                  <span>Total Deductions</span><span className="text-rose-700">₹{selectedPayslip.total_deductions.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="bg-emerald-50 border border-emerald-200 p-3 rounded flex justify-between items-center">
              <div>
                <p className="text-xs text-emerald-800 font-semibold uppercase">Net Take Home Pay</p>
                <p className="text-xl font-bold text-emerald-950">
                  ₹{selectedPayslip.net_salary_payable.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="text-xs text-slate-500">
                Bank: {selectedPayslip.bank_name || 'N/A'} (A/C: {selectedPayslip.bank_account_number || 'N/A'})
              </div>
            </div>
          </div>
        )}
      </Dialog>

      {/* Dialog: Accounting Journal Entry */}
      <Dialog
        isOpen={isJournalOpen}
        onClose={() => setIsJournalOpen(false)}
        title={`General Ledger Journal Voucher: ${journalEntry?.voucher_number}`}
      >
        {journalEntry && (
          <div className="space-y-4 text-xs max-h-[75vh] overflow-y-auto">
            <div className="flex justify-between text-slate-600 bg-slate-50 p-2.5 rounded border">
              <div>Voucher: <span className="font-mono font-bold text-slate-900">{journalEntry.voucher_number}</span></div>
              <div>Posting Date: <span className="font-semibold">{journalEntry.posting_date}</span></div>
              <div>
                Balanced:{' '}
                <Badge variant={journalEntry.is_balanced ? 'success' : 'error'}>
                  {journalEntry.is_balanced ? 'BALANCED' : 'UNBALANCED'}
                </Badge>
              </div>
            </div>

            <table className="w-full border-collapse border text-left">
              <thead>
                <tr className="bg-slate-100 border-b">
                  <th className="p-2 border-r">Account Code & Name</th>
                  <th className="p-2 border-r text-right">Debit (₹)</th>
                  <th className="p-2 border-r text-right">Credit (₹)</th>
                  <th className="p-2">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {journalEntry.lines.map((line, idx) => (
                  <tr key={idx}>
                    <td className="p-2 border-r font-medium text-slate-800">
                      {line.account_code} - {line.account_name}
                    </td>
                    <td className="p-2 border-r text-right font-mono text-emerald-700">
                      {line.debit > 0 ? line.debit.toFixed(2) : '-'}
                    </td>
                    <td className="p-2 border-r text-right font-mono text-[#254936]">
                      {line.credit > 0 ? line.credit.toFixed(2) : '-'}
                    </td>
                    <td className="p-2 text-slate-500">{line.description}</td>
                  </tr>
                ))}
                <tr className="bg-slate-50 font-bold border-t">
                  <td className="p-2 border-r text-right">Totals:</td>
                  <td className="p-2 border-r text-right font-mono text-emerald-800">
                    ₹{journalEntry.total_debit.toFixed(2)}
                  </td>
                  <td className="p-2 border-r text-right font-mono text-blue-800">
                    ₹{journalEntry.total_credit.toFixed(2)}
                  </td>
                  <td className="p-2 text-emerald-700 font-semibold">Matched</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </Dialog>
    </div>
  );
}
