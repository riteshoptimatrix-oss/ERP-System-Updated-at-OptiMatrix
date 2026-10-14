'use client';

import React from 'react';
import { usePathname } from 'next/navigation';

export const Footer: React.FC = () => {
  const pathname = usePathname();
  if (pathname === '/login') return null;

  return (
    <footer className="border-t border-[#E7E5DE] bg-[#FFFFFF] py-6 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-[#73786F] gap-4">
        <div>
          &copy;2023 Opti Matrix Inc. All rights reserved.
        </div>
        <div className="flex items-center space-x-6">
          <span>Unit 1 &bull; Heavy Machining & Fabrication</span>
          <span>Unit 2 &bull; Precision Assembly & QC</span>
        </div>
      </div>
    </footer>
  );
};
