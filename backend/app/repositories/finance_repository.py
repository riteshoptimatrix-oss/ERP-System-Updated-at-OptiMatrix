from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
import logging
from app.schemas.finance import (
    AccountCreate,
    AccountType,
    CustomerInvoiceCreate,
    InvoiceStatus,
    SupplierBillCreate,
    BillStatus,
    PaymentCreate,
    PaymentType,
    ExpenseCreate,
    JournalEntryCreate,
    JournalLineInput,
    JournalEntryStatus,
    TrialBalanceLine,
    TrialBalanceResponse,
    ProfitLossResponse,
    BalanceSheetResponse,
    FinanceSummary,
)
from app.models.user import ManufacturingUnit

logger = logging.getLogger(__name__)

STANDARD_CHART_OF_ACCOUNTS = [
    {"account_code": "1000-CASH", "name": "Petty Cash", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1010-BANK-HDFC", "name": "HDFC Bank Operating Account", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1020-BANK-SBI", "name": "SBI Bank Current Account", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1100-ACCOUNTS-RECEIVABLE", "name": "Trade Accounts Receivable (Customers)", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1200-RAW-MATERIAL-INVENTORY", "name": "Raw Materials Inventory Valuation", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1210-FINISHED-GOODS-INVENTORY", "name": "Finished Goods Inventory Valuation", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "1220-WIP-INVENTORY", "name": "Work-in-Progress (WIP) Valuation", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "2000-ACCOUNTS-PAYABLE", "name": "Trade Accounts Payable (Vendors)", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2100-PF-PAYABLE", "name": "Provident Fund (PF) Liability", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2110-ESI-PAYABLE", "name": "Employee State Insurance (ESI) Liability", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2120-PT-PAYABLE", "name": "Professional Tax (PT) Liability", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2130-TDS-PAYABLE", "name": "TDS Withholding Tax Liability", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2140-SALARY-NET-PAYABLE", "name": "Net Salaries Payable", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2200-GST-OUTPUT-PAYABLE", "name": "Output GST / IGST Tax Payable", "account_type": "LIABILITY", "unit_id": "BOTH"},
    {"account_code": "2210-GST-INPUT-CREDIT", "name": "Input GST / IGST Tax Credit", "account_type": "ASSET", "unit_id": "BOTH"},
    {"account_code": "3000-SHARE-CAPITAL", "name": "Owners Share Capital", "account_type": "EQUITY", "unit_id": "BOTH"},
    {"account_code": "3100-RETAINED-EARNINGS", "name": "Retained Earnings / Surplus", "account_type": "EQUITY", "unit_id": "BOTH"},
    {"account_code": "4000-SALES-REVENUE", "name": "Sales Revenue - Finished Products", "account_type": "REVENUE", "unit_id": "BOTH"},
    {"account_code": "4100-SCRAP-SALES-REVENUE", "name": "Scrap & By-product Sales Revenue", "account_type": "REVENUE", "unit_id": "BOTH"},
    {"account_code": "5000-RAW-MATERIAL-CONSUMPTION", "name": "Direct Raw Material Consumption Cost", "account_type": "EXPENSE", "unit_id": "BOTH"},
    {"account_code": "5100-DIRECT-LABOR-WAGES", "name": "Direct Shopfloor Wages & Salaries", "account_type": "EXPENSE", "unit_id": "BOTH"},
    {"account_code": "5200-POWER-ELECTRICITY-EXPENSE", "name": "Plant Power & Electricity Expense", "account_type": "EXPENSE", "unit_id": "BOTH"},
    {"account_code": "5300-OPERATING-EXPENSES", "name": "General Administrative & Operating Expenses", "account_type": "EXPENSE", "unit_id": "BOTH"},
    {"account_code": "5400-SCRAP-LOSS-EXPENSE", "name": "Production Scrap & Wastage Loss", "account_type": "EXPENSE", "unit_id": "BOTH"},
]


class FinanceRepository:
    def __init__(self, db: Any):
        self.db = db
        self.accounts_col = db["accounts"]
        self.invoices_col = db["invoices"]
        self.bills_col = db["supplier_bills"]
        self.payments_col = db["payments"]
        self.expenses_col = db["expenses"]
        self.journals_col = db["journal_entries"]
        self.customers_col = db["customers"]
        self.vendors_col = db["vendors"]

    async def generate_doc_number(self, collection_name: str, prefix: str) -> str:
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.db[collection_name].count_documents({
            "$or": [
                {"invoice_number": {"$regex": f"^{prefix}-{ym_prefix}-"}},
                {"bill_number": {"$regex": f"^{prefix}-{ym_prefix}-"}},
                {"payment_number": {"$regex": f"^{prefix}-{ym_prefix}-"}},
                {"expense_number": {"$regex": f"^{prefix}-{ym_prefix}-"}},
                {"entry_number": {"$regex": f"^{prefix}-{ym_prefix}-"}},
            ]
        })
        return f"{prefix}-{ym_prefix}-{(count + 1):04d}"

    # -------------------------------------------------------------
    # 1. Chart of Accounts (COA)
    # -------------------------------------------------------------
    async def seed_chart_of_accounts(self) -> None:
        """Idempotently seed standard chart of accounts."""
        now = datetime.now(timezone.utc)
        for acc in STANDARD_CHART_OF_ACCOUNTS:
            existing = await self.accounts_col.find_one({"account_code": acc["account_code"]})
            if not existing:
                doc = {
                    **acc,
                    "parent_account_code": None,
                    "current_balance": 0.0,
                    "is_active": True,
                    "description": f"Standard {acc['account_type']} Account",
                    "created_at": now,
                    "created_by": "SYSTEM",
                }
                await self.accounts_col.insert_one(doc)

    async def create_account(self, data: AccountCreate, created_by: str) -> Dict[str, Any]:
        existing = await self.accounts_col.find_one({"account_code": data.account_code})
        if existing:
            raise ValueError(f"Account code '{data.account_code}' already exists.")

        now = datetime.now(timezone.utc)
        doc = {
            "account_code": data.account_code,
            "name": data.name,
            "account_type": data.account_type.value,
            "parent_account_code": data.parent_account_code,
            "unit_id": data.unit_id.value,
            "current_balance": 0.0,
            "is_active": data.is_active,
            "description": data.description,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.accounts_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"is_active": True}
        if account_type:
            query["account_type"] = account_type
        cursor = self.accounts_col.find(query).sort("account_code", 1)
        return await cursor.to_list(length=200)

    # -------------------------------------------------------------
    # 2. Double-Entry Journal Engine (Strict Balancing Enforced)
    # -------------------------------------------------------------
    async def post_journal_entry(self, entry: JournalEntryCreate, created_by: str) -> Dict[str, Any]:
        """
        Creates and immediately posts a balanced double-entry journal voucher.
        Enforces sum(Debit) == sum(Credit).
        Source transaction referencing and duplicate posting checks are mandatory.
        """
        # Duplicate check by source module and reference
        if entry.source_module != "MANUAL":
            existing = await self.journals_col.find_one({
                "source_module": entry.source_module,
                "source_reference": entry.source_reference,
                "status": JournalEntryStatus.POSTED.value,
            })
            if existing:
                raise ValueError(
                    f"Duplicate journal posting blocked: A posted entry for {entry.source_module} "
                    f"'{entry.source_reference}' already exists (Voucher: {existing.get('entry_number')})."
                )

        tot_debit = round(sum(line.debit for line in entry.lines), 2)
        tot_credit = round(sum(line.credit for line in entry.lines), 2)

        if abs(tot_debit - tot_credit) > 0.01:
            raise ValueError(
                f"Double-entry balancing error: Total debits (₹{tot_debit}) must exactly match "
                f"total credits (₹{tot_credit}). Difference: ₹{round(tot_debit - tot_credit, 2)}."
            )

        if tot_debit <= 0:
            raise ValueError("Journal entry total amount must be greater than zero.")

        entry_number = await self.generate_doc_number("journal_entries", "JV")
        now = datetime.now(timezone.utc)

        prepared_lines = []
        for line in entry.lines:
            prepared_lines.append({
                "account_code": line.account_code,
                "account_name": line.account_name,
                "debit": round(line.debit, 2),
                "credit": round(line.credit, 2),
                "description": line.description or entry.description,
            })

            # Update account balances in COA
            # ASSET / EXPENSE increase with DEBIT, decrease with CREDIT
            # LIABILITY / EQUITY / REVENUE increase with CREDIT, decrease with DEBIT
            acc = await self.accounts_col.find_one({"account_code": line.account_code})
            if acc:
                acc_type = acc.get("account_type")
                if acc_type in [AccountType.ASSET.value, AccountType.EXPENSE.value]:
                    delta = round(line.debit - line.credit, 2)
                else:
                    delta = round(line.credit - line.debit, 2)

                await self.accounts_col.update_one(
                    {"account_code": line.account_code},
                    {"$inc": {"current_balance": delta}},
                )

        doc = {
            "entry_number": entry_number,
            "entry_date": entry.entry_date,
            "unit_id": entry.unit_id.value,
            "source_module": entry.source_module,
            "source_reference": entry.source_reference,
            "description": entry.description,
            "lines": prepared_lines,
            "total_debit": tot_debit,
            "total_credit": tot_credit,
            "is_balanced": True,
            "status": JournalEntryStatus.POSTED.value,
            "is_reversal": False,
            "reversed_entry_id": None,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.journals_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def reverse_journal_entry(self, entry_id: str, reason: str, reversed_by: str) -> Dict[str, Any]:
        """
        Standard audit reversal: posted journals are never silently deleted.
        Creates an exact countervailing journal entry and links it.
        """
        query = {"_id": ObjectId(entry_id)} if ObjectId.is_valid(entry_id) else {"entry_number": entry_id}
        doc = await self.journals_col.find_one(query)
        if not doc:
            raise ValueError("Journal entry not found.")
        if doc.get("status") == JournalEntryStatus.REVERSED.value:
            raise ValueError("Journal entry is already reversed.")

        # Prepare reversal lines (swap debit and credit)
        rev_lines = []
        for line in doc.get("lines", []):
            rev_lines.append(
                JournalLineInput(
                    account_code=line["account_code"],
                    account_name=line.get("account_name"),
                    debit=line["credit"],
                    credit=line["debit"],
                    description=f"Reversal of {doc['entry_number']}: {reason}",
                )
            )

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        reversal_payload = JournalEntryCreate(
            entry_date=now_str,
            unit_id=ManufacturingUnit(doc.get("unit_id", "Unit_1")),
            source_module="REVERSAL",
            source_reference=doc["entry_number"],
            description=f"Reversal of {doc['entry_number']} - {reason}",
            lines=rev_lines,
        )

        reversal_doc = await self.post_journal_entry(reversal_payload, created_by=reversed_by)

        # Mark original as REVERSED
        await self.journals_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": JournalEntryStatus.REVERSED.value,
                    "reversed_by_entry": reversal_doc["entry_number"],
                    "reversal_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return reversal_doc

    async def list_journal_entries(
        self,
        unit_id: Optional[str] = None,
        source_module: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if source_module:
            query["source_module"] = source_module

        total = await self.journals_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.journals_col.find(query).sort("entry_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 3. Customer Invoices & Accounts Receivable (AR)
    # -------------------------------------------------------------
    async def create_invoice(self, inv_data: CustomerInvoiceCreate, created_by: str) -> Dict[str, Any]:
        """Create and post customer sales invoice, generating automated AR journal voucher."""
        cust_query = (
            {"_id": ObjectId(inv_data.customer_id)}
            if ObjectId.is_valid(inv_data.customer_id)
            else {"code": inv_data.customer_id}
        )
        cust = await self.customers_col.find_one(cust_query)
        if not cust:
            raise ValueError("Customer not found.")

        subtotal = round(sum(line.subtotal for line in inv_data.lines), 2)
        tax = round(sum(line.tax_amount for line in inv_data.lines), 2)
        total = round(subtotal + tax, 2)

        inv_num = await self.generate_doc_number("invoices", "INV")
        now = datetime.now(timezone.utc)

        # Build automated journal lines
        # Debit: Accounts Receivable (Total)
        # Credit: Sales Revenue (Subtotal)
        # Credit: Output GST (Tax)
        j_lines = [
            JournalLineInput(
                account_code="1100-ACCOUNTS-RECEIVABLE",
                account_name="Trade Accounts Receivable (Customers)",
                debit=total,
                credit=0.0,
                description=f"Receivable for Invoice {inv_num}",
            ),
            JournalLineInput(
                account_code="4000-SALES-REVENUE",
                account_name="Sales Revenue - Finished Products",
                debit=0.0,
                credit=subtotal,
                description=f"Sales revenue for Invoice {inv_num}",
            ),
        ]
        if tax > 0:
            j_lines.append(
                JournalLineInput(
                    account_code="2200-GST-OUTPUT-PAYABLE",
                    account_name="Output GST / IGST Tax Payable",
                    debit=0.0,
                    credit=tax,
                    description=f"Output GST liability on Invoice {inv_num}",
                )
            )

        j_entry = await self.post_journal_entry(
            JournalEntryCreate(
                entry_date=inv_data.invoice_date,
                unit_id=inv_data.unit_id,
                source_module="INVOICE",
                source_reference=inv_num,
                description=f"Sales Invoice {inv_num} for {cust.get('name')}",
                lines=j_lines,
            ),
            created_by=created_by,
        )

        doc = {
            "invoice_number": inv_num,
            "customer_id": str(cust["_id"]),
            "customer_code": cust.get("code", ""),
            "customer_name": cust.get("name", inv_data.customer_name or "Customer"),
            "sales_order_id": inv_data.sales_order_id,
            "sales_order_number": inv_data.sales_order_number,
            "project_id": inv_data.project_id,
            "project_code": inv_data.project_code,
            "unit_id": inv_data.unit_id.value,
            "invoice_date": inv_data.invoice_date,
            "due_date": inv_data.due_date,
            "subtotal_amount": subtotal,
            "tax_amount": tax,
            "total_amount": total,
            "amount_paid": 0.0,
            "balance_due": total,
            "status": InvoiceStatus.POSTED.value,
            "lines": [line.model_dump() for line in inv_data.lines],
            "journal_entry_id": str(j_entry["_id"]),
            "notes": inv_data.notes,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.invoices_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_invoices(
        self,
        customer_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if customer_id:
            query["customer_id"] = customer_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status:
            query["status"] = status

        total = await self.invoices_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.invoices_col.find(query).sort("invoice_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 4. Supplier Bills & Accounts Payable (AP) with QC Holds
    # -------------------------------------------------------------
    async def create_supplier_bill(self, bill_data: SupplierBillCreate, created_by: str) -> Dict[str, Any]:
        """Create and post supplier purchase bill. Holds payment if QC issues are flagged."""
        vendor_query = (
            {"_id": ObjectId(bill_data.vendor_id)}
            if ObjectId.is_valid(bill_data.vendor_id)
            else {"code": bill_data.vendor_id}
        )
        vendor = await self.vendors_col.find_one(vendor_query)
        if not vendor:
            raise ValueError("Vendor not found.")

        # Duplicate vendor invoice protection
        dup_bill = await self.bills_col.find_one({
            "vendor_id": str(vendor["_id"]),
            "bill_number_vendor": bill_data.bill_number_vendor,
        })
        if dup_bill:
            raise ValueError(
                f"Duplicate vendor bill prevented: Bill '{bill_data.bill_number_vendor}' "
                f"from {vendor.get('name')} is already registered."
            )

        subtotal = round(sum(line.subtotal for line in bill_data.lines), 2)
        tax = round(sum(line.tax_amount for line in bill_data.lines), 2)
        total = round(subtotal + tax, 2)

        bill_num = await self.generate_doc_number("supplier_bills", "BILL")
        now = datetime.now(timezone.utc)

        # Journal Posting:
        # Debit: Raw Materials Inventory (or respective line accounts)
        # Debit: Input GST Tax Credit
        # Credit: Accounts Payable
        j_lines = [
            JournalLineInput(
                account_code="1200-RAW-MATERIAL-INVENTORY",
                account_name="Raw Materials Inventory Valuation",
                debit=subtotal,
                credit=0.0,
                description=f"Material purchase bill {bill_num}",
            )
        ]
        if tax > 0:
            j_lines.append(
                JournalLineInput(
                    account_code="2210-GST-INPUT-CREDIT",
                    account_name="Input GST / IGST Tax Credit",
                    debit=tax,
                    credit=0.0,
                    description=f"Input tax credit on Bill {bill_num}",
                )
            )
        j_lines.append(
            JournalLineInput(
                account_code="2000-ACCOUNTS-PAYABLE",
                account_name="Trade Accounts Payable (Vendors)",
                debit=0.0,
                credit=total,
                description=f"Payable for Bill {bill_num}",
            )
        )

        j_entry = await self.post_journal_entry(
            JournalEntryCreate(
                entry_date=bill_data.bill_date,
                unit_id=bill_data.unit_id,
                source_module="BILL",
                source_reference=bill_num,
                description=f"Supplier Bill {bill_num} from {vendor.get('name')} ({bill_data.bill_number_vendor})",
                lines=j_lines,
            ),
            created_by=created_by,
        )

        initial_status = BillStatus.ON_HOLD.value if bill_data.has_qc_hold else BillStatus.POSTED.value

        doc = {
            "bill_number": bill_num,
            "vendor_id": str(vendor["_id"]),
            "vendor_code": vendor.get("code", ""),
            "vendor_name": vendor.get("name", bill_data.vendor_name or "Vendor"),
            "bill_number_vendor": bill_data.bill_number_vendor,
            "po_reference": bill_data.po_reference,
            "project_id": bill_data.project_id,
            "project_code": bill_data.project_code,
            "unit_id": bill_data.unit_id.value,
            "bill_date": bill_data.bill_date,
            "due_date": bill_data.due_date,
            "subtotal_amount": subtotal,
            "tax_amount": tax,
            "total_amount": total,
            "amount_paid": 0.0,
            "balance_due": total,
            "status": initial_status,
            "has_qc_hold": bill_data.has_qc_hold,
            "qc_hold_reason": bill_data.qc_hold_reason,
            "qc_released_by": None,
            "qc_released_at": None,
            "lines": [line.model_dump() for line in bill_data.lines],
            "journal_entry_id": str(j_entry["_id"]),
            "notes": bill_data.notes,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.bills_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def release_qc_hold(self, bill_id: str, release_notes: str, released_by: str) -> Dict[str, Any]:
        """Release QC hold on vendor bill, enabling payment authorization."""
        query = {"_id": ObjectId(bill_id)} if ObjectId.is_valid(bill_id) else {"bill_number": bill_id}
        doc = await self.bills_col.find_one(query)
        if not doc:
            raise ValueError("Supplier bill not found.")
        if not doc.get("has_qc_hold"):
            raise ValueError("Bill is not under QC hold.")

        now = datetime.now(timezone.utc)
        await self.bills_col.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "has_qc_hold": False,
                    "status": BillStatus.APPROVED.value,
                    "qc_released_by": released_by,
                    "qc_released_at": now,
                    "qc_release_notes": release_notes,
                }
            },
        )
        return await self.bills_col.find_one({"_id": doc["_id"]})

    async def list_supplier_bills(
        self,
        vendor_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if vendor_id:
            query["vendor_id"] = vendor_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status:
            query["status"] = status

        total = await self.bills_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.bills_col.find(query).sort("bill_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 5. Payments & Receipts
    # -------------------------------------------------------------
    async def record_payment(self, pay_data: PaymentCreate, created_by: str) -> Dict[str, Any]:
        """
        Record customer receipt or vendor payment.
        Blocks vendor payment if bill is on QC hold.
        Generates corresponding balancing double-entry voucher.
        """
        pay_num = await self.generate_doc_number("payments", "PAY")
        now = datetime.now(timezone.utc)

        target_name = "Entity"
        target_code = "ENT"

        if pay_data.payment_type == PaymentType.VENDOR_PAYMENT:
            # Check vendor and bill
            if pay_data.reference_doc_id:
                bill_query = (
                    {"_id": ObjectId(pay_data.reference_doc_id)}
                    if ObjectId.is_valid(pay_data.reference_doc_id)
                    else {"bill_number": pay_data.reference_doc_id}
                )
                bill = await self.bills_col.find_one(bill_query)
                if not bill:
                    raise ValueError("Target supplier bill not found.")

                # QC Hold Check!
                if bill.get("has_qc_hold") or bill.get("status") == BillStatus.ON_HOLD.value:
                    raise ValueError(
                        f"Payment Blocked by QC: Supplier Bill '{bill.get('bill_number')}' is on quality hold "
                        f"({bill.get('qc_hold_reason')}). Unresolved quality holds must be released before payment."
                    )

                if pay_data.amount > round(bill.get("balance_due", 0.0) + 0.05, 2):
                    raise ValueError(
                        f"Overpayment error: Payment amount ₹{pay_data.amount} exceeds bill balance due ₹{bill.get('balance_due')}."
                    )

                target_name = bill.get("vendor_name", "Vendor")
                target_code = bill.get("vendor_code", "VEN")

            # Vendor Payment: Debit Accounts Payable, Credit Bank
            j_lines = [
                JournalLineInput(
                    account_code="2000-ACCOUNTS-PAYABLE",
                    account_name="Trade Accounts Payable (Vendors)",
                    debit=pay_data.amount,
                    credit=0.0,
                    description=f"Disbursement for {pay_data.reference_doc_number or pay_num}",
                ),
                JournalLineInput(
                    account_code=pay_data.bank_account_code,
                    account_name="Bank / Cash Account",
                    debit=0.0,
                    credit=pay_data.amount,
                    description=f"Bank payout for {pay_num}",
                ),
            ]

        elif pay_data.payment_type == PaymentType.CUSTOMER_RECEIPT:
            if pay_data.reference_doc_id:
                inv_query = (
                    {"_id": ObjectId(pay_data.reference_doc_id)}
                    if ObjectId.is_valid(pay_data.reference_doc_id)
                    else {"invoice_number": pay_data.reference_doc_id}
                )
                inv = await self.invoices_col.find_one(inv_query)
                if not inv:
                    raise ValueError("Target customer invoice not found.")

                if pay_data.amount > round(inv.get("balance_due", 0.0) + 0.05, 2):
                    raise ValueError(
                        f"Overpayment error: Receipt amount ₹{pay_data.amount} exceeds invoice balance due ₹{inv.get('balance_due')}."
                    )

                target_name = inv.get("customer_name", "Customer")
                target_code = inv.get("customer_code", "CUST")

            # Customer Receipt: Debit Bank, Credit Accounts Receivable
            j_lines = [
                JournalLineInput(
                    account_code=pay_data.bank_account_code,
                    account_name="Bank / Cash Account",
                    debit=pay_data.amount,
                    credit=0.0,
                    description=f"Customer deposit for {pay_num}",
                ),
                JournalLineInput(
                    account_code="1100-ACCOUNTS-RECEIVABLE",
                    account_name="Trade Accounts Receivable (Customers)",
                    debit=0.0,
                    credit=pay_data.amount,
                    description=f"Receivable receipt for {pay_data.reference_doc_number or pay_num}",
                ),
            ]

        else:
            raise ValueError(f"Unsupported payment type '{pay_data.payment_type}'.")

        j_entry = await self.post_journal_entry(
            JournalEntryCreate(
                entry_date=pay_data.payment_date,
                unit_id=pay_data.unit_id,
                source_module="PAYMENT",
                source_reference=pay_num,
                description=f"{pay_data.payment_type.value} {pay_num} ({pay_data.payment_method.value})",
                lines=j_lines,
            ),
            created_by=created_by,
        )

        doc = {
            "payment_number": pay_num,
            "payment_type": pay_data.payment_type.value,
            "entity_id": pay_data.entity_id,
            "entity_code": target_code,
            "entity_name": target_name,
            "reference_doc_id": pay_data.reference_doc_id,
            "reference_doc_number": pay_data.reference_doc_number,
            "project_id": pay_data.project_id,
            "project_code": pay_data.project_code,
            "unit_id": pay_data.unit_id.value,
            "payment_date": pay_data.payment_date,
            "payment_method": pay_data.payment_method.value,
            "payment_reference": pay_data.payment_reference,
            "amount": pay_data.amount,
            "bank_account_code": pay_data.bank_account_code,
            "journal_entry_id": str(j_entry["_id"]),
            "notes": pay_data.notes,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.payments_col.insert_one(doc)
        doc["_id"] = res.inserted_id

        # Update balance due on invoice or bill
        if pay_data.payment_type == PaymentType.CUSTOMER_RECEIPT and pay_data.reference_doc_id:
            inv_ref_query = (
                {"_id": ObjectId(pay_data.reference_doc_id)}
                if ObjectId.is_valid(pay_data.reference_doc_id)
                else {"invoice_number": pay_data.reference_doc_id}
            )
            inv_target = await self.invoices_col.find_one(inv_ref_query)
            if inv_target:
                new_paid = round(float(inv_target.get("amount_paid", 0.0)) + pay_data.amount, 2)
                new_balance = max(0.0, round(float(inv_target.get("total_amount", 0.0)) - new_paid, 2))
                new_status = InvoiceStatus.PAID.value if new_balance <= 0.05 else InvoiceStatus.PARTIALLY_PAID.value
                await self.invoices_col.update_one(
                    {"_id": inv_target["_id"]},
                    {
                        "$set": {
                            "amount_paid": new_paid,
                            "balance_due": new_balance,
                            "status": new_status,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
        elif pay_data.payment_type == PaymentType.VENDOR_PAYMENT and pay_data.reference_doc_id:
            bill_ref_query = (
                {"_id": ObjectId(pay_data.reference_doc_id)}
                if ObjectId.is_valid(pay_data.reference_doc_id)
                else {"bill_number": pay_data.reference_doc_id}
            )
            bill_target = await self.bills_col.find_one(bill_ref_query)
            if bill_target:
                new_paid = round(float(bill_target.get("amount_paid", 0.0)) + pay_data.amount, 2)
                new_balance = max(0.0, round(float(bill_target.get("total_amount", 0.0)) - new_paid, 2))
                new_status = BillStatus.PAID.value if new_balance <= 0.05 else BillStatus.APPROVED.value
                await self.bills_col.update_one(
                    {"_id": bill_target["_id"]},
                    {
                        "$set": {
                            "amount_paid": new_paid,
                            "balance_due": new_balance,
                            "status": new_status,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )

        return doc

    async def list_payments(
        self,
        payment_type: Optional[str] = None,
        unit_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if payment_type:
            query["payment_type"] = payment_type
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        total = await self.payments_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.payments_col.find(query).sort("payment_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 6. Direct Operating Expenses
    # -------------------------------------------------------------
    async def record_expense(self, exp_data: ExpenseCreate, created_by: str) -> Dict[str, Any]:
        """Record operational expense and create double-entry voucher."""
        exp_num = await self.generate_doc_number("expenses", "EXP")
        now = datetime.now(timezone.utc)
        total = round(exp_data.amount + exp_data.tax_amount, 2)

        j_lines = [
            JournalLineInput(
                account_code=exp_data.expense_account_code,
                account_name="Operating Expense",
                debit=exp_data.amount,
                credit=0.0,
                description=f"Expense {exp_num}: {exp_data.expense_category}",
            )
        ]
        if exp_data.tax_amount > 0:
            j_lines.append(
                JournalLineInput(
                    account_code="2210-GST-INPUT-CREDIT",
                    account_name="Input GST Credit",
                    debit=exp_data.tax_amount,
                    credit=0.0,
                    description=f"Input GST for Expense {exp_num}",
                )
            )
        j_lines.append(
            JournalLineInput(
                account_code=exp_data.paid_from_account_code,
                account_name="Bank / Cash Asset",
                debit=0.0,
                credit=total,
                description=f"Payout for Expense {exp_num}",
            )
        )

        j_entry = await self.post_journal_entry(
            JournalEntryCreate(
                entry_date=exp_data.expense_date,
                unit_id=exp_data.unit_id,
                source_module="EXPENSE",
                source_reference=exp_num,
                description=f"Expense {exp_num} paid to {exp_data.vendor_or_payee}",
                lines=j_lines,
            ),
            created_by=created_by,
        )

        doc = {
            "expense_number": exp_num,
            "expense_category": exp_data.expense_category,
            "expense_account_code": exp_data.expense_account_code,
            "project_id": exp_data.project_id,
            "project_code": exp_data.project_code,
            "unit_id": exp_data.unit_id.value,
            "expense_date": exp_data.expense_date,
            "amount": exp_data.amount,
            "tax_amount": exp_data.tax_amount,
            "total_amount": total,
            "payment_method": exp_data.payment_method.value,
            "paid_from_account_code": exp_data.paid_from_account_code,
            "vendor_or_payee": exp_data.vendor_or_payee,
            "reference_number": exp_data.reference_number,
            "journal_entry_id": str(j_entry["_id"]),
            "notes": exp_data.notes,
            "created_at": now,
            "created_by": created_by,
        }
        res = await self.expenses_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def list_expenses(
        self,
        unit_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        total = await self.expenses_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.expenses_col.find(query).sort("expense_date", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    # -------------------------------------------------------------
    # 7. Financial Reports: Trial Balance, P&L, Balance Sheet
    # -------------------------------------------------------------
    async def get_trial_balance(self, as_of_date: Optional[str] = None, unit_id: Optional[str] = None) -> TrialBalanceResponse:
        """
        Aggregate all journal entries to date and report debit/credit per account.
        Guarantees Trial Balance reconciliation.
        """
        match_q: Dict[str, Any] = {"status": JournalEntryStatus.POSTED.value}
        if as_of_date:
            match_q["entry_date"] = {"$lte": as_of_date}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            match_q["unit_id"] = unit_id

        pipeline = [
            {"$match": match_q},
            {"$unwind": "$lines"},
            {
                "$group": {
                    "_id": "$lines.account_code",
                    "total_debit": {"$sum": "$lines.debit"},
                    "total_credit": {"$sum": "$lines.credit"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        results = await self.journals_col.aggregate(pipeline).to_list(length=200)

        accounts_map = {acc["account_code"]: acc for acc in await self.list_accounts()}

        lines = []
        tot_deb = 0.0
        tot_cred = 0.0

        for r in results:
            code = r["_id"]
            acc = accounts_map.get(code, {})
            d = round(r["total_debit"], 2)
            c = round(r["total_credit"], 2)
            lines.append(
                TrialBalanceLine(
                    account_code=code,
                    account_name=acc.get("name", code),
                    account_type=acc.get("account_type", "ASSET"),
                    debit=d,
                    credit=c,
                )
            )
            tot_deb += d
            tot_cred += c

        tot_deb = round(tot_deb, 2)
        tot_cred = round(tot_cred, 2)

        return TrialBalanceResponse(
            unit_id=unit_id,
            as_of_date=as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            lines=lines,
            accounts=lines,
            total_debit=tot_deb,
            total_credit=tot_cred,
            is_balanced=abs(tot_deb - tot_cred) < 0.05,
        )

    async def get_profit_and_loss(
        self,
        from_date: str,
        to_date: str,
        unit_id: Optional[str] = None,
    ) -> ProfitLossResponse:
        """Calculate net profit/loss (Revenue minus Expenses) for date period."""
        match_q: Dict[str, Any] = {
            "status": JournalEntryStatus.POSTED.value,
            "entry_date": {"$gte": from_date, "$lte": to_date},
        }
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            match_q["unit_id"] = unit_id

        pipeline = [
            {"$match": match_q},
            {"$unwind": "$lines"},
            {
                "$group": {
                    "_id": "$lines.account_code",
                    "net_debit": {"$sum": "$lines.debit"},
                    "net_credit": {"$sum": "$lines.credit"},
                }
            },
        ]
        results = await self.journals_col.aggregate(pipeline).to_list(length=200)
        accounts_map = {acc["account_code"]: acc for acc in await self.list_accounts()}

        revenue_list = []
        expense_list = []
        total_rev = 0.0
        total_exp = 0.0

        for r in results:
            code = r["_id"]
            acc = accounts_map.get(code, {})
            acc_type = acc.get("account_type")

            if acc_type == AccountType.REVENUE.value:
                # Revenue net = Credit - Debit
                amount = round(r["net_credit"] - r["net_debit"], 2)
                if amount != 0:
                    revenue_list.append({"account_code": code, "account_name": acc.get("name", code), "amount": amount})
                    total_rev += amount
            elif acc_type == AccountType.EXPENSE.value:
                # Expense net = Debit - Credit
                amount = round(r["net_debit"] - r["net_credit"], 2)
                if amount != 0:
                    expense_list.append({"account_code": code, "account_name": acc.get("name", code), "amount": amount})
                    total_exp += amount

        total_rev = round(total_rev, 2)
        total_exp = round(total_exp, 2)
        net_profit = round(total_rev - total_exp, 2)

        return ProfitLossResponse(
            unit_id=unit_id,
            from_date=from_date,
            to_date=to_date,
            total_revenue=total_rev,
            total_expenses=total_exp,
            net_profit_or_loss=net_profit,
            revenue_breakdown=revenue_list,
            expense_breakdown=expense_list,
        )

    async def get_balance_sheet(self, as_of_date: Optional[str] = None, unit_id: Optional[str] = None) -> BalanceSheetResponse:
        """Assets = Liabilities + Equity statement."""
        tb = await self.get_trial_balance(as_of_date=as_of_date, unit_id=unit_id)
        assets = []
        liabs = []
        equity = []
        tot_a = 0.0
        tot_l = 0.0
        tot_e = 0.0

        for line in tb.lines:
            if line.account_type == AccountType.ASSET.value:
                bal = round(line.debit - line.credit, 2)
                assets.append({"account_code": line.account_code, "account_name": line.account_name, "balance": bal})
                tot_a += bal
            elif line.account_type == AccountType.LIABILITY.value:
                bal = round(line.credit - line.debit, 2)
                liabs.append({"account_code": line.account_code, "account_name": line.account_name, "balance": bal})
                tot_l += bal
            elif line.account_type == AccountType.EQUITY.value:
                bal = round(line.credit - line.debit, 2)
                equity.append({"account_code": line.account_code, "account_name": line.account_name, "balance": bal})
                tot_e += bal

        tot_a = round(tot_a, 2)
        tot_l = round(tot_l, 2)
        tot_e = round(tot_e, 2)

        return BalanceSheetResponse(
            unit_id=unit_id,
            as_of_date=as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            total_assets=tot_a,
            total_liabilities=tot_l,
            total_equity=tot_e,
            assets_breakdown=assets,
            liabilities_breakdown=liabs,
            equity_breakdown=equity,
            is_balanced=abs(tot_a - (tot_l + tot_e)) < 0.05,
        )

    async def get_finance_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Dashboard high-level metrics for AR, AP, Cash/Bank, and monthly totals."""
        u_filter: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            u_filter["unit_id"] = unit_id

        # Total Receivables (unpaid balance on invoices)
        ar_pipeline = [
            {"$match": {**u_filter, "status": {"$in": [InvoiceStatus.POSTED.value, InvoiceStatus.PARTIALLY_PAID.value]}}},
            {"$group": {"_id": None, "total": {"$sum": "$balance_due"}}},
        ]
        ar_res = await self.invoices_col.aggregate(ar_pipeline).to_list(length=1)
        tot_ar = float(ar_res[0]["total"]) if ar_res else 0.0

        # Total Payables (unpaid balance on bills)
        ap_pipeline = [
            {"$match": {**u_filter, "status": {"$in": [BillStatus.POSTED.value, BillStatus.APPROVED.value, BillStatus.ON_HOLD.value]}}},
            {"$group": {"_id": None, "total": {"$sum": "$balance_due"}}},
        ]
        ap_res = await self.bills_col.aggregate(ap_pipeline).to_list(length=1)
        tot_ap = float(ap_res[0]["total"]) if ap_res else 0.0

        # Bank/Cash Balances from accounts
        bank_accounts = await self.accounts_col.find({
            "account_code": {"$in": ["1000-CASH", "1010-BANK-HDFC", "1020-BANK-SBI"]}
        }).to_list(length=10)
        tot_cash = sum(acc.get("current_balance", 0.0) for acc in bank_accounts)

        # MTD figures
        now = datetime.now(timezone.utc)
        month_prefix = now.strftime("%Y-%m")
        pl = await self.get_profit_and_loss(f"{month_prefix}-01", f"{month_prefix}-31", unit_id=unit_id)

        # Counts
        qc_holds = await self.bills_col.count_documents({**u_filter, "has_qc_hold": True})
        unposted_inv = await self.invoices_col.count_documents({**u_filter, "status": InvoiceStatus.DRAFT.value})
        unposted_bills = await self.bills_col.count_documents({**u_filter, "status": BillStatus.DRAFT.value})

        return {
            "unit_id": unit_id,
            "total_receivables": round(tot_ar, 2),
            "total_payables": round(tot_ap, 2),
            "cash_and_bank_balance": round(tot_cash, 2),
            "mtd_revenue": pl.total_revenue,
            "mtd_expenses": pl.total_expenses,
            "unposted_invoices_count": unposted_inv,
            "unposted_bills_count": unposted_bills,
            "qc_holds_count": qc_holds,
        }
