from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, require_permission, verify_csrf_token
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import (
    AccountCreate,
    AccountResponse,
    CustomerInvoiceCreate,
    CustomerInvoiceResponse,
    SupplierBillCreate,
    SupplierBillResponse,
    QCHoldReleaseRequest,
    PaymentCreate,
    PaymentResponse,
    ExpenseCreate,
    ExpenseResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalReversalRequest,
    TrialBalanceResponse,
    ProfitLossResponse,
    BalanceSheetResponse,
    FinanceSummary,
)
from app.schemas.master import PaginatedResponse

router = APIRouter(prefix="/finance", tags=["Finance & Accounting"])


def get_finance_repo() -> FinanceRepository:
    db = mongodb_manager.get_database()
    return FinanceRepository(db)


def serialize_account(doc: Dict[str, Any]) -> AccountResponse:
    return AccountResponse(
        id=str(doc["_id"]),
        account_code=doc["account_code"],
        name=doc["name"],
        account_type=doc["account_type"],
        parent_account_code=doc.get("parent_account_code"),
        unit_id=doc.get("unit_id", "BOTH"),
        current_balance=doc.get("current_balance", 0.0),
        is_active=doc.get("is_active", True),
        description=doc.get("description"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_invoice(doc: Dict[str, Any]) -> CustomerInvoiceResponse:
    return CustomerInvoiceResponse(
        id=str(doc["_id"]),
        invoice_number=doc["invoice_number"],
        customer_id=doc["customer_id"],
        customer_code=doc.get("customer_code", ""),
        customer_name=doc.get("customer_name", ""),
        sales_order_id=doc.get("sales_order_id"),
        sales_order_number=doc.get("sales_order_number"),
        project_id=doc.get("project_id"),
        project_code=doc.get("project_code"),
        unit_id=doc.get("unit_id", "Unit_1"),
        invoice_date=doc["invoice_date"],
        due_date=doc["due_date"],
        subtotal_amount=doc.get("subtotal_amount", 0.0),
        tax_amount=doc.get("tax_amount", 0.0),
        total_amount=doc.get("total_amount", 0.0),
        amount_paid=doc.get("amount_paid", 0.0),
        balance_due=doc.get("balance_due", 0.0),
        status=doc.get("status", "DRAFT"),
        journal_entry_id=doc.get("journal_entry_id"),
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_bill(doc: Dict[str, Any]) -> SupplierBillResponse:
    return SupplierBillResponse(
        id=str(doc["_id"]),
        bill_number=doc["bill_number"],
        vendor_id=doc["vendor_id"],
        vendor_code=doc.get("vendor_code", ""),
        vendor_name=doc.get("vendor_name", ""),
        bill_number_vendor=doc.get("bill_number_vendor", ""),
        po_reference=doc.get("po_reference"),
        project_id=doc.get("project_id"),
        project_code=doc.get("project_code"),
        unit_id=doc.get("unit_id", "Unit_1"),
        bill_date=doc["bill_date"],
        due_date=doc["due_date"],
        subtotal_amount=doc.get("subtotal_amount", 0.0),
        tax_amount=doc.get("tax_amount", 0.0),
        total_amount=doc.get("total_amount", 0.0),
        amount_paid=doc.get("amount_paid", 0.0),
        balance_due=doc.get("balance_due", 0.0),
        status=doc.get("status", "DRAFT"),
        has_qc_hold=doc.get("has_qc_hold", False),
        qc_hold_reason=doc.get("qc_hold_reason"),
        qc_released_by=doc.get("qc_released_by"),
        qc_released_at=doc.get("qc_released_at"),
        journal_entry_id=doc.get("journal_entry_id"),
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_payment(doc: Dict[str, Any]) -> PaymentResponse:
    return PaymentResponse(
        id=str(doc["_id"]),
        payment_number=doc["payment_number"],
        payment_type=doc["payment_type"],
        entity_id=doc["entity_id"],
        entity_code=doc.get("entity_code", ""),
        entity_name=doc.get("entity_name", ""),
        reference_doc_id=doc.get("reference_doc_id"),
        reference_doc_number=doc.get("reference_doc_number"),
        project_id=doc.get("project_id"),
        project_code=doc.get("project_code"),
        unit_id=doc.get("unit_id", "Unit_1"),
        payment_date=doc["payment_date"],
        payment_method=doc.get("payment_method", "BANK_TRANSFER"),
        payment_reference=doc.get("payment_reference"),
        amount=doc.get("amount", 0.0),
        bank_account_code=doc.get("bank_account_code", "1010-BANK-HDFC"),
        journal_entry_id=doc.get("journal_entry_id"),
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_expense(doc: Dict[str, Any]) -> ExpenseResponse:
    return ExpenseResponse(
        id=str(doc["_id"]),
        expense_number=doc["expense_number"],
        expense_category=doc["expense_category"],
        expense_account_code=doc["expense_account_code"],
        project_id=doc.get("project_id"),
        project_code=doc.get("project_code"),
        unit_id=doc.get("unit_id", "Unit_1"),
        expense_date=doc["expense_date"],
        amount=doc.get("amount", 0.0),
        tax_amount=doc.get("tax_amount", 0.0),
        total_amount=doc.get("total_amount", 0.0),
        payment_method=doc.get("payment_method", "BANK_TRANSFER"),
        paid_from_account_code=doc.get("paid_from_account_code", "1010-BANK-HDFC"),
        vendor_or_payee=doc["vendor_or_payee"],
        reference_number=doc.get("reference_number"),
        journal_entry_id=doc.get("journal_entry_id"),
        notes=doc.get("notes"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


def serialize_journal(doc: Dict[str, Any]) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=str(doc["_id"]),
        entry_number=doc["entry_number"],
        entry_date=doc["entry_date"],
        unit_id=doc.get("unit_id", "Unit_1"),
        source_module=doc.get("source_module", "MANUAL"),
        source_reference=doc.get("source_reference", ""),
        description=doc.get("description", ""),
        lines=doc.get("lines", []),
        total_debit=doc.get("total_debit", 0.0),
        total_credit=doc.get("total_credit", 0.0),
        is_balanced=doc.get("is_balanced", True),
        status=doc.get("status", "POSTED"),
        is_reversal=doc.get("is_reversal", False),
        reversed_entry_id=doc.get("reversed_entry_id"),
        created_at=doc["created_at"],
        created_by=doc.get("created_by", "SYSTEM"),
    )


# -------------------------------------------------------------
# Summary & Analytics
# -------------------------------------------------------------
@router.get(
    "/summary",
    response_model=FinanceSummary,
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def get_finance_summary(
    unit_id: Optional[str] = Query(None, description="Unit_1 or Unit_2"),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Retrieve finance dashboard metrics, AR/AP totals, and cash balance."""
    return await repo.get_finance_summary(unit_id=unit_id)


# -------------------------------------------------------------
# Chart of Accounts (COA)
# -------------------------------------------------------------
@router.get(
    "/accounts",
    response_model=List[AccountResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_accounts(
    account_type: Optional[str] = Query(None),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List chart of accounts."""
    docs = await repo.list_accounts(account_type=account_type)
    return [serialize_account(d) for d in docs]


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "create")), Depends(verify_csrf_token)],
)
async def create_account(
    payload: AccountCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Create a new account in Chart of Accounts."""
    try:
        doc = await repo.create_account(payload, created_by=current_user["email"])
        return serialize_account(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# Customer Invoices (AR)
# -------------------------------------------------------------
@router.post(
    "/invoices",
    response_model=CustomerInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "create")), Depends(verify_csrf_token)],
)
async def create_invoice(
    payload: CustomerInvoiceCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Create and post customer invoice with automated double-entry voucher."""
    try:
        doc = await repo.create_invoice(payload, created_by=current_user["email"])
        return serialize_invoice(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/invoices",
    response_model=PaginatedResponse[CustomerInvoiceResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_invoices(
    customer_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List customer sales invoices."""
    items, total = await repo.list_invoices(
        customer_id=customer_id,
        unit_id=unit_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_invoice(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


# -------------------------------------------------------------
# Supplier Bills (AP) & QC Holds
# -------------------------------------------------------------
@router.post(
    "/bills",
    response_model=SupplierBillResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "create")), Depends(verify_csrf_token)],
)
async def create_supplier_bill(
    payload: SupplierBillCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Create and post supplier bill with duplicate invoice protection."""
    try:
        doc = await repo.create_supplier_bill(payload, created_by=current_user["email"])
        return serialize_bill(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/bills",
    response_model=PaginatedResponse[SupplierBillResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_supplier_bills(
    vendor_id: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List supplier purchase bills."""
    items, total = await repo.list_supplier_bills(
        vendor_id=vendor_id,
        unit_id=unit_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_bill(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.post(
    "/bills/{bill_id}/release-qc-hold",
    response_model=SupplierBillResponse,
    dependencies=[Depends(require_permission("finance", "approve")), Depends(verify_csrf_token)],
)
async def release_qc_hold(
    bill_id: str = Path(...),
    payload: QCHoldReleaseRequest = ...,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Authorized release of QC hold on supplier bill."""
    try:
        doc = await repo.release_qc_hold(
            bill_id=bill_id,
            release_notes=payload.release_notes,
            released_by=current_user["email"],
        )
        return serialize_bill(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# Payments & Receipts
# -------------------------------------------------------------
@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "create")), Depends(verify_csrf_token)],
)
async def record_payment(
    payload: PaymentCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Process customer receipt or vendor payment. Blocks vendor payments on QC hold."""
    try:
        doc = await repo.record_payment(payload, created_by=current_user["email"])
        return serialize_payment(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/payments",
    response_model=PaginatedResponse[PaymentResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_payments(
    payment_type: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List financial payments and receipts."""
    items, total = await repo.list_payments(
        payment_type=payment_type,
        unit_id=unit_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_payment(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


# -------------------------------------------------------------
# Operating Expenses
# -------------------------------------------------------------
@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "create")), Depends(verify_csrf_token)],
)
async def record_expense(
    payload: ExpenseCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Record direct operational expense with double-entry voucher."""
    try:
        doc = await repo.record_expense(payload, created_by=current_user["email"])
        return serialize_expense(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/expenses",
    response_model=PaginatedResponse[ExpenseResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_expenses(
    unit_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List operating expenses."""
    items, total = await repo.list_expenses(
        unit_id=unit_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_expense(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


# -------------------------------------------------------------
# Double-Entry Journal Engine
# -------------------------------------------------------------
@router.post(
    "/journals",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("finance", "post")), Depends(verify_csrf_token)],
)
async def post_journal_entry(
    payload: JournalEntryCreate,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Post manual or integrated double-entry journal voucher. Enforces debit-credit balance."""
    try:
        doc = await repo.post_journal_entry(payload, created_by=current_user["email"])
        return serialize_journal(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/journals",
    response_model=PaginatedResponse[JournalEntryResponse],
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def list_journal_entries(
    unit_id: Optional[str] = Query(None),
    source_module: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """List double-entry general ledger journal vouchers."""
    items, total = await repo.list_journal_entries(
        unit_id=unit_id,
        source_module=source_module,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_journal(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if page_size else 1,
    )


@router.post(
    "/journals/{entry_id}/reverse",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permission("finance", "post")), Depends(verify_csrf_token)],
)
async def reverse_journal_entry(
    entry_id: str = Path(...),
    payload: JournalReversalRequest = ...,
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Reverse a posted journal voucher with audit trail link."""
    try:
        doc = await repo.reverse_journal_entry(
            entry_id=entry_id,
            reason=payload.reversal_reason,
            reversed_by=current_user["email"],
        )
        return serialize_journal(doc)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -------------------------------------------------------------
# Financial Reports & Statements
# -------------------------------------------------------------
@router.get(
    "/reports/trial-balance",
    response_model=TrialBalanceResponse,
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def get_trial_balance(
    as_of_date: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Generate reconciled Trial Balance."""
    return await repo.get_trial_balance(as_of_date=as_of_date, unit_id=unit_id)


@router.get(
    "/reports/profit-and-loss",
    response_model=ProfitLossResponse,
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def get_profit_and_loss(
    from_date: str = Query(...),
    to_date: str = Query(...),
    unit_id: Optional[str] = Query(None),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Generate Profit & Loss Statement."""
    return await repo.get_profit_and_loss(from_date=from_date, to_date=to_date, unit_id=unit_id)


@router.get(
    "/reports/balance-sheet",
    response_model=BalanceSheetResponse,
    dependencies=[Depends(require_permission("finance", "read"))],
)
async def get_balance_sheet(
    as_of_date: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    repo: FinanceRepository = Depends(get_finance_repo),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """Generate Balance Sheet (Assets = Liabilities + Equity)."""
    return await repo.get_balance_sheet(as_of_date=as_of_date, unit_id=unit_id)
