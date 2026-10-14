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

  // If user is on the login or change-password page, render immediately without blocking on session check
  if (isAuthPage) {
    return <>{children}</>;
  }

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
