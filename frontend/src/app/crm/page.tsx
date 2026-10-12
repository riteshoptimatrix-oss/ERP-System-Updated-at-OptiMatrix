'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { crmClient, ListLeadsParams } from '@/services/crm-client';
import { Lead, LeadStatus, LeadPriority, LeadSource, CrmDashboardSummary } from '@/types/crm';
import { ManufacturingUnit } from '@/types/auth';
import {
  UserPlus,
  Flame,
  Clock,
  CheckCircle2,
  TrendingUp,
  Building2,
  Phone,
  Mail,
  ArrowRight,
  ShieldAlert,
  AlertCircle,
  Calendar,
} from 'lucide-react';

const STATUS_OPTIONS: { label: string; value: LeadStatus | 'ALL' }[] = [
  { label: 'All Stages', value: 'ALL' },
  { label: 'New', value: 'NEW' },
  { label: 'Contacted', value: 'CONTACTED' },
  { label: 'Qualified', value: 'QUALIFIED' },
  { label: 'Proposal Sent', value: 'PROPOSAL_SENT' },
  { label: 'Negotiation', value: 'NEGOTIATION' },
  { label: 'Converted', value: 'CONVERTED' },
  { label: 'Lost', value: 'LOST' },
];

const PRIORITY_OPTIONS: { label: string; value: LeadPriority | 'ALL' }[] = [
  { label: 'All Priorities', value: 'ALL' },
  { label: 'Hot', value: 'HOT' },
  { label: 'Warm', value: 'WARM' },
  { label: 'Cold', value: 'COLD' },
];

export default function CrmDashboardPage() {
  const { activeUnit, hasPermission, user } = useAuth();
  const canRead = hasPermission('crm', 'read');
  const canCreate = hasPermission('crm', 'create');

  // Dashboard KPI state
  const [metrics, setMetrics] = useState<CrmDashboardSummary | null>(null);
  const [isMetricsLoading, setIsMetricsLoading] = useState(false);

  // Leads table state
  const [leads, setLeads] = useState<Lead[]>([]);
  const [totalLeads, setTotalLeads] = useState(0);
  const [isLoadingLeads, setIsLoadingLeads] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');
  const [followUpFilter, setFollowUpFilter] = useState<'today' | 'overdue' | 'upcoming' | undefined>(undefined);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Create Lead Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    company_name: '',
    contact_person: '',
    email: '',
    phone: '',
    source: 'DIRECT_INQUIRY' as LeadSource,
    priority: 'WARM' as LeadPriority,
    status: 'NEW' as LeadStatus,
    estimated_value: 0,
    machine_interest: '',
    unit_id: (activeUnit || 'Unit_1') as ManufacturingUnit,
    next_follow_up: '',
    notes: '',
  });

  // Load KPI Dashboard metrics
  const fetchDashboardMetrics = useCallback(async () => {
    if (!canRead) return;
    try {
      setIsMetricsLoading(true);
      const data = await crmClient.getDashboard(activeUnit || undefined);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load CRM dashboard metrics:', err);
    } finally {
      setIsMetricsLoading(false);
    }
  }, [canRead, activeUnit]);

  // Load Paginated Leads
  const fetchLeads = useCallback(async () => {
    if (!canRead) return;
    try {
      setIsLoadingLeads(true);
      const params: ListLeadsParams = {
        search: searchQuery || undefined,
        status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        priority: selectedPriority !== 'ALL' ? selectedPriority : undefined,
        unit_id: activeUnit || undefined,
        follow_up_filter: followUpFilter,
        page,
        page_size: pageSize,
      };
      const res = await crmClient.listLeads(params);
      setLeads(res.items);
      setTotalLeads(res.total);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setIsLoadingLeads(false);
    }
  }, [canRead, searchQuery, selectedStatus, selectedPriority, activeUnit, followUpFilter, page]);

  useEffect(() => {
    fetchDashboardMetrics();
  }, [fetchDashboardMetrics]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Update default unit on unit switch
  useEffect(() => {
    if (activeUnit) {
      setFormData((prev) => ({ ...prev, unit_id: activeUnit }));
    }
  }, [activeUnit]);

  // Handle Create Lead Submission
  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!formData.company_name.trim() || !formData.contact_person.trim() || !formData.phone.trim()) {
      setFormError('Company name, contact person, and phone number are required.');
      return;
    }

    try {
      setCreateSubmitting(true);
      await crmClient.createLead({
        ...formData,
        estimated_value: Number(formData.estimated_value) || 0,
        next_follow_up: formData.next_follow_up ? new Date(formData.next_follow_up).toISOString() : undefined,
      });
      setIsCreateOpen(false);
      setFormData({
        company_name: '',
        contact_person: '',
        email: '',
        phone: '',
        source: 'DIRECT_INQUIRY',
        priority: 'WARM',
        status: 'NEW',
        estimated_value: 0,
        machine_interest: '',
        unit_id: activeUnit || 'Unit_1',
        next_follow_up: '',
        notes: '',
      });
      fetchLeads();
      fetchDashboardMetrics();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create lead';
      setFormError(msg);
    } finally {
      setCreateSubmitting(false);
    }
  };

  const getPriorityBadge = (priority: LeadPriority) => {
    switch (priority) {
      case 'HOT':
        return <Badge variant="error" className="font-semibold">HOT</Badge>;
      case 'WARM':
        return <Badge variant="warning">WARM</Badge>;
      case 'COLD':
        return <Badge variant="neutral">COLD</Badge>;
    }
  };

  const getStatusBadge = (status: LeadStatus) => {
    switch (status) {
      case 'NEW':
        return <Badge variant="neutral">NEW</Badge>;
      case 'CONTACTED':
        return <Badge variant="neutral">CONTACTED</Badge>;
      case 'QUALIFIED':
        return <Badge variant="warning">QUALIFIED</Badge>;
      case 'PROPOSAL_SENT':
        return <Badge variant="warning">PROPOSAL SENT</Badge>;
      case 'NEGOTIATION':
        return <Badge variant="warning">NEGOTIATION</Badge>;
      case 'CONVERTED':
        return <Badge variant="success">CONVERTED</Badge>;
      case 'LOST':
        return <Badge variant="error">LOST</Badge>;
    }
  };

  const columns: Column<Lead>[] = [
    {
      key: 'code',
      header: 'Lead Code',
      render: (row) => (
        <div>
          <Link
            href={`/crm/${row.id}`}
            className="font-semibold text-[#315C45] hover:text-blue-800 hover:underline"
          >
            {row.code}
          </Link>
          <div className="text-[10px] text-slate-400">
            {new Date(row.created_at).toLocaleDateString()}
          </div>
        </div>
      ),
    },
    {
      key: 'company_name',
      header: 'Company & Contact',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900  flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            {row.company_name}
          </div>
          <div className="text-slate-500 text-[11px] flex items-center gap-2 mt-0.5">
            <span>{row.contact_person}</span>
            <span>•</span>
            <span className="flex items-center gap-0.5">
              <Phone className="w-3 h-3 text-slate-400" /> {row.phone}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'interest',
      header: 'Machine Interest & Value',
      render: (row) => (
        <div>
          <div className="font-medium text-slate-800 ">
            {row.machine_interest || 'General Machining'}
          </div>
          <div className="text-slate-500 text-[11px]">
            ₹{row.estimated_value.toLocaleString('en-IN')}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Stage',
      render: (row) => getStatusBadge(row.status),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (row) => getPriorityBadge(row.priority),
    },
    {
      key: 'follow_up',
      header: 'Next Follow-Up',
      render: (row) => {
        if (!row.next_follow_up) return <span className="text-slate-400">—</span>;
        const fDate = new Date(row.next_follow_up);
        const isPast = fDate < new Date() && row.status !== 'CONVERTED' && row.status !== 'LOST';
        return (
          <div className="flex items-center gap-1">
            <Calendar className={`w-3.5 h-3.5 ${isPast ? 'text-rose-500' : 'text-slate-400'}`} />
            <span className={isPast ? 'text-rose-600 font-semibold' : 'text-slate-600'}>
              {fDate.toLocaleDateString()}
            </span>
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (row) => (
        <Link
          href={`/crm/${row.id}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-[#315C45] hover:text-blue-800"
        >
          View
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      ),
    },
  ];

  if (!canRead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Access Restricted</h2>
        <p className="text-sm text-slate-600  mt-2">
          You do not possess the required <code>crm:read</code> permission to view CRM & Lead records.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white  border border-[#E7E5DE]  rounded-xl p-6 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900  tracking-tight">
            CRM & Lead Management
          </h1>
          <p className="text-xs text-slate-500  mt-1">
            Track inquiries, lead stages, customer follow-up schedules, and qualify prospects for{' '}
            <span className="font-semibold text-[#315C45] text-blue-400">
              {activeUnit ? activeUnit.replace('_', ' ') : 'All Units'}
            </span>.
          </p>
        </div>
        {canCreate && (
          <Button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 self-start md:self-auto"
          >
            <UserPlus className="w-4 h-4" />
            Add New Lead
          </Button>
        )}
      </div>

      {/* Dashboard Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#EAF0E9] bg-blue-950/40 text-[#315C45] text-blue-400 flex items-center justify-center shrink-0">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Total Leads</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {isMetricsLoading ? '—' : metrics?.total_leads ?? 0}
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {metrics?.active_leads ?? 0} active in pipeline
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-rose-50 bg-rose-950/40 text-rose-600 text-rose-400 flex items-center justify-center shrink-0">
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Hot Prospects</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {isMetricsLoading ? '—' : metrics?.hot_leads ?? 0}
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">High purchasing intent</p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 bg-amber-950/40 text-amber-600 text-amber-400 flex items-center justify-center shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Follow-Ups Due</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {isMetricsLoading ? '—' : metrics?.follow_ups_due_today ?? 0}
            </h3>
            <p className="text-[11px] text-rose-500 font-medium mt-0.5">
              {metrics?.follow_ups_overdue ?? 0} overdue
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 bg-emerald-950/40 text-emerald-600 text-emerald-400 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Converted Clients</p>
            <h3 className="text-2xl font-bold text-slate-900 ">
              {isMetricsLoading ? '—' : metrics?.converted_leads ?? 0}
            </h3>
            <p className="text-[11px] text-emerald-600 text-emerald-400 font-medium mt-0.5">
              {metrics?.conversion_rate_percentage ?? 0}% conversion rate
            </p>
          </div>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={(q) => {
          setSearchQuery(q);
          setPage(1);
        }}
        placeholder="Search by company, contact person, phone, or code..."
        onReset={() => {
          setSearchQuery('');
          setSelectedStatus('ALL');
          setSelectedPriority('ALL');
          setFollowUpFilter(undefined);
          setPage(1);
        }}
      >
        {/* Status Dropdown */}
        <select
          value={selectedStatus}
          onChange={(e) => {
            setSelectedStatus(e.target.value);
            setPage(1);
          }}
          className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700  focus:outline-none focus:ring-1 focus:ring-[#315C45]"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Priority Dropdown */}
        <select
          value={selectedPriority}
          onChange={(e) => {
            setSelectedPriority(e.target.value);
            setPage(1);
          }}
          className="px-2.5 py-1.5 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-700  focus:outline-none focus:ring-1 focus:ring-[#315C45]"
        >
          {PRIORITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Follow-up shortcut pills */}
        <div className="flex items-center gap-1 border-l border-[#E7E5DE]  pl-2">
          <button
            type="button"
            onClick={() => {
              setFollowUpFilter(followUpFilter === 'today' ? undefined : 'today');
              setPage(1);
            }}
            className={`px-2 py-1 text-[11px] rounded-md font-medium transition-colors ${followUpFilter === 'today'
              ? 'bg-amber-100 text-amber-800 bg-amber-950 text-amber-300'
              : 'text-slate-500 hover:bg-slate-100 '
              }`}
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => {
              setFollowUpFilter(followUpFilter === 'overdue' ? undefined : 'overdue');
              setPage(1);
            }}
            className={`px-2 py-1 text-[11px] rounded-md font-medium transition-colors ${followUpFilter === 'overdue'
              ? 'bg-rose-100 text-rose-800 bg-rose-950 text-rose-300'
              : 'text-slate-500 hover:bg-slate-100 '
              }`}
          >
            Overdue
          </button>
        </div>
      </FilterBar>

      {/* Lead Table */}
      <DataTable
        columns={columns}
        data={leads}
        isLoading={isLoadingLeads}
        keyExtractor={(r) => r.id}
        emptyTitle="No leads in pipeline"
        emptyDescription="There are currently no matching leads found for the selected filters."
      />

      {/* Pagination summary */}
      {totalLeads > pageSize && (
        <div className="flex items-center justify-between text-xs text-slate-500 px-2">
          <span>
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalLeads)} of {totalLeads} leads
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page * pageSize >= totalLeads}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Create Lead Modal */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Add New Lead Inquiry"
        description="Record initial inquiry details and set the first follow-up reminder."
        maxWidth="lg"
      >
        <form onSubmit={handleCreateLead} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Company Name *
              </label>
              <input
                type="text"
                required
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                placeholder="e.g. Apex Engineering Works"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Contact Person *
              </label>
              <input
                type="text"
                required
                value={formData.contact_person}
                onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                placeholder="e.g. Rajesh Sharma"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Phone Number *
              </label>
              <input
                type="tel"
                required
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="contact@apexeng.com"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Lead Source
              </label>
              <select
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value as LeadSource })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              >
                <option value="DIRECT_INQUIRY">Direct Inquiry</option>
                <option value="TRADE_EXPO">Trade Expo</option>
                <option value="WEBSITE">Website Form</option>
                <option value="REFERRAL">Client Referral</option>
                <option value="COLD_CALL">Cold Call / Outreach</option>
                <option value="EXISTING_CLIENT">Existing Client</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Lead Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value as LeadPriority })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              >
                <option value="HOT">Hot (Immediate Requirement)</option>
                <option value="WARM">Warm (Evaluating Options)</option>
                <option value="COLD">Cold (Long-term Interest)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Machine / Solution Interest
              </label>
              <input
                type="text"
                value={formData.machine_interest}
                onChange={(e) => setFormData({ ...formData, machine_interest: e.target.value })}
                placeholder="e.g. CNC Horizontal Milling 4-Axis"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Estimated Deal Value (₹)
              </label>
              <input
                type="number"
                min="0"
                value={formData.estimated_value}
                onChange={(e) => setFormData({ ...formData, estimated_value: Number(e.target.value) })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Manufacturing Unit
              </label>
              <select
                value={formData.unit_id}
                onChange={(e) => setFormData({ ...formData, unit_id: e.target.value as ManufacturingUnit })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              >
                <option value="Unit_1">Unit 1 — Heavy Machining</option>
                <option value="Unit_2">Unit 2 — Assembly &amp; QC</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Next Follow-up Reminder
              </label>
              <input
                type="datetime-local"
                value={formData.next_follow_up}
                onChange={(e) => setFormData({ ...formData, next_follow_up: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Initial Notes / Requirement Scope
            </label>
            <textarea
              rows={3}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Client reached out regarding custom machine build for Q3 production line..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
              disabled={createSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createSubmitting}>
              {createSubmitting ? 'Saving Lead...' : 'Create Lead'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
