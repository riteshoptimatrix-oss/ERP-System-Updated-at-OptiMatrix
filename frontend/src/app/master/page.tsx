'use client';

import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import {
  Users,
  Truck,
  UserSquare2,
  PackageCheck,
  Boxes,
  Ruler,
  Warehouse,
  Tags,
  Download,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { masterClient } from '@/services/master-client';
import { MasterEntityKey } from '@/types/master';

interface MasterModuleCard {
  title: string;
  description: string;
  href: string;
  entityKey: MasterEntityKey;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  badge: string;
}

export default function MasterDataHubPage() {
  const { hasPermission } = useAuth();
  const canRead = hasPermission('master', 'read');

  const modules: MasterModuleCard[] = [
    {
      title: 'Customer Master',
      description: 'Manage client accounts, GSTIN, PAN, billing & shipping addresses, payment terms, and credit limits.',
      href: '/master/customers',
      entityKey: 'customers',
      icon: Users,
      color: 'bg-[#EAF0E9] text-[#254936] border-[#315C45]/20',
      badge: 'Sales & Dispatch'
    },
    {
      title: 'Supplier & Vendor Master',
      description: 'Vendor profiles, GST registration, payment terms, quality ratings, and procurement categories.',
      href: '/master/vendors',
      entityKey: 'vendors',
      icon: Truck,
      color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      badge: 'Procurement'
    },
    {
      title: 'Employee Master',
      description: 'Workforce records, department assignments, designations, facility scoping (Unit 1 & Unit 2), and active status.',
      href: '/master/employees',
      entityKey: 'employees',
      icon: UserSquare2,
      color: 'bg-purple-50 text-purple-700 border-purple-200',
      badge: 'HR & Operations'
    },
    {
      title: 'Finished-Product Master',
      description: 'Finished machines, SKUs, engineering drawing numbers, revision control, costs, and selling prices.',
      href: '/master/products',
      entityKey: 'products',
      icon: PackageCheck,
      color: 'bg-amber-50 text-amber-700 border-amber-200',
      badge: 'Production & Sales'
    },
    {
      title: 'Raw-Material Master',
      description: 'Steel plates, hydraulic valves, seals, hardware, HSN/SAC codes, UoM, and reorder levels.',
      href: '/master/materials',
      entityKey: 'materials',
      icon: Boxes,
      color: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      badge: 'Inventory & BOM'
    },
    {
      title: 'Unit of Measure (UoM)',
      description: 'Standard units of measure (KG, MTR, PCS, SET, TON, LTR) with precision symbols.',
      href: '/master/uom',
      entityKey: 'uom',
      icon: Ruler,
      color: 'bg-slate-50 text-slate-700 border-[#E7E5DE]',
      badge: 'Standards'
    },
    {
      title: 'Warehouse & Storage Locations',
      description: 'Raw yards, WIP bays, racks, and finished goods depots with facility isolation (Unit 1 & Unit 2).',
      href: '/master/warehouses',
      entityKey: 'warehouses',
      icon: Warehouse,
      color: 'bg-orange-50 text-orange-700 border-orange-200',
      badge: 'Shop-Floor Logistics'
    },
    {
      title: 'Product & Material Categories',
      description: 'Structural classification for raw materials, finished products, assemblies, and consumables.',
      href: '/master/categories',
      entityKey: 'categories',
      icon: Tags,
      color: 'bg-rose-50 text-rose-700 border-rose-200',
      badge: 'Taxonomy'
    },
  ];

  if (!canRead) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center p-8 bg-white rounded-xl shadow-sm border border-neutral-200">
        <ShieldAlert className="w-12 h-12 text-amber-600 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-neutral-900">Access Restricted</h2>
        <p className="text-sm text-neutral-600 mt-2">
          You do not possess the required <code>master:read</code> permission to view Master Data records.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
        {/* Header Banner */}
        <div className="bg-white border border-neutral-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">
              Master Data Management
            </h1>
            <p className="text-sm text-neutral-600 mt-1 max-w-2xl">
              Centralized, unit-aware master registries for RG Tech. Maintained with duplicate prevention,
              strict validations, audit trails, and import template capabilities.
            </p>
          </div>
        </div>

        {/* Master Data Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {modules.map((m) => {
            const Icon = m.icon;
            return (
              <Card key={m.title} className="hover:shadow-md transition-shadow flex flex-col justify-between border-neutral-200">
                <div className="flex flex-col h-full justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${m.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-neutral-100 text-neutral-700 border border-neutral-200">
                        {m.badge}
                      </span>
                    </div>

                    <h3 className="font-semibold text-neutral-900 text-base">{m.title}</h3>
                    <p className="text-xs text-neutral-500 mt-2 line-clamp-3 leading-relaxed">
                      {m.description}
                    </p>
                  </div>

                  <div className="mt-5 pt-4 border-t border-neutral-100 flex items-center justify-between">
                    <a
                      href={masterClient.getTemplateUrl(m.entityKey)}
                      download
                      className="inline-flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-900 font-medium px-2 py-1 rounded hover:bg-neutral-100 transition-colors"
                      title="Download clean CSV Excel template"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Template</span>
                    </a>

                    <Link
                      href={m.href}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-[#315C45] hover:text-blue-800"
                    >
                      <span>Manage</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
  );
}
