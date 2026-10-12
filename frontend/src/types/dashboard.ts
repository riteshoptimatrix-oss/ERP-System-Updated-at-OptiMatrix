export interface KpiMetricItem {
  title: string;
  value: number;
  pending_action_count: number;
  unit_id: string;
  module: string;
  permitted: boolean;
  subtitle?: string;
}

export interface RecentActivityItem {
  id: string;
  module: string;
  action: string;
  description: string;
  timestamp: string;
  user_email?: string;
  unit_id?: string;
  status: string;
}

export interface DashboardSummaryResponse {
  active_unit: 'Unit_1' | 'Unit_2';
  timestamp: string;
  kpis: {
    orders?: KpiMetricItem | null;
    dispatch?: KpiMetricItem | null;
    stock?: KpiMetricItem | null;
    production?: KpiMetricItem | null;
    qc?: KpiMetricItem | null;
    wastage?: KpiMetricItem | null;
    attendance?: KpiMetricItem | null;
    approvals?: KpiMetricItem | null;
    [key: string]: KpiMetricItem | null | undefined;
  };
  total_permitted_kpis: number;
}

export interface DashboardActivityResponse {
  active_unit: 'Unit_1' | 'Unit_2';
  activities: RecentActivityItem[];
}
