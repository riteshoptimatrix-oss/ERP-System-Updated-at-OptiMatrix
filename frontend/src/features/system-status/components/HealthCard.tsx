'use client';

import React from 'react';
import { useSystemHealth } from '../hooks/useSystemHealth';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export const HealthCard: React.FC = () => {
  const { liveness, readiness, isLoading, error, lastChecked, refetch } = useSystemHealth();

  const isLive = liveness?.status === 'healthy';
  const isReady = readiness?.status === 'ready';
  const dbStatus = readiness?.dependencies?.mongodb?.status;

  return (
    <Card
      title="System Connectivity & Diagnostics"
      subtitle="Real-time status of backend services and database connections"
      className="shadow-sm border-[#E7E5DE] "
    >
      <div className="space-y-4">
        {/* Status Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* FastAPI Liveness */}
          <div className="p-4 rounded-lg bg-slate-50 /50 border border-[#EFEEE8]  flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 ">
                FastAPI Backend
              </span>
              <Badge variant={isLive ? 'success' : 'error'}>
                {isLive ? 'Online' : 'Offline'}
              </Badge>
            </div>
            <div className="text-sm font-medium text-slate-800 ">
              {liveness ? `Env: ${liveness.environment}` : 'Connecting...'}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {liveness ? `API v${liveness.version}` : 'Liveness Probe'}
            </div>
          </div>

          {/* Service Readiness */}
          <div className="p-4 rounded-lg bg-slate-50 /50 border border-[#EFEEE8]  flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 ">
                Readiness State
              </span>
              <Badge variant={isReady ? 'success' : 'warning'}>
                {isReady ? 'Ready' : 'Not Ready'}
              </Badge>
            </div>
            <div className="text-sm font-medium text-slate-800 ">
              {isReady ? 'Accepting Traffic' : 'Initializing Dependencies'}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Readiness Probe
            </div>
          </div>

          {/* MongoDB Status */}
          <div className="p-4 rounded-lg bg-slate-50 /50 border border-[#EFEEE8]  flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 ">
                MongoDB Cluster
              </span>
              <Badge
                variant={
                  dbStatus === 'connected'
                    ? 'success'
                    : dbStatus === 'degraded'
                    ? 'warning'
                    : 'error'
                }
              >
                {dbStatus ? dbStatus.toUpperCase() : 'UNKNOWN'}
              </Badge>
            </div>
            <div className="text-sm font-medium text-slate-800 ">
              {readiness?.dependencies?.mongodb?.latency_ms !== undefined
                ? `${readiness.dependencies.mongodb.latency_ms} ms ping`
                : 'Connection Check'}
            </div>
            <div className="text-xs text-slate-500 mt-1 truncate" title={readiness?.dependencies?.mongodb?.details}>
              {readiness?.dependencies?.mongodb?.details || 'Database Probe'}
            </div>
          </div>
        </div>

        {/* Error message banner if degraded */}
        {error && (
          <div className="p-3 rounded-lg bg-amber-50 bg-amber-950/30 border border-amber-200 border-amber-800 text-xs text-amber-800 text-amber-300">
            <strong>Diagnostic Notice:</strong> {error}
          </div>
        )}

        {/* Footer info & manual re-check */}
        <div className="flex flex-col sm:flex-row items-center justify-between pt-2 border-t border-[#EFEEE8]  text-xs text-slate-500">
          <span>
            {lastChecked
              ? `Last checked: ${lastChecked.toLocaleTimeString()}`
              : 'Checking status...'}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
            className="mt-2 sm:mt-0"
          >
            {isLoading ? 'Checking...' : 'Refresh Status'}
          </Button>
        </div>
      </div>
    </Card>
  );
};
