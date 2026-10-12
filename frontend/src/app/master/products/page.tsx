'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { FinishedProduct } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function ProductsPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [products, setProducts] = useState<FinishedProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<FinishedProduct | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    category_id: 'CAT-PRESS',
    uom: 'PCS',
    drawing_no: '',
    revision_no: 'R0',
    standard_cost: 0,
    selling_price: 0,
    min_stock_level: 0,
    unit_id: 'BOTH',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<FinishedProduct>('products', {
        page,
        page_size: pageSize,
        search: search || undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
      });
      setProducts(res.items);
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
    setEditingProduct(null);
    setFormData({
      code: '',
      name: '',
      description: '',
      category_id: 'CAT-PRESS',
      uom: 'PCS',
      drawing_no: '',
      revision_no: 'R0',
      standard_cost: 0,
      selling_price: 0,
      min_stock_level: 0,
      unit_id: 'BOTH',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (p: FinishedProduct) => {
    setEditingProduct(p);
    setFormData({
      code: p.code,
      name: p.name,
      description: p.description || '',
      category_id: p.category_id || 'CAT-PRESS',
      uom: p.uom,
      drawing_no: p.drawing_no || '',
      revision_no: p.revision_no || 'R0',
      standard_cost: p.standard_cost,
      selling_price: p.selling_price,
      min_stock_level: p.min_stock_level,
      unit_id: p.unit_id,
      is_active: p.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingProduct) {
        await masterClient.update<FinishedProduct>('products', editingProduct.id, formData);
      } else {
        await masterClient.create<FinishedProduct>('products', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save finished product record.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (p: FinishedProduct) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('products', p.id, false);
      loadData();
    } catch {
      // error handled
    }
  };

  const columns: Column<FinishedProduct>[] = [
    {
      key: 'code',
      header: 'Model / Code',
      render: (p: FinishedProduct) => <span className="font-semibold text-neutral-900">{p.code}</span>,
    },
    {
      key: 'name',
      header: 'Machine / Product Name',
      render: (p: FinishedProduct) => (
        <div>
          <div className="font-medium text-neutral-900">{p.name}</div>
          <div className="text-xs text-neutral-500">{p.description || 'No description'}</div>
        </div>
      ),
    },
    {
      key: 'drawing',
      header: 'Drawing & Rev',
      render: (p: FinishedProduct) => (
        <div className="text-xs">
          <div className="font-mono text-neutral-700">{p.drawing_no || 'N/A'}</div>
          <div className="text-neutral-500">Rev: {p.revision_no}</div>
        </div>
      ),
    },
    {
      key: 'cost',
      header: 'Standard Cost',
      render: (p: FinishedProduct) => <span className="text-xs font-mono">₹{p.standard_cost.toLocaleString('en-IN')}</span>,
    },
    {
      key: 'price',
      header: 'Selling Price',
      render: (p: FinishedProduct) => <span className="text-xs font-semibold text-neutral-900 font-mono">₹{p.selling_price.toLocaleString('en-IN')}</span>,
    },
    {
      key: 'uom',
      header: 'UoM',
      render: (p: FinishedProduct) => <span className="text-xs font-semibold px-2 py-0.5 rounded bg-neutral-100">{p.uom}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (p: FinishedProduct) => (
        <Badge variant={p.is_active ? 'success' : 'neutral'} className="text-xs">
          {p.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (p: FinishedProduct) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(p)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit Product"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(p)}
              className={`p-1 rounded transition-colors ${
                p.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
              }`}
              title={p.is_active ? 'Deactivate' : 'Activate'}
            >
              {p.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Finished-Product Master</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Hydraulic presses, specialized machinery models, drawings, standard costs, and price catalogues.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={masterClient.getTemplateUrl('products')}
              download
              className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Import Template</span>
            </a>

            {canCreate && (
              <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                <Plus className="w-4 h-4" />
                <span>Add Product</span>
              </Button>
            )}
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          placeholder="Search machine code, name or drawing..."
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
            data={products}
            isLoading={isLoading}
            emptyTitle="No products found"
            emptyDescription="No finished products registered. Click 'Add Product' or download the template."
            keyExtractor={(p) => p.id}
          />

          {total > pageSize && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
              <div>Total: {total} products</div>
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
          title={editingProduct ? `Edit Product (${editingProduct.code})` : 'Register Finished Product'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Model / SKU Code *</label>
                <input
                  type="text"
                  required
                  disabled={!!editingProduct}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. FP-ENV-500"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase disabled:bg-neutral-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Machine Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. 500 Ton Hydraulic Press"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Drawing Number</label>
                <input
                  type="text"
                  value={formData.drawing_no}
                  onChange={(e) => setFormData({ ...formData, drawing_no: e.target.value })}
                  placeholder="DWG-500-01"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Revision</label>
                <input
                  type="text"
                  value={formData.revision_no}
                  onChange={(e) => setFormData({ ...formData, revision_no: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Base UoM</label>
                <input
                  type="text"
                  value={formData.uom}
                  onChange={(e) => setFormData({ ...formData, uom: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Standard Cost (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.standard_cost}
                  onChange={(e) => setFormData({ ...formData, standard_cost: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Selling Price (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.selling_price}
                  onChange={(e) => setFormData({ ...formData, selling_price: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Machine Specifications</label>
              <textarea
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : editingProduct ? 'Update Product' : 'Create Product'}
              </Button>
            </div>
          </form>
        </Dialog>
      </div>
  );
}
