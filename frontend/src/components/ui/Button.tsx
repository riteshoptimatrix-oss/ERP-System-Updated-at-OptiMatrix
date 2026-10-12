import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-[#0F172A] hover:bg-[#1E293B] text-white focus:ring-[#0F172A] shadow-xs font-semibold',
    secondary: 'bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#0F172A] border border-[#E2E8F0] focus:ring-[#0F172A]',
    outline: 'border border-[#E2E8F0] bg-[#FFFFFF] hover:bg-[#F1F5F9] text-[#0F172A] focus:ring-[#0F172A]',
    danger: 'bg-[#B91C1C] hover:bg-[#991B1B] text-white focus:ring-[#B91C1C] shadow-xs font-semibold',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
