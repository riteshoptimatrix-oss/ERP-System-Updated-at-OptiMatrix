'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { employeeClient } from '@/services/employee-client';
import { Payslip, SalaryStructure } from '@/types/hr';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  RefreshCw,
  AlertCircle,
  Download,
  Eye,
  FileText,
} from 'lucide-react';

export default function EmployeePayrollPage() {
  const [structure, setStructure] = useState<SalaryStructure | null>(null);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedPayslip, setSelectedPayslip] = useState<Payslip | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage('');
    try {
      const [structRes, slipsRes] = await Promise.all([
        employeeClient.getSalaryStructure().catch(() => null),
        employeeClient.listPayslips().catch(() => []),
      ]);
      setStructure(structRes);
      setPayslips(slipsRes || []);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to fetch payroll records');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const formatCurrency = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const calculatedPF = structure ? (structure.basic_salary * (structure.pf_percentage || 12)) / 100 : 0;
  const calculatedESI = structure ? (structure.gross_monthly_standard * (structure.esi_percentage || 0.75)) / 100 : 0;
  const totalDeductions = structure
    ? calculatedPF + calculatedESI + (structure.professional_tax || 0) + (structure.tds_monthly || 0)
    : 0;
  const estimatedNet = structure ? Math.max(0, structure.gross_monthly_standard - totalDeductions) : 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] p-6 rounded-2xl shadow-card border border-[#E2E8F0] relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0F172A]" />
        <div className="space-y-1 pl-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] font-mono">
              Compensation & Statutory Compliance
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            My Salary Structure & Payslips
          </h1>
          <p className="text-xs text-[#64748B]">
            Official remuneration schedule, monthly disbursements, PF & ESI contributions, and downloadable wage slips.
          </p>
        </div>

        <div className="flex items-center gap-2">
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

      {/* Error alert */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Salary Structure Card */}
      {structure ? (
        <Card title="Official Remuneration Structure">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-2">
            {/* Earnings Breakdown */}
            <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2 text-xs">
              <span className="font-bold text-[#0F172A] uppercase tracking-wider text-[11px] block border-b border-[#E2E8F0] pb-1.5">
                Monthly Earnings
              </span>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">Basic Salary</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.basic_salary)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">House Rent Allowance (HRA)</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.hra)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">Conveyance Allowance</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.conveyance_allowance)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">Special Allowance</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.special_allowance)}</span>
              </div>
              <div className="flex justify-between pt-2 text-[#0F172A] font-bold">
                <span>Gross Remuneration</span>
                <span className="font-mono text-emerald-700">{formatCurrency(structure.gross_monthly_standard)}</span>
              </div>
            </div>

            {/* Deductions Breakdown */}
            <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2 text-xs">
              <span className="font-bold text-[#0F172A] uppercase tracking-wider text-[11px] block border-b border-[#E2E8F0] pb-1.5">
                Statutory Deductions
              </span>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">Provident Fund ({structure.pf_percentage || 12}%)</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(calculatedPF)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">ESI ({structure.esi_percentage || 0.75}%)</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(calculatedESI)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">Professional Tax (PT)</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.professional_tax)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#E2E8F0]/60">
                <span className="text-[#64748B]">TDS / Income Tax</span>
                <span className="font-mono font-medium text-[#0F172A]">{formatCurrency(structure.tds_monthly)}</span>
              </div>
              <div className="flex justify-between pt-2 text-[#0F172A] font-bold">
                <span>Total Statutory Deductions</span>
                <span className="font-mono text-rose-700">
                  {formatCurrency(totalDeductions)}
                </span>
              </div>
            </div>

            {/* Net Take-Home Highlight */}
            <div className="p-5 rounded-xl bg-[#0F172A] text-white flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-1">
                  Monthly Net Take-Home Pay
                </span>
                <span className="text-3xl font-mono font-bold block text-emerald-400">
                  {formatCurrency(estimatedNet)}
                </span>
                <p className="text-xs text-slate-300 mt-2">
                  Direct credit to verified bank account on the 1st of every month.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-700 text-[11px] text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Pay Frequency:</span>
                  <span className="text-slate-200">Monthly (30 Days)</span>
                </div>
                <div className="flex justify-between">
                  <span>Bank Account:</span>
                  <span className="text-slate-200 font-mono">
                    {structure.bank_account_number ? `•••• •••• ${structure.bank_account_number.slice(-4)}` : 'On Record'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-8 text-center text-xs text-[#64748B]">
          No active salary structure documented yet. Contact HR Operations for compensation onboarding.
        </Card>
      )}

      {/* Finalized Payslips List */}
      <Card title="Finalized Payslips & Wage Records">
        {payslips.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#64748B]">
            No finalized payslips generated for your profile yet. Monthly payslips appear once payroll runs are published.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0]">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">Pay Period</th>
                  <th className="py-2.5 px-3 font-semibold">Slip #</th>
                  <th className="py-2.5 px-3 font-semibold">Total Earnings</th>
                  <th className="py-2.5 px-3 font-semibold">Deductions</th>
                  <th className="py-2.5 px-3 font-semibold">Net Disbursed</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {payslips.map((slip) => (
                  <tr key={slip.payslip_number || slip.period} className="hover:bg-[#F8FAFC]/80">
                    <td className="py-2.5 px-3 font-mono font-bold text-[#0F172A]">
                      {slip.period}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[#64748B]">
                      {slip.payslip_number}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-medium text-[#0F172A]">
                      {formatCurrency(slip.total_earnings)}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-rose-700">
                      {formatCurrency(slip.total_deductions)}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-emerald-700">
                      {formatCurrency(slip.net_salary_payable)}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedPayslip(slip)}
                        className="h-6 text-[10px] flex items-center gap-1 border-[#CBD5E1] text-[#0F172A] hover:bg-[#F8FAFC]"
                      >
                        <Eye className="w-3 h-3" />
                        View Breakdown
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Detailed Payslip Modal */}
      {selectedPayslip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#FFFFFF] rounded-2xl shadow-xl border border-[#E2E8F0] max-w-xl w-full p-6 animate-in fade-in-50 zoom-in-95">
            <div className="flex items-center justify-between pb-4 border-b border-[#E2E8F0]">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#0F172A]" />
                <div>
                  <h3 className="text-base font-bold text-[#0F172A]">
                    Payslip Breakdown &bull; {selectedPayslip.period}
                  </h3>
                  <span className="text-[11px] text-[#64748B]">Opti Matrix Manufacturing Operations ERP</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPayslip(null)}
                className="text-xs text-[#64748B] hover:text-[#0F172A] px-2 py-1 rounded"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4 mt-4 text-xs">
              <div className="grid grid-cols-2 gap-4 p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div>
                  <span className="text-[#64748B] block text-[11px]">Employee</span>
                  <span className="font-semibold text-[#0F172A]">{selectedPayslip.employee_name} ({selectedPayslip.employee_code})</span>
                </div>
                <div>
                  <span className="text-[#64748B] block text-[11px]">Payslip Number</span>
                  <span className="font-mono font-bold text-[#0F172A]">{selectedPayslip.payslip_number}</span>
                </div>
              </div>

              {/* Items Breakdown Table */}
              <div className="border border-[#E2E8F0] rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B]">
                    <tr>
                      <th className="py-2 px-3 text-left">Component</th>
                      <th className="py-2 px-3 text-left">Type</th>
                      <th className="py-2 px-3 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">Basic Pay</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">EARNING</span></td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700">+{formatCurrency(selectedPayslip.basic)}</td>
                    </tr>
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">House Rent Allowance (HRA)</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">EARNING</span></td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700">+{formatCurrency(selectedPayslip.hra)}</td>
                    </tr>
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">Conveyance Allowance</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">EARNING</span></td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700">+{formatCurrency(selectedPayslip.conveyance)}</td>
                    </tr>
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">Special Allowance</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">EARNING</span></td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700">+{formatCurrency(selectedPayslip.special_allowance)}</td>
                    </tr>
                    {selectedPayslip.overtime_pay > 0 && (
                      <tr className="hover:bg-[#F8FAFC]/60">
                        <td className="py-2 px-3 font-medium text-[#0F172A]">Overtime Pay ({selectedPayslip.overtime_hours} hrs)</td>
                        <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">EARNING</span></td>
                        <td className="py-2 px-3 text-right font-mono text-emerald-700">+{formatCurrency(selectedPayslip.overtime_pay)}</td>
                      </tr>
                    )}
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">Provident Fund (PF)</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700">DEDUCTION</span></td>
                      <td className="py-2 px-3 text-right font-mono text-rose-700">-{formatCurrency(selectedPayslip.pf_deduction)}</td>
                    </tr>
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">ESI Contribution</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700">DEDUCTION</span></td>
                      <td className="py-2 px-3 text-right font-mono text-rose-700">-{formatCurrency(selectedPayslip.esi_deduction)}</td>
                    </tr>
                    <tr className="hover:bg-[#F8FAFC]/60">
                      <td className="py-2 px-3 font-medium text-[#0F172A]">Professional Tax (PT)</td>
                      <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700">DEDUCTION</span></td>
                      <td className="py-2 px-3 text-right font-mono text-rose-700">-{formatCurrency(selectedPayslip.professional_tax)}</td>
                    </tr>
                    {selectedPayslip.lop_deduction > 0 && (
                      <tr className="hover:bg-[#F8FAFC]/60">
                        <td className="py-2 px-3 font-medium text-[#0F172A]">Loss of Pay ({selectedPayslip.lop_days} days)</td>
                        <td className="py-2 px-3"><span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700">DEDUCTION</span></td>
                        <td className="py-2 px-3 text-right font-mono text-rose-700">-{formatCurrency(selectedPayslip.lop_deduction)}</td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot className="bg-[#F8FAFC] border-t border-[#E2E8F0] font-bold">
                    <tr>
                      <td colSpan={2} className="py-2 px-3 text-[#0F172A]">Net Remitted Pay</td>
                      <td className="py-2 px-3 text-right font-mono text-emerald-700 text-sm">
                        {formatCurrency(selectedPayslip.net_salary_payable)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
                <Button
                  variant="outline"
                  onClick={() => setSelectedPayslip(null)}
                >
                  Close
                </Button>
                <Button
                  onClick={() => window.print()}
                  className="bg-[#0F172A] text-white hover:bg-[#1E293B] flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  Print / Save PDF
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
