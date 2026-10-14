'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { employeeClient } from '@/services/employee-client';
import { NotificationItem, AnnouncementItem } from '@/types/employee';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Bell,
  Megaphone,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Clock,
  Check,
  MailCheck,
  Plus,
} from 'lucide-react';
import { formatISTDateTime, formatRelativeTime } from '@/lib/date';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

export default function EmployeeNotificationsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [activeTab, setActiveTab] = useState<'notifications' | 'announcements'>('notifications');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isMarkingAll, setIsMarkingAll] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const [notifs, anncs] = await Promise.all([
        employeeClient.listNotifications(),
        employeeClient.listAnnouncements(),
      ]);
      setNotifications(notifs);
      setAnnouncements(anncs);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load notifications');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await employeeClient.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to mark as read');
    }
  };

  const handleMarkAllRead = async () => {
    setIsMarkingAll(true);
    try {
      await employeeClient.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setSuccessMessage('All notifications marked as read.');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to mark all as read');
    } finally {
      setIsMarkingAll(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] p-6 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
              Communications & Alerts
            </span>
            {unreadCount > 0 && (
              <Badge variant="warning" className="text-[10px] bg-amber-50 text-amber-700 border-amber-200">
                {unreadCount} Unread
              </Badge>
            )}
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Notifications & Corporate Bulletins
          </h1>
          <p className="text-xs text-[#64748B]">
            Leave approvals, task dispatches, safety notices, and factory announcements from management.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isSuperAdmin && (
            <Button
              size="sm"
              onClick={() => router.push('/announcements')}
              className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5 font-semibold shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              Create Announcement
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={isLoading}
            className="text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {unreadCount > 0 && activeTab === 'notifications' && (
            <Button
              size="sm"
              onClick={handleMarkAllRead}
              disabled={isMarkingAll}
              className="text-xs bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
            >
              <MailCheck className="w-3.5 h-3.5" />
              Mark All as Read
            </Button>
          )}
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-2 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('notifications')}
          className={`px-4 py-2 font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'notifications'
            ? 'bg-[#0F172A] text-white shadow-xs'
            : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
            }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>Personal Alerts ({notifications.length})</span>
          {unreadCount > 0 && (
            <span className="bg-amber-400 text-slate-900 text-[10px] font-bold px-1.5 py-0.2 rounded-full">
              {unreadCount}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('announcements')}
          className={`px-4 py-2 font-semibold rounded-lg transition-all flex items-center gap-2 ${activeTab === 'announcements'
            ? 'bg-[#0F172A] text-white shadow-xs'
            : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
            }`}
        >
          <Megaphone className="w-3.5 h-3.5" />
          <span>Factory Announcements ({announcements.length})</span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'notifications' ? (
        <Card title="Activity & Workflow Alerts">
          {notifications.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#64748B]">
              No notifications yet. You are completely up to date.
            </div>
          ) : (
            <div className="divide-y divide-[#E2E8F0]">
              {notifications.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 flex items-start justify-between gap-3 transition-colors ${item.is_read ? 'bg-[#FFFFFF]' : 'bg-[#F8FAFC]'
                    }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-2 rounded-xl mt-0.5 shrink-0 ${item.notification_type === 'SUCCESS' ? 'bg-emerald-50 text-emerald-700' :
                        item.notification_type === 'ALERT' || item.notification_type === 'WARNING' ? 'bg-rose-50 text-rose-700' :
                          'bg-blue-50 text-blue-700'
                        }`}
                    >
                      <Bell className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className={`text-xs ${item.is_read ? 'font-medium text-[#0F172A]' : 'font-bold text-[#0F172A]'}`}>
                          {item.title}
                        </h3>
                        {!item.is_read && (
                          <span className="h-2 w-2 rounded-full bg-blue-600 inline-block" />
                        )}
                      </div>
                      <p className="text-xs text-[#64748B] mt-0.5">
                        {item.message}
                      </p>
                      <div className="flex items-center gap-1.5 text-[10px] text-[#94A3B8] mt-1 font-mono">
                        <Clock className="w-3 h-3" />
                        <span>{formatISTDateTime(item.created_at)}</span>
                        <span>&bull;</span>
                        <span>{formatRelativeTime(item.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {!item.is_read && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleMarkAsRead(item.id)}
                      className="h-7 text-[11px] shrink-0 border-[#CBD5E1] text-[#0F172A] hover:bg-[#FFFFFF]"
                    >
                      <Check className="w-3 h-3 mr-1" />
                      Mark Read
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {announcements.length === 0 ? (
            <Card className="p-12 text-center text-xs text-[#64748B]">
              No factory announcements posted at this time.
            </Card>
          ) : (
            announcements.map((ann) => (
              <Card key={ann.id} className={`p-6 border-l-4 transition-all ${ann.is_read ? 'border-l-[#CBD5E1]' : 'border-l-[#0F172A] bg-[#FFFFFF]'}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#F1F5F9] text-[#0F172A] font-bold border border-[#E2E8F0]">
                      {ann.unit_id === 'Unit_1' ? 'UNIT 1 (MACHINING)' : ann.unit_id === 'Unit_2' ? 'UNIT 2 (ASSEMBLY)' : 'COMPANY WIDE'}
                    </span>

                    {ann.audience_type === 'specific' ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 font-semibold border border-amber-200">
                        DIRECT NOTICE TO YOU
                      </span>
                    ) : ann.audience_type === 'department' ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-800 font-semibold border border-blue-200">
                        DEPARTMENT NOTICE
                      </span>
                    ) : null}

                    <Badge variant="neutral" className="text-[10px]">
                      {ann.priority || 'NORMAL'}
                    </Badge>
                  </div>
                  <span className="text-[11px] text-[#64748B] font-mono">
                    {formatISTDateTime(ann.published_at || ann.created_at)}
                  </span>
                </div>

                <h3 className="text-base font-bold text-[#0F172A] mb-2">
                  {ann.title}
                </h3>
                <p className="text-xs text-[#475569] leading-relaxed whitespace-pre-line">
                  {ann.message || ann.content}
                </p>

                <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#64748B]">
                  <span>Published by: <span className="font-semibold text-[#0F172A]">{ann.author_name || 'Management Office'}</span></span>
                  <div className="flex items-center gap-3">
                    <span>Opti Matrix Manufacturing Operations</span>
                    {!ann.is_read && (
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await employeeClient.markAnnouncementRead(ann.id);
                            setAnnouncements((prev) =>
                              prev.map((a) => (a.id === ann.id ? { ...a, is_read: true } : a))
                            );
                          } catch {
                            // silent
                          }
                        }}
                        className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded transition-colors"
                      >
                        Acknowledge / Mark Read
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
