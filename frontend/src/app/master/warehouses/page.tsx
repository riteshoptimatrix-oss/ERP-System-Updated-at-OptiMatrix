'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { DataTable, Column } from '@/components/ui/DataTable';
import { FilterBar } from '@/components/ui/FilterBar';
import { Dialog } from '@/components/ui/Dialog';
import { Badge } from '@/components/ui/Badge';
import { Warehouse } from '@/types/master';
import { masterClient } from '@/services/master-client';
import { useAuth } from '@/context/AuthContext';
import { Plus, Download, Edit2, Ban, CheckCircle2 } from 'lucide-react';

export default function WarehousesPage() {
  const { hasPermission, activeUnit } = useAuth();
  const canCreate = hasPermission('master', 'create');
  const canUpdate = hasPermission('master', 'update');

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    unit_id: activeUnit,
    location_type: 'RAW_MATERIAL',
    bay_rack: '',
    capacity_description: '',
    is_active: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await masterClient.list<Warehouse>('warehouses', {
        page,
        page_size: pageSize,
        search: search || undefined,
        unit_id: activeUnit,
      });
      setWarehouses(res.items);
      setTotal(res.total);
    } catch {
      // Handled
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, activeUnit]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingWarehouse(null);
    setFormData({
      code: '',
      name: '',
      unit_id: activeUnit,
      location_type: 'RAW_MATERIAL',
      bay_rack: '',
      capacity_description: '',
      is_active: true,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (w: Warehouse) => {
    setEditingWarehouse(w);
    setFormData({
      code: w.code,
      name: w.name,
      unit_id: w.unit_id,
      location_type: w.location_type,
      bay_rack: w.bay_rack || '',
      capacity_description: w.capacity_description || '',
      is_active: w.is_active,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (editingWarehouse) {
        await masterClient.update<Warehouse>('warehouses', editingWarehouse.id, formData);
      } else {
        await masterClient.create<Warehouse>('warehouses', formData);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Failed to save warehouse record.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleStatus = async (w: Warehouse) => {
    if (!canUpdate) return;
    try {
      await masterClient.delete('warehouses', w.id, false);
      loadData();
    } catch {
      // Handled
    }
  };

  const columns: Column<Warehouse>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (w: Warehouse) => <span className="font-semibold font-mono text-neutral-900">{w.code}</span>,
    },
    {
      key: 'name',
      header: 'Location / Warehouse Name',
      render: (w: Warehouse) => (
        <div>
          <div className="font-medium text-neutral-900">{w.name}</div>
          <div className="text-xs text-neutral-500">{w.bay_rack || 'Main storage area'}</div>
        </div>
      ),
    },
    {
      key: 'unit_id',
      header: 'Facility',
      render: (w: Warehouse) => (
        <Badge variant={w.unit_id === 'Unit_1' ? 'neutral' : 'warning'} className="text-xs">
          {w.unit_id === 'Unit_1'
            ? 'Unit 1 (Machining)'
            : w.unit_id === 'Unit_2'
              ? 'Unit 2 (Assembly & QC)'
              : 'Both Facilities'}
        </Badge>
      ),
    },
    {
      key: 'type',
      header: 'Storage Type',
      render: (w: Warehouse) => <span className="text-xs font-semibold px-2 py-0.5 rounded bg-neutral-100">{w.location_type}</span>,
    },
    {
      key: 'capacity',
      header: 'Capacity Details',
      render: (w: Warehouse) => <span className="text-xs text-neutral-600">{w.capacity_description || '-'}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (w: Warehouse) => (
        <Badge variant={w.is_active ? 'success' : 'neutral'} className="text-xs">
          {w.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (w: Warehouse) => (
        <div className="flex items-center gap-2">
          {canUpdate && (
            <button
              onClick={() => handleOpenEdit(w)}
              className="p-1 text-neutral-500 hover:text-[#315C45] rounded transition-colors"
              title="Edit Location"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {canUpdate && (
            <button
              onClick={() => handleToggleStatus(w)}
              className={`p-1 rounded transition-colors ${w.is_active ? 'text-neutral-500 hover:text-amber-600' : 'text-neutral-500 hover:text-emerald-600'
                }`}
              title={w.is_active ? 'Deactivate' : 'Activate'}
            >
              {w.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
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
          <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">Warehouse & Storage-Location Master</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Raw material yards, sub-assembly racks, staging bays, and finished dispatch holding areas.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={masterClient.getTemplateUrl('warehouses')}
            download
            className="inline-flex items-center gap-2 px-3 py-2 border border-neutral-300 rounded-lg text-sm font-medium text-neutral-700 bg-white hover:bg-neutral-50 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            <span>Import Template</span>
          </a>

          {canCreate && (
            <Button onClick={handleOpenCreate} className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              <span>Add Storage Location</span>
            </Button>
          )}
        </div>
      </div>

      <FilterBar
        searchQuery={search}
        onSearchChange={setSearch}
        placeholder="Search location code or name..."
      >
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="text-xs border border-[#E7E5DE]  rounded-lg px-2.5 py-2 bg-white "
        >
          <option value="">All Types</option>
          <option value="RAW_MATERIAL">Raw Material</option>
          <option value="WIP">WIP / Staging</option>
          <option value="FINISHED_GOODS">Finished Goods</option>
          <option value="SCRAP">Scrap & Wastage</option>
        </select>
      </FilterBar>

      <div className="bg-white border border-neutral-200 rounded-xl overflow-hidden shadow-sm">
        <DataTable
          columns={columns}
          data={warehouses}
          isLoading={isLoading}
          emptyTitle="No storage locations found"
          emptyDescription="No warehouses or storage locations configured for this facility."
          keyExtractor={(w) => w.id}
        />

        {total > pageSize && (
          <div className="px-6 py-4 border-t border-neutral-200 flex items-center justify-between text-sm text-neutral-600">
            <div>Total: {total} locations</div>
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
        title={editingWarehouse ? `Edit Storage Location (${editingWarehouse.code})` : 'Create Storage Location'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Location Code *</label>
              <input
                type="text"
                required
                disabled={!!editingWarehouse}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="e.g. WH-E1-RM01"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm uppercase disabled:bg-neutral-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Name *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. Unit 1 Heavy Raw Yard"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Facility *</label>
              <select
                value={formData.unit_id}
                onChange={(e) => setFormData({ ...formData, unit_id: e.target.value as 'Unit_1' | 'Unit_2' })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                <option value="Unit_1">Unit 1 — Heavy Machining &amp; Fabrication</option>
                <option value="Unit_2">Unit 2 — Precision Assembly &amp; QC</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Storage Type *</label>
              <select
                value={formData.location_type}
                onChange={(e) => setFormData({ ...formData, location_type: e.target.value })}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm bg-white"
              >
                <option value="RAW_MATERIAL">Raw Material Yard</option>
                <option value="WIP">Work-in-Progress (WIP)</option>
                <option value="FINISHED_GOODS">Finished Goods Holding</option>
                <option value="SCRAP">Scrap Yard</option>
                <option value="TOOL_ROOM">Tool Room</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Bay / Rack Locator</label>
              <input
                type="text"
                value={formData.bay_rack}
                onChange={(e) => setFormData({ ...formData, bay_rack: e.target.value })}
                placeholder="e.g. Bay 2, Rack C"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-700 mb-1">Capacity Notes</label>
              <input
                type="text"
                value={formData.capacity_description}
                onChange={(e) => setFormData({ ...formData, capacity_description: e.target.value })}
                placeholder="e.g. Max 50 Metric Tons"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : editingWarehouse ? 'Update Location' : 'Save Location'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
