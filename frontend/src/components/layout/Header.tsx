'use client';

import React from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/Badge';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/Button';
import { LogOut, UserCircle, Eye } from 'lucide-react';

export interface HeaderProps {
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { user, isAuthenticated, logout, activeUnit, setActiveUnit, canAccessUnit } = useAuth();

  return (
    <header className="border-b border-[#E2E8F0] bg-[#FFFFFF] sticky top-0 z-50 shadow-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {isAuthenticated && onToggleSidebar && (
            <button
              type="button"
              onClick={onToggleSidebar}
              className="md:hidden p-2 rounded-lg text-[#475569] hover:bg-[#F1F5F9] hover:text-[#0F172A] focus:outline-none"
              title="Open Navigation Menu"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          <Link href="/" className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-[#0F172A] flex items-center justify-center text-white font-bold text-sm shadow-xs tracking-tight">
              RG
            </div>
            <div>
              <h1 className="text-base font-semibold text-[#0F172A] leading-tight">
                RG Tech
              </h1>
              <p className="text-xs text-[#64748B]">
                Manufacturing Operations ERP
              </p>
            </div>
          </Link>
        </div>

        <div className="flex items-center space-x-3">
          {isAuthenticated && user ? (
            <div className="flex items-center space-x-3">
              {/* Plant Switcher in Top Navigation - only for plant/operational roles, hidden for HR */}
              {user.role !== 'HR' && user.account_type !== 'HR' && (
                <div className="hidden sm:flex items-center space-x-1 bg-[#F1F5F9] border border-[#E2E8F0] p-1 rounded-lg text-xs font-semibold">
                  <button
                    type="button"
                    onClick={() => setActiveUnit('Unit_1')}
                    disabled={!canAccessUnit('Unit_1')}
                    className={`px-3 py-1 rounded-md transition-all ${activeUnit === 'Unit_1'
                      ? 'bg-[#0F172A] text-white shadow-xs font-bold'
                      : canAccessUnit('Unit_1')
                        ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#FFFFFF]'
                        : 'opacity-40 cursor-not-allowed'
                      }`}
                  >
                    Unit 1 (Machining)
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveUnit('Unit_2')}
                    disabled={!canAccessUnit('Unit_2')}
                    className={`px-3 py-1 rounded-md transition-all ${activeUnit === 'Unit_2'
                      ? 'bg-[#0F172A] text-white shadow-xs font-bold'
                      : canAccessUnit('Unit_2')
                        ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#FFFFFF]'
                        : 'opacity-40 cursor-not-allowed'
                      }`}
                  >
                    Unit 2 (Assembly & QC)
                  </button>
                </div>
              )}

              <div className="hidden lg:flex items-center space-x-2 text-xs text-[#475569]">
                <UserCircle className="h-4 w-4 text-[#0F172A]" />
                <span className="font-semibold text-[#0F172A]">{user.full_name}</span>
                {user.role === 'SUPER_ADMIN' ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-100 text-amber-900 border border-amber-300">
                    <Eye className="h-3 w-3 text-amber-700" />
                    Read-Only Owner
                  </span>
                ) : (
                  <Badge variant="neutral">{user.role}</Badge>
                )}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-1.5 text-xs text-[#B91C1C] border-[#E2E8F0] hover:bg-[#FEE2E2] hover:border-[#B91C1C]/30"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          ) : (
            <Link href="/login">
              <Button variant="primary" size="sm" className="text-xs">
                Employee Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
