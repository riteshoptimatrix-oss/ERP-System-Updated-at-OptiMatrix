import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'neutral';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'neutral',
  ...props
}) => {
  const variants = {
    success: 'bg-[#DCFCE7] text-[#15803D] border-[#15803D]/20',
    warning: 'bg-[#FEF3C7] text-[#B45309] border-[#B45309]/20',
    error: 'bg-[#FEE2E2] text-[#B91C1C] border-[#B91C1C]/20',
    neutral: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border font-mono',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
