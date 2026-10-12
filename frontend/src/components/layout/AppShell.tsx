'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { usePathname } from 'next/navigation';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const isAuthPage = pathname === '/login' || pathname === '/change-password';

  if (isLoading) {
    return (
      <div className="min-h-[500px] flex items-center justify-center bg-[#F8FAFC]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-4 border-[#0F172A] border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-[#64748B] font-medium">Verifying session...</p>
        </div>
      </div>
    );
  }

  // If user is on the login or change-password page, render full-bleed without the main dashboard header/sidebar
  if (isAuthPage) {
    return <>{children}</>;
  }

  // If unauthenticated on another route, render header and children
  if (!user) {
    return (
      <>
        <Header />
        {children}
      </>
    );
  }

  return (
    <>
      <Header onToggleSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} />
      {user.role === 'SUPER_ADMIN' && (
        <div className="bg-[#0F172A] text-white border-b border-neutral-700/60 px-4 py-2 sm:px-6">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-xs">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              </span>
              <span className="font-mono tracking-wider font-bold text-amber-400 uppercase text-[11px] bg-amber-950/60 border border-amber-500/30 px-2 py-0.5 rounded">
                READ-ONLY MONITORING
              </span>
              <span className="text-slate-200 font-medium">
                Super Admin (Owner) Executive Surveillance Mode
              </span>
            </div>
            <div className="text-slate-400 text-[11px] hidden sm:block">
              Full cross-unit read access (Unit 1 & 2) • Business mutations & approvals strictly prohibited
            </div>
          </div>
        </div>
      )}
      <div className="flex min-h-[calc(100vh-4rem)]">
        <Sidebar
          isOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />
        <div className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full overflow-x-hidden">
          <Breadcrumbs />
          {children}
        </div>
      </div>
    </>
  );
};
