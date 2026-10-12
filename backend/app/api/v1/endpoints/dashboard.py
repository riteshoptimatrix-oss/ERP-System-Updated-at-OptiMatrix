import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.database.mongodb import mongodb_manager
from app.models.user import ManufacturingUnit, RoleName
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardActivityResponse,
    KpiMetricItem,
    RecentActivityItem,
)
from app.api.deps import get_current_active_user, require_unit_access

logger = logging.getLogger("app.api.v1.dashboard")
router = APIRouter(prefix="/dashboard", tags=["Dashboard & KPIs"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get Unit-Scoped & Permission-Filtered Dashboard KPIs",
    dependencies=[Depends(require_unit_access("unit_id"))]
)
async def get_dashboard_summary(
    unit_id: ManufacturingUnit = Query(
        default=ManufacturingUnit.Unit_1,
        description="Facility identifier (Unit_1 or Unit_2)"
    ),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> DashboardSummaryResponse:
    """
    Returns verified KPI metrics scoped to the requested manufacturing plant.
    Permission-aware: Only returns data for modules where the user has 'read' authorization.
    Queries live MongoDB collections without inventing fake numbers.
    """
    db = mongodb_manager.get_database()
    user_perms: List[str] = current_user.get("permissions", [])
    user_role = current_user.get("role")
    is_super_admin = user_role == RoleName.SUPER_ADMIN.value

    unit_val = unit_id.value
    # Unit filter matches records specific to this plant or corporate records marked BOTH
    unit_query = {"unit_id": {"$in": [unit_val, ManufacturingUnit.BOTH.value]}}

    kpis: Dict[str, Optional[KpiMetricItem]] = {}
    permitted_count = 0

    # Helper to check read permission for a module
    def can_view(module_name: str) -> bool:
        if is_super_admin:
            return True
        return f"{module_name}:read" in user_perms

    # 1. Orders KPI
    if can_view("orders"):
        order_count = await db["sales_orders"].count_documents(unit_query)
        if order_count == 0:
            order_count = await db["orders"].count_documents(unit_query)
        pending_orders = await db["sales_orders"].count_documents({**unit_query, "status": {"$in": ["PENDING", "CONFIRMED", "PROCESSING", "IN_PRODUCTION"]}})
        if pending_orders == 0:
            pending_orders = await db["orders"].count_documents({**unit_query, "status": "PENDING"})
        kpis["orders"] = KpiMetricItem(
            title="Active Purchase Orders",
            value=order_count,
            pending_action_count=pending_orders,
            unit_id=unit_val,
            module="orders",
            permitted=True,
            subtitle="Customer orders in progress"
        )
        permitted_count += 1
    else:
        kpis["orders"] = None

    # 2. Sales & Dispatch KPI
    if can_view("sales"):
        dispatch_count = await db["dispatch_records"].count_documents(unit_query)
        if dispatch_count == 0:
            dispatch_count = await db["sales"].count_documents(unit_query)
        pending_dispatch = await db["dispatch_records"].count_documents({**unit_query, "status": {"$in": ["PENDING", "AWAITING_DISPATCH", "PACKED"]}})
        if pending_dispatch == 0:
            pending_dispatch = await db["sales_orders"].count_documents({**unit_query, "status": {"$in": ["CONFIRMED", "PROCESSING"]}})
        kpis["dispatch"] = KpiMetricItem(
            title="Scheduled Dispatches",
            value=dispatch_count,
            pending_action_count=pending_dispatch,
            unit_id=unit_val,
            module="sales",
            permitted=True,
            subtitle="Shipments & e-way bills"
        )
        permitted_count += 1
    else:
        kpis["dispatch"] = None

    # 3. Inventory Stock KPI
    if can_view("inventory"):
        stock_count = await db["inventory_stock"].count_documents(unit_query)
        if stock_count == 0:
            stock_count = await db["inventory"].count_documents(unit_query)
        low_stock = await db["inventory_stock"].count_documents({**unit_query, "$or": [{"is_below_reorder": True}, {"is_below_minimum": True}]})
        if low_stock == 0:
            low_stock = await db["inventory"].count_documents({**unit_query, "is_below_minimum": True})
        kpis["stock"] = KpiMetricItem(
            title="Tracked Inventory Items",
            value=stock_count,
            pending_action_count=low_stock,
            unit_id=unit_val,
            module="inventory",
            permitted=True,
            subtitle="Raw material & components"
        )
        permitted_count += 1
    else:
        kpis["stock"] = None

    # 4. Production Tracking KPI
    if can_view("production"):
        batch_count = await db["production_orders"].count_documents(unit_query)
        if batch_count == 0:
            batch_count = await db["production"].count_documents(unit_query)
        in_progress = await db["production_orders"].count_documents({**unit_query, "status": {"$in": ["IN_PROGRESS", "RELEASED", "PLANNED"]}})
        if in_progress == 0:
            in_progress = await db["production"].count_documents({**unit_query, "status": "IN_PROGRESS"})
        kpis["production"] = KpiMetricItem(
            title="Active Shop-Floor Batches",
            value=batch_count,
            pending_action_count=in_progress,
            unit_id=unit_val,
            module="production",
            permitted=True,
            subtitle="Machining & assembly stages"
        )
        permitted_count += 1
    else:
        kpis["production"] = None

    # 5. Quality Control KPI
    if can_view("qc"):
        qc_count = await db["production_outputs"].count_documents(unit_query)
        if qc_count == 0:
            qc_count = await db["qc"].count_documents(unit_query)
        pending_qc = await db["production_outputs"].count_documents({**unit_query, "status": {"$in": ["PENDING", "PENDING_INSPECTION"]}})
        if pending_qc == 0:
            pending_qc = await db["qc"].count_documents({**unit_query, "status": "PENDING_INSPECTION"})
        kpis["qc"] = KpiMetricItem(
            title="Quality Inspections",
            value=qc_count,
            pending_action_count=pending_qc,
            unit_id=unit_val,
            module="qc",
            permitted=True,
            subtitle="Dimensional & tolerance audits"
        )
        permitted_count += 1
    else:
        kpis["qc"] = None

    # 6. Wastage & Scrap KPI
    if can_view("wastage"):
        scrap_records = await db["scrap_entries"].count_documents(unit_query)
        if scrap_records == 0:
            scrap_records = await db["wastage"].count_documents(unit_query)
        unreconciled_scrap = await db["scrap_entries"].count_documents({**unit_query, "status": {"$in": ["PENDING", "UNRECONCILED"]}})
        if unreconciled_scrap == 0:
            unreconciled_scrap = await db["wastage"].count_documents({**unit_query, "status": "UNRECONCILED"})
        kpis["wastage"] = KpiMetricItem(
            title="Scrap & Offcut Logs",
            value=scrap_records,
            pending_action_count=unreconciled_scrap,
            unit_id=unit_val,
            module="wastage",
            permitted=True,
            subtitle="Melting loss & recycling batches"
        )
        permitted_count += 1
    else:
        kpis["wastage"] = None

    # 7. Attendance KPI
    if can_view("attendance"):
        today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        present_count = await db["hr_attendance"].count_documents({**unit_query, "date": today_date, "status": "PRESENT"})
        if present_count == 0:
            present_count = await db["hr_attendance"].count_documents({**unit_query, "status": "PRESENT"})
        absent_count = await db["hr_attendance"].count_documents({**unit_query, "date": today_date, "status": "ABSENT"})
        if absent_count == 0:
            absent_count = await db["hr_attendance"].count_documents({**unit_query, "status": "ABSENT"})
        kpis["attendance"] = KpiMetricItem(
            title="Shop-Floor Attendance",
            value=present_count,
            pending_action_count=absent_count,
            unit_id=unit_val,
            module="attendance",
            permitted=True,
            subtitle="Shift workforce count"
        )
        permitted_count += 1
    else:
        kpis["attendance"] = None

    # 8. Approvals KPI (HR/Finance/Admin)
    if can_view("hr") or can_view("finance") or is_super_admin:
        pending_approvals = await db["audit_logs"].count_documents({**unit_query, "action": {"$regex": "PENDING_APPROVAL"}})
        if pending_approvals == 0:
            pending_approvals = await db["leave_requests"].count_documents({**unit_query, "status": "PENDING"})
        kpis["approvals"] = KpiMetricItem(
            title="Pending Approvals",
            value=pending_approvals,
            pending_action_count=pending_approvals,
            unit_id=unit_val,
            module="roles",
            permitted=True,
            subtitle="Purchase orders & leave requests"
        )
        permitted_count += 1
    else:
        kpis["approvals"] = None

    return DashboardSummaryResponse(
        active_unit=unit_id,
        timestamp=datetime.now(timezone.utc),
        kpis=kpis,
        total_permitted_kpis=permitted_count
    )


def _format_utc_timestamp(ts: Any) -> str:
    """Standardize timestamps to canonical ISO-8601 UTC with Z suffix."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat().replace("+00:00", "Z")
    if isinstance(ts, str):
        if not ts.endswith("Z") and not ("+" in ts or "-" in ts[-6:]):
            return ts + "Z"
        return ts
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_activity_description(action: str, resource: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Format human-readable operations description for the live dashboard feed."""
    action_upper = (action or "").upper()
    details = details or {}
    
    if action_upper == "AUTH_LOGIN_SUCCESS":
        role_label = details.get("role", "User")
        return f"User login verified ({role_label} session)"
    if action_upper == "AUTH_LOGIN_FAILED":
        reason = details.get("reason", "invalid_credentials")
        return f"Authentication failed ({reason})"
    if action_upper == "AUTH_LOGOUT":
        return "User logged out (Session terminated)"
    if action_upper == "USER_CREATED":
        return f"New employee account created: {details.get('email', '')}"
    if action_upper == "USER_UPDATED":
        return f"Account permissions updated: {details.get('email', '')}"
    if action_upper == "USER_DEACTIVATED":
        return f"Employee account deactivated: {details.get('email', '')}"
    if action_upper == "SECURITY_OWNER_MUTATION_DENIED":
        return f"Executive protection: Super Admin mutation blocked ({resource})"
    if action_upper == "ORDER_CREATED":
        return f"Sales Order created ({details.get('order_number', 'Draft')})"
    if action_upper == "ORDER_CONFIRMED":
        return f"Sales Order confirmed for production"
    if action_upper == "ORDER_CANCELLED":
        return f"Sales Order cancelled"
    if action_upper == "PACKING_SLIP_GENERATED":
        return f"Packing slip generated for dispatch"
    if action_upper == "DISPATCH_RECORD_CREATED":
        return f"Finished goods dispatched from warehouse"
    if action_upper == "PRODUCTION_OUTPUT_RECORDED":
        return f"Batch production output logged"
    if action_upper == "SCRAP_RECORDED":
        return f"Material scrap / tolerance wastage logged"

    # Fallback to readable string
    clean_action = action.replace("_", " ").title()
    clean_resource = resource.replace("_", " ").title()
    return f"{clean_action} ({clean_resource})"


@router.get(
    "/activity",
    response_model=DashboardActivityResponse,
    summary="Get Unit-Scoped Recent Operations Feed",
    dependencies=[Depends(require_unit_access("unit_id"))]
)
async def get_dashboard_activity(
    unit_id: ManufacturingUnit = Query(
        default=ManufacturingUnit.Unit_1,
        description="Facility identifier (Unit_1 or Unit_2)"
    ),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> DashboardActivityResponse:
    """
    Returns recent operational activity logs for the selected facility in real-time.
    """
    db = mongodb_manager.get_database()
    unit_val = unit_id.value

    # Query audit logs scoped to this unit or global events
    cursor = db["audit_logs"].find({
        "$or": [
            {"unit_id": unit_val},
            {"unit_id": ManufacturingUnit.BOTH.value},
            {"unit_id": {"$exists": False}},
            {"unit_id": None}
        ]
    }).sort("timestamp", -1).limit(25)

    raw_logs = await cursor.to_list(length=25)
    activities: List[RecentActivityItem] = []

    for log in raw_logs:
        ts_str = _format_utc_timestamp(log.get("timestamp"))
        action_name = log.get("action", "EVENT")
        resource_name = log.get("resource", "system")
        details = log.get("details")

        activities.append(
            RecentActivityItem(
                id=str(log["_id"]),
                module=resource_name,
                action=action_name,
                description=_format_activity_description(action_name, resource_name, details),
                timestamp=ts_str,
                user_email=log.get("email"),
                unit_id=log.get("unit_id", unit_val),
                status=log.get("status", "SUCCESS")
            )
        )

    # Also include recent order activities if available
    order_activities_cursor = db["order_activities"].find({}).sort("timestamp", -1).limit(10)
    order_acts = await order_activities_cursor.to_list(length=10)
    for act in order_acts:
        ts_str = _format_utc_timestamp(act.get("timestamp"))
        activities.append(
            RecentActivityItem(
                id=str(act["_id"]),
                module="orders",
                action=act.get("action", "ORDER_EVENT"),
                description=act.get("description") or f"Order event: {act.get('action')}",
                timestamp=ts_str,
                user_email=act.get("performed_by"),
                unit_id=unit_val,
                status="SUCCESS"
            )
        )

    # Sort merged activities by timestamp descending and take top 25
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    activities = activities[:25]

    return DashboardActivityResponse(
        active_unit=unit_id,
        activities=activities
    )

