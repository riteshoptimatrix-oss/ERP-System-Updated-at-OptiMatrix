import React from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LucideIcon, Lock, ArrowUpRight } from 'lucide-react';
import { KpiMetricItem } from '@/types/dashboard';

interface KpiCardProps {
  kpi?: KpiMetricItem | null;
  defaultTitle: string;
  defaultSubtitle?: string;
  icon: LucideIcon;
  isLoading?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  kpi,
  defaultTitle,
  defaultSubtitle,
  icon: Icon,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <Card className="animate-pulse space-y-3 bg-[#FFFFFF] border-[#E7E5DE]">
        <div className="flex justify-between items-start">
          <div className="h-4 bg-[#F1F0EA] rounded w-24" />
          <div className="h-8 w-8 bg-[#F1F0EA] rounded-lg" />
        </div>
        <div className="h-8 bg-[#F1F0EA] rounded w-16" />
        <div className="h-3 bg-[#F1F0EA] rounded w-32" />
      </Card>
    );
  }

  // Unauthorized / Masked state: do not show restricted cards
  if (!kpi || kpi.permitted === false) {
    return null;
  }

  const title = kpi?.title || defaultTitle;
  const subtitle = kpi?.subtitle || defaultSubtitle;
  const value = kpi?.value ?? 0;
  const pending = kpi?.pending_action_count ?? 0;

  return (
    <Card className="relative hover:shadow-card-elevated transition-all group border-[#E2E8F0] bg-[#FFFFFF]">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
            {title}
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-[#0F172A]">
              {value}
            </span>
            {pending > 0 && (
              <Badge variant="warning" className="text-[10px] px-1.5 py-0.5">
                {pending} pending
              </Badge>
            )}
          </div>
        </div>
        <div className="p-2.5 rounded-xl bg-[#F1F5F9] text-[#0F172A] group-hover:bg-[#0F172A] group-hover:text-white transition-colors">
          <Icon className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-[11px] text-[#64748B]">
        <span className="truncate">{subtitle}</span>
        <ArrowUpRight className="h-3 w-3 text-[#94A3B8] shrink-0" />
      </div>
    </Card>
  );
};
