'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  Cpu,
  Layers,
  Activity,
  ArrowRight
} from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Please enter both username/email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const result = await login(email, password);
    if (!result.success) {
      setErrorMessage(result.error || 'Authentication failed. Please verify your credentials.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#F7F6F2] text-[#202722]">
      {/* =========================================================================
          LEFT PANEL — Brand and Precision Industrial Identity (55–60% desktop width)
          ========================================================================= */}
      <section className="relative flex-1 lg:w-[58%] bg-[#F0EFE9] border-b lg:border-b-0 lg:border-r border-[#E6E4DC] p-8 sm:p-12 lg:p-16 flex flex-col justify-between overflow-hidden">
        {/* Subtle architectural background grid / precision lines */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.35]"
          style={{
            backgroundImage: `radial-gradient(#73786F 0.75px, transparent 0.75px), linear-gradient(to right, #E6E4DC 1px, transparent 1px), linear-gradient(to bottom, #E6E4DC 1px, transparent 1px)`,
            backgroundSize: `24px 24px, 72px 72px, 72px 72px`,
          }}
        />

        {/* Ambient warm gradient highlight */}
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#E8EEE7] blur-3xl pointer-events-none opacity-70" />

        {/* Top Header: Wordmark & Operational Badges */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* Minimalist Engineered Geometric Mark */}
            <div className="w-9 h-9 rounded-md bg-[#315C45] flex items-center justify-center text-white shadow-xs">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <span className="font-semibold text-base tracking-tight text-[#202722] block font-sans">
                RG TECH
              </span>
              <span className="text-[11px] font-medium tracking-wider text-[#73786F] uppercase block">
                Enterprise Operations
              </span>
            </div>
          </div>

          {/* Plant Unit Identification Badge */}
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#E8EEE7] text-[#315C45] border border-[#315C45]/20">
              <span className="w-1.5 h-1.5 rounded-full bg-[#315C45] animate-pulse" />
              Unit 1 &bull; Heavy Machining &amp; Fabrication
            </span>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#FFFFFF] text-[#73786F] border border-[#E6E4DC]">
              Unit 2 &bull; Precision Assembly &amp; QC
            </span>
          </div>
        </div>

        {/* Center: Editorial Industrial Typography & Technical Visual */}
        <div className="relative z-10 my-12 lg:my-auto max-w-xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#FFFFFF] border border-[#E6E4DC] text-[11px] font-mono font-medium text-[#73786F] mb-6 shadow-xs">
            <Activity className="w-3.5 h-3.5 text-[#315C45]" />
            <span>RG-TECH-ERP // Enterprise Operations</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-[44px] font-serif font-normal text-[#202722] leading-[1.15] tracking-tight">
            Precision in Production.
            <br />
            <span className="italic text-[#315C45] font-serif">Clarity in Every Operation.</span>
          </h1>

          <p className="mt-5 text-sm sm:text-base text-[#73786F] leading-relaxed max-w-lg font-sans">
            One connected workspace for manufacturing, inventory, quality, and enterprise operations. Designed for precision machinery engineering.
          </p>

          {/* Precision Architectural Composition (Refined CSS Line Structure) */}
          <div className="mt-8 p-5 rounded-xl bg-[#FFFFFF] border border-[#E6E4DC] shadow-xs">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[#F7F6F2] border border-[#E6E4DC] text-[#315C45] shrink-0">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-[#202722]">Integrated Manufacturing</h4>
                  <p className="text-[11px] text-[#73786F] mt-0.5 leading-snug">Multi-level BOM &amp; live WIP tracking</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[#F7F6F2] border border-[#E6E4DC] text-[#315C45] shrink-0">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-[#202722]">Real-Time Inventory</h4>
                  <p className="text-[11px] text-[#73786F] mt-0.5 leading-snug">Zero-discrepancy stock movement</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-[#F7F6F2] border border-[#E6E4DC] text-[#315C45] shrink-0">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-[#202722]">Unified Operations</h4>
                  <p className="text-[11px] text-[#73786F] mt-0.5 leading-snug">QC release &amp; balanced accounts</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-15 pt-6 border-t border-[#E6E4DC] flex flex-wrap items-center justify-between gap-2 text-xs text-[#73786F]">
          <h2><span>&copy; 2023 RG Tech Inc.</span></h2>
          <span className="font-mono text-[15px]">RG Tech Manufacturing ERP &bull; Dual-Facility Architecture</span>
        </div>
      </section>

      {/* =========================================================================
          RIGHT PANEL — Ultra-Premium Authentication Card (40–45% desktop width)
          ========================================================================= */}
      <section className="flex-1 lg:w-[42%] flex items-center justify-center p-6 sm:p-10 lg:p-14">
        <div className="w-full max-w-[420px]">
          {/* Card Container */}
          <div className="bg-[#FFFFFF] border border-[#E6E4DC] rounded-[20px] p-8 sm:p-10 shadow-card-elevated transition-all">
            {/* Header with Understated Brand Symbol */}
            <div className="mb-8">
              <div className="w-10 h-10 rounded-xl bg-[#E8EEE7] border border-[#315C45]/20 flex items-center justify-center text-[#315C45] mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="text-2xl font-semibold tracking-tight text-[#202722]">
                Welcome back
              </h2>
              <p className="text-xs sm:text-sm text-[#73786F] mt-1.5">
                Sign in to your RG Tech workspace.
              </p>
            </div>

            {/* Error Message Alert */}
            {errorMessage && (
              <div
                role="alert"
                className="mb-6 p-3.5 rounded-xl bg-[#FEF3F2] border border-[#FECDCA] flex items-start gap-3 text-xs text-[#B42318] animate-in fade-in duration-200"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#B42318]" />
                <span className="leading-relaxed font-medium">{errorMessage}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Username or Corporate Email */}
              <div className="space-y-1.5">
                <label
                  htmlFor="email-address"
                  className="block text-xs font-semibold text-[#202722] tracking-wide"
                >
                  Username or Corporate Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#73786F]">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    id="email-address"
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin or name@rgtech.com"
                    autoComplete="username"
                    required
                    disabled={isSubmitting}
                    className="block w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-[#E6E4DC] bg-[#FBFBF8] text-[#202722] placeholder-[#73786F]/60 transition-colors focus:bg-[#FFFFFF] focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:border-[#315C45] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-semibold text-[#202722] tracking-wide"
                >
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#73786F]">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    autoComplete="current-password"
                    required
                    disabled={isSubmitting}
                    className="block w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm rounded-xl border border-[#E6E4DC] bg-[#FBFBF8] text-[#202722] placeholder-[#73786F]/60 transition-colors focus:bg-[#FFFFFF] focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:border-[#315C45] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#73786F] hover:text-[#202722] transition-colors focus:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Primary Action Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-3 px-4 rounded-xl font-medium text-xs sm:text-sm text-white bg-[#315C45] hover:bg-[#254936] active:bg-[#1E3B2C] shadow-sm transition-all flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-[#315C45] focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <>
                    <span>Sign in to ERP</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Subtext info */}
              <div className="pt-3 text-center space-y-1.5">
                <p className="text-[11px] font-medium text-[#73786F] flex items-center justify-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#315C45]" />
                  Secure access for authorized personnel
                </p>
                <p className="text-[11px] text-[#73786F]/80">
                  Self-registration is disabled for security.
                </p>
              </div>
            </form>
          </div>

          {/* Understated bottom badge */}
          <div className="mt-6 text-center text-xs text-[#73786F]">
            <span>RG Tech ERP &bull; Protected by enterprise RBAC</span>
          </div>
        </div>
      </section>
    </div>
  );
}
