'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { crmClient } from '@/services/crm-client';
import { Lead, LeadStatus, LeadPriority, ActivityType, LeadConvertPayload } from '@/types/crm';
import {
  ArrowLeft,
  Building2,
  Phone,
  Mail,
  Calendar,
  CheckCircle2,
  MessageSquare,
  Clock,
  UserCheck,
  Tag,
  AlertCircle,
  ExternalLink,
  ShieldAlert,
  Send,
  PhoneCall,
  Users,
  Compass,
} from 'lucide-react';

const STATUS_PROGRESS: LeadStatus[] = [
  'NEW',
  'CONTACTED',
  'QUALIFIED',
  'PROPOSAL_SENT',
  'NEGOTIATION',
  'CONVERTED',
];

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const leadId = params?.id as string;

  const { hasPermission, user } = useAuth();
  const canRead = hasPermission('crm', 'read');
  const canUpdate = hasPermission('crm', 'update');

  const [lead, setLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Activity Modal State
  const [isActivityOpen, setIsActivityOpen] = useState(false);
  const [activitySubmitting, setActivitySubmitting] = useState(false);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [activityForm, setActivityForm] = useState({
    activity_type: 'CALL' as ActivityType,
    summary: '',
    details: '',
    next_follow_up: '',
  });

  // Convert to Customer Modal State
  const [isConvertOpen, setIsConvertOpen] = useState(false);
  const [convertSubmitting, setConvertSubmitting] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);
  const [convertPayload, setConvertPayload] = useState<LeadConvertPayload>({
    customer_code: '',
    gstin: '',
    pan: '',
    billing_address: '',
    shipping_address: '',
    credit_limit: 500000,
    payment_terms_days: 30,
    unit_id: 'Unit_1',
  });

  // Load Lead data with timeline
  const loadLead = useCallback(async () => {
    if (!leadId || !canRead) return;
    try {
      setIsLoading(true);
      setError(null);
      const data = await crmClient.getLead(leadId);
      setLead(data);
      // Pre-fill conversion payload
      setConvertPayload((prev) => ({
        ...prev,
        customer_code: `CUST-${data.code.replace('LEAD-', '')}`,
        unit_id: data.unit_id,
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch lead details';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [leadId, canRead]);

  useEffect(() => {
    loadLead();
  }, [loadLead]);

  // Stage change quick action
  const handleStageChange = async (newStatus: LeadStatus) => {
    if (!lead || !canUpdate) return;
    try {
      await crmClient.updateLead(lead.id, { status: newStatus });
      await loadLead();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Stage transition failed');
    }
  };

  // Submit Activity
  const handleLogActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lead || !activityForm.summary.trim()) return;
    try {
      setActivitySubmitting(true);
      setActivityError(null);
      await crmClient.addActivity(lead.id, {
        ...activityForm,
        next_follow_up: activityForm.next_follow_up
          ? new Date(activityForm.next_follow_up).toISOString()
          : undefined,
      });
      setIsActivityOpen(false);
      setActivityForm({
        activity_type: 'CALL',
        summary: '',
        details: '',
        next_follow_up: '',
      });
      await loadLead();
    } catch (err: unknown) {
      setActivityError(err instanceof Error ? err.message : 'Failed to log interaction');
    } finally {
      setActivitySubmitting(false);
    }
  };

  // Convert Lead to Customer
  const handleConvertLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lead || !convertPayload.customer_code.trim()) return;
    try {
      setConvertSubmitting(true);
      setConvertError(null);
      const res = await crmClient.convertLead(lead.id, {
        customer_code: convertPayload.customer_code.trim() || `CUST-${lead.code.replace('LEAD-', '')}`,
        gstin: convertPayload.gstin?.trim() || undefined,
        pan: convertPayload.pan?.trim() || undefined,
        billing_address: convertPayload.billing_address?.trim() || undefined,
        shipping_address: convertPayload.shipping_address?.trim() || undefined,
        credit_limit: Number(convertPayload.credit_limit) || 0,
        payment_terms_days: Number(convertPayload.payment_terms_days) || 30,
        unit_id: convertPayload.unit_id || 'Unit_1',
      });
      setIsConvertOpen(false);
      await loadLead();
      alert(`Lead successfully converted to Customer Master: ${res.customer_code}`);
    } catch (err: unknown) {
      setConvertError(err instanceof Error ? err.message : 'Conversion failed');
    } finally {
      setConvertSubmitting(false);
    }
  };

  const getActivityIcon = (type: ActivityType) => {
    switch (type) {
      case 'CALL':
        return <PhoneCall className="w-4 h-4 text-blue-500" />;
      case 'EMAIL':
        return <Send className="w-4 h-4 text-indigo-500" />;
      case 'MEETING':
        return <Users className="w-4 h-4 text-purple-500" />;
      case 'SITE_VISIT':
        return <Compass className="w-4 h-4 text-emerald-500" />;
      case 'STATUS_CHANGE':
        return <CheckCircle2 className="w-4 h-4 text-amber-500" />;
      default:
        return <MessageSquare className="w-4 h-4 text-slate-500" />;
    }
  };

  if (!canRead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Access Restricted</h2>
        <p className="text-sm text-slate-600  mt-2">
          You do not possess the required <code>crm:read</code> permission to view this lead.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="w-8 h-8 border-2 border-[#315C45] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading lead details & activity timeline...</p>
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white  rounded-xl shadow-sm border border-[#E7E5DE] ">
        <AlertCircle className="w-12 h-12 text-rose-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-900 ">Lead Not Found</h2>
        <p className="text-sm text-slate-600  mt-2">
          {error || 'The requested lead record could not be loaded.'}
        </p>
        <div className="mt-6">
          <Button onClick={() => router.push('/crm')}>Return to Leads Hub</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Link & Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/crm"
            className="p-2 rounded-lg border border-[#E7E5DE]  hover:bg-slate-50  text-slate-600  transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900  tracking-tight">
                {lead.company_name}
              </h1>
              <Badge variant={lead.priority === 'HOT' ? 'error' : lead.priority === 'WARM' ? 'warning' : 'neutral'}>
                {lead.priority}
              </Badge>
              <Badge variant={lead.status === 'CONVERTED' ? 'success' : lead.status === 'LOST' ? 'error' : 'warning'}>
                {lead.status.replace('_', ' ')}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Lead Code: <span className="font-semibold text-slate-700 ">{lead.code}</span> • Assigned to {lead.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : lead.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'All Units'}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {canUpdate && lead.status !== 'CONVERTED' && (
            <>
              <Button variant="outline" onClick={() => setIsActivityOpen(true)}>
                <Clock className="w-4 h-4 mr-1.5" />
                Log Interaction
              </Button>

              <Button
                onClick={() => setIsConvertOpen(true)}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <UserCheck className="w-4 h-4 mr-1.5" />
                Convert to Customer
              </Button>
            </>
          )}

          {lead.status === 'CONVERTED' && lead.converted_customer_id && (
            <Link href="/master/customers">
              <Button variant="outline" className="text-emerald-700 border-emerald-300 bg-emerald-50">
                <ExternalLink className="w-4 h-4 mr-1.5" />
                View Customer Record
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Pipeline Stage Bar */}
      <Card className="p-4 bg-white ">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
          <span>Pipeline Progression</span>
          <span>Current Stage: <span className="text-[#315C45] text-blue-400 font-bold">{lead.status}</span></span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
          {STATUS_PROGRESS.map((stage, idx) => {
            const currentIdx = STATUS_PROGRESS.indexOf(lead.status);
            const isPast = idx < currentIdx;
            const isCurrent = lead.status === stage;
            return (
              <button
                key={stage}
                type="button"
                disabled={!canUpdate || lead.status === 'CONVERTED'}
                onClick={() => handleStageChange(stage)}
                className={`px-3 py-2 rounded-lg text-xs font-medium text-center transition-all ${isCurrent
                  ? 'bg-[#315C45] text-white font-bold shadow-sm ring-2 ring-blue-500 ring-offset-2'
                  : isPast
                    ? 'bg-[#EAF0E9] bg-blue-950/40 text-[#254936] text-blue-300 border border-[#315C45]/20 border-blue-800'
                    : 'bg-slate-50  text-slate-500 hover:bg-slate-100 '
                  }`}
              >
                {stage.replace('_', ' ')}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Lead Profile Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Lead Info Cards */}
        <div className="space-y-6">
          <Card className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900  border-b border-[#EFEEE8]  pb-2">
              Contact & Company Profile
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Contact Person</span>
                <div className="font-semibold text-slate-800 ">
                  {lead.contact_person}
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Phone Number</span>
                <div className="flex items-center gap-2 font-medium text-slate-800 ">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <a href={`tel:${lead.phone}`} className="hover:underline">
                    {lead.phone}
                  </a>
                </div>
              </div>

              {lead.email && (
                <div>
                  <span className="text-slate-400 block mb-0.5">Email Address</span>
                  <div className="flex items-center gap-2 font-medium text-slate-800 ">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <a href={`mailto:${lead.email}`} className="hover:underline">
                      {lead.email}
                    </a>
                  </div>
                </div>
              )}

              <div>
                <span className="text-slate-400 block mb-0.5">Lead Acquisition Source</span>
                <div className="font-medium text-slate-700 ">
                  {lead.source.replace('_', ' ')}
                </div>
              </div>
            </div>
          </Card>

          <Card className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900  border-b border-[#EFEEE8]  pb-2">
              Machinery Requirements & Value
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Machine Interest</span>
                <div className="font-semibold text-slate-800 ">
                  {lead.machine_interest || 'General Custom Machine Tooling'}
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Estimated Potential Deal Value</span>
                <div className="text-lg font-bold text-emerald-600 text-emerald-400">
                  ₹{lead.estimated_value.toLocaleString('en-IN')}
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Next Follow-Up Reminder</span>
                <div className="flex items-center gap-1.5 font-medium text-amber-600">
                  <Calendar className="w-3.5 h-3.5" />
                  {lead.next_follow_up
                    ? new Date(lead.next_follow_up).toLocaleString()
                    : 'No follow-up scheduled'}
                </div>
              </div>

              {lead.notes && (
                <div>
                  <span className="text-slate-400 block mb-0.5">Requirement Notes</span>
                  <p className="text-slate-600  bg-slate-50 /50 p-2.5 rounded-lg text-xs leading-relaxed">
                    {lead.notes}
                  </p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Activity History Timeline */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <div className="flex items-center justify-between border-b border-[#EFEEE8]  pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[#315C45]" />
                <h3 className="text-sm font-bold text-slate-900 ">
                  Activity & Interaction Timeline
                </h3>
              </div>
              {canUpdate && lead.status !== 'CONVERTED' && (
                <Button size="sm" variant="outline" onClick={() => setIsActivityOpen(true)}>
                  + Log Activity
                </Button>
              )}
            </div>

            {!lead.activities || lead.activities.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                No interactions or calls recorded yet for this prospect.
              </div>
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 before:bg-slate-800">
                {lead.activities.map((act) => (
                  <div key={act.id} className="relative group">
                    {/* Timeline icon dot */}
                    <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-white  border-2 border-[#315C45] flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#EAF0E9]0" />
                    </div>

                    <div className="bg-slate-50 /50 rounded-xl p-3 border border-[#EFEEE8] ">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2">
                          {getActivityIcon(act.activity_type)}
                          <span className="font-semibold text-xs text-slate-900 ">
                            {act.summary}
                          </span>
                          <Badge variant="neutral" className="text-[10px]">
                            {act.activity_type}
                          </Badge>
                        </div>
                        <span className="text-[11px] text-slate-400">
                          {new Date(act.created_at).toLocaleString()}
                        </span>
                      </div>

                      {act.details && (
                        <p className="text-xs text-slate-600  mt-1">
                          {act.details}
                        </p>
                      )}

                      {act.next_follow_up && (
                        <div className="mt-2 pt-2 border-t border-[#E7E5DE]  flex items-center gap-1.5 text-[11px] text-amber-600">
                          <Clock className="w-3 h-3" />
                          Next action set for: {new Date(act.next_follow_up).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Log Activity Modal */}
      <Dialog
        isOpen={isActivityOpen}
        onClose={() => setIsActivityOpen(false)}
        title="Log Interaction or Follow-Up"
        description="Record phone call notes, meetings, or emails and set the next reminder."
        maxWidth="md"
      >
        <form onSubmit={handleLogActivity} className="space-y-4">
          {activityError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{activityError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Interaction Type *
            </label>
            <select
              value={activityForm.activity_type}
              onChange={(e) =>
                setActivityForm({ ...activityForm, activity_type: e.target.value as ActivityType })
              }
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            >
              <option value="CALL">Phone Call</option>
              <option value="EMAIL">Email Discussion</option>
              <option value="MEETING">In-Person Meeting</option>
              <option value="SITE_VISIT">Client Site Inspection</option>
              <option value="NOTE">General Progress Note</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Summary / Headline *
            </label>
            <input
              type="text"
              required
              value={activityForm.summary}
              onChange={(e) => setActivityForm({ ...activityForm, summary: e.target.value })}
              placeholder="e.g. Discussed machine specs with Chief Engineer"
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Discussion Details
            </label>
            <textarea
              rows={3}
              value={activityForm.details}
              onChange={(e) => setActivityForm({ ...activityForm, details: e.target.value })}
              placeholder="Client requested custom motor mounting drawing and updated quote..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Next Follow-Up Date & Time
            </label>
            <input
              type="datetime-local"
              value={activityForm.next_follow_up}
              onChange={(e) => setActivityForm({ ...activityForm, next_follow_up: e.target.value })}
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsActivityOpen(false)}
              disabled={activitySubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={activitySubmitting}>
              {activitySubmitting ? 'Saving...' : 'Log Activity'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Convert to Customer Modal */}
      <Dialog
        isOpen={isConvertOpen}
        onClose={() => setIsConvertOpen(false)}
        title="Convert Lead to Customer Master"
        description="Transfer qualified prospect into an official Customer Master record with unique code verification."
        maxWidth="lg"
      >
        <form onSubmit={handleConvertLead} className="space-y-4">
          {convertError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{convertError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Customer Code * (Must be Unique)
              </label>
              <input
                type="text"
                required
                value={convertPayload.customer_code}
                onChange={(e) =>
                  setConvertPayload({ ...convertPayload, customer_code: e.target.value })
                }
                placeholder="CUST-2026-0001"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45] uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                GSTIN Number
              </label>
              <input
                type="text"
                value={convertPayload.gstin || ''}
                onChange={(e) => setConvertPayload({ ...convertPayload, gstin: e.target.value })}
                placeholder="27ABCDE1234F1Z5"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45] uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                PAN Number
              </label>
              <input
                type="text"
                value={convertPayload.pan || ''}
                onChange={(e) => setConvertPayload({ ...convertPayload, pan: e.target.value })}
                placeholder="ABCDE1234F"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45] uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Credit Limit (₹)
              </label>
              <input
                type="number"
                min="0"
                value={convertPayload.credit_limit}
                onChange={(e) =>
                  setConvertPayload({ ...convertPayload, credit_limit: Number(e.target.value) })
                }
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Payment Terms (Days)
              </label>
              <input
                type="number"
                min="0"
                value={convertPayload.payment_terms_days}
                onChange={(e) =>
                  setConvertPayload({
                    ...convertPayload,
                    payment_terms_days: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700  mb-1">
                Assigned Unit
              </label>
              <input
                type="text"
                disabled
                value={
                  convertPayload.unit_id === 'Unit_1'
                    ? 'Unit 1 (Machining)'
                    : convertPayload.unit_id === 'Unit_2'
                      ? 'Unit 2 (Assembly & QC)'
                      : 'All Units'
                }
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-slate-100  text-slate-500 cursor-not-allowed font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700  mb-1">
              Billing Address
            </label>
            <textarea
              rows={2}
              value={convertPayload.billing_address || ''}
              onChange={(e) =>
                setConvertPayload({ ...convertPayload, billing_address: e.target.value })
              }
              placeholder="Factory / Registered office address"
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E7E5DE]  bg-white  text-slate-900  focus:outline-none focus:ring-2 focus:ring-[#315C45]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#EFEEE8] ">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsConvertOpen(false)}
              disabled={convertSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={convertSubmitting}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {convertSubmitting ? 'Converting...' : 'Complete Conversion'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
