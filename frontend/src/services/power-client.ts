import { apiClient } from './api-client';
import {
  ElectricityReading,
  ElectricityReadingCreateInput,
  PowerCutLog,
  PowerCutLogCreateInput,
  PowerSummary,
} from '@/types/power';
import { PaginatedResponse } from '@/types/master';

export interface ListReadingsParams {
  unit_id?: string;
  meter_id?: string;
  meter_type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface ListOutagesParams {
  unit_id?: string;
  outage_type?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export const powerClient = {
  /**
   * Fetch power analytics & downtime summary
   */
  async getSummary(unit_id?: string): Promise<PowerSummary> {
    const query = unit_id ? `?unit_id=${unit_id}` : '';
    const res = await apiClient.get<PowerSummary>(`/power/summary${query}`);
    if (!res.data) throw new Error('Failed to retrieve power analytics summary');
    return res.data;
  },

  /**
   * List electricity meter readings
   */
  async listReadings(params: ListReadingsParams = {}): Promise<PaginatedResponse<ElectricityReading>> {
    const query = new URLSearchParams();
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.meter_id) query.append('meter_id', params.meter_id);
    if (params.meter_type) query.append('meter_type', params.meter_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<ElectricityReading>>(`/power/readings${qs}`);
    if (!res.data) throw new Error('Failed to retrieve electricity readings');
    return res.data;
  },

  /**
   * Record new electricity reading
   */
  async recordReading(input: ElectricityReadingCreateInput): Promise<ElectricityReading> {
    const res = await apiClient.post<ElectricityReading>('/power/readings', input);
    if (!res.data) throw new Error('Failed to record electricity reading');
    return res.data;
  },

  /**
   * List power-cut / downtime records
   */
  async listOutages(params: ListOutagesParams = {}): Promise<PaginatedResponse<PowerCutLog>> {
    const query = new URLSearchParams();
    if (params.unit_id) query.append('unit_id', params.unit_id);
    if (params.outage_type) query.append('outage_type', params.outage_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<PaginatedResponse<PowerCutLog>>(`/power/outages${qs}`);
    if (!res.data) throw new Error('Failed to retrieve power outages');
    return res.data;
  },

  /**
   * Log new power-cut incident
   */
  async logOutage(input: PowerCutLogCreateInput): Promise<PowerCutLog> {
    const res = await apiClient.post<PowerCutLog>('/power/outages', input);
    if (!res.data) throw new Error('Failed to log power outage incident');
    return res.data;
  },
};
