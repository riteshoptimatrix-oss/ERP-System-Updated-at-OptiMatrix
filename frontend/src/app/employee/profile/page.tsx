'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { employeeClient } from '@/services/employee-client';
import { EmployeeProfileResponse } from '@/types/employee';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  User,
  Mail,
  Phone,
  Building2,
  Briefcase,
  Calendar,
  CreditCard,
  ShieldAlert,
  Send,
  Lock,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { formatISTDate } from '@/lib/date';

export default function EmployeeProfilePage() {
  const [profile, setProfile] = useState<EmployeeProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showCorrectionModal, setShowCorrectionModal] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  // Correction request form state
  const [fieldName, setFieldName] = useState<string>('phone');
  const [requestedValue, setRequestedValue] = useState<string>('');
  const [reason, setReason] = useState<string>('');

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const data = await employeeClient.getProfile();
      setProfile(data);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load profile details');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleCorrectionSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!requestedValue.trim() || !reason.trim()) {
      setErrorMessage('Please provide both the corrected value and an explanatory reason.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      await employeeClient.submitProfileCorrection({
        field_name: fieldName,
        requested_value: requestedValue.trim(),
        reason: reason.trim(),
      });
      setSuccessMessage('Profile correction request submitted to HR successfully.');
      setShowCorrectionModal(false);
      setRequestedValue('');
      setReason('');
      await loadProfile();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-3 border-[#0F172A] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-[#64748B]">Loading your official employee profile...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] p-6 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
              Workforce Identity & Dossier
            </span>
            <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A] border-[#E2E8F0]">
              {profile?.employee_code || profile?.employee_id || 'ID Pending'}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            {profile?.full_name || 'Employee Profile'}
          </h1>
          <p className="text-xs text-[#64748B]">
            Official employment records, facility assignments, shift schedule, and compliance details.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadProfile}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setShowCorrectionModal(true)}
            className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            Request Data Correction
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Personal & Contact */}
        <div className="lg:col-span-2 space-y-6">
          {/* Official Personal Card */}
          <Card title="Employment & Identity Details">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs mt-2">
              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Full Legal Name</span>
                <span className="font-semibold text-[#0F172A] text-sm">
                  {profile?.full_name || '—'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Company Employee Code</span>
                <span className="font-mono font-bold text-[#0F172A] text-sm">
                  {profile?.employee_code || profile?.employee_id || 'Not assigned'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Official Work Email</span>
                <span className="font-medium text-[#0F172A] flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-[#64748B]" />
                  {profile?.email || '—'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Contact Phone</span>
                <span className="font-medium text-[#0F172A] flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-[#64748B]" />
                  {profile?.phone || 'Not provided'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Department</span>
                <span className="font-medium text-[#0F172A] flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-[#64748B]" />
                  {profile?.department || 'Operations'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Designation</span>
                <span className="font-medium text-[#0F172A]">
                  {profile?.designation || profile?.role || 'Team Member'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Joining Date</span>
                <span className="font-medium text-[#0F172A] flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-[#64748B]" />
                  {profile?.joining_date ? formatISTDate(profile.joining_date) : 'On record'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[11px] mb-1">Operational Facility</span>
                <span className="font-semibold text-[#0F172A] flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-[#64748B]" />
                  {profile?.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : profile?.unit_id === 'Unit_2' ? 'Unit 2 (Assembly & QC)' : 'Unit 1 & Unit 2'}
                </span>
              </div>
            </div>

            {/* Assigned Job Roles */}
            {profile?.job_roles && profile.job_roles.length > 0 && (
              <div className="mt-4 pt-4 border-t border-[#E2E8F0]">
                <span className="text-[11px] font-semibold text-[#64748B] uppercase tracking-wider block mb-2">
                  Assigned Operational Qualifications / Job Roles
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {profile.job_roles.map((jr: string) => (
                    <Badge key={jr} variant="neutral" className="bg-[#FFFFFF] border-[#CBD5E1] text-[#0F172A] font-medium text-xs py-1">
                      {jr}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Emergency & Workplace Contact */}
          <Card title="Emergency & Residential Contact">
            <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-xs">
              <span className="text-[#64748B] block text-[11px] mb-1">Emergency Contact Details</span>
              <span className="font-medium text-[#0F172A]">
                {profile?.emergency_contact || 'On record with HR Administration'}
              </span>
            </div>
          </Card>
        </div>

        {/* Right Column: Account Security & Shift */}
        <div className="space-y-6">
          {/* Shift Schedule */}
          <Card title="Working Shift Schedule">
            <div className="space-y-3 text-xs mt-1">
              <div className="flex items-center justify-between pb-2 border-b border-[#E2E8F0]">
                <span className="text-[#64748B]">Shift Type</span>
                <span className="font-mono font-bold text-[#0F172A]">
                  GENERAL (9:00 - 18:00)
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-[#E2E8F0]">
                <span className="text-[#64748B]">Grace Period</span>
                <span className="font-medium text-[#0F172A]">
                  15 minutes
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#64748B]">Standard Shift</span>
                <span className="font-bold text-[#0F172A]">
                  8.00 Hours / Day
                </span>
              </div>
            </div>
          </Card>

          {/* Account Security */}
          <Card title="Account Security">
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-[#E2E8F0]">
                <span className="text-[#64748B]">Auth Email</span>
                <span className="font-medium text-[#0F172A] truncate max-w-[150px]">
                  {profile?.email || '—'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-2 border-b border-[#E2E8F0]">
                <span className="text-[#64748B]">Account Role</span>
                <Badge variant="neutral" className="bg-[#F1F5F9] text-[#0F172A]">
                  {profile?.role || 'EMPLOYEE'}
                </Badge>
              </div>

              <div className="pt-2">
                <Link href="/change-password" className="w-full block">
                  <Button
                    variant="outline"
                    className="w-full text-xs flex items-center justify-center gap-1.5 border-[#CBD5E1] text-[#0F172A] hover:bg-[#F8FAFC]"
                  >
                    <Lock className="w-3.5 h-3.5" />
                    Change Account Password
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Profile Correction Request Modal */}
      {showCorrectionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#FFFFFF] rounded-2xl shadow-xl border border-[#E2E8F0] max-w-lg w-full p-6 animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-[#0F172A]" />
                <h3 className="text-base font-bold text-[#0F172A]">
                  Submit Profile Correction Request
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowCorrectionModal(false)}
                className="text-xs text-[#64748B] hover:text-[#0F172A] px-2 py-1 rounded"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4 mt-4 text-xs">
              <p className="text-[#64748B]">
                Changes to official personal information (phone, emergency contact, residential address) require verification and approval by HR operations.
              </p>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Field Requiring Correction
                </label>
                <select
                  value={fieldName}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFieldName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                >
                  <option value="phone">Phone Number</option>
                  <option value="emergency_contact">Emergency Contact Person & Phone</option>
                  <option value="address">Residential Address</option>
                  <option value="full_name">Legal Name Spelling</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Requested Accurate Value
                </label>
                <Input
                  value={requestedValue}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRequestedValue(e.target.value)}
                  placeholder="Enter updated contact or details..."
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Reason / Document Reference
                </label>
                <textarea
                  value={reason}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReason(e.target.value)}
                  rows={3}
                  placeholder="Explain why this correction is requested..."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCorrectionModal(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  {isSubmitting ? 'Submitting...' : 'Submit to HR'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
