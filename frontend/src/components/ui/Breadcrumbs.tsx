'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';

export const Breadcrumbs: React.FC = () => {
  const pathname = usePathname();

  if (pathname === '/login') return null;

  const segments = pathname.split('/').filter(Boolean);

  const formatSegment = (str: string) => {
    return str
      .replace(/-/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  return (
    <nav aria-label="Breadcrumb" className="flex items-center space-x-1.5 text-xs text-[#73786F] mb-6">
      <Link
        href="/"
        className="flex items-center gap-1 hover:text-[#315C45] transition-colors"
      >
        <Home className="h-3.5 w-3.5" />
        <span>Dashboard</span>
      </Link>

      {segments.map((segment, idx) => {
        const isLast = idx === segments.length - 1;
        const href = `/${segments.slice(0, idx + 1).join('/')}`;

        return (
          <React.Fragment key={href}>
            <ChevronRight className="h-3 w-3 text-[#8A8F87]" />
            {isLast ? (
              <span className="font-semibold text-[#202722]">
                {formatSegment(segment)}
              </span>
            ) : (
              <Link href={href} className="hover:text-[#315C45] transition-colors">
                {formatSegment(segment)}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
