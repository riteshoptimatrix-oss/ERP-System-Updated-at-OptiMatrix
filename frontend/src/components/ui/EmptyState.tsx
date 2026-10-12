import React from 'react';
import { LucideIcon, PackageOpen } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = PackageOpen,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`p-8 text-center rounded-xl border border-dashed border-[#E7E5DE]  bg-slate-50/50 /40 ${className}`}>
      <div className="mx-auto h-12 w-12 rounded-xl bg-slate-100  text-slate-500 flex items-center justify-center mb-3">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-sm font-bold text-slate-900 ">
        {title}
      </h3>
      <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="primary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
