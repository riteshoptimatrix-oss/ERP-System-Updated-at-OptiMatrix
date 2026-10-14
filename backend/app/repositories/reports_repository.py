import csv
import io
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.models.user import ManufacturingUnit
from app.schemas.reports import ReportType, ReportSummaryKpi, GenericReportResponse

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    openpyxl = None


class ReportsRepository:
    """
    Central reporting and analytics engine for Opti Matrix.
    Reconciles real transactions across orders, dispatch, inventory, BOM,
    production, QC, wastage, downtime, attendance, payroll, and finance.
    """

    def __init__(self, db):
        self.db = db

    async def get_report_data(
        self,
        report_type: ReportType,
        unit_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> GenericReportResponse:
        """
        Executes verified aggregation queries according to the requested report type.
        """
        unit_filter = {}
        if unit_id and unit_id != "BOTH":
            unit_filter = {"unit_id": {"$in": [unit_id, "BOTH"]}}

        date_filter = {}
        if start_date and end_date:
            date_filter = {"$gte": start_date, "$lte": end_date}
        elif start_date:
            date_filter = {"$gte": start_date}
        elif end_date:
            date_filter = {"$lte": end_date}

        handler = getattr(self, f"_report_{report_type.value}", None)
        if not handler:
            raise ValueError(f"Unsupported report type: {report_type}")

        columns, items, total, kpis = await handler(
            unit_filter=unit_filter,
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            search=search,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if page_size else 1

        return GenericReportResponse(
            report_type=report_type,
            unit_id=unit_id,
            start_date=start_date,
            end_date=end_date,
            kpis=kpis,
            columns=columns,
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            generated_at=datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------------
    # 1. Sales & Customer Invoices
    # -------------------------------------------------------------------------
    async def _report_sales(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["invoice_date"] = date_filter
        if search:
            query["$or"] = [
                {"invoice_number": {"$regex": search, "$options": "i"}},
                {"customer_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["invoices"].find(query).sort("invoice_date", -1)
        total = await self.db["invoices"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        # Aggregate total revenue and outstanding balances
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$total_amount"},
                    "total_received": {"$sum": "$amount_paid"},
                    "total_outstanding": {"$sum": "$balance_amount"},
                }
            },
        ]
        agg = await self.db["invoices"].aggregate(pipeline).to_list(length=1)
        rev = round(agg[0]["total_revenue"], 2) if agg else 0.0
        rec = round(agg[0]["total_received"], 2) if agg else 0.0
        bal = round(agg[0]["total_outstanding"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Invoiced Revenue", metric_value=rev, formatted_value=f"₹{rev:,.2f}"),
            ReportSummaryKpi(metric_name="Total Collected Receipts", metric_value=rec, formatted_value=f"₹{rec:,.2f}"),
            ReportSummaryKpi(metric_name="Outstanding Receivables", metric_value=bal, formatted_value=f"₹{bal:,.2f}"),
            ReportSummaryKpi(metric_name="Invoice Volume", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "invoice_number", "label": "Invoice #"},
            {"key": "invoice_date", "label": "Date"},
            {"key": "customer_name", "label": "Customer"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "total_amount", "label": "Total Amount (₹)"},
            {"key": "amount_paid", "label": "Paid (₹)"},
            {"key": "balance_amount", "label": "Balance (₹)"},
            {"key": "status", "label": "Payment Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "invoice_number": d.get("invoice_number", ""),
                "invoice_date": d.get("invoice_date", ""),
                "customer_name": d.get("customer_name", ""),
                "unit_id": d.get("unit_id", ""),
                "total_amount": round(d.get("total_amount", 0.0), 2),
                "amount_paid": round(d.get("amount_paid", 0.0), 2),
                "balance_amount": round(d.get("balance_amount", 0.0), 2),
                "status": d.get("status", ""),
            }
            for d in docs
        ]

        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 2. Sales Orders
    # -------------------------------------------------------------------------
    async def _report_orders(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["order_date"] = date_filter
        if search:
            query["$or"] = [
                {"order_number": {"$regex": search, "$options": "i"}},
                {"customer_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["orders"].find(query).sort("created_at", -1)
        total = await self.db["orders"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_order_val": {"$sum": "$total_amount"},
                }
            },
        ]
        agg = await self.db["orders"].aggregate(pipeline).to_list(length=1)
        val = round(agg[0]["total_order_val"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Order Value", metric_value=val, formatted_value=f"₹{val:,.2f}"),
            ReportSummaryKpi(metric_name="Total Sales Orders", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "order_number", "label": "Order #"},
            {"key": "order_date", "label": "Date"},
            {"key": "customer_name", "label": "Customer"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "total_amount", "label": "Amount (₹)"},
            {"key": "status", "label": "Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "order_number": d.get("order_number", ""),
                "order_date": d.get("order_date", str(d.get("created_at", ""))[:10]),
                "customer_name": d.get("customer_name", ""),
                "unit_id": d.get("unit_id", ""),
                "total_amount": round(d.get("total_amount", 0.0), 2),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 3. Dispatches & Packing Slips
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    async def _report_dispatch(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        # Prefer detailed packing_dispatch_records if available
        pdr_count = await self.db["packing_dispatch_records"].count_documents({})
        if pdr_count > 0:
            query = {**unit_filter}
            if search:
                query["$or"] = [
                    {"dispatch_no": {"$regex": search, "$options": "i"}},
                    {"box_no": {"$regex": search, "$options": "i"}},
                    {"operator": {"$regex": search, "$options": "i"}},
                    {"brand": {"$regex": search, "$options": "i"}},
                    {"product_type": {"$regex": search, "$options": "i"}},
                    {"size_length": {"$regex": search, "$options": "i"}},
                    {"remarks": {"$regex": search, "$options": "i"}},
                ]

            cursor = self.db["packing_dispatch_records"].find(query).sort("_id", 1)
            total = await self.db["packing_dispatch_records"].count_documents(query)
            docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

            kpis = [
                ReportSummaryKpi(metric_name="Total Packed Bins/Boxes", metric_value=total, formatted_value=str(total)),
            ]

            columns = [
                {"key": "date", "label": "Packing Date"},
                {"key": "box_no", "label": "Box/Bin #"},
                {"key": "weight_kg", "label": "Weight (kg)"},
                {"key": "operator", "label": "Packed By / Operator"},
                {"key": "brand", "label": "Brand / Customer"},
                {"key": "product_type", "label": "Product Type"},
                {"key": "size_length", "label": "Size / Length"},
                {"key": "quantity", "label": "Quantity (Pcs)"},
                {"key": "dispatch_date", "label": "Dispatch Date"},
                {"key": "dispatch_no", "label": "Dispatch Slip #"},
                {"key": "remarks", "label": "Remarks"},
            ]

            items = [
                {
                    "id": str(d["_id"]),
                    "date": d.get("date", ""),
                    "box_no": str(d.get("box_no", "")),
                    "weight_kg": d.get("weight_kg", 0.0),
                    "operator": d.get("operator", ""),
                    "brand": d.get("brand", ""),
                    "product_type": d.get("product_type", ""),
                    "size_length": d.get("size_length", ""),
                    "quantity": d.get("quantity", 0),
                    "dispatch_date": d.get("dispatch_date", ""),
                    "dispatch_no": d.get("dispatch_no", ""),
                    "remarks": d.get("remarks", ""),
                }
                for d in docs
            ]
            return columns, items, total, kpis

        query = {**unit_filter}
        if date_filter:
            query["dispatch_date"] = date_filter
        if search:
            query["$or"] = [
                {"dispatch_number": {"$regex": search, "$options": "i"}},
                {"order_number": {"$regex": search, "$options": "i"}},
                {"customer_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["dispatches"].find(query).sort("created_at", -1)
        total = await self.db["dispatches"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        kpis = [
            ReportSummaryKpi(metric_name="Total Dispatches", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "dispatch_number", "label": "Dispatch Slip #"},
            {"key": "order_number", "label": "Sales Order #"},
            {"key": "customer_name", "label": "Customer"},
            {"key": "dispatch_date", "label": "Date"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "status", "label": "Dispatch Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "dispatch_number": d.get("dispatch_number", ""),
                "order_number": d.get("order_number", ""),
                "customer_name": d.get("customer_name", ""),
                "dispatch_date": d.get("dispatch_date", str(d.get("created_at", ""))[:10]),
                "unit_id": d.get("unit_id", ""),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 4. Inventory Balances & Valuation
    # -------------------------------------------------------------------------
    async def _report_inventory(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if search:
            query["$or"] = [
                {"material_code": {"$regex": search, "$options": "i"}},
                {"material_name": {"$regex": search, "$options": "i"}},
                {"product_code": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["stock_balances"].find(query).sort("quantity", -1)
        total = await self.db["stock_balances"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_qty": {"$sum": "$quantity"},
                    "low_stock_items": {
                        "$sum": {"$cond": [{"$lte": ["$quantity", "$reorder_level"]}, 1, 0]}
                    },
                }
            },
        ]
        agg = await self.db["stock_balances"].aggregate(pipeline).to_list(length=1)
        t_qty = round(agg[0]["total_qty"], 2) if agg else 0.0
        low_stk = agg[0]["low_stock_items"] if agg else 0

        kpis = [
            ReportSummaryKpi(metric_name="Total Stocked Qty", metric_value=t_qty, formatted_value=f"{t_qty:,.2f}"),
            ReportSummaryKpi(metric_name="Low Stock Alerts", metric_value=low_stk, formatted_value=str(low_stk)),
            ReportSummaryKpi(metric_name="Tracked SKU Count", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "item_code", "label": "Item / SKU Code"},
            {"key": "item_name", "label": "Description"},
            {"key": "item_type", "label": "Type"},
            {"key": "warehouse_id", "label": "Warehouse"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "quantity", "label": "Current Balance"},
            {"key": "uom", "label": "UoM"},
            {"key": "reorder_level", "label": "Reorder Level"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "item_code": d.get("material_code") or d.get("product_code") or d.get("item_code", ""),
                "item_name": d.get("material_name") or d.get("product_name") or d.get("item_name", ""),
                "item_type": d.get("item_type", "RAW_MATERIAL"),
                "warehouse_id": d.get("warehouse_id", ""),
                "unit_id": d.get("unit_id", ""),
                "quantity": round(d.get("quantity", 0.0), 2),
                "uom": d.get("uom", "NOS"),
                "reorder_level": d.get("reorder_level", 0.0),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 5. Bill of Materials (BOM)
    # -------------------------------------------------------------------------
    async def _report_bom(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if search:
            query["$or"] = [
                {"bom_number": {"$regex": search, "$options": "i"}},
                {"product_code": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["boms"].find(query).sort("created_at", -1)
        total = await self.db["boms"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        approved_count = await self.db["boms"].count_documents({**query, "status": "APPROVED"})

        kpis = [
            ReportSummaryKpi(metric_name="Total Active BOMs", metric_value=total, formatted_value=str(total)),
            ReportSummaryKpi(metric_name="Approved Revisions", metric_value=approved_count, formatted_value=str(approved_count)),
        ]

        columns = [
            {"key": "bom_number", "label": "BOM Number"},
            {"key": "product_code", "label": "Product Code"},
            {"key": "product_name", "label": "Product Name"},
            {"key": "revision_no", "label": "Revision #"},
            {"key": "total_estimated_cost", "label": "Est. Cost (₹)"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "status", "label": "Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "bom_number": d.get("bom_number", ""),
                "product_code": d.get("product_code", ""),
                "product_name": d.get("product_name", ""),
                "revision_no": d.get("revision_no", 1),
                "total_estimated_cost": round(d.get("total_estimated_cost", 0.0), 2),
                "unit_id": d.get("unit_id", ""),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 6. Production Orders & WIP
    # -------------------------------------------------------------------------
    async def _report_production(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["planned_start_date"] = date_filter
        if search:
            query["$or"] = [
                {"production_order_number": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["production_orders"].find(query).sort("created_at", -1)
        total = await self.db["production_orders"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "planned_qty": {"$sum": "$planned_quantity"},
                    "completed_qty": {"$sum": "$completed_quantity"},
                    "rejected_qty": {"$sum": "$rejected_quantity"},
                }
            },
        ]
        agg = await self.db["production_orders"].aggregate(pipeline).to_list(length=1)
        p_qty = round(agg[0]["planned_qty"], 2) if agg else 0.0
        c_qty = round(agg[0]["completed_qty"], 2) if agg else 0.0
        r_qty = round(agg[0]["rejected_qty"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Planned Quantity", metric_value=p_qty, formatted_value=f"{p_qty:,.2f}"),
            ReportSummaryKpi(metric_name="Completed Finished Goods", metric_value=c_qty, formatted_value=f"{c_qty:,.2f}"),
            ReportSummaryKpi(metric_name="Rejected In-Process", metric_value=r_qty, formatted_value=f"{r_qty:,.2f}"),
            ReportSummaryKpi(metric_name="Total Production Orders", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "production_order_number", "label": "Prod Order #"},
            {"key": "product_name", "label": "Finished Product"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "planned_quantity", "label": "Planned Qty"},
            {"key": "completed_quantity", "label": "Completed Qty"},
            {"key": "rejected_quantity", "label": "Rejected Qty"},
            {"key": "status", "label": "Order Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "production_order_number": d.get("production_order_number", ""),
                "product_name": d.get("product_name", ""),
                "unit_id": d.get("unit_id", ""),
                "planned_quantity": round(d.get("planned_quantity", 0.0), 2),
                "completed_quantity": round(d.get("completed_quantity", 0.0), 2),
                "rejected_quantity": round(d.get("rejected_quantity", 0.0), 2),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 7. Quality Control & Non-Conformance
    # -------------------------------------------------------------------------
    async def _report_qc(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["inspection_date"] = date_filter
        if search:
            query["$or"] = [
                {"inspection_number": {"$regex": search, "$options": "i"}},
                {"item_name": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["qc_inspections"].find(query).sort("created_at", -1)
        total = await self.db["qc_inspections"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        passed = await self.db["qc_inspections"].count_documents({**query, "status": "PASSED"})
        failed = await self.db["qc_inspections"].count_documents({**query, "status": "FAILED"})
        quarantined = await self.db["qc_inspections"].count_documents({**query, "status": "QUARANTINED"})

        kpis = [
            ReportSummaryKpi(metric_name="Passed Inspections", metric_value=passed, formatted_value=str(passed)),
            ReportSummaryKpi(metric_name="Failed / Rejected", metric_value=failed, formatted_value=str(failed)),
            ReportSummaryKpi(metric_name="Quarantined Lots", metric_value=quarantined, formatted_value=str(quarantined)),
            ReportSummaryKpi(metric_name="Total Inspections", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "inspection_number", "label": "QC Report #"},
            {"key": "inspection_type", "label": "Stage"},
            {"key": "item_name", "label": "Inspected Item"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "status", "label": "Result Status"},
            {"key": "inspector_name", "label": "Inspector"},
            {"key": "inspection_date", "label": "Inspection Date"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "inspection_number": d.get("inspection_number", ""),
                "inspection_type": d.get("inspection_type", ""),
                "item_name": d.get("item_name", ""),
                "unit_id": d.get("unit_id", ""),
                "status": d.get("status", ""),
                "inspector_name": d.get("inspector_name", ""),
                "inspection_date": d.get("inspection_date", str(d.get("created_at", ""))[:10]),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 8. Wastage & Scrap
    # -------------------------------------------------------------------------
    async def _report_wastage(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["date"] = date_filter
        if search:
            query["$or"] = [
                {"scrap_code": {"$regex": search, "$options": "i"}},
                {"reason": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["wastage"].find(query).sort("date", -1)
        total = await self.db["wastage"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_scrap_qty": {"$sum": "$quantity"},
                }
            },
        ]
        agg = await self.db["wastage"].aggregate(pipeline).to_list(length=1)
        s_qty = round(agg[0]["total_scrap_qty"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Scrap Generated", metric_value=s_qty, formatted_value=f"{s_qty:,.2f}"),
            ReportSummaryKpi(metric_name="Scrap Entry Count", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "date", "label": "Date"},
            {"key": "scrap_code", "label": "Scrap / Material"},
            {"key": "category", "label": "Category"},
            {"key": "quantity", "label": "Quantity"},
            {"key": "uom", "label": "UoM"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "reason", "label": "Reason / Root Cause"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "date": d.get("date", ""),
                "scrap_code": d.get("scrap_code") or d.get("material_name", ""),
                "category": d.get("category", "PRODUCTION_SCRAP"),
                "quantity": round(d.get("quantity", 0.0), 2),
                "uom": d.get("uom", "KG"),
                "unit_id": d.get("unit_id", ""),
                "reason": d.get("reason", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 9. Downtime & Power Outages
    # -------------------------------------------------------------------------
    async def _report_downtime(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["date"] = date_filter
        if search:
            query["reason"] = {"$regex": search, "$options": "i"}

        cursor = self.db["power_outages"].find(query).sort("date", -1)
        total = await self.db["power_outages"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_duration_mins": {"$sum": "$duration_minutes"},
                }
            },
        ]
        agg = await self.db["power_outages"].aggregate(pipeline).to_list(length=1)
        d_mins = agg[0]["total_duration_mins"] if agg else 0
        d_hrs = round(d_mins / 60.0, 2)

        kpis = [
            ReportSummaryKpi(metric_name="Total Downtime (Hours)", metric_value=d_hrs, formatted_value=f"{d_hrs:,.1f} hrs"),
            ReportSummaryKpi(metric_name="Total Outage Incidents", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "date", "label": "Date"},
            {"key": "start_time", "label": "Start Time"},
            {"key": "end_time", "label": "End Time"},
            {"key": "duration_minutes", "label": "Duration (Mins)"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "reason", "label": "Outage Reason"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "date": d.get("date", ""),
                "start_time": d.get("start_time", ""),
                "end_time": d.get("end_time", ""),
                "duration_minutes": d.get("duration_minutes", 0),
                "unit_id": d.get("unit_id", ""),
                "reason": d.get("reason", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 10. HR & Attendance
    # -------------------------------------------------------------------------
    async def _report_attendance(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["date"] = date_filter
        if search:
            query["$or"] = [
                {"employee_name": {"$regex": search, "$options": "i"}},
                {"employee_code": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["attendance"].find(query).sort("date", -1)
        total = await self.db["attendance"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        present = await self.db["attendance"].count_documents({**query, "status": "PRESENT"})
        absent = await self.db["attendance"].count_documents({**query, "status": "ABSENT"})

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_ot_hours": {"$sum": "$overtime_hours"},
                }
            },
        ]
        agg = await self.db["attendance"].aggregate(pipeline).to_list(length=1)
        ot = round(agg[0]["total_ot_hours"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Present Records", metric_value=present, formatted_value=str(present)),
            ReportSummaryKpi(metric_name="Absent Records", metric_value=absent, formatted_value=str(absent)),
            ReportSummaryKpi(metric_name="Total Overtime Hours", metric_value=ot, formatted_value=f"{ot:,.1f} hrs"),
            ReportSummaryKpi(metric_name="Total Shifts Logged", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "date", "label": "Date"},
            {"key": "employee_code", "label": "Employee Code"},
            {"key": "employee_name", "label": "Employee Name"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "status", "label": "Attendance Status"},
            {"key": "check_in", "label": "In Time"},
            {"key": "check_out", "label": "Out Time"},
            {"key": "overtime_hours", "label": "Overtime (Hrs)"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "date": d.get("date", ""),
                "employee_code": d.get("employee_code", ""),
                "employee_name": d.get("employee_name", ""),
                "unit_id": d.get("unit_id", ""),
                "status": d.get("status", ""),
                "check_in": d.get("check_in", "-"),
                "check_out": d.get("check_out", "-"),
                "overtime_hours": round(d.get("overtime_hours", 0.0), 2),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 11. Payroll Runs & Disbursements
    # -------------------------------------------------------------------------
    async def _report_payroll(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if search:
            query["period"] = {"$regex": search, "$options": "i"}

        cursor = self.db["payroll_runs"].find(query).sort("created_at", -1)
        total = await self.db["payroll_runs"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_gross": {"$sum": "$total_gross_pay"},
                    "total_net": {"$sum": "$total_net_pay"},
                }
            },
        ]
        agg = await self.db["payroll_runs"].aggregate(pipeline).to_list(length=1)
        gross = round(agg[0]["total_gross"], 2) if agg else 0.0
        net = round(agg[0]["total_net"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Gross Pay", metric_value=gross, formatted_value=f"₹{gross:,.2f}"),
            ReportSummaryKpi(metric_name="Total Net Disbursed", metric_value=net, formatted_value=f"₹{net:,.2f}"),
            ReportSummaryKpi(metric_name="Total Payroll Runs", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "payroll_run_number", "label": "Payroll Run #"},
            {"key": "period", "label": "Month / Period"},
            {"key": "unit_id", "label": "Unit"},
            {"key": "employee_count", "label": "Headcount"},
            {"key": "total_gross_pay", "label": "Gross Pay (₹)"},
            {"key": "total_net_pay", "label": "Net Pay (₹)"},
            {"key": "status", "label": "Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "payroll_run_number": d.get("payroll_run_number", ""),
                "period": d.get("period", ""),
                "unit_id": d.get("unit_id", ""),
                "employee_count": d.get("employee_count", 0),
                "total_gross_pay": round(d.get("total_gross_pay", 0.0), 2),
                "total_net_pay": round(d.get("total_net_pay", 0.0), 2),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # 12. Finance & General Ledger Summary
    # -------------------------------------------------------------------------
    async def _report_finance(self, unit_filter, date_filter, start_date, end_date, search, page, page_size):
        query = {**unit_filter}
        if date_filter:
            query["entry_date"] = date_filter
        if search:
            query["$or"] = [
                {"entry_number": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        cursor = self.db["journal_entries"].find(query).sort("entry_date", -1)
        total = await self.db["journal_entries"].count_documents(query)
        docs = await cursor.skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_debit": {"$sum": "$total_debit"},
                    "total_credit": {"$sum": "$total_credit"},
                }
            },
        ]
        agg = await self.db["journal_entries"].aggregate(pipeline).to_list(length=1)
        deb = round(agg[0]["total_debit"], 2) if agg else 0.0
        crd = round(agg[0]["total_credit"], 2) if agg else 0.0

        kpis = [
            ReportSummaryKpi(metric_name="Total Debits", metric_value=deb, formatted_value=f"₹{deb:,.2f}"),
            ReportSummaryKpi(metric_name="Total Credits", metric_value=crd, formatted_value=f"₹{crd:,.2f}"),
            ReportSummaryKpi(metric_name="Balanced Ledger Difference", metric_value=round(deb - crd, 2), formatted_value=f"₹{round(deb - crd, 2):,.2f}"),
            ReportSummaryKpi(metric_name="Journal Entries Count", metric_value=total, formatted_value=str(total)),
        ]

        columns = [
            {"key": "entry_number", "label": "Journal Entry #"},
            {"key": "entry_date", "label": "Date"},
            {"key": "unit_id", "label": "Facility"},
            {"key": "source_module", "label": "Source"},
            {"key": "description", "label": "Description"},
            {"key": "total_debit", "label": "Total Amount (₹)"},
            {"key": "status", "label": "Status"},
        ]

        items = [
            {
                "id": str(d["_id"]),
                "entry_number": d.get("entry_number", ""),
                "entry_date": d.get("entry_date", ""),
                "unit_id": d.get("unit_id", ""),
                "source_module": d.get("source_module", ""),
                "description": d.get("description", ""),
                "total_debit": round(d.get("total_debit", 0.0), 2),
                "status": d.get("status", ""),
            }
            for d in docs
        ]
        return columns, items, total, kpis

    # -------------------------------------------------------------------------
    # Export Generators (CSV and Excel)
    # -------------------------------------------------------------------------
    def export_csv(self, report_response: GenericReportResponse) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = [col["label"] for col in report_response.columns]
        keys = [col["key"] for col in report_response.columns]
        writer.writerow(headers)

        # Data rows
        for item in report_response.items:
            row = [str(item.get(k, "")) for k in keys]
            writer.writerow(row)

        return output.getvalue().encode("utf-8")

    def export_xlsx(self, report_response: GenericReportResponse) -> bytes:
        if not openpyxl:
            # Fallback to CSV bytes if openpyxl is not available
            return self.export_csv(report_response)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{report_response.report_type.value.title()} Report"

        # Title and KPI banner
        ws.append([f"Opti Matrix ERP - {report_response.report_type.value.upper()} REPORT"])
        title_cell = ws.cell(row=1, column=1)
        title_cell.font = Font(name="Arial", size=14, bold=True, color="1E3A8A")

        ws.append([f"Generated at: {report_response.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | Unit: {report_response.unit_id or 'ALL'}"])
        ws.append([])

        # KPIs
        if report_response.kpis:
            kpi_headers = [k.metric_name for k in report_response.kpis]
            kpi_values = [k.formatted_value for k in report_response.kpis]
            ws.append(kpi_headers)
            ws.append(kpi_values)
            ws.append([])

        # Table Headers
        headers = [col["label"] for col in report_response.columns]
        keys = [col["key"] for col in report_response.columns]
        ws.append(headers)
        header_row_idx = ws.max_row

        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row_idx, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Table Data
        for item in report_response.items:
            row_data = [item.get(k, "") for k in keys]
            ws.append(row_data)

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream.getvalue()
