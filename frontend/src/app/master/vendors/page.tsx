'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Vendor } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function VendorsPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    gstin: '',
    pan: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    payment_terms_days: 30,
    category: 'Raw Material',
    rating: 5.0,
    unit_id: 'BOTH',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<Vendor>('vendors', {
        page,
        page_size: pageSize,
        search: search || undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
      });
      setVendors(res.items);
      setTotal(res.total);
    } catch {
      // Empty state
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingVendor(null);
    setFormData({
      code: '',
      name: '',
      gstin: '',
      pan: '',
      contact_person: '',
      phone: '',
      email: '',
      address: '',
      payment_terms_days: 30,
      category: 'Raw Material',
      rating: 5.0,
      unit_id: 'BOTH',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (vendor: Vendor) => {
    setEditingVendor(vendor);
    setFormData({
      code: vendor.code,
      name: vendor.name,
      gstin: vendor.gstin || '',
      pan: vendor.pan || '',
      contact_person: vendor.contact_person || '',
      phone: vendor.phone || '',
      email: vendor.email || '',
      address: vendor.address || '',
      payment_terms_days: vendor.payment_terms_days,
      category: vendor.category || 'Raw Material',
      rating: vendor.rating || 5.0,
      unit_id: vendor.unit_id,
      is_active: vendor.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingVendor) {
        await masterClient.update<Vendor>('vendors', editingVendor.id, formData);
      } else {
        await masterClient.create<Vendor>('vendors', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save vendor record.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (vendor: Vendor) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('vendors', vendor.id, false);
      loadData();
    } catch {
      // error handled
    }
  };

  const columns: Column<Vendor>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (v: Vendor) => <span className="font-semibold text-neutral-900">{v.code}</span>,
    },
    {
      key: 'name',
      header: 'Vendor Name',
      render: (v: Vendor) => (
        <div>
          <div className="font-medium text-neutral-900">{v.name}</div>
          <div className="text-xs text-neutral-500">{v.category || 'General'}</div>
        </div>
      ),
    },
    {
      key: 'tax',
      header: 'Tax Info',
      render: (v: Vendor) => (
        <div className="text-xs">
          <div>GST: <span className="font-mono text-neutral-700">{v.gstin || 'Unregistered'}</span></div>
          <div>PAN: <span className="font-mono text-neutral-700">{v.pan || 'N/A'}</span></div>
        </div>
      ),
    },
    {
      key: 'contact',
      header: 'Contact',
      render: (v: Vendor) => (
        <div className="text-xs">
          <div>{v.contact_person || 'N/A'}</div>
          <div className="text-neutral-500">{v.phone || v.email || 'No phone'}</div>
        </div>
      ),
    },
    {
      key: 'terms',
      header: 'Payment Terms',
      render: (v: Vendor) => <span className="text-xs text-neutral-700">{v.payment_terms_days} Days</span>,
    },
    {
      key: 'rating',
      header: 'Rating',
      render: (v: Vendor) => (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
          ★ {v.rating || 5.0}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (v: Vendor) => (
        <Badge variant={v.is_active ? 'success' : 'neutral'} className="text-xs">
          {v.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (v: Vendor) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(v)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit Vendor"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(v)}
              className={`p-1 rounded transition-colors ${
                v.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
              }`}
              title={v.is_active ? 'Deactivate' : 'Activate'}
            >
              {v.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Supplier & Vendor Master</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Suppliers of raw materials, steel plates, hydraulic parts, tooling, and fabrication services.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={masterClient.getTemplateUrl('vendors')}
              download
              className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Import Template</span>
            </a>

            {canCreate && (
              <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                <Plus className="w-4 h-4" />
                <span>Add Vendor</span>
              </Button>
            )}
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          placeholder="Search vendor code or name..."
        >
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-[#E7E5DE]  rounded-lg px-2.5 py-2 bg-white "
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Inactive Only</option>
          </select>
        </FilterBar>

        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-sm">
          <DataTable
            columns={columns}
            data={vendors}
            isLoading={isLoading}
            emptyTitle="No vendors registered"
            emptyDescription="No suppliers or vendors found. Click 'Add Vendor' to register one."
            keyExtractor={(v) => v.id}
          />

          {total > pageSize && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
              <div>Total: {total} vendors</div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <span>Page {page} of {Math.ceil(total / pageSize)}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= Math.ceil(total / pageSize)}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>

        <Dialog
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={editingVendor ? `Edit Vendor (${editingVendor.code})` : 'Register New Vendor'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">
                  Vendor Code *
                </label>
                <input
                  type="text"
                  required
                  disabled={!!editingVendor}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. VEND-001"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase focus:ring-2 focus:ring-[#315C45] disabled:bg-neutral-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">
                  Vendor Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Gujarat Steel Tube Mills"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-[#315C45]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">GSTIN</label>
                <input
                  type="text"
                  value={formData.gstin}
                  onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="Raw Material, Hardware, Services"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Contact Person</label>
                <input
                  type="text"
                  value={formData.contact_person}
                  onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Phone</label>
                <input
                  type="text"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Address</label>
              <textarea
                rows={2}
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : editingVendor ? 'Update Vendor' : 'Register Vendor'}
              </Button>
            </div>
          </form>
        </Dialog>
      </div>
  );
}
