'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/services/api-client';
import { History, RefreshCw, Search, ShieldAlert, Clock } from 'lucide-react';
import { formatISTDateTime, formatRelativeTime } from '@/lib/date';

interface AuditLogRecord {
  id: string;
  action: string;
  actor_email?: string;
  user_email?: string;
  ip_address?: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export default function AuditLogsPage() {
  const { hasPermission } = useAuth();
  const [logs, setLogs] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchAuditLogs = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) setLoading(true);
      const res = await apiClient.get<AuditLogRecord[]>('/api/v1/audit');
      if (res.data) {
        setLogs(res.data);
      }
    } catch {
      // Fallback
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAuditLogs(false);
    // Real-time polling every 8 seconds
    const interval = setInterval(() => {
      fetchAuditLogs(true);
    }, 8000);
    return () => clearInterval(interval);
  }, [fetchAuditLogs]);

  if (!hasPermission('audit', 'read')) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-neutral-200">
        <h3 className="text-lg font-bold text-slate-900">Access Restricted</h3>
        <p className="text-sm text-slate-500 mt-1">You do not have permission to inspect Security Audit Logs.</p>
      </div>
    );
  }

  const filteredLogs = logs.filter((l) => {
    const q = search.toLowerCase().trim();
    if (!q) return true;
    const actor = (l.actor_email || l.user_email || '').toLowerCase();
    const action = (l.action || '').toLowerCase();
    const ip = (l.ip_address || '').toLowerCase();
    return actor.includes(q) || action.includes(q) || ip.includes(q);
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <History className="w-7 h-7 text-[#315C45]" />
            Security Audit Trail
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable log of user logins, role changes, administrative actions, and security operations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAuditLogs(false)}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Card */}
      <Card className="p-4 bg-white border-neutral-200 shadow-xs flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400 shrink-0" />
        <input
          type="text"
          placeholder="Filter logs by actor email, event name, or IP address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full text-sm bg-transparent border-none focus:outline-none placeholder-slate-400"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="text-xs text-slate-400 hover:text-slate-600 px-2 py-1 rounded"
          >
            Clear
          </button>
        )}
      </Card>

      {/* Logs Table */}
      <Card className="bg-white border-neutral-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-[#F8FAFC] border-b border-neutral-200 text-xs font-semibold text-slate-600 uppercase">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Event Action</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filteredLogs.length > 0 ? (
                filteredLogs.map((log) => {
                  const isFailure = log.action.includes('FAIL') || log.action.includes('DENIED');
                  const isLogin = log.action.includes('LOGIN');
                  return (
                    <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4 text-xs font-mono whitespace-nowrap">
                        <div className="font-semibold text-slate-800">
                          {formatISTDateTime(log.timestamp)}
                        </div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Clock className="w-2.5 h-2.5 text-slate-300" />
                          <span>{formatRelativeTime(log.timestamp)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={isFailure ? 'error' : isLogin ? 'success' : 'neutral'}
                        >
                          {log.action}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        {log.actor_email || log.user_email || 'System'}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-slate-500">
                        {log.ip_address || '-'}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-600 max-w-xs truncate font-mono">
                        {log.details ? JSON.stringify(log.details) : '-'}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <ShieldAlert className="w-8 h-8 text-slate-300" />
                      <p className="text-sm font-medium">No audit events found</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
