'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { employeeClient } from '@/services/employee-client';
import { AnnouncementItem, AnnouncementRecipientOption } from '@/types/employee';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import {
  Megaphone,
  Plus,
  Search,
  Filter,
  RefreshCw,
  Trash2,
  Edit2,
  Users,
  UserCheck,
  Building,
  Shield,
  Eye,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Clock,
  Sparkles,
  Info,
  Check,
} from 'lucide-react';
import { formatISTDateTime, formatISTDate } from '@/lib/date';

export default function AnnouncementsManagementPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [recipients, setRecipients] = useState<AnnouncementRecipientOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [audienceFilter, setAudienceFilter] = useState<string>('all_filter');
  const [priorityFilter, setPriorityFilter] = useState<string>('all_filter');

  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<AnnouncementItem | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    title: '',
    message: '',
    priority: 'NORMAL' as 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT',
    unit_id: 'BOTH',
    audience_type: 'all' as 'all' | 'specific' | 'department' | 'role',
    selectedRecipients: [] as string[],
    departmentTarget: 'Production',
    roleTarget: 'HR',
    expires_at: '',
  });

  const departmentList = [
    'Production',
    'Production Department',
    'Quality Control',
    'Maintenance & Technical',
    'Inventory & Purchase',
    'Dispatch & Logistics',
    'Billing & Finance',
    'HR',
    'HR & Admin',
    'HR & Administration',
    'Sales & CRM',
    'Employee General',
  ];

  const roleList = [
    { value: 'SUPER_ADMIN', label: 'Super Admin' },
    { value: 'ADMIN', label: 'Admin' },
    { value: 'HR', label: 'HR' },
    { value: 'EMPLOYEE', label: 'Employee' },
    { value: 'PRODUCTION_MANAGER', label: 'Production Manager' },
    { value: 'INVENTORY_MANAGER', label: 'Inventory Manager' },
    { value: 'QC_INSPECTOR', label: 'QC Inspector' },
    { value: 'SALES_DISPATCH', label: 'Sales & Dispatch' },
  ];

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const promises: [Promise<AnnouncementItem[]>, Promise<AnnouncementRecipientOption[]>?] = [
        employeeClient.listAnnouncements({
          search: search.trim() || undefined,
          audienceType: audienceFilter !== 'all_filter' ? audienceFilter : undefined,
          priority: priorityFilter !== 'all_filter' ? priorityFilter : undefined,
        }),
      ];

      if (isSuperAdmin) {
        promises.push(employeeClient.listAnnouncementRecipients().catch(() => []));
      }

      const [anncs, recips] = await Promise.all(promises);
      setAnnouncements(anncs);
      if (recips) {
        setRecipients(recips);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load announcements');
    } finally {
      setIsLoading(false);
    }
  }, [search, audienceFilter, priorityFilter, isSuperAdmin]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreateModal = () => {
    setEditingItem(null);
    setFormData({
      title: '',
      message: '',
      priority: 'NORMAL',
      unit_id: 'BOTH',
      audience_type: 'all',
      selectedRecipients: [],
      departmentTarget: 'Production',
      roleTarget: 'HR',
      expires_at: '',
    });
    setErrorMessage('');
    setIsModalOpen(true);
  };

  const openEditModal = (item: AnnouncementItem) => {
    setEditingItem(item);
    setFormData({
      title: item.title,
      message: item.message || item.content || '',
      priority: item.priority,
      unit_id: item.unit_id,
      audience_type: item.audience_type || 'all',
      selectedRecipients: item.recipients || [],
      departmentTarget:
        item.audience_type === 'department' && item.recipients?.[0] ? item.recipients[0] : 'Production',
      roleTarget: item.audience_type === 'role' && item.recipients?.[0] ? item.recipients[0] : 'HR',
      expires_at: item.expires_at ? new Date(item.expires_at).toISOString().split('T')[0] : '',
    });
    setErrorMessage('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSuperAdmin) return;
    setIsSubmitting(true);
    setErrorMessage('');

    try {
      let finalRecipients: string[] = [];
      let finalRecipientNames: string[] = [];

      if (formData.audience_type === 'all') {
        finalRecipients = [];
      } else if (formData.audience_type === 'specific') {
        if (formData.selectedRecipients.length === 0) {
          throw new Error('Please select at least one employee or user recipient.');
        }
        finalRecipients = formData.selectedRecipients;
        finalRecipientNames = formData.selectedRecipients.map((id) => {
          const found = recipients.find((r) => r.id === id || r.code === id || r.email === id);
          return found ? `${found.name} (${found.code || found.email})` : id;
        });
      } else if (formData.audience_type === 'department') {
        finalRecipients = [formData.departmentTarget];
        finalRecipientNames = [`Department: ${formData.departmentTarget}`];
      } else if (formData.audience_type === 'role') {
        finalRecipients = [formData.roleTarget];
        finalRecipientNames = [`Role: ${formData.roleTarget}`];
      }

      if (editingItem) {
        await employeeClient.updateAnnouncement(editingItem.id, {
          title: formData.title,
          message: formData.message,
          priority: formData.priority,
          unit_id: formData.unit_id,
          audience_type: formData.audience_type,
          recipients: finalRecipients,
          recipient_names: finalRecipientNames,
          expires_at: formData.expires_at ? new Date(formData.expires_at).toISOString() : null,
        });
        setSuccessMessage('Announcement updated successfully!');
      } else {
        await employeeClient.createAnnouncement({
          title: formData.title,
          message: formData.message,
          priority: formData.priority,
          unit_id: formData.unit_id,
          audience_type: formData.audience_type,
          recipients: finalRecipients,
          recipient_names: finalRecipientNames,
          expires_at: formData.expires_at ? new Date(formData.expires_at).toISOString() : null,
        });
        setSuccessMessage('Announcement published successfully to target audience!');
      }

      setIsModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Action failed. Please check inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string, title: string) => {
    if (!isSuperAdmin) return;
    if (!confirm(`Are you sure you want to delete announcement "${title}"?`)) return;

    try {
      await employeeClient.deleteAnnouncement(id);
      setSuccessMessage('Announcement deleted.');
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to delete announcement');
    }
  };

  const toggleRecipient = (id: string) => {
    setFormData((prev) => {
      const exists = prev.selectedRecipients.includes(id);
      return {
        ...prev,
        selectedRecipients: exists
          ? prev.selectedRecipients.filter((x) => x !== id)
          : [...prev.selectedRecipients, id],
      };
    });
  };

  const filteredRecipients = useMemo(() => {
    return recipients;
  }, [recipients]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Off-white Hero Section */}
      <div className="p-6 sm:p-8 rounded-2xl bg-[#FAF8F5] border border-[#E7E5DE] shadow-xs relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#78716C] font-semibold bg-[#FFFFFF] px-2.5 py-1 rounded-md border border-[#E7E5DE]">
              Company Bulletins & Targeted Broadcasts
            </span>
            <Badge variant="neutral" className="text-[10px] bg-emerald-50 text-emerald-800 border-emerald-200">
              Live Gateway
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]">
            Corporate Announcements Command Center
          </h1>
          <p className="text-xs sm:text-sm text-[#57534E] max-w-2xl leading-relaxed">
            Publish company-wide announcements or send targeted notices to specific employees, HR, quality control, or custom departments with read tracking.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={isLoading}
            className="text-xs bg-[#FFFFFF] border-[#E7E5DE] text-[#0F172A] hover:bg-[#FAF8F5]"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {isSuperAdmin && (
            <Button
              onClick={openCreateModal}
              className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B] shadow-sm flex items-center gap-1.5 px-4 py-2"
            >
              <Plus className="w-4 h-4" />
              <span>Create Announcement</span>
            </Button>
          )}
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#E2E8F0] shadow-xs flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search headline, message, or author..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#CBD5E1] focus:outline-none focus:ring-2 focus:ring-[#0F172A]/20 focus:border-[#0F172A]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#64748B] font-medium">Audience:</span>
            <select
              value={audienceFilter}
              onChange={(e) => setAudienceFilter(e.target.value)}
              className="text-xs rounded-lg border border-[#CBD5E1] px-2.5 py-1.5 focus:outline-none focus:border-[#0F172A]"
            >
              <option value="all_filter">All Audiences</option>
              <option value="all">Company Wide (@All)</option>
              <option value="specific">Targeted Specific Employees</option>
              <option value="department">By Department</option>
              <option value="role">By Role</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#64748B] font-medium">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="text-xs rounded-lg border border-[#CBD5E1] px-2.5 py-1.5 focus:outline-none focus:border-[#0F172A]"
            >
              <option value="all_filter">All Priorities</option>
              <option value="LOW">Low</option>
              <option value="NORMAL">Normal</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>
        </div>
      </div>

      {/* Announcements List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-[#64748B] bg-[#FFFFFF] rounded-2xl border border-[#E2E8F0]">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0F172A]" />
            Loading announcements...
          </div>
        ) : announcements.length === 0 ? (
          <div className="p-12 text-center text-xs text-[#64748B] bg-[#FFFFFF] rounded-2xl border border-[#E2E8F0]">
            No announcements found matching the criteria.
          </div>
        ) : (
          announcements.map((ann) => {
            const isSpecific = ann.audience_type === 'specific';
            const isDept = ann.audience_type === 'department';
            const isRole = ann.audience_type === 'role';

            return (
              <div
                key={ann.id}
                className="p-5 sm:p-6 rounded-2xl bg-[#FFFFFF] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F1F5F9] pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Audience badge */}
                    {isSpecific ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-amber-50 text-amber-800 border border-amber-200">
                        <UserCheck className="w-3 h-3" />
                        Specific ({ann.recipient_names?.length || ann.recipients?.length || 1} Employee)
                      </span>
                    ) : isDept ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200">
                        <Building className="w-3 h-3" />
                        Dept: {ann.recipients?.[0] || 'Department'}
                      </span>
                    ) : isRole ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-purple-50 text-purple-800 border border-purple-200">
                        <Shield className="w-3 h-3" />
                        Role: {ann.recipients?.[0] || 'Role'}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <Users className="w-3 h-3" />
                        Company Wide (@All)
                      </span>
                    )}

                    <Badge
                      variant="neutral"
                      className={`text-[10px] ${
                        ann.priority === 'URGENT'
                          ? 'bg-rose-100 text-rose-800 border-rose-300 font-bold'
                          : ann.priority === 'HIGH'
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {ann.priority}
                    </Badge>

                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#F8FAFC] text-[#475569] border border-[#E2E8F0]">
                      {ann.unit_id === 'Unit_1'
                        ? 'Unit 1 (Machining)'
                        : ann.unit_id === 'Unit_2'
                        ? 'Unit 2 (Assembly)'
                        : 'All Facilities'}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-[#64748B]">
                    <span className="font-mono text-[11px]">
                      {formatISTDateTime(ann.published_at || ann.created_at)}
                    </span>

                    {isSuperAdmin && (
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => openEditModal(ann)}
                          className="p-1.5 text-[#475569] hover:text-[#0F172A] hover:bg-[#F1F5F9] rounded-lg transition-colors"
                          title="Edit Announcement"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(ann.id, ann.title)}
                          className="p-1.5 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete Announcement"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-bold text-[#0F172A]">{ann.title}</h3>
                  <p className="text-xs text-[#334155] mt-1.5 leading-relaxed whitespace-pre-line">
                    {ann.message || ann.content}
                  </p>
                </div>

                {/* Target recipients preview if specific */}
                {isSpecific && ann.recipient_names && ann.recipient_names.length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[#FAF8F5] border border-[#E7E5DE] text-[11px] text-[#57534E]">
                    <span className="font-semibold text-[#0F172A]">Targeted To: </span>
                    <span>{ann.recipient_names.join(', ')}</span>
                  </div>
                )}

                <div className="pt-2 text-[11px] text-[#64748B] flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span>Published by:</span>
                    <span className="font-semibold text-[#0F172A]">{ann.author_name}</span>
                    <span className="text-[#94A3B8]">({ann.author_role})</span>
                  </div>

                  {isSuperAdmin && typeof ann.read_count === 'number' && (
                    <div className="flex items-center gap-1 text-[11px] font-mono text-[#475569]">
                      <Eye className="w-3.5 h-3.5 text-[#0F172A]" />
                      <span>{ann.read_count} Acknowledgements</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Creation & Edit Dialog */}
      <Dialog
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingItem ? 'Edit Corporate Announcement' : 'Publish New Corporate Announcement'}
        description="Broadcast notices across all departments or target specific employees and job roles."
        maxWidth="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">
              Headline / Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              minLength={3}
              maxLength={150}
              placeholder="e.g., Mandatory Quality Checklist Updates or Unit 1 Machine Maintenance"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2.5 focus:outline-none focus:border-[#0F172A]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#0F172A] mb-1">
              Full Announcement Content <span className="text-rose-500">*</span>
            </label>
            <textarea
              required
              minLength={5}
              rows={4}
              placeholder="Type your official announcement or directive details here..."
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2.5 focus:outline-none focus:border-[#0F172A]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) =>
                  setFormData({ ...formData, priority: e.target.value as 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT' })
                }
                className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2 focus:outline-none focus:border-[#0F172A]"
              >
                <option value="LOW">Low</option>
                <option value="NORMAL">Normal</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Manufacturing Unit</label>
              <select
                value={formData.unit_id}
                onChange={(e) => setFormData({ ...formData, unit_id: e.target.value })}
                className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2 focus:outline-none focus:border-[#0F172A]"
              >
                <option value="BOTH">All Facilities (Unit 1 & 2)</option>
                <option value="Unit_1">Unit 1 (Machining)</option>
                <option value="Unit_2">Unit 2 (Assembly & QC)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F172A] mb-1">Expiry Date (Optional)</label>
              <input
                type="date"
                value={formData.expires_at}
                onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
                className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2 focus:outline-none focus:border-[#0F172A]"
              />
            </div>
          </div>

          {/* Audience Selection Selector */}
          <div className="space-y-2 pt-2 border-t border-[#E2E8F0]">
            <label className="block text-xs font-semibold text-[#0F172A]">
              Audience Targeting Mode <span className="text-rose-500">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, audience_type: 'all' })}
                className={`p-2.5 rounded-xl border text-left text-xs transition-all ${
                  formData.audience_type === 'all'
                    ? 'border-[#0F172A] bg-[#0F172A] text-white shadow-xs font-semibold'
                    : 'border-[#E2E8F0] bg-[#FFFFFF] text-[#475569] hover:bg-[#F8FAFC]'
                }`}
              >
                <Users className="w-4 h-4 mb-1" />
                <div className="font-medium text-xs">Everyone (@All)</div>
                <div className="text-[10px] opacity-80">All company staff</div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, audience_type: 'specific' })}
                className={`p-2.5 rounded-xl border text-left text-xs transition-all ${
                  formData.audience_type === 'specific'
                    ? 'border-[#0F172A] bg-[#0F172A] text-white shadow-xs font-semibold'
                    : 'border-[#E2E8F0] bg-[#FFFFFF] text-[#475569] hover:bg-[#F8FAFC]'
                }`}
              >
                <UserCheck className="w-4 h-4 mb-1" />
                <div className="font-medium text-xs">Specific Person</div>
                <div className="text-[10px] opacity-80">Pick employee/user</div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, audience_type: 'department' })}
                className={`p-2.5 rounded-xl border text-left text-xs transition-all ${
                  formData.audience_type === 'department'
                    ? 'border-[#0F172A] bg-[#0F172A] text-white shadow-xs font-semibold'
                    : 'border-[#E2E8F0] bg-[#FFFFFF] text-[#475569] hover:bg-[#F8FAFC]'
                }`}
              >
                <Building className="w-4 h-4 mb-1" />
                <div className="font-medium text-xs">Department</div>
                <div className="text-[10px] opacity-80">Target whole dept</div>
              </button>

              <button
                type="button"
                onClick={() => setFormData({ ...formData, audience_type: 'role' })}
                className={`p-2.5 rounded-xl border text-left text-xs transition-all ${
                  formData.audience_type === 'role'
                    ? 'border-[#0F172A] bg-[#0F172A] text-white shadow-xs font-semibold'
                    : 'border-[#E2E8F0] bg-[#FFFFFF] text-[#475569] hover:bg-[#F8FAFC]'
                }`}
              >
                <Shield className="w-4 h-4 mb-1" />
                <div className="font-medium text-xs">Job Role</div>
                <div className="text-[10px] opacity-80">e.g. HR, Production</div>
              </button>
            </div>
          </div>

          {/* Department Targeting Details */}
          {formData.audience_type === 'department' && (
            <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E7E5DE] space-y-2">
              <label className="block text-xs font-semibold text-[#0F172A]">Select Target Department</label>
              <select
                value={formData.departmentTarget}
                onChange={(e) => setFormData({ ...formData, departmentTarget: e.target.value })}
                className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2 bg-white focus:outline-none focus:border-[#0F172A]"
              >
                {departmentList.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Role Targeting Details */}
          {formData.audience_type === 'role' && (
            <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E7E5DE] space-y-2">
              <label className="block text-xs font-semibold text-[#0F172A]">Select Target Role / Designation</label>
              <select
                value={formData.roleTarget}
                onChange={(e) => setFormData({ ...formData, roleTarget: e.target.value })}
                className="w-full text-xs rounded-lg border border-[#CBD5E1] p-2 bg-white focus:outline-none focus:border-[#0F172A]"
              >
                {roleList.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Specific Recipient Picker */}
          {formData.audience_type === 'specific' && (
            <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E7E5DE] space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-[#0F172A]">
                  Select Employees or Users ({formData.selectedRecipients.length} selected)
                </label>
                {formData.selectedRecipients.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, selectedRecipients: [] })}
                    className="text-[11px] text-rose-600 hover:underline"
                  >
                    Clear All
                  </button>
                )}
              </div>

              <div className="max-h-52 overflow-y-auto divide-y divide-[#E7E5DE] border border-[#E7E5DE] rounded-lg bg-white">
                {filteredRecipients.map((recip) => {
                  const isChecked = formData.selectedRecipients.includes(recip.id);
                  return (
                    <div
                      key={recip.id}
                      onClick={() => toggleRecipient(recip.id)}
                      className={`p-2.5 flex items-center justify-between cursor-pointer text-xs transition-colors ${
                        isChecked ? 'bg-[#F1F5F9]' : 'hover:bg-[#FAF8F5]'
                      }`}
                    >
                      <div>
                        <div className="font-semibold text-[#0F172A] flex items-center gap-1.5">
                          <span>{recip.name}</span>
                          <span className="text-[10px] font-mono text-[#64748B]">({recip.code || recip.email})</span>
                        </div>
                        <div className="text-[11px] text-[#64748B]">
                          {recip.department} &bull; {recip.role}
                        </div>
                      </div>

                      <div
                        className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                          isChecked ? 'bg-[#0F172A] border-[#0F172A] text-white' : 'border-[#CBD5E1]'
                        }`}
                      >
                        {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
              disabled={isSubmitting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting}
              className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B]"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1.5" />
                  Publishing...
                </>
              ) : editingItem ? (
                'Save Changes'
              ) : (
                'Publish Announcement'
              )}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
