import React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  title,
  subtitle,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-[#FFFFFF] border border-[#E2E8F0] rounded-xl p-6 shadow-card',
        className
      )}
      {...props}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="text-base font-semibold text-[#0F172A]">{title}</h3>}
          {subtitle && <p className="text-xs text-[#64748B] mt-1">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
};
