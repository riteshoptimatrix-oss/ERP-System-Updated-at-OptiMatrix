'use client';

import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { Button } from './Button';

interface FilterBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  placeholder?: string;
  onReset?: () => void;
  children?: React.ReactNode;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchQuery,
  onSearchChange,
  placeholder = 'Search by batch #, SKU, or keyword...',
  onReset,
  children,
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-[#FFFFFF] border border-[#E2E8F0] rounded-xl shadow-card">
      {/* Search Input */}
      <div className="relative flex-1 min-w-[240px]">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#64748B]">
          <Search className="h-4 w-4" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[#E2E8F0] bg-[#FFFFFF] text-[#0F172A] placeholder-[#94A3B8] focus:outline-none focus:ring-1 focus:ring-[#0F172A] focus:border-[#0F172A]"
        />
      </div>

      {/* Extra Filters (dropdowns, unit pills) */}
      {children && (
        <div className="flex items-center gap-2 flex-wrap">
          {children}
        </div>
      )}

      {/* Reset button */}
      {onReset && (
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          className="flex items-center gap-1.5 text-xs shrink-0"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </Button>
      )}
    </div>
  );
};
