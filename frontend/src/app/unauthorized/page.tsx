'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-[500px] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white  border border-[#E7E5DE]  rounded-2xl p-8 shadow-sm text-center space-y-4">
        <div className="h-14 w-14 rounded-2xl bg-amber-50 bg-amber-950/50 text-amber-600 text-amber-400 mx-auto flex items-center justify-center">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 ">
          Access Restricted
        </h2>
        <p className="text-sm text-slate-500 ">
          Your current account role does not possess the permissions required to view or perform operations in this manufacturing module.
        </p>
        <div className="p-3 rounded-lg bg-slate-50 /50 border border-[#EFEEE8]  text-xs text-slate-600  text-left">
          <strong>Security Notice:</strong> Cross-module or cross-unit operations must be granted by a System Super Admin.
        </div>
        <div className="pt-2">
          <Link href="/">
            <Button variant="primary" className="flex items-center gap-2 mx-auto">
              <ArrowLeft className="h-4 w-4" />
              Return to Authorized Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
