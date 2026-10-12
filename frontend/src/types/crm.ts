import { ManufacturingUnit } from './auth';

export type LeadStatus =
  | 'NEW'
  | 'CONTACTED'
  | 'QUALIFIED'
  | 'PROPOSAL_SENT'
  | 'NEGOTIATION'
  | 'CONVERTED'
  | 'LOST';

export type LeadPriority = 'HOT' | 'WARM' | 'COLD';

export type LeadSource =
  | 'DIRECT_INQUIRY'
  | 'TRADE_EXPO'
  | 'WEBSITE'
  | 'REFERRAL'
  | 'COLD_CALL'
  | 'EXISTING_CLIENT';

export type ActivityType =
  | 'CALL'
  | 'EMAIL'
  | 'MEETING'
  | 'SITE_VISIT'
  | 'NOTE'
  | 'STATUS_CHANGE';

export interface LeadActivity {
  id: string;
  lead_id: string;
  activity_type: ActivityType;
  summary: string;
  details?: string;
  next_follow_up?: string;
  created_at: string;
  created_by: string;
}

export interface Lead {
  id: string;
  code: string;
  company_name: string;
  contact_person: string;
  email?: string;
  phone: string;
  source: LeadSource;
  status: LeadStatus;
  priority: LeadPriority;
  assigned_to?: string;
  estimated_value: number;
  machine_interest?: string;
  unit_id: ManufacturingUnit;
  next_follow_up?: string;
  notes?: string;
  converted_customer_id?: string;
  converted_at?: string;
  created_at: string;
  created_by: string;
  updated_at?: string;
  updated_by?: string;
  activities?: LeadActivity[];
}

export interface LeadConvertPayload {
  customer_code: string;
  gstin?: string;
  pan?: string;
  billing_address?: string;
  shipping_address?: string;
  credit_limit: number;
  payment_terms_days: number;
  unit_id: ManufacturingUnit;
}

export interface CrmDashboardSummary {
  total_leads: number;
  active_leads: number;
  hot_leads: number;
  converted_leads: number;
  conversion_rate_percentage: number;
  pipeline_by_status: Record<string, number>;
  follow_ups_due_today: number;
  follow_ups_overdue: number;
}
