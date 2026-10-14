export type MeterType = 'GRID_EB' | 'DIESEL_GENERATOR' | 'SOLAR';

export type OutageType =
  | 'GRID_FAILURE'
  | 'SCHEDULED_MAINTENANCE'
  | 'EMERGENCY_SHUTDOWN'
  | 'GENERATOR_FAILURE'
  | 'LOCAL_TRIP';

export interface ElectricityReading {
  id: string;
  reading_number: string;
  reading_date: string;
  unit_id: string;
  meter_id: string;
  meter_type: MeterType;
  opening_reading_kwh: number;
  closing_reading_kwh: number;
  units_consumed_kwh: number;
  power_factor?: number | null;
  shift?: string | null;
  remarks?: string | null;
  status: string;
  created_at: string;
  created_by: string;
}

export interface ElectricityReadingCreateInput {
  reading_date: string;
  unit_id: 'Unit_1' | 'Unit_2';
  meter_id: string;
  meter_type: MeterType;
  opening_reading_kwh: number;
  closing_reading_kwh: number;
  power_factor?: number | null;
  shift?: string;
  remarks?: string;
}

export interface PowerCutLog {
  id: string;
  incident_number: string;
  unit_id: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  outage_type: OutageType;
  reason: string;
  backup_generator_used: boolean;
  fuel_consumed_liters?: number | null;
  affected_departments: string[];
  production_order_ids: string[];
  restart_delay_minutes?: number | null;
  downtime_duration_str?: string | null;
  power_cut_time?: string | null;
  power_restored_time?: string | null;
  incident_date?: string | null;
  remarks?: string | null;
  created_at: string;
  created_by: string;
}

export interface PowerCutLogCreateInput {
  unit_id: 'Unit_1' | 'Unit_2';
  start_time: string;
  end_time: string;
  outage_type: OutageType;
  reason: string;
  backup_generator_used: boolean;
  fuel_consumed_liters?: number | null;
  affected_departments: string[];
  production_order_ids?: string[];
  restart_delay_minutes?: number | null;
  downtime_duration_str?: string | null;
  power_cut_time?: string | null;
  power_restored_time?: string | null;
  incident_date?: string | null;
  remarks?: string;
}

export interface DailyElectricityScrapTracker {
  id: string;
  date: string;
  total_production_kg: number;
  product_type: string;
  startup_scrap_kg: number;
  cutting_scrap_kg: number;
  total_scrap_kg: number;
  scrap_percent_str: string;
  electricity_off_count: number;
  total_off_time_min: number;
  machine_working_hours: string;
  shift_duration_hr: number;
  main_reason?: string | null;
  remarks?: string | null;
  unit_id: string;
  created_at?: string;
}

export interface PowerSummary {
  unit_id?: string | null;
  total_outages_count: number;
  total_downtime_minutes: number;
  total_downtime_hours: number;
  generator_run_count: number;
  total_fuel_consumed_liters: number;
  total_grid_consumption_kwh: number;
  total_dg_consumption_kwh: number;
  total_solar_consumption_kwh: number;
}

