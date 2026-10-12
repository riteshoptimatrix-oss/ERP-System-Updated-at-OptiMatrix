'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Category } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function CategoriesPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [categories, setCategories] = useState<Category[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    category_type: 'RAW_MATERIAL',
    description: '',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<Category>('categories', {
        page,
        page_size: pageSize,
        search: search || undefined,
        category: typeFilter || undefined,
      });
      setCategories(res.items);
      setTotal(res.total);
    } catch {
      // Handled
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, typeFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingCategory(null);
    setFormData({
      code: '',
      name: '',
      category_type: 'RAW_MATERIAL',
      description: '',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (c: Category) => {
    setEditingCategory(c);
    setFormData({
      code: c.code,
      name: c.name,
      category_type: c.category_type,
      description: c.description || '',
      is_active: c.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingCategory) {
        await masterClient.update<Category>('categories', editingCategory.id, formData);
      } else {
        await masterClient.create<Category>('categories', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save category.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (c: Category) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('categories', c.id, false);
      loadData();
    } catch {
      // Handled
    }
  };

  const columns: Column<Category>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (c: Category) => <span className="font-semibold font-mono text-neutral-900">{c.code}</span>,
    },
    {
      key: 'name',
      header: 'Category Name',
      render: (c: Category) => <span className="font-medium text-neutral-900">{c.name}</span>,
    },
    {
      key: 'classification',
      header: 'Classification',
      render: (c: Category) => (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#EAF0E9] text-[#254936] border border-[#315C45]/20">
          {c.category_type}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (c: Category) => <span className="text-xs text-neutral-500">{c.description || '-'}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (c: Category) => (
        <Badge variant={c.is_active ? 'success' : 'neutral'} className="text-xs">
          {c.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (c: Category) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(c)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit Category"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(c)}
              className={`p-1 rounded transition-colors ${
                c.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
              }`}
              title={c.is_active ? 'Deactivate' : 'Activate'}
            >
              {c.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Product & Material Categories</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Hierarchical grouping for raw plates, hydraulic equipment, machine models, and consumables.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={masterClient.getTemplateUrl('categories')}
              download
              className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Import Template</span>
            </a>

            {canCreate && (
              <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                <Plus className="w-4 h-4" />
                <span>Add Category</span>
              </Button>
            )}
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          placeholder="Search category code or name..."
        >
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs border border-[#E7E5DE]  rounded-lg px-2.5 py-2 bg-white "
          >
            <option value="">All Types</option>
            <option value="RAW_MATERIAL">Raw Material</option>
            <option value="FINISHED_PRODUCT">Finished Product</option>
            <option value="CONSUMABLE">Consumables</option>
          </select>
        </FilterBar>

        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-sm">
          <DataTable
            columns={columns}
            data={categories}
            isLoading={isLoading}
            emptyTitle="No categories defined"
            emptyDescription="No product or material categories defined. Click 'Add Category' or download the template."
            keyExtractor={(c) => c.id}
          />

          {total > pageSize && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
              <div>Total: {total} categories</div>
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
          title={editingCategory ? `Edit Category (${editingCategory.code})` : 'Create Category'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Category Code *</label>
                <input
                  type="text"
                  required
                  disabled={!!editingCategory}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. CAT-STEEL"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase disabled:bg-neutral-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Category Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Structural Steel & Heavy Plates"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Classification *</label>
                <select
                  value={formData.category_type}
                  onChange={(e) => setFormData({ ...formData, category_type: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
                >
                  <option value="RAW_MATERIAL">Raw Material</option>
                  <option value="FINISHED_PRODUCT">Finished Product</option>
                  <option value="CONSUMABLE">Consumable & Tooling</option>
                  <option value="SPARES">Maintenance Spares</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Scope or standard specifications"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : editingCategory ? 'Update Category' : 'Create Category'}
              </Button>
            </div>
          </form>
        </Dialog>
      </div>
  );
}
