import type { Metadata } from 'next';
import React, { Suspense } from 'react';
import '../styles/globals.css';
import { Footer } from '@/components/layout/Footer';
import { AuthProvider } from '@/context/AuthContext';
import { AppShell } from '@/components/layout/AppShell';

export const metadata: Metadata = {
  title: 'RG Tech ERP',
  description: 'Production-grade Manufacturing ERP System for RG Tech (Unit 1: Heavy Machining & Unit 2: Assembly & QC)',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-[#F8FAFC] text-[#0F172A] antialiased font-sans">
        <Suspense fallback={
          <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
            <div className="w-8 h-8 border-4 border-[#0F172A] border-t-transparent rounded-full animate-spin" />
          </div>
        }>
          <AuthProvider>
            <main className="flex-1 w-full">
              <AppShell>
                {children}
              </AppShell>
            </main>
            <Footer />
          </AuthProvider>
        </Suspense>
      </body>
    </html>
  );
}
