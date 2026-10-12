'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { UoM } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function UoMPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [units, setUnits] = useState<UoM[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUoM, setEditingUoM] = useState<UoM | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    symbol: '',
    description: '',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<UoM>('uom', {
        page,
        page_size: pageSize,
        search: search || undefined,
      });
      setUnits(res.items);
      setTotal(res.total);
    } catch {
      // Empty
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingUoM(null);
    setFormData({
      code: '',
      name: '',
      symbol: '',
      description: '',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (uom: UoM) => {
    setEditingUoM(uom);
    setFormData({
      code: uom.code,
      name: uom.name,
      symbol: uom.symbol || '',
      description: uom.description || '',
      is_active: uom.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingUoM) {
        await masterClient.update<UoM>('uom', editingUoM.id, formData);
      } else {
        await masterClient.create<UoM>('uom', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save UoM.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (uom: UoM) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('uom', uom.id, false);
      loadData();
    } catch {
      // Handled
    }
  };

  const columns: Column<UoM>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (u: UoM) => <span className="font-semibold font-mono text-neutral-900">{u.code}</span>,
    },
    {
      key: 'name',
      header: 'Unit Name',
      render: (u: UoM) => <span className="font-medium text-neutral-900">{u.name}</span>,
    },
    {
      key: 'symbol',
      header: 'Symbol',
      render: (u: UoM) => <span className="text-xs font-mono font-bold text-neutral-700">{u.symbol || u.code}</span>,
    },
    {
      key: 'description',
      header: 'Description',
      render: (u: UoM) => <span className="text-xs text-neutral-500">{u.description || '-'}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (u: UoM) => (
        <Badge variant={u.is_active ? 'success' : 'neutral'} className="text-xs">
          {u.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u: UoM) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(u)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit UoM"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(u)}
              className={`p-1 rounded transition-colors ${
                u.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
              }`}
              title={u.is_active ? 'Deactivate' : 'Activate'}
            >
              {u.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Unit-of-Measure Master</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Measurement units across raw materials, finished machines, machining tolerances, and BOMs.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={masterClient.getTemplateUrl('uom')}
              download
              className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Import Template</span>
            </a>

            {canCreate && (
              <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                <Plus className="w-4 h-4" />
                <span>Add UoM</span>
              </Button>
            )}
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          placeholder="Search unit code or name..."
        />

        <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-sm">
          <DataTable
            columns={columns}
            data={units}
            isLoading={isLoading}
            emptyTitle="No units of measure defined"
            emptyDescription="No units of measure found. Click 'Add UoM' or download the template."
            keyExtractor={(u) => u.id}
          />

          {total > pageSize && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
              <div>Total: {total} units</div>
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
          title={editingUoM ? `Edit UoM (${editingUoM.code})` : 'Define Unit of Measure'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">UoM Code *</label>
                <input
                  type="text"
                  required
                  disabled={!!editingUoM}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. KG, PCS, MTR"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase disabled:bg-neutral-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Unit Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Kilogram"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Symbol</label>
                <input
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                  placeholder="e.g. kg, m, pc"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Standard mass / weight"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : editingUoM ? 'Update UoM' : 'Create UoM'}
              </Button>
            </div>
          </form>
        </Dialog>
      </div>
  );
}
