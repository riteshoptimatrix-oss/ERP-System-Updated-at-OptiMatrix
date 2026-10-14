'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/context/AuthContext';
import { powerClient } from '@/services/power-client';
import {
  ElectricityReading,
  PowerCutLog,
  MeterType,
  OutageType,
  PowerSummary,
  DailyElectricityScrapTracker,
} from '@/types/power';
import {
  Zap,
  AlertTriangle,
  Clock,
  Fuel,
  Plus,
  Activity,
  CheckCircle2,
  X,
  Gauge,
  FileSpreadsheet,
} from 'lucide-react';

const OUTAGE_TYPE_LABELS: Record<OutageType, string> = {
  GRID_FAILURE: 'Grid (EB) Failure',
  SCHEDULED_MAINTENANCE: 'Scheduled Maintenance',
  EMERGENCY_SHUTDOWN: 'Emergency Shutdown',
  GENERATOR_FAILURE: 'Generator Trip / Failure',
  LOCAL_TRIP: 'Internal Line Trip',
};

const METER_TYPE_LABELS: Record<MeterType, string> = {
  GRID_EB: 'Electricity Board (EB)',
  DIESEL_GENERATOR: 'Diesel Generator (DG)',
  SOLAR: 'Rooftop Solar Array',
};

export default function PowerTrackingPage() {
  const { activeUnit, hasPermission } = useAuth();
  const canCreate = hasPermission('power', 'create');

  // Active Tab: 'OUTAGES' | 'SCRAP' | 'READINGS'
  const [activeTab, setActiveTab] = useState<'OUTAGES' | 'SCRAP' | 'READINGS'>('OUTAGES');

  // KPI Metrics
  const [summary, setSummary] = useState<PowerSummary | null>(null);

  // Outages State
  const [outages, setOutages] = useState<PowerCutLog[]>([]);
  const [isLoadingOutages, setIsLoadingOutages] = useState(false);
  const [selectedOutageType, setSelectedOutageType] = useState<string>('ALL');

  // Scrap Tracker State
  const [scrapTrackers, setScrapTrackers] = useState<DailyElectricityScrapTracker[]>([]);
  const [isLoadingScrap, setIsLoadingScrap] = useState(false);
  const [scrapSearch, setScrapSearch] = useState<string>('');

  // Meter Readings State
  const [readings, setReadings] = useState<ElectricityReading[]>([]);
  const [isLoadingReadings, setIsLoadingReadings] = useState(false);
  const [selectedMeterType, setSelectedMeterType] = useState<string>('ALL');

  // Modals
  const [showOutageModal, setShowOutageModal] = useState(false);
  const [showReadingModal, setShowReadingModal] = useState(false);

  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Outage Form State
  const [outageForm, setOutageForm] = useState({
    unit_id: (activeUnit === 'Unit_2' ? 'Unit_2' : 'Unit_1') as 'Unit_1' | 'Unit_2',
    start_time: '',
    end_time: '',
    outage_type: 'GRID_FAILURE' as OutageType,
    reason: '',
    backup_generator_used: false,
    fuel_consumed_liters: 0,
    affected_departments: 'Machine Shop, Assembly',
    remarks: '',
  });

  // Reading Form State
  const [readingForm, setReadingForm] = useState({
    reading_date: new Date().toISOString().split('T')[0],
    unit_id: (activeUnit === 'Unit_2' ? 'Unit_2' : 'Unit_1') as 'Unit_1' | 'Unit_2',
    meter_id: 'METER-MAIN-EB-01',
    meter_type: 'GRID_EB' as MeterType,
    opening_reading_kwh: 0,
    closing_reading_kwh: 0,
    power_factor: 0.98,
    shift: 'General',
    remarks: '',
  });

  const loadData = useCallback(async () => {
    setActionError(null);
    const unitParam = activeUnit && activeUnit !== 'BOTH' ? activeUnit : undefined;
    try {
      const summaryRes = await powerClient.getSummary(unitParam);
      setSummary(summaryRes);

      if (activeTab === 'OUTAGES') {
        setIsLoadingOutages(true);
        const outagesRes = await powerClient.listOutages({
          unit_id: unitParam,
          outage_type: selectedOutageType !== 'ALL' ? selectedOutageType : undefined,
          page_size: 100,
        });
        setOutages(outagesRes.items || []);
        setIsLoadingOutages(false);
      } else if (activeTab === 'SCRAP') {
        setIsLoadingScrap(true);
        const scrapRes = await powerClient.listScrapTracker({
          unit_id: unitParam,
          search: scrapSearch || undefined,
          page_size: 100,
        });
        setScrapTrackers(scrapRes.items || []);
        setIsLoadingScrap(false);
      } else {
        setIsLoadingReadings(true);
        const readingsRes = await powerClient.listReadings({
          unit_id: unitParam,
          meter_type: selectedMeterType !== 'ALL' ? selectedMeterType : undefined,
          page_size: 100,
        });
        setReadings(readingsRes.items || []);
        setIsLoadingReadings(false);
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to fetch power data');
      setIsLoadingOutages(false);
      setIsLoadingScrap(false);
      setIsLoadingReadings(false);
    }
  }, [activeUnit, activeTab, selectedOutageType, scrapSearch, selectedMeterType]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Log Outage
  const handleLogOutage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!outageForm.start_time || !outageForm.end_time || !outageForm.reason) {
      setActionError('Start time, end time, and reason are required.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);
    try {
      await powerClient.logOutage({
        unit_id: outageForm.unit_id,
        start_time: new Date(outageForm.start_time).toISOString(),
        end_time: new Date(outageForm.end_time).toISOString(),
        outage_type: outageForm.outage_type,
        reason: outageForm.reason,
        backup_generator_used: outageForm.backup_generator_used,
        fuel_consumed_liters: outageForm.backup_generator_used ? Number(outageForm.fuel_consumed_liters) : undefined,
        affected_departments: outageForm.affected_departments.split(',').map((s) => s.trim()).filter(Boolean),
        remarks: outageForm.remarks || undefined,
      });

      setActionSuccess('Power outage logged successfully.');
      setShowOutageModal(false);
      setOutageForm({
        unit_id: (activeUnit === 'Unit_2' ? 'Unit_2' : 'Unit_1') as 'Unit_1' | 'Unit_2',
        start_time: '',
        end_time: '',
        outage_type: 'GRID_FAILURE',
        reason: '',
        backup_generator_used: false,
        fuel_consumed_liters: 0,
        affected_departments: 'Machine Shop, Assembly',
        remarks: '',
      });
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to log outage');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Record Reading
  const handleRecordReading = async (e: React.FormEvent) => {
    e.preventDefault();
    if (readingForm.closing_reading_kwh < readingForm.opening_reading_kwh) {
      setActionError('Closing reading cannot be less than opening reading.');
      return;
    }

    setIsSubmitting(true);
    setActionError(null);
    try {
      await powerClient.recordReading({
        reading_date: readingForm.reading_date,
        unit_id: readingForm.unit_id,
        meter_id: readingForm.meter_id,
        meter_type: readingForm.meter_type,
        opening_reading_kwh: Number(readingForm.opening_reading_kwh),
        closing_reading_kwh: Number(readingForm.closing_reading_kwh),
        power_factor: Number(readingForm.power_factor),
        shift: readingForm.shift,
        remarks: readingForm.remarks || undefined,
      });

      setActionSuccess('Electricity meter reading recorded successfully.');
      setShowReadingModal(false);
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Failed to record meter reading');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Columns for Outages
  const outageColumns: Column<PowerCutLog>[] = [
    {
      key: 'incident_number',
      header: 'Incident #',
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-rose-600 text-rose-400">
          {row.incident_number}
        </span>
      ),
    },
    {
      key: 'unit_id',
      header: 'Facility',
      render: (row) => (
        <Badge variant={row.unit_id === 'Unit_1' ? 'neutral' : 'warning'}>
          {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : 'Unit 2 (Assembly & QC)'}
        </Badge>
      ),
    },
    {
      key: 'incident_date',
      header: 'Date',
      render: (row) => (
        <span className="text-xs font-medium text-slate-800">
          {row.incident_date || (row.start_time ? new Date(row.start_time).toISOString().split('T')[0] : '—')}
        </span>
      ),
    },
    {
      key: 'power_cut_time',
      header: 'Power Cut Time',
      render: (row) => (
        <span className="text-xs font-mono font-medium text-rose-600">
          {row.power_cut_time || (row.start_time ? new Date(row.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—')}
        </span>
      ),
    },
    {
      key: 'power_restored_time',
      header: 'Restored Time',
      render: (row) => (
        <span className="text-xs font-mono font-medium text-emerald-600">
          {row.power_restored_time || (row.end_time ? new Date(row.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—')}
        </span>
      ),
    },
    {
      key: 'restart_delay_minutes',
      header: 'Restart Delay (Min)',
      render: (row) => (
        <span className="text-xs font-semibold text-amber-600">
          {row.restart_delay_minutes ? `${row.restart_delay_minutes} min` : '—'}
        </span>
      ),
    },
    {
      key: 'duration_minutes',
      header: 'Downtime Duration',
      render: (row) => (
        <span className="font-bold text-xs text-rose-600">
          {row.downtime_duration_str || `${row.duration_minutes} mins`}
        </span>
      ),
    },
    {
      key: 'backup_generator_used',
      header: 'Generator Run',
      render: (row) => (
        row.backup_generator_used ? (
          <Badge variant="warning">
            DG Active ({row.fuel_consumed_liters || 0} L)
          </Badge>
        ) : (
          <Badge variant="neutral">No Generator</Badge>
        )
      ),
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (row) => (
        <span className="text-xs text-slate-700  truncate max-w-xs block">
          {row.reason}
        </span>
      ),
    },
    {
      key: 'remarks',
      header: 'Remarks',
      render: (row) => (
        <span className="text-xs text-slate-500">
          {row.remarks || '—'}
        </span>
      ),
    },
  ];

  // Columns for Daily Electricity & Scrap Tracker
  const scrapTrackerColumns: Column<DailyElectricityScrapTracker>[] = [
    {
      key: 'date',
      header: 'Date',
      render: (row) => (
        <span className="font-medium text-xs text-slate-900">
          {row.date}
        </span>
      ),
    },
    {
      key: 'total_production_kg',
      header: 'Total Prod (kg)',
      render: (row) => (
        <span className="font-semibold text-xs text-[#315C45]">
          {row.total_production_kg.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'product_type',
      header: 'Product Type',
      render: (row) => (
        <Badge variant={row.product_type === 'Braider' ? 'success' : 'neutral'}>
          {row.product_type || '—'}
        </Badge>
      ),
    },
    {
      key: 'startup_scrap_kg',
      header: 'Startup Scrap (kg)',
      render: (row) => (
        <span className="text-xs text-slate-700">
          {row.startup_scrap_kg.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'cutting_scrap_kg',
      header: 'Cutting Scrap (kg)',
      render: (row) => (
        <span className="text-xs text-slate-700">
          {row.cutting_scrap_kg.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'total_scrap_kg',
      header: 'Total Scrap (kg)',
      render: (row) => (
        <span className="font-bold text-xs text-rose-600">
          {row.total_scrap_kg.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'scrap_percent_str',
      header: 'Scrap %',
      render: (row) => (
        <span className="font-semibold text-xs text-amber-600">
          {row.scrap_percent_str}
        </span>
      ),
    },
    {
      key: 'electricity_off_count',
      header: 'Power Off Times',
      render: (row) => (
        <span className="text-xs font-semibold text-slate-800">
          {row.electricity_off_count}
        </span>
      ),
    },
    {
      key: 'total_off_time_min',
      header: 'Off Time (min)',
      render: (row) => (
        <span className="text-xs text-rose-500 font-medium">
          {row.total_off_time_min}
        </span>
      ),
    },
    {
      key: 'machine_working_hours',
      header: 'Working Hrs',
      render: (row) => (
        <span className="text-xs text-slate-700">
          {row.machine_working_hours}
        </span>
      ),
    },
    {
      key: 'shift_duration_hr',
      header: 'Shift (Hr)',
      render: (row) => (
        <span className="text-xs text-slate-600">
          {row.shift_duration_hr}
        </span>
      ),
    },
    {
      key: 'main_reason',
      header: 'Main Reason',
      render: (row) => (
        <span className="text-xs text-slate-600 max-w-xs truncate block">
          {row.main_reason || '—'}
        </span>
      ),
    },
    {
      key: 'remarks',
      header: 'Remarks',
      render: (row) => (
        <span className="text-xs text-slate-500 max-w-xs truncate block">
          {row.remarks || '—'}
        </span>
      ),
    },
  ];

  // Columns for Meter Readings
  const readingColumns: Column<ElectricityReading>[] = [
    {
      key: 'reading_number',
      header: 'Reading #',
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-[#315C45] text-blue-400">
          {row.reading_number}
        </span>
      ),
    },
    {
      key: 'reading_date',
      header: 'Date',
      render: (row) => <span>{row.reading_date}</span>,
    },
    {
      key: 'unit_id',
      header: 'Facility',
      render: (row) => (
        <Badge variant={row.unit_id === 'Unit_1' ? 'neutral' : 'warning'}>
          {row.unit_id === 'Unit_1' ? 'Unit 1 (Machining)' : 'Unit 2 (Assembly & QC)'}
        </Badge>
      ),
    },
    {
      key: 'meter_id',
      header: 'Meter ID',
      render: (row) => (
        <span className="font-mono text-xs font-medium">{row.meter_id}</span>
      ),
    },
    {
      key: 'meter_type',
      header: 'Type',
      render: (row) => (
        <span className="text-xs">
          {METER_TYPE_LABELS[row.meter_type as MeterType] || row.meter_type}
        </span>
      ),
    },
    {
      key: 'opening_reading_kwh',
      header: 'Opening kWh',
      render: (row) => (
        <span className="font-mono text-xs text-slate-500">{row.opening_reading_kwh.toLocaleString()}</span>
      ),
    },
    {
      key: 'closing_reading_kwh',
      header: 'Closing kWh',
      render: (row) => (
        <span className="font-mono text-xs text-slate-500">{row.closing_reading_kwh.toLocaleString()}</span>
      ),
    },
    {
      key: 'units_consumed_kwh',
      header: 'Net Consumption',
      render: (row) => (
        <span className="font-bold text-xs text-[#315C45] text-blue-400">
          {row.units_consumed_kwh.toLocaleString()} kWh
        </span>
      ),
    },
    {
      key: 'power_factor',
      header: 'Power Factor',
      render: (row) => (
        <span className="text-xs font-mono text-slate-600 ">
          {row.power_factor ? row.power_factor.toFixed(2) : 'N/A'}
        </span>
      ),
    },
    {
      key: 'shift',
      header: 'Shift',
      render: (row) => (
        <span className="text-xs">{row.shift || 'General'}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900  flex items-center gap-2">
            <Zap className="w-7 h-7 text-amber-500" />
            Electricity & Power-Cut Tracking
          </h1>
          <p className="text-sm text-slate-500 ">
            Machine downtime duration logs, backup generator tracking, and daily electricity meter consumption
          </p>
        </div>

        <div className="flex gap-2">
          {canCreate && (
            <>
              <Button
                variant={activeTab === 'OUTAGES' ? 'primary' : 'outline'}
                onClick={() => setShowOutageModal(true)}
                className="flex items-center gap-2"
              >
                <AlertTriangle className="w-4 h-4 text-rose-500" />
                Log Power Outage
              </Button>
              <Button
                variant={activeTab === 'READINGS' ? 'primary' : 'outline'}
                onClick={() => setShowReadingModal(true)}
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Record Meter Reading
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Feedback Alerts */}
      {actionSuccess && (
        <div className="p-3 bg-emerald-50 bg-emerald-950/30 border border-emerald-200 border-emerald-800 rounded-lg text-xs text-emerald-800 text-emerald-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            {actionSuccess}
          </span>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-3 bg-rose-50 bg-rose-950/30 border border-rose-200 border-rose-800 rounded-lg text-xs text-rose-800 text-rose-300 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {actionError}
          </span>
          <button onClick={() => setActionError(null)} className="text-rose-600 hover:text-rose-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Total Downtime</span>
            <Clock className="w-5 h-5 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-600 text-rose-400">
            {summary?.total_downtime_hours || 0} hrs
          </div>
          <span className="text-xs text-slate-500">
            {summary?.total_downtime_minutes || 0} mins across {summary?.total_outages_count || 0} outages
          </span>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">DG Generator Runs</span>
            <Fuel className="w-5 h-5 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-600 text-amber-400">
            {summary?.generator_run_count || 0} times
          </div>
          <span className="text-xs text-slate-500">
            {summary?.total_fuel_consumed_liters || 0} L diesel consumed
          </span>
        </Card>

        <Card className="p-4 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Grid EB Power</span>
            <Gauge className="w-5 h-5 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#315C45] text-blue-400">
            {(summary?.total_grid_consumption_kwh || 0).toLocaleString()} kWh
          </div>
          <span className="text-xs text-slate-500">Net recorded grid consumption</span>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase">Solar / Alternative</span>
            <Activity className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-600 text-emerald-400">
            {(summary?.total_solar_consumption_kwh || 0).toLocaleString()} kWh
          </div>
          <span className="text-xs text-slate-500">Generated clean power</span>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#E7E5DE] ">
        <button
          onClick={() => setActiveTab('OUTAGES')}
          className={`py-2 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'OUTAGES'
            ? 'border-[#315C45] text-[#315C45] border-blue-400 text-blue-400'
            : 'border-transparent text-slate-500 hover:text-slate-700 hover:text-slate-300'
            }`}
        >
          <Clock className="w-4 h-4" />
          Daily Power Cut Log ({outages.length})
        </button>

        <button
          onClick={() => setActiveTab('SCRAP')}
          className={`py-2 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'SCRAP'
            ? 'border-[#315C45] text-[#315C45] border-blue-400 text-blue-400'
            : 'border-transparent text-slate-500 hover:text-slate-700 hover:text-slate-300'
            }`}
        >
          <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
          Daily Electricity &amp; Scrap Tracker ({scrapTrackers.length})
        </button>

        <button
          onClick={() => setActiveTab('READINGS')}
          className={`py-2 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'READINGS'
            ? 'border-[#315C45] text-[#315C45] border-blue-400 text-blue-400'
            : 'border-transparent text-slate-500 hover:text-slate-700 hover:text-slate-300'
            }`}
        >
          <Gauge className="w-4 h-4" />
          Electricity Meter Readings ({readings.length})
        </button>
      </div>

      {/* Content based on Active Tab */}
      {activeTab === 'OUTAGES' ? (
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4 justify-between">
            <h2 className="text-sm font-semibold text-slate-800  flex items-center gap-2">
              <Clock className="w-4 h-4 text-rose-500" />
              Power-Cut Interruption Log (60+ Incidents with Restart Delay &amp; Downtime)
            </h2>

            <select
              value={selectedOutageType}
              onChange={(e) => setSelectedOutageType(e.target.value)}
              className="py-1.5 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              <option value="ALL">All Outage Categories</option>
              {Object.entries(OUTAGE_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <DataTable
            columns={outageColumns}
            data={outages}
            isLoading={isLoadingOutages}
            keyExtractor={(row) => row.id}
          />
        </Card>
      ) : activeTab === 'SCRAP' ? (
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4 justify-between items-start sm:items-center">
            <div>
              <h2 className="text-sm font-semibold text-slate-800  flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                Daily Electricity &amp; Scrap Tracker (Production, Scrap Breakdown &amp; Working Hours)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Tracks total production kg, startup &amp; cutting scrap breakdown, electricity off frequency, and downtime
              </p>
            </div>

            <input
              type="text"
              placeholder="Search date, type, reason..."
              value={scrapSearch}
              onChange={(e) => setScrapSearch(e.target.value)}
              className="py-1.5 px-3 text-xs bg-slate-50 border border-[#E7E5DE] rounded-lg w-full sm:w-64"
            />
          </div>

          <DataTable
            columns={scrapTrackerColumns}
            data={scrapTrackers}
            isLoading={isLoadingScrap}
            keyExtractor={(row) => row.id}
          />
        </Card>
      ) : (
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4 justify-between">
            <h2 className="text-sm font-semibold text-slate-800  flex items-center gap-2">
              <Gauge className="w-4 h-4 text-blue-500" />
              Daily Meter Consumption Records
            </h2>

            <select
              value={selectedMeterType}
              onChange={(e) => setSelectedMeterType(e.target.value)}
              className="py-1.5 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            >
              <option value="ALL">All Meter Types</option>
              {Object.entries(METER_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <DataTable
            columns={readingColumns}
            data={readings}
            isLoading={isLoadingReadings}
            keyExtractor={(row) => row.id}
          />
        </Card>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Log Outage Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showOutageModal}
        onClose={() => setShowOutageModal(false)}
        title="Log Power Outage Incident"
      >
        <form onSubmit={handleLogOutage} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Manufacturing Facility
              </label>
              <select
                value={outageForm.unit_id}
                onChange={(e) => setOutageForm({ ...outageForm, unit_id: e.target.value as 'Unit_1' | 'Unit_2' })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                <option value="Unit_1">Unit 1 — Heavy Machining</option>
                <option value="Unit_2">Unit 2 — Assembly &amp; QC</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Outage Category
              </label>
              <select
                value={outageForm.outage_type}
                onChange={(e) => setOutageForm({ ...outageForm, outage_type: e.target.value as OutageType })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                {Object.entries(OUTAGE_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Start Timestamp *
              </label>
              <input
                type="datetime-local"
                value={outageForm.start_time}
                onChange={(e) => setOutageForm({ ...outageForm, start_time: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                End Timestamp *
              </label>
              <input
                type="datetime-local"
                value={outageForm.end_time}
                onChange={(e) => setOutageForm({ ...outageForm, end_time: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Reason / Cause of Outage *
            </label>
            <textarea
              value={outageForm.reason}
              onChange={(e) => setOutageForm({ ...outageForm, reason: e.target.value })}
              placeholder="e.g. Substation 11kV feeder trip, thunderstorm damage, internal breaker trip..."
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg h-16"
              required
            />
          </div>

          <div className="p-3 bg-slate-50  rounded-lg space-y-3 border border-[#E7E5DE] ">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="dg_used"
                checked={outageForm.backup_generator_used}
                onChange={(e) => setOutageForm({ ...outageForm, backup_generator_used: e.target.checked })}
                className="rounded border-[#E7E5DE] text-[#315C45]"
              />
              <label htmlFor="dg_used" className="text-xs font-medium text-slate-700 ">
                Backup Diesel Generator (DG) Was Started
              </label>
            </div>

            {outageForm.backup_generator_used && (
              <div>
                <label className="text-xs font-medium text-slate-600  block mb-1">
                  Estimated Diesel Consumed (Liters)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={outageForm.fuel_consumed_liters}
                  onChange={(e) => setOutageForm({ ...outageForm, fuel_consumed_liters: parseFloat(e.target.value) || 0 })}
                  className="w-full py-1.5 px-3 text-xs bg-white  border border-[#E7E5DE]  rounded-lg"
                />
              </div>
            )}
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600  block mb-1">
              Affected Departments / Lines (comma-separated)
            </label>
            <input
              type="text"
              value={outageForm.affected_departments}
              onChange={(e) => setOutageForm({ ...outageForm, affected_departments: e.target.value })}
              className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#EFEEE8] ">
            <Button type="button" variant="outline" onClick={() => setShowOutageModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? 'Logging...' : 'Confirm Outage Record'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* Record Reading Modal */}
      {/* ------------------------------------------------------------- */}
      <Dialog
        isOpen={showReadingModal}
        onClose={() => setShowReadingModal(false)}
        title="Record Electricity Meter Reading"
      >
        <form onSubmit={handleRecordReading} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Reading Date
              </label>
              <input
                type="date"
                value={readingForm.reading_date}
                onChange={(e) => setReadingForm({ ...readingForm, reading_date: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Facility
              </label>
              <select
                value={readingForm.unit_id}
                onChange={(e) => setReadingForm({ ...readingForm, unit_id: e.target.value as 'Unit_1' | 'Unit_2' })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                <option value="Unit_1">Unit 1 — Heavy Machining</option>
                <option value="Unit_2">Unit 2 — Assembly &amp; QC</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Meter ID *
              </label>
              <input
                type="text"
                value={readingForm.meter_id}
                onChange={(e) => setReadingForm({ ...readingForm, meter_id: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Meter Category
              </label>
              <select
                value={readingForm.meter_type}
                onChange={(e) => setReadingForm({ ...readingForm, meter_type: e.target.value as MeterType })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                {Object.entries(METER_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Opening Reading (kWh) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={readingForm.opening_reading_kwh}
                onChange={(e) => setReadingForm({ ...readingForm, opening_reading_kwh: parseFloat(e.target.value) || 0 })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Closing Reading (kWh) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={readingForm.closing_reading_kwh}
                onChange={(e) => setReadingForm({ ...readingForm, closing_reading_kwh: parseFloat(e.target.value) || 0 })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
                required
              />
            </div>
          </div>

          {readingForm.closing_reading_kwh >= readingForm.opening_reading_kwh && (
            <div className="p-2.5 bg-[#EAF0E9] bg-blue-950/30 border border-[#315C45]/20 border-blue-800 rounded-lg text-xs flex justify-between items-center text-blue-800 text-blue-300">
              <span>Calculated Net Consumption:</span>
              <span className="font-bold font-mono">
                {(readingForm.closing_reading_kwh - readingForm.opening_reading_kwh).toFixed(2)} kWh
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Power Factor
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={readingForm.power_factor}
                onChange={(e) => setReadingForm({ ...readingForm, power_factor: parseFloat(e.target.value) || 0 })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600  block mb-1">
                Shift
              </label>
              <select
                value={readingForm.shift}
                onChange={(e) => setReadingForm({ ...readingForm, shift: e.target.value })}
                className="w-full py-2 px-3 text-xs bg-slate-50  border border-[#E7E5DE]  rounded-lg"
              >
                <option value="General">General Shift</option>
                <option value="Shift 1">Shift 1 (Morning)</option>
                <option value="Shift 2">Shift 2 (Evening)</option>
                <option value="Shift 3">Shift 3 (Night)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#EFEEE8] ">
            <Button type="button" variant="outline" onClick={() => setShowReadingModal(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? 'Recording...' : 'Record Reading'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
