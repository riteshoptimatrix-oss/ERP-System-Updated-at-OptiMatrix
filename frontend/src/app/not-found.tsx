import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export default function NotFound() {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white  border border-[#E7E5DE]  rounded-xl p-6 shadow-sm text-center space-y-4">
        <h2 className="text-3xl font-extrabold text-slate-900 ">
          404
        </h2>
        <h3 className="text-lg font-semibold text-slate-800 ">
          Page Not Found
        </h3>
        <p className="text-sm text-slate-500 ">
          The requested manufacturing module or resource does not exist.
        </p>
        <div className="pt-2">
          <Link href="/">
            <Button variant="primary">Return Home</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
