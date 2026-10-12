from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class BillStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    ON_HOLD = "ON_HOLD"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentType(str, Enum):
    CUSTOMER_RECEIPT = "CUSTOMER_RECEIPT"
    VENDOR_PAYMENT = "VENDOR_PAYMENT"
    EXPENSE_PAYMENT = "EXPENSE_PAYMENT"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    NEFT_RTGS = "NEFT_RTGS"
    CHEQUE = "CHEQUE"
    CASH = "CASH"
    UPI = "UPI"


class JournalEntryStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


# -------------------------------------------------------------
# 1. Chart of Accounts (COA)
# -------------------------------------------------------------
class AccountCreate(BaseModel):
    account_code: str = Field(..., min_length=2, max_length=50, description="Unique account code e.g. 1100-AR")
    name: str = Field(..., min_length=2, max_length=150)
    account_type: AccountType = Field(..., description="ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE")
    parent_account_code: Optional[str] = Field(None, description="Parent account code for hierarchy")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.BOTH)
    is_active: bool = True
    description: Optional[str] = Field(None, max_length=300)


class AccountResponse(AccountCreate):
    id: str
    current_balance: float = 0.0
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# 2. Customer Invoices (AR)
# -------------------------------------------------------------
class InvoiceLineItem(BaseModel):
    item_code: str = Field(..., description="Product SKU or Service code")
    description: str = Field(..., min_length=2, max_length=200)
    quantity: float = Field(..., gt=0.0)
    unit_price: float = Field(..., ge=0.0)
    discount_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    tax_percent: float = Field(default=18.0, ge=0.0, le=100.0)
    account_code: str = Field(default="4000-SALES-REVENUE", description="Revenue account code")

    @property
    def subtotal(self) -> float:
        discounted = self.unit_price * (1.0 - (self.discount_percent / 100.0))
        return round(self.quantity * discounted, 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * (self.tax_percent / 100.0), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)


class CustomerInvoiceCreate(BaseModel):
    customer_id: str = Field(..., description="Customer Master ID")
    customer_name: Optional[str] = None
    sales_order_id: Optional[str] = Field(None, description="Linked Sales Order")
    sales_order_number: Optional[str] = None
    project_id: Optional[str] = Field(None, description="Linked Project/Lead ID")
    project_code: Optional[str] = Field(None, description="Linked Project/Lead Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    invoice_date: str = Field(..., description="YYYY-MM-DD")
    due_date: str = Field(..., description="YYYY-MM-DD")
    lines: List[InvoiceLineItem] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=500)


class CustomerInvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    customer_id: str
    customer_code: str
    customer_name: str
    sales_order_id: Optional[str] = None
    sales_order_number: Optional[str] = None
    project_id: Optional[str] = None
    project_code: Optional[str] = None
    unit_id: str
    invoice_date: str
    due_date: str
    subtotal_amount: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    balance_due: float
    status: str
    journal_entry_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# 3. Supplier Bills (AP) & QC Holds
# -------------------------------------------------------------
class BillLineItem(BaseModel):
    item_code: str = Field(..., description="Raw Material or Expense item")
    description: str = Field(..., min_length=2, max_length=200)
    quantity: float = Field(..., gt=0.0)
    unit_price: float = Field(..., ge=0.0)
    tax_percent: float = Field(default=18.0, ge=0.0, le=100.0)
    account_code: str = Field(default="1200-RAW-MATERIAL-INVENTORY", description="Asset or Expense account code")

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * (self.tax_percent / 100.0), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)


class SupplierBillCreate(BaseModel):
    vendor_id: str = Field(..., description="Vendor Master ID")
    vendor_name: Optional[str] = None
    bill_number_vendor: str = Field(..., min_length=2, max_length=100, description="Vendor's invoice/bill number")
    po_reference: Optional[str] = Field(None, max_length=100)
    project_id: Optional[str] = Field(None, description="Linked Project/Lead ID")
    project_code: Optional[str] = Field(None, description="Linked Project/Lead Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    bill_date: str = Field(..., description="YYYY-MM-DD")
    due_date: str = Field(..., description="YYYY-MM-DD")
    lines: List[BillLineItem] = Field(..., min_length=1)
    has_qc_hold: bool = Field(default=False, description="Flag indicating unresolved quality hold")
    qc_hold_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=500)


class SupplierBillResponse(BaseModel):
    id: str
    bill_number: str
    vendor_id: str
    vendor_code: str
    vendor_name: str
    bill_number_vendor: str
    po_reference: Optional[str] = None
    project_id: Optional[str] = None
    project_code: Optional[str] = None
    unit_id: str
    bill_date: str
    due_date: str
    subtotal_amount: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    balance_due: float
    status: str
    has_qc_hold: bool = False
    qc_hold_reason: Optional[str] = None
    qc_released_by: Optional[str] = None
    qc_released_at: Optional[datetime] = None
    journal_entry_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


class QCHoldReleaseRequest(BaseModel):
    release_notes: str = Field(..., min_length=3, max_length=500, description="Authorized reason for releasing hold")


# -------------------------------------------------------------
# 4. Payments and Receipts
# -------------------------------------------------------------
class PaymentCreate(BaseModel):
    payment_type: PaymentType = Field(..., description="CUSTOMER_RECEIPT or VENDOR_PAYMENT")
    entity_id: str = Field(..., description="Customer ID or Vendor ID")
    reference_doc_id: Optional[str] = Field(None, description="Invoice ID or Bill ID")
    reference_doc_number: Optional[str] = None
    project_id: Optional[str] = Field(None, description="Linked Project/Lead ID")
    project_code: Optional[str] = Field(None, description="Linked Project/Lead Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    payment_date: str = Field(..., description="YYYY-MM-DD")
    payment_method: PaymentMethod = Field(default=PaymentMethod.BANK_TRANSFER)
    payment_reference: Optional[str] = Field(None, description="UTR, Cheque No, Transaction ID")
    amount: float = Field(..., gt=0.0)
    bank_account_code: str = Field(default="1010-BANK-HDFC", description="Bank/Cash Asset Account")
    notes: Optional[str] = Field(None, max_length=500)


class PaymentResponse(BaseModel):
    id: str
    payment_number: str
    payment_type: str
    entity_id: str
    entity_code: str
    entity_name: str
    reference_doc_id: Optional[str] = None
    reference_doc_number: Optional[str] = None
    project_id: Optional[str] = None
    project_code: Optional[str] = None
    unit_id: str
    payment_date: str
    payment_method: str
    payment_reference: Optional[str] = None
    amount: float
    bank_account_code: str
    journal_entry_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# 5. Expense Management
# -------------------------------------------------------------
class ExpenseCreate(BaseModel):
    expense_category: str = Field(..., min_length=2, max_length=100, description="e.g. UTILITIES, REPAIRS, TRAVEL, PROJECT_SITE")
    expense_account_code: str = Field(default="5300-OPERATING-EXPENSES")
    project_id: Optional[str] = Field(None, description="Linked Project/Lead ID")
    project_code: Optional[str] = Field(None, description="Linked Project/Lead Code")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    expense_date: str = Field(..., description="YYYY-MM-DD")
    amount: float = Field(..., gt=0.0)
    tax_amount: float = Field(default=0.0, ge=0.0)
    payment_method: PaymentMethod = Field(default=PaymentMethod.BANK_TRANSFER)
    paid_from_account_code: str = Field(default="1010-BANK-HDFC")
    vendor_or_payee: str = Field(..., min_length=2, max_length=150)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class ExpenseResponse(BaseModel):
    id: str
    expense_number: str
    expense_category: str
    expense_account_code: str
    project_id: Optional[str] = None
    project_code: Optional[str] = None
    unit_id: str
    expense_date: str
    amount: float
    tax_amount: float
    total_amount: float
    payment_method: str
    paid_from_account_code: str
    vendor_or_payee: str
    reference_number: Optional[str] = None
    journal_entry_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: str


# -------------------------------------------------------------
# 6. Double-Entry Journal Engine
# -------------------------------------------------------------
class JournalLineInput(BaseModel):
    account_code: str = Field(..., description="Chart of Accounts code")
    account_name: Optional[str] = None
    debit: float = Field(default=0.0, ge=0.0)
    credit: float = Field(default=0.0, ge=0.0)
    description: Optional[str] = Field(None, max_length=300)


class JournalEntryCreate(BaseModel):
    entry_date: str = Field(..., description="YYYY-MM-DD")
    unit_id: ManufacturingUnit = Field(default=ManufacturingUnit.Unit_1)
    source_module: str = Field(..., description="e.g. INVOICE, BILL, PAYMENT, PAYROLL, INVENTORY, MANUAL")
    source_reference: str = Field(..., description="Source doc number e.g. INV-202610-001, PAY-2026-10")
    description: str = Field(..., min_length=3, max_length=500)
    lines: List[JournalLineInput] = Field(..., min_length=2)


class JournalEntryResponse(BaseModel):
    id: str
    entry_number: str
    entry_date: str
    unit_id: str
    source_module: str
    source_reference: str
    description: str
    lines: List[Dict[str, Any]]
    total_debit: float
    total_credit: float
    is_balanced: bool
    status: str
    is_reversal: bool = False
    reversed_entry_id: Optional[str] = None
    created_at: datetime
    created_by: str


class JournalReversalRequest(BaseModel):
    reversal_reason: str = Field(..., min_length=3, max_length=500, description="Mandatory reason for reversal")


# -------------------------------------------------------------
# 7. Financial Reports & Metrics
# -------------------------------------------------------------
class TrialBalanceLine(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    debit: float
    credit: float


class TrialBalanceResponse(BaseModel):
    unit_id: Optional[str] = None
    as_of_date: str
    lines: List[TrialBalanceLine] = Field(default_factory=list)
    accounts: List[TrialBalanceLine] = Field(default_factory=list)
    total_debit: float
    total_credit: float
    is_balanced: bool


class ProfitLossResponse(BaseModel):
    unit_id: Optional[str] = None
    from_date: str
    to_date: str
    total_revenue: float
    total_expenses: float
    net_profit_or_loss: float
    revenue_breakdown: List[Dict[str, Any]]
    expense_breakdown: List[Dict[str, Any]]


class BalanceSheetResponse(BaseModel):
    unit_id: Optional[str] = None
    as_of_date: str
    total_assets: float
    total_liabilities: float
    total_equity: float
    assets_breakdown: List[Dict[str, Any]]
    liabilities_breakdown: List[Dict[str, Any]]
    equity_breakdown: List[Dict[str, Any]]
    is_balanced: bool


class FinanceSummary(BaseModel):
    unit_id: Optional[str] = None
    total_receivables: float
    total_payables: float
    cash_and_bank_balance: float
    mtd_revenue: float
    mtd_expenses: float
    unposted_invoices_count: int
    unposted_bills_count: int
    qc_holds_count: int
