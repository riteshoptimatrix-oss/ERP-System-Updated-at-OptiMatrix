'use client';

import React from 'react';
import { Button } from '@/components/ui/Button';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white  border border-rose-200 border-rose-900/50 rounded-xl p-6 shadow-sm text-center space-y-4">
        <div className="h-12 w-12 rounded-full bg-rose-100 bg-rose-950/60 text-rose-600 text-rose-400 mx-auto flex items-center justify-center text-xl font-bold">
          !
        </div>
        <h2 className="text-xl font-bold text-slate-900 ">
          Application Error
        </h2>
        <p className="text-sm text-slate-500 ">
          {error.message || 'An unexpected error occurred while rendering the interface.'}
        </p>
        <div className="pt-2">
          <Button variant="primary" onClick={() => reset()}>
            Retry Action
          </Button>
        </div>
      </div>
    </div>
  );
}
