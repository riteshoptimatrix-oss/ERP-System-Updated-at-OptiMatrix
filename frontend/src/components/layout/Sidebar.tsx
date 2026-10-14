'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard,
  ShoppingCart,
  Boxes,
  Scroll,
  Cog,
  CheckCircle2,
  Trash2,
  Zap,
  Users2,
  IndianRupee,
  CalendarCheck,
  Send,
  LineChart,
  UserCog,
  Shield,
  History,
  Building2,
  LogOut,
  Search,
  ChevronDown,
  Sparkles,
  Layers,
  Factory,
  Users,
  Briefcase,
  User,
  CheckSquare,
  Bell,
  Receipt,
  Clock,
  Calendar,
  ClipboardList,
  Megaphone,
} from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  module: string;
  action: string;
  badge?: string;
  isEmployeePortal?: boolean;
}

interface NavGroup {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  items: NavItem[];
}

// Logically grouped enterprise navigation structure
const RAW_NAV_GROUPS: NavGroup[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: LayoutDashboard,
    items: [
      { name: 'Dashboard', href: '/', icon: LayoutDashboard, module: 'orders', action: 'read' },
    ],
  },
  {
    id: 'employee_workspace',
    label: 'My Workspace',
    icon: User,
    items: [
      { name: 'My Profile', href: '/employee/profile', icon: User, module: 'employee', action: 'read', isEmployeePortal: true },
      { name: 'My Attendance', href: '/employee/attendance', icon: CalendarCheck, module: 'employee', action: 'read', isEmployeePortal: true },
      { name: 'My Leaves', href: '/employee/leave', icon: Clock, module: 'employee', action: 'read', isEmployeePortal: true },
      { name: 'My Tasks', href: '/employee/tasks', icon: CheckSquare, module: 'employee', action: 'read', isEmployeePortal: true },
      { name: 'My Salary & Payslips', href: '/employee/payroll', icon: Receipt, module: 'employee', action: 'read', isEmployeePortal: true },
      { name: 'Announcements & Bulletins', href: '/announcements', icon: Megaphone, module: 'employee', action: 'read', isEmployeePortal: true },
    ],
  },
  {
    id: 'commercial',
    label: 'Commercial & Sales',
    icon: Briefcase,
    items: [
      { name: 'CRM & Leads', href: '/crm', icon: Users2, module: 'crm', action: 'read' },
      { name: 'Sales Orders & Dispatch', href: '/orders', icon: ShoppingCart, module: 'orders', action: 'read' },
      { name: 'Order Planning', href: '/orders?tab=planning', icon: ClipboardList, module: 'orders', action: 'read' },
    ],
  },
  {
    id: 'manufacturing',
    label: 'Manufacturing & Shop-Floor',
    icon: Factory,
    items: [
      { name: 'Inventory & Stock', href: '/inventory', icon: Boxes, module: 'inventory', action: 'read' },
      { name: 'Bill of Materials', href: '/bom', icon: Scroll, module: 'bom', action: 'read' },
      { name: 'Production & WIP', href: '/production', icon: Cog, module: 'production', action: 'read' },
      { name: 'Daily Production Planning', href: '/production?tab=daily', icon: ClipboardList, module: 'production', action: 'read' },
      { name: 'Wastage & Scrap', href: '/wastage', icon: Trash2, module: 'wastage', action: 'read' },
      { name: 'Power & Downtime', href: '/power', icon: Zap, module: 'power', action: 'read' },
    ],
  },
  {
    id: 'people',
    label: 'Human Resources',
    icon: Users,
    items: [
      { name: 'Employee Directory', href: '/hr', icon: Users2, module: 'hr', action: 'read' },
      { name: 'Daily Attendance', href: '/attendance', icon: CalendarCheck, module: 'hr', action: 'read' },
      { name: 'Leave Applications', href: '/attendance?tab=leaves', icon: Calendar, module: 'hr', action: 'read' },
      { name: 'Payroll & Salaries', href: '/payroll', icon: IndianRupee, module: 'hr', action: 'read' },
    ],
  },
  {
    id: 'management',
    label: 'Management & Governance',
    icon: Layers,
    items: [
      { name: 'Finance & Accounts', href: '/finance', icon: IndianRupee, module: 'finance', action: 'read' },
      { name: 'Reports & Analytics', href: '/reports', icon: LineChart, module: 'reports', action: 'read' },
      { name: 'Master Data Hub', href: '/master', icon: Building2, module: 'master', action: 'read' },
      { name: 'Excel Migration', href: '/master/import', icon: LineChart, module: 'master', action: 'create' },
      { name: 'User Management', href: '/users', icon: UserCog, module: 'users', action: 'read' },
      { name: 'Roles & RBAC', href: '/roles', icon: Shield, module: 'roles', action: 'read' },
      { name: 'Company Announcements', href: '/announcements', icon: Megaphone, module: 'users', action: 'read' },
      { name: 'Audit Logs', href: '/audit', icon: History, module: 'audit', action: 'read' },
    ],
  },
];

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const pathname = usePathname();
  const { user, hasPermission, activeUnit, setActiveUnit, canAccessUnit, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [isLeavesTab, setIsLeavesTab] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsLeavesTab(window.location.search.includes('tab=leaves'));
    }
  }, [pathname]);

  const toggleGroup = (groupId: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  // Filter groups and items strictly according to authorized permissions and search query
  const filteredGroups = useMemo(() => {
    if (!user) return [];

    const isHRUser =
      user.role === 'HR' ||
      user.account_type === 'HR' ||
      user.role === 'ADMIN' ||
      user.role === 'SUPER_ADMIN' ||
      user.department?.toUpperCase() === 'HR' ||
      user.department?.toLowerCase() === 'human resources' ||
      hasPermission('hr', 'read');

    return RAW_NAV_GROUPS
      .map((group) => {
        // Human Resources is strictly reserved for HR personnel and company administrators
        if (group.id === 'people' && !isHRUser) {
          return {
            ...group,
            items: [],
          };
        }

        const authorizedItems = group.items.filter((item) => {
          // Hide 'My Salary & Payslips' specifically for Super Admin
          if (user.role === 'SUPER_ADMIN' && item.href === '/employee/payroll') {
            return false;
          }

          const hasAccess = item.href === '/' || Boolean(item.isEmployeePortal) || hasPermission(item.module, item.action);
          if (!hasAccess) return false;
          if (!searchQuery.trim()) return true;
          return item.name.toLowerCase().includes(searchQuery.toLowerCase().trim());
        });
        return {
          ...group,
          items: authorizedItems,
        };
      })
      .filter((group) => group.items.length > 0);
  }, [user, hasPermission, searchQuery]);

  if (!user) return null;

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#202722]/30 backdrop-blur-xs md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed md:sticky top-16 bottom-0 left-0 z-40 w-68 shrink-0 bg-[#FFFFFF] border-r border-[#E2E8F0] flex flex-col h-[calc(100vh-4rem)] transition-transform duration-200 ease-in-out shadow-subtle ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
      >
        {/* Plant Facility Selector - only for plant/operational roles, hidden for HR */}
        {user?.role !== 'HR' && user?.account_type !== 'HR' && (
          <div className="p-3.5 border-b border-[#F1F5F9] bg-[#F8FAFC]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#64748B] font-mono flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-[#0F172A]" />
                Plant Scope
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[#0F172A] font-semibold border border-[#E2E8F0]">
                {activeUnit === 'Unit_1' ? 'UNIT 1' : activeUnit === 'Unit_2' ? 'UNIT 2' : 'ALL'}
              </span>
            </div>

            <div className="flex gap-1.5 bg-[#FFFFFF] p-1 rounded-xl border border-[#E2E8F0] shadow-2xs">
              <button
                type="button"
                onClick={() => setActiveUnit('Unit_1')}
                disabled={!canAccessUnit('Unit_1')}
                className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${activeUnit === 'Unit_1'
                  ? 'bg-[#0F172A] text-white shadow-xs font-bold'
                  : canAccessUnit('Unit_1')
                    ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
                    : 'opacity-35 cursor-not-allowed text-[#94A3B8]'
                  }`}
              >
                <Building2 className="h-3.5 w-3.5" />
                <span>Unit 1 (Machining)</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveUnit('Unit_2')}
                disabled={!canAccessUnit('Unit_2')}
                className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${activeUnit === 'Unit_2'
                  ? 'bg-[#0F172A] text-white shadow-xs font-bold'
                  : canAccessUnit('Unit_2')
                    ? 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
                    : 'opacity-35 cursor-not-allowed text-[#94A3B8]'
                  }`}
              >
                <Building2 className="h-3.5 w-3.5" />
                <span>Unit 2 (Assembly & QC)</span>
              </button>
            </div>
          </div>
        )}

        {/* Quick Navigation Search Filter */}
        <div className="px-3.5 pt-3 pb-1">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#64748B]">
              <Search className="h-3.5 w-3.5" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search modules (e.g. BOM, QC)..."
              className="w-full pl-8 pr-2.5 py-1.5 text-xs rounded-lg border border-[#E2E8F0] bg-[#FFFFFF] text-[#0F172A] placeholder-[#94A3B8] focus:outline-none focus:ring-1 focus:ring-[#0F172A] focus:border-[#0F172A] transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-[10px] text-[#64748B] hover:text-[#0F172A]"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Scrollable Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
          {filteredGroups.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#64748B]">
              <p>No matching modules found.</p>
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="mt-1.5 text-[11px] text-[#0F172A] font-semibold underline"
              >
                Reset search
              </button>
            </div>
          ) : (
            filteredGroups.map((group) => {
              const isCollapsed = Boolean(collapsedGroups[group.id]) && !searchQuery.trim();
              const GroupIcon = group.icon;

              return (
                <div key={group.id} className="space-y-1">
                  {/* Group Header */}
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.id)}
                    className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-semibold tracking-wider text-[#64748B] uppercase hover:text-[#0F172A] rounded transition-colors group"
                  >
                    <span className="flex items-center gap-1.5 font-mono">
                      <GroupIcon className="w-3 h-3 text-[#94A3B8] group-hover:text-[#0F172A] transition-colors" />
                      {group.label}
                    </span>
                    {!searchQuery && (
                      <ChevronDown
                        className={`w-3 h-3 text-[#94A3B8] transition-transform duration-200 ${isCollapsed ? '-rotate-90' : 'rotate-0'
                          }`}
                      />
                    )}
                  </button>

                  {/* Group Items */}
                  {!isCollapsed && (
                    <div className="space-y-0.5 pl-1">
                      {group.items.map((item) => {
                        const isActive = item.href.includes('?tab=leaves')
                          ? pathname === '/attendance' && isLeavesTab
                          : pathname === item.href && !(item.href === '/attendance' && isLeavesTab);
                        const Icon = item.icon;

                        return (
                          <Link
                            key={item.name}
                            href={item.href}
                            onClick={onClose}
                            className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all group ${isActive
                              ? 'bg-[#0F172A] text-white font-semibold shadow-xs'
                              : 'text-[#334155] hover:bg-[#F1F5F9] hover:text-[#0F172A]'
                              }`}
                          >
                            <div className="flex items-center gap-2.5 truncate">
                              <div
                                className={`p-1 rounded-md transition-colors ${isActive
                                  ? 'bg-[#1E293B] text-white'
                                  : 'bg-[#F1F5F9] text-[#64748B] group-hover:bg-[#E2E8F0] group-hover:text-[#0F172A]'
                                  }`}
                              >
                                <Icon className="h-3.5 w-3.5" />
                              </div>
                              <span className="truncate">{item.name}</span>
                            </div>

                            {isActive && (
                              <span className="w-1.5 h-1.5 rounded-full bg-white shrink-0 ml-2" />
                            )}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* User Session Bottom Card */}
        <div className="p-3 border-t border-[#F1F5F9] bg-[#F8FAFC]">
          <div className="p-2.5 rounded-xl bg-[#FFFFFF] border border-[#E2E8F0] shadow-2xs flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-[#0F172A] text-white flex items-center justify-center font-bold text-xs shrink-0 font-mono shadow-2xs">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 truncate">
                <p className="text-xs font-semibold text-[#0F172A] truncate leading-tight">
                  {user.full_name}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] text-[#475569] font-mono px-1 py-0.2 rounded bg-[#F1F5F9] border border-[#E2E8F0]">
                    {user.role}
                  </span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              title="Sign Out of Session"
              className="p-1.5 rounded-lg text-[#64748B] hover:text-[#B91C1C] hover:bg-[#FEE2E2] border border-transparent hover:border-[#B91C1C]/20 transition-all shrink-0"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

