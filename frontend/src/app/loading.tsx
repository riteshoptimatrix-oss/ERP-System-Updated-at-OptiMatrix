import React from 'react';

export default function Loading() {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-6">
      <div className="flex flex-col items-center space-y-3">
        <div className="w-8 h-8 border-4 border-[#315C45] border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500  font-medium">
          Loading Opti Matrix ERP...
        </p>
      </div>
    </div>
  );
}
