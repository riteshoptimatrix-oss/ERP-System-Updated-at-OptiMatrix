'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { RawMaterial } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function MaterialsPage() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<RawMaterial | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    category_id: 'CAT-STEEL',
    uom: 'KG',
    hsn_code: '7208',
    reorder_level: 0,
    safety_stock: 0,
    default_vendor_code: '',
    unit_id: 'BOTH',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<RawMaterial>('materials', {
        page,
        page_size: pageSize,
        search: search || undefined,
        is_active: statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined,
      });
      setMaterials(res.items);
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
    setEditingMaterial(null);
    setFormData({
      code: '',
      name: '',
      description: '',
      category_id: 'CAT-STEEL',
      uom: 'KG',
      hsn_code: '7208',
      reorder_level: 0,
      safety_stock: 0,
      default_vendor_code: '',
      unit_id: 'BOTH',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (m: RawMaterial) => {
    setEditingMaterial(m);
    setFormData({
      code: m.code,
      name: m.name,
      description: m.description || '',
      category_id: m.category_id || 'CAT-STEEL',
      uom: m.uom,
      hsn_code: m.hsn_code || '',
      reorder_level: m.reorder_level,
      safety_stock: m.safety_stock,
      default_vendor_code: m.default_vendor_code || '',
      unit_id: m.unit_id,
      is_active: m.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingMaterial) {
        await masterClient.update<RawMaterial>('materials', editingMaterial.id, formData);
      } else {
        await masterClient.create<RawMaterial>('materials', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save raw material record.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (m: RawMaterial) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('materials', m.id, false);
      loadData();
    } catch {
      // error handled
    }
  };

  const columns: Column<RawMaterial>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (m: RawMaterial) => <span className="font-semibold text-neutral-900">{m.code}</span>,
    },
    {
      key: 'name',
      header: 'Material Name',
      render: (m: RawMaterial) => (
        <div>
          <div className="font-medium text-neutral-900">{m.name}</div>
          <div className="text-xs text-neutral-500">{m.description || 'No description'}</div>
        </div>
      ),
    },
    {
      key: 'hsn',
      header: 'HSN & UoM',
      render: (m: RawMaterial) => (
        <div className="text-xs">
          <div>HSN: <span className="font-mono text-neutral-700">{m.hsn_code || 'N/A'}</span></div>
          <div>UoM: <span className="font-semibold">{m.uom}</span></div>
        </div>
      ),
    },
    {
      key: 'reorder',
      header: 'Reorder / Safety',
      render: (m: RawMaterial) => (
        <div className="text-xs">
          <div>Reorder: {m.reorder_level} {m.uom}</div>
          <div className="text-neutral-500">Safety: {m.safety_stock} {m.uom}</div>
        </div>
      ),
    },
    {
      key: 'vendor',
      header: 'Default Supplier',
      render: (m: RawMaterial) => <span className="text-xs font-mono">{m.default_vendor_code || 'None'}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (m: RawMaterial) => (
        <Badge variant={m.is_active ? 'success' : 'neutral'} className="text-xs">
          {m.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (m: RawMaterial) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(m)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit Material"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(m)}
              className={`p-1 rounded transition-colors ${
                m.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
              }`}
              title={m.is_active ? 'Deactivate' : 'Activate'}
            >
              {m.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Raw-Material Master</h1>
            <p className="text-sm text-neutral-500 mt-1">
              MS plates, forging billets, hydraulic cylinders, fasteners, oil seals, and fabrication stock.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={masterClient.getTemplateUrl('materials')}
              download
              className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>Import Template</span>
            </a>

            {canCreate && (
              <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                <Plus className="w-4 h-4" />
                <span>Add Material</span>
              </Button>
            )}
          </div>
        </div>

        <FilterBar
          searchQuery={search}
          onSearchChange={setSearch}
          placeholder="Search material code or description..."
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
            data={materials}
            isLoading={isLoading}
            emptyTitle="No raw materials registered"
            emptyDescription="No raw materials registered. Click 'Add Material' or download the template."
            keyExtractor={(m) => m.id}
          />

          {total > pageSize && (
            <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
              <div>Total: {total} materials</div>
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
          title={editingMaterial ? `Edit Material (${editingMaterial.code})` : 'Register Raw Material'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Material Code *</label>
                <input
                  type="text"
                  required
                  disabled={!!editingMaterial}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. RM-MS-PL-25"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase disabled:bg-neutral-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Material Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Mild Steel Plate 25mm"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">UoM *</label>
                <input
                  type="text"
                  required
                  value={formData.uom}
                  onChange={(e) => setFormData({ ...formData, uom: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">HSN / SAC Code</label>
                <input
                  type="text"
                  value={formData.hsn_code}
                  onChange={(e) => setFormData({ ...formData, hsn_code: e.target.value })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Default Supplier Code</label>
                <input
                  type="text"
                  value={formData.default_vendor_code}
                  onChange={(e) => setFormData({ ...formData, default_vendor_code: e.target.value.toUpperCase() })}
                  placeholder="e.g. VEND-001"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Reorder Level</label>
                <input
                  type="number"
                  min="0"
                  value={formData.reorder_level}
                  onChange={(e) => setFormData({ ...formData, reorder_level: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">Safety Stock</label>
                <input
                  type="number"
                  min="0"
                  value={formData.safety_stock}
                  onChange={(e) => setFormData({ ...formData, safety_stock: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : editingMaterial ? 'Update Material' : 'Register Material'}
              </Button>
            </div>
          </form>
        </Dialog>
      </div>
  );
}
