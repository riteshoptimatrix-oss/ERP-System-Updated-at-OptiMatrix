'use client';

import React, { useState, useId } from 'react';
import Image from 'next/image';
import { useAuth } from '@/context/AuthContext';
import {
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  LogOut,
  ArrowRight,
  ShieldAlert,
  Building2,
  UserCheck
} from 'lucide-react';

export default function ChangePasswordPage() {
  const { user, changePassword, logout } = useAuth();
  const currentPasswordId = useId();
  const newPasswordId = useId();
  const confirmPasswordId = useId();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Policy validation checks
  const isMinLength = newPassword.length >= 12;
  const isDifferentFromCurrent = newPassword.length > 0 && currentPassword.length > 0 && newPassword !== currentPassword;
  const isMatching = newPassword.length > 0 && confirmPassword.length > 0 && newPassword === confirmPassword;
  const isValid = isMinLength && (currentPassword.length === 0 || isDifferentFromCurrent) && isMatching;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!currentPassword) {
      setErrorMessage('Please enter your current initial password.');
      return;
    }

    if (!isMinLength) {
      setErrorMessage('New password must be at least 12 characters long.');
      return;
    }

    if (newPassword === currentPassword) {
      setErrorMessage('New password must be different from your current initial password.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('New password and confirmation do not match.');
      return;
    }

    setIsSubmitting(true);
    const result = await changePassword(currentPassword, newPassword, confirmPassword);

    if (result.success) {
      setSuccessMessage('Password changed successfully! Establishing secure session...');
      // AuthContext.changePassword handles redirect to dashboard after refreshing user
    } else {
      setErrorMessage(result.error || 'Failed to update password. Please check your credentials.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between bg-[#F7F6F2] text-[#202722]">
      {/* Top Header Bar */}
      <header className="border-b border-[#E6E4DC] bg-[#FFFFFF] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-auto flex items-center">
            <Image
              src="/logo.png"
              alt="Opti Matrix Logo"
              width={120}
              height={32}
              className="h-8 w-auto object-contain"
              priority
            />
          </div>
          <div className="border-l border-[#E6E4DC] pl-3">
            <span className="font-semibold text-sm tracking-tight text-[#202722]">Opti Matrix ERP</span>
          </div>
        </div>

        <button
          onClick={() => logout()}
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#73786F] hover:text-[#202722] hover:bg-[#F0EFE9] transition-colors border border-[#E6E4DC]"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign Out
        </button>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-xl bg-[#FFFFFF] rounded-xl border border-[#E6E4DC] shadow-sm overflow-hidden">
          {/* Banner / Notice Header */}
          <div className="bg-[#FAF9F5] border-b border-[#E6E4DC] p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#315C45]/10 border border-[#315C45]/20 flex items-center justify-center text-[#315C45] shrink-0 mt-0.5">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide uppercase bg-[#315C45]/10 text-[#315C45]">
                  Security Mandate
                </div>
                <h1 className="text-xl font-semibold tracking-tight text-[#202722]">
                  Set Your Secure Password
                </h1>
                <p className="text-xs sm:text-sm text-[#73786F] leading-relaxed">
                  Welcome to Opti Matrix ERP. Your account was provisioned with a temporary initial password.
                  To protect manufacturing operations and access your workspace, please create a new confidential password.
                </p>
              </div>
            </div>

            {/* User context card (safe metadata only) */}
            {user && (
              <div className="mt-4 pt-4 border-t border-[#E6E4DC]/60 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 text-[#202722] font-medium">
                  <UserCheck className="w-4 h-4 text-[#315C45]" />
                  <span>{user.full_name}</span>
                  <span className="text-[#73786F]">({user.email})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-[#F0EFE9] text-[#202722] font-mono text-[11px]">
                    {user.job_role || user.role}
                  </span>
                  {user.department && (
                    <span className="px-2 py-0.5 rounded bg-[#F0EFE9] text-[#73786F] text-[11px]">
                      {user.department}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Form Section */}
          <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-5">
            {/* Error Notification */}
            {errorMessage && (
              <div className="rounded-lg bg-red-50 border border-red-200 p-3.5 flex items-start gap-3 text-red-800 text-xs sm:text-sm">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <div className="flex-1">{errorMessage}</div>
              </div>
            )}

            {/* Success Notification */}
            {successMessage && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 flex items-start gap-3 text-emerald-800 text-xs sm:text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div className="flex-1">{successMessage}</div>
              </div>
            )}

            {/* Current Initial Password */}
            <div className="space-y-1.5">
              <label
                htmlFor={currentPasswordId}
                className="block text-xs font-semibold tracking-wide text-[#202722] uppercase"
              >
                Current Initial Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#73786F]">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id={currentPasswordId}
                  type={showCurrent ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter the initial password provided by HR"
                  autoComplete="current-password"
                  required
                  disabled={isSubmitting}
                  className="w-full pl-9 pr-10 py-2.5 bg-[#FAF9F5] border border-[#E6E4DC] rounded-lg text-sm text-[#202722] placeholder-[#73786F]/60 focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:border-transparent transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent(!showCurrent)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#73786F] hover:text-[#202722] transition-colors"
                  aria-label={showCurrent ? 'Hide current password' : 'Show current password'}
                >
                  {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="space-y-1.5">
              <label
                htmlFor={newPasswordId}
                className="block text-xs font-semibold tracking-wide text-[#202722] uppercase"
              >
                New Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#73786F]">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <input
                  id={newPasswordId}
                  type={showNew ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Create your new secure password (min 12 chars)"
                  autoComplete="new-password"
                  required
                  disabled={isSubmitting}
                  className="w-full pl-9 pr-10 py-2.5 bg-[#FAF9F5] border border-[#E6E4DC] rounded-lg text-sm text-[#202722] placeholder-[#73786F]/60 focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:border-transparent transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowNew(!showNew)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#73786F] hover:text-[#202722] transition-colors"
                  aria-label={showNew ? 'Hide new password' : 'Show new password'}
                >
                  {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Confirm New Password */}
            <div className="space-y-1.5">
              <label
                htmlFor={confirmPasswordId}
                className="block text-xs font-semibold tracking-wide text-[#202722] uppercase"
              >
                Confirm New Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#73786F]">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <input
                  id={confirmPasswordId}
                  type={showConfirm ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-type your new password"
                  autoComplete="new-password"
                  required
                  disabled={isSubmitting}
                  className="w-full pl-9 pr-10 py-2.5 bg-[#FAF9F5] border border-[#E6E4DC] rounded-lg text-sm text-[#202722] placeholder-[#73786F]/60 focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:border-transparent transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#73786F] hover:text-[#202722] transition-colors"
                  aria-label={showConfirm ? 'Hide confirmation password' : 'Show confirmation password'}
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Password Policy Checklist */}
            <div className="rounded-lg bg-[#FAF9F5] border border-[#E6E4DC] p-4 space-y-2">
              <p className="text-[11px] font-semibold tracking-wide text-[#73786F] uppercase">
                Password Security Requirements
              </p>
              <ul className="space-y-1.5 text-xs">
                <li className="flex items-center gap-2">
                  {isMinLength ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-[#73786F]/50 shrink-0" />
                  )}
                  <span className={isMinLength ? 'text-emerald-700 font-medium' : 'text-[#73786F]'}>
                    Minimum 12 characters long (passphrases & password managers recommended)
                  </span>
                </li>

                <li className="flex items-center gap-2">
                  {newPassword.length > 0 && isDifferentFromCurrent ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-[#73786F]/50 shrink-0" />
                  )}
                  <span className={newPassword.length > 0 && isDifferentFromCurrent ? 'text-emerald-700 font-medium' : 'text-[#73786F]'}>
                    Must be different from your initial temporary password
                  </span>
                </li>

                <li className="flex items-center gap-2">
                  {isMatching ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-[#73786F]/50 shrink-0" />
                  )}
                  <span className={isMatching ? 'text-emerald-700 font-medium' : 'text-[#73786F]'}>
                    Password confirmation matches exactly
                  </span>
                </li>
              </ul>
            </div>

            {/* Form Actions */}
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => logout()}
                disabled={isSubmitting}
                className="w-full sm:w-auto px-4 py-2.5 rounded-lg text-xs font-medium text-[#73786F] hover:text-[#202722] hover:bg-[#F0EFE9] transition-colors order-2 sm:order-1"
              >
                Cancel and Log Out
              </button>

              <button
                type="submit"
                disabled={isSubmitting || !isValid}
                className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg text-xs font-semibold text-white transition-all shadow-xs order-1 sm:order-2 ${isValid && !isSubmitting
                    ? 'bg-[#315C45] hover:bg-[#284a37] cursor-pointer'
                    : 'bg-[#315C45]/50 cursor-not-allowed'
                  }`}
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Updating Password...</span>
                  </>
                ) : (
                  <>
                    <span>Save Password & Enter ERP</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E6E4DC] bg-[#FFFFFF] px-6 py-3 text-center text-xs text-[#73786F]">
        <span>Opti Matrix Enterprise Resource Planning • Secure Authentication Gateway</span>
      </footer>
    </div>
  );
}
