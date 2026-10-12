'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { employeeClient } from '@/services/employee-client';
import { AttendanceCorrectionResponseItem } from '@/types/employee';
import { AttendanceEntry } from '@/types/hr';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  CalendarCheck,
  Clock,
  LogIn,
  LogOut,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileEdit,
  Send,
} from 'lucide-react';
import { formatISTDate, formatISTTime } from '@/lib/date';

export default function EmployeeAttendancePage() {
  const [history, setHistory] = useState<AttendanceEntry[]>([]);
  const [corrections, setCorrections] = useState<AttendanceCorrectionResponseItem[]>([]);
  const [todayEntry, setTodayEntry] = useState<AttendanceEntry | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPunching, setIsPunching] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'history' | 'corrections'>('history');

  // Live IST Clock
  const [liveClockIST, setLiveClockIST] = useState<string>('');

  // Messages
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  // Correction Modal State
  const [showCorrectionModal, setShowCorrectionModal] = useState<boolean>(false);
  const [correctionDate, setCorrectionDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [reqCheckIn, setReqCheckIn] = useState<string>('09:00');
  const [reqCheckOut, setReqCheckOut] = useState<string>('18:00');
  const [reqStatus, setReqStatus] = useState<string>('PRESENT');
  const [correctionReason, setCorrectionReason] = useState<string>('');
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState<boolean>(false);

  // Live IST Ticking
  useEffect(() => {
    const tick = () => {
      setLiveClockIST(formatISTTime(new Date(), true, true));
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const todayStr = new Date().toISOString().slice(0, 10);
      const [histRes, corrRes, todayRes] = await Promise.all([
        employeeClient.getAttendanceHistory({ page_size: 50 }),
        employeeClient.listAttendanceCorrections(),
        employeeClient.getAttendanceHistory({ date: todayStr }).catch(() => null),
      ]);

      setHistory(histRes.items || []);
      setCorrections(corrRes || []);
      if (todayRes && todayRes.items && todayRes.items.length > 0) {
        setTodayEntry(todayRes.items[0]);
      } else {
        setTodayEntry(null);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to fetch attendance data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCheckIn = async () => {
    setIsPunching(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const res = await employeeClient.checkIn();
      setTodayEntry(res);
      setSuccessMessage('Shift check-in recorded successfully at ' + formatISTTime(new Date(), false, false) + ' IST');
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Check-in failed');
    } finally {
      setIsPunching(false);
    }
  };

  const handleCheckOut = async () => {
    setIsPunching(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const res = await employeeClient.checkOut();
      setTodayEntry(res);
      setSuccessMessage('Shift check-out recorded successfully at ' + formatISTTime(new Date(), false, false) + ' IST');
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Check-out failed');
    } finally {
      setIsPunching(false);
    }
  };

  const handleCorrectionSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!correctionDate || !correctionReason.trim()) {
      setErrorMessage('Please select a date and enter an explanatory reason.');
      return;
    }

    setIsSubmittingCorrection(true);
    setErrorMessage('');
    try {
      await employeeClient.submitAttendanceCorrection({
        date: correctionDate,
        requested_check_in: reqCheckIn || undefined,
        requested_check_out: reqCheckOut || undefined,
        requested_status: reqStatus,
        reason: correctionReason.trim(),
      });
      setSuccessMessage('Attendance regularization request submitted to supervisor successfully.');
      setShowCorrectionModal(false);
      setCorrectionReason('');
      await loadData();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to submit correction request');
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] p-6 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
              Attendance & Shift Compliance
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
              LIVE IST
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            My Attendance Record
          </h1>
          <p className="text-xs text-[#64748B]">
            Punch-in / punch-out timestamps, daily working hours, overtime credits, and shift regularization requests.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-sm font-mono font-bold text-[#0F172A] block">
              {liveClockIST || 'Syncing IST...'}
            </span>
            <span className="text-[10px] text-[#64748B] uppercase font-mono">
              IST (UTC+05:30)
            </span>
          </div>
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
        </div>
      </div>

      {/* Alert Banners */}
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

      {/* Today's Punch Widget */}
      <Card title="Today's Shift Attendance Widget">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-2">
          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
            <span className="text-[#64748B] text-xs block mb-1">Check-In Punch</span>
            <span className="text-base font-mono font-bold text-[#0F172A]">
              {todayEntry?.check_in ? formatISTTime(todayEntry.check_in, true, false) : 'Not Checked In'}
            </span>
            <div className="mt-2">
              <Button
                size="sm"
                onClick={handleCheckIn}
                disabled={isPunching || Boolean(todayEntry?.check_in)}
                className="w-full text-xs bg-emerald-700 hover:bg-emerald-800 text-white flex items-center justify-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                {todayEntry?.check_in ? 'Checked In' : 'Punch In'}
              </Button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
            <span className="text-[#64748B] text-xs block mb-1">Check-Out Punch</span>
            <span className="text-base font-mono font-bold text-[#0F172A]">
              {todayEntry?.check_out ? formatISTTime(todayEntry.check_out, true, false) : 'Active Shift'}
            </span>
            <div className="mt-2">
              <Button
                size="sm"
                onClick={handleCheckOut}
                disabled={isPunching || !todayEntry?.check_in || Boolean(todayEntry?.check_out)}
                className="w-full text-xs bg-amber-700 hover:bg-amber-800 text-white flex items-center justify-center gap-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                {todayEntry?.check_out ? 'Checked Out' : 'Punch Out'}
              </Button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
            <span className="text-[#64748B] text-xs block mb-1">Total Shift Hours</span>
            <span className="text-xl font-mono font-bold text-[#0F172A]">
              {(todayEntry?.hours_worked || 0).toFixed(2)} hrs
            </span>
            <span className="text-[11px] text-[#64748B] block mt-1">
              Overtime: <span className="font-semibold text-emerald-700">{(todayEntry?.overtime_hours || 0).toFixed(2)} hrs</span>
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex flex-col justify-between">
            <div>
              <span className="text-[#64748B] text-xs block mb-1">Shift Regularization</span>
              <span className="text-xs text-[#0F172A]">
                Missed a biometric punch or worked remote?
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCorrectionModal(true)}
              className="w-full text-xs flex items-center justify-center gap-1.5 border-[#CBD5E1] text-[#0F172A] hover:bg-[#FFFFFF]"
            >
              <FileEdit className="w-3.5 h-3.5" />
              Regularize Punch
            </Button>
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all ${activeTab === 'history'
            ? 'bg-[#0F172A] text-white'
            : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
            }`}
        >
          Attendance Log ({history.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('corrections')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all ${activeTab === 'corrections'
            ? 'bg-[#0F172A] text-white'
            : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F1F5F9]'
            }`}
        >
          Regularization Requests ({corrections.length})
        </button>
      </div>

      {/* Tab 1: History Log */}
      {activeTab === 'history' && (
        <Card title="Attendance Records">
          {history.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#64748B]">
              No attendance records found. Check in for your shift above.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0]">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Date</th>
                    <th className="py-2.5 px-3 font-semibold">Shift In</th>
                    <th className="py-2.5 px-3 font-semibold">Shift Out</th>
                    <th className="py-2.5 px-3 font-semibold">Total Hours</th>
                    <th className="py-2.5 px-3 font-semibold">Overtime</th>
                    <th className="py-2.5 px-3 font-semibold">Status</th>
                    <th className="py-2.5 px-3 font-semibold">Facility</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  {history.map((record) => (
                    <tr key={record.id || `${record.employee_id}-${record.date}`} className="hover:bg-[#F8FAFC]/80">
                      <td className="py-2.5 px-3 font-mono font-medium text-[#0F172A]">
                        {record.date}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {record.check_in ? formatISTTime(record.check_in, true, false) : '—'}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {record.check_out ? formatISTTime(record.check_out, true, false) : '—'}
                      </td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-[#0F172A]">
                        {(record.hours_worked || 0).toFixed(2)} hrs
                      </td>
                      <td className="py-2.5 px-3 font-mono text-emerald-700">
                        {record.overtime_hours > 0 ? `+${record.overtime_hours.toFixed(2)} hrs` : '0.00 hrs'}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge
                          variant={
                            record.status === 'PRESENT' ? 'success' :
                              record.status === 'HALF_DAY' ? 'warning' :
                                record.status === 'ON_LEAVE' ? 'neutral' : 'error'
                          }
                          className="text-[10px] font-semibold"
                        >
                          {record.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-[#64748B]">
                        {record.unit_id === 'Unit_1' ? 'Unit 1' : record.unit_id === 'Unit_2' ? 'Unit 2' : (record.unit_id || 'Unit 1')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Tab 2: Regularization Requests */}
      {activeTab === 'corrections' && (
        <Card title="Submitted Regularization Requests">
          {corrections.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#64748B]">
              No regularization requests submitted yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0]">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Date</th>
                    <th className="py-2.5 px-3 font-semibold">Requested In</th>
                    <th className="py-2.5 px-3 font-semibold">Requested Out</th>
                    <th className="py-2.5 px-3 font-semibold">Status Requested</th>
                    <th className="py-2.5 px-3 font-semibold">Reason</th>
                    <th className="py-2.5 px-3 font-semibold">Review Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  {corrections.map((corr) => (
                    <tr key={corr.id} className="hover:bg-[#F8FAFC]/80">
                      <td className="py-2.5 px-3 font-mono font-medium text-[#0F172A]">
                        {corr.date}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {corr.requested_check_in || '—'}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {corr.requested_check_out || '—'}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-[#0F172A]">
                        {corr.requested_status || 'PRESENT'}
                      </td>
                      <td className="py-2.5 px-3 text-[#64748B] max-w-xs truncate">
                        {corr.reason}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge
                          variant={
                            corr.status === 'APPROVED' ? 'success' :
                              corr.status === 'REJECTED' ? 'error' : 'warning'
                          }
                          className="text-[10px]"
                        >
                          {corr.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Attendance Regularization Modal */}
      {showCorrectionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#FFFFFF] rounded-2xl shadow-xl border border-[#E2E8F0] max-w-lg w-full p-6 animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <FileEdit className="h-5 w-5 text-[#0F172A]" />
                <h3 className="text-base font-bold text-[#0F172A]">
                  Regularize Punch / Request Attendance Correction
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowCorrectionModal(false)}
                className="text-xs text-[#64748B] hover:text-[#0F172A] px-2 py-1 rounded"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4 mt-4 text-xs">
              <p className="text-[#64748B]">
                Submit timestamps for biometric sync failure or authorized duty travel. Your supervisor will review and approve.
              </p>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Attendance Date
                </label>
                <Input
                  type="date"
                  value={correctionDate}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCorrectionDate(e.target.value)}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-[#0F172A] mb-1">
                    Requested Check-In (IST)
                  </label>
                  <Input
                    type="time"
                    value={reqCheckIn}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setReqCheckIn(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block font-semibold text-[#0F172A] mb-1">
                    Requested Check-Out (IST)
                  </label>
                  <Input
                    type="time"
                    value={reqCheckOut}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setReqCheckOut(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Requested Attendance Status
                </label>
                <select
                  value={reqStatus}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setReqStatus(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                >
                  <option value="PRESENT">Full Day Present</option>
                  <option value="HALF_DAY">Half Day</option>
                  <option value="ON_LEAVE">Duty Leave</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-[#0F172A] mb-1">
                  Justification / Remarks
                </label>
                <textarea
                  value={correctionReason}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCorrectionReason(e.target.value)}
                  rows={3}
                  placeholder="Explain why punch was missed (e.g. power cut at factory gate scanner, on-site client audit)..."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] bg-[#FFFFFF] text-[#0F172A] focus:outline-none focus:ring-1 focus:ring-[#0F172A]"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCorrectionModal(false)}
                  disabled={isSubmittingCorrection}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmittingCorrection}
                  className="bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  {isSubmittingCorrection ? 'Submitting...' : 'Submit Regularization'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
