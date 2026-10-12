'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Customer } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function CustomersPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
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
    billing_address: '',
    shipping_address: '',
    credit_limit: 0,
    payment_terms_days: 30,
    unit_id: 'BOTH',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<Customer>('customers', {
        page,
        page_size: pageSize,
        search: search || undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
      });
      setCustomers(res.items);
      setTotal(res.total);
    } catch {
      // Handled
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingCustomer(null);
    setFormData({
      code: '',
      name: '',
      gstin: '',
      pan: '',
      contact_person: '',
      phone: '',
      email: '',
      billing_address: '',
      shipping_address: '',
      credit_limit: 0,
      payment_terms_days: 30,
      unit_id: 'BOTH',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (customer: Customer) => {
    setEditingCustomer(customer);
    setFormData({
      code: customer.code,
      name: customer.name,
      gstin: customer.gstin || '',
      pan: customer.pan || '',
      contact_person: customer.contact_person || '',
      phone: customer.phone || '',
      email: customer.email || '',
      billing_address: customer.billing_address || '',
      shipping_address: customer.shipping_address || '',
      credit_limit: customer.credit_limit,
      payment_terms_days: customer.payment_terms_days,
      unit_id: customer.unit_id,
      is_active: customer.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingCustomer) {
        await masterClient.update<Customer>('customers', editingCustomer.id, formData);
      } else {
        await masterClient.create<Customer>('customers', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save customer record. Please check code uniqueness.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (customer: Customer) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('customers', customer.id, false);
      loadData();
    } catch {
      // Handled
    }
  };

  const columns: Column<Customer>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (c: Customer) => <span className="font-semibold text-neutral-900">{c.code}</span>,
    },
    {
      key: 'name',
      header: 'Customer Name',
      render: (c: Customer) => (
        <div>
          <div className="font-medium text-neutral-900">{c.name}</div>
          <div className="text-xs text-neutral-500">{c.billing_address || 'No address'}</div>
        </div>
      ),
    },
    {
      key: 'tax',
      header: 'Tax Info',
      render: (c: Customer) => (
        <div className="text-xs">
          <div>GST: <span className="font-mono text-neutral-700">{c.gstin || 'Unregistered'}</span></div>
          <div>PAN: <span className="font-mono text-neutral-700">{c.pan || 'N/A'}</span></div>
        </div>
      ),
    },
    {
      key: 'contact',
      header: 'Contact',
      render: (c: Customer) => (
        <div className="text-xs">
          <div>{c.contact_person || 'N/A'}</div>
          <div className="text-neutral-500">{c.phone || c.email || 'No phone'}</div>
        </div>
      ),
    },
    {
      key: 'terms',
      header: 'Terms & Limit',
      render: (c: Customer) => (
        <div className="text-xs">
          <div>₹{c.credit_limit.toLocaleString('en-IN')}</div>
          <div className="text-neutral-500">{c.payment_terms_days} Days</div>
        </div>
      ),
    },
    {
      key: 'unit_id',
      header: 'Facility',
      render: (c: Customer) => (
        <Badge variant={c.unit_id === 'BOTH' ? 'neutral' : 'warning'} className="text-xs">
          {c.unit_id === 'Unit_1'
            ? 'Unit 1 (Machining)'
            : c.unit_id === 'Unit_2'
              ? 'Unit 2 (Assembly & QC)'
              : 'Both Facilities'}
        </Badge>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (c: Customer) => (
        <Badge variant={c.is_active ? 'success' : 'neutral'} className="text-xs">
          {c.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (c: Customer) => (
        <div className="flex items-center gap-2">
          {!canUpdate ? (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
              Read-only
            </span>
          ) : (
            <>
              <button
                onClick={() => handleOpenEdit(c)}
                className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
                title="Edit Customer"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleToggleStatus(c)}
                className={`p-1 rounded transition-colors ${c.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
                  }`}
                title={c.is_active ? 'Deactivate' : 'Activate'}
              >
                {c.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Customer Master</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Registered buyers, billing addresses, GST details, credit limits, and unit associations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={masterClient.getTemplateUrl('customers')}
            download
            className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            <span>Import Template</span>
          </a>

          {canCreate && (
            <Button onClick={handleOpenCreate} className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              <span>Add Customer</span>
            </Button>
          )}
        </div>
      </div>

      <FilterBar
        searchQuery={search}
        onSearchChange={setSearch}
        placeholder="Search customer code or name..."
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
          data={customers}
          isLoading={isLoading}
          emptyTitle="No customers found"
          emptyDescription="No customer records exist. Click 'Add Customer' or download the import template to migrate legacy records."
          keyExtractor={(c) => c.id}
        />

        {total > pageSize && (
          <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
            <div>Total: {total} customers</div>
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
        title={editingCustomer ? `Edit Customer (${editingCustomer.code})` : 'Create New Customer'}
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
                Customer Code *
              </label>
              <input
                type="text"
                required
                disabled={!!editingCustomer}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="e.g. CUST-001"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase focus:ring-2 focus:ring-[#315C45] disabled:bg-neutral-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Customer Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. Acme Hydraulics Ltd"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-[#315C45]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                GSTIN
              </label>
              <input
                type="text"
                value={formData.gstin}
                onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                placeholder="24AAAAA0000A1Z5"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase focus:ring-2 focus:ring-[#315C45]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                PAN
              </label>
              <input
                type="text"
                value={formData.pan}
                onChange={(e) => setFormData({ ...formData, pan: e.target.value.toUpperCase() })}
                placeholder="AAAAA0000A"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase focus:ring-2 focus:ring-[#315C45]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Contact Person
              </label>
              <input
                type="text"
                value={formData.contact_person}
                onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Phone
              </label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Credit Limit (₹)
              </label>
              <input
                type="number"
                min="0"
                value={formData.credit_limit}
                onChange={(e) => setFormData({ ...formData, credit_limit: Number(e.target.value) })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">
                Payment Terms (Days)
              </label>
              <input
                type="number"
                min="0"
                value={formData.payment_terms_days}
                onChange={(e) => setFormData({ ...formData, payment_terms_days: Number(e.target.value) })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1">
              Billing Address
            </label>
            <textarea
              rows={2}
              value={formData.billing_address}
              onChange={(e) => setFormData({ ...formData, billing_address: e.target.value })}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : editingCustomer ? 'Update Customer' : 'Create Customer'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
