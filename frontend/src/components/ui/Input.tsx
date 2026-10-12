import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-semibold text-[#0F172A] mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full px-3 py-2 text-xs rounded-lg border bg-[#FFFFFF] text-[#0F172A] placeholder-[#94A3B8] transition-all focus:outline-none focus:ring-1 focus:ring-[#0F172A] ${error ? 'border-rose-400 focus:border-rose-500' : 'border-[#CBD5E1] focus:border-[#0F172A]'
            } ${className}`}
          {...props}
        />
        {error && (
          <span className="text-[11px] text-rose-600 mt-1 block">{error}</span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
