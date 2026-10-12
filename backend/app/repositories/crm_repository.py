import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.repositories.base import BaseRepository
from app.repositories.master_repository import MasterRepository

class CrmRepository(BaseRepository):
    """
    Dedicated MongoDB repository for CRM Leads, Follow-ups, Activities, and Conversion.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "crm_leads")
        self.activities_col = db["crm_activities"]
        self.customers_repo = MasterRepository(db, "customers")

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find lead by unique lead code."""
        pattern = re.compile(f"^{re.escape(code.strip())}$", re.IGNORECASE)
        return await self.collection.find_one({"code": pattern})

    async def generate_lead_code(self) -> str:
        """Generate next sequence code e.g. LEAD-2026-0001."""
        year = datetime.now(timezone.utc).year
        count = await self.collection.count_documents({})
        return f"LEAD-{year}-{count + 1:04d}"

    async def list_leads(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        source: Optional[str] = None,
        assigned_to: Optional[str] = None,
        unit_id: Optional[str] = None,
        follow_up_filter: Optional[str] = None, # 'today', 'overdue', 'upcoming'
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query leads with dynamic filters, search regex, pagination, and sorting.
        """
        filter_query: Dict[str, Any] = {}

        if status:
            filter_query["status"] = status
        if priority:
            filter_query["priority"] = priority
        if source:
            filter_query["source"] = source
        if assigned_to:
            filter_query["assigned_to"] = assigned_to

        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [
                {"unit_id": unit_id},
                {"unit_id": "BOTH"},
            ]

        # Follow-up date filters
        now = datetime.now(timezone.utc)
        if follow_up_filter == "overdue":
            filter_query["next_follow_up"] = {"$lt": now, "$ne": None}
            filter_query["status"] = {"$nin": ["CONVERTED", "LOST"]}
        elif follow_up_filter == "today":
            start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
            filter_query["next_follow_up"] = {"$gte": start_of_day, "$lte": end_of_day}
        elif follow_up_filter == "upcoming":
            filter_query["next_follow_up"] = {"$gt": now}

        # Text search
        if search and search.strip():
            clean_search = re.escape(search.strip())
            search_regex = {"$regex": clean_search, "$options": "i"}
            search_clauses = [
                {"code": search_regex},
                {"company_name": search_regex},
                {"contact_person": search_regex},
                {"phone": search_regex},
                {"email": search_regex},
            ]
            if "$or" in filter_query:
                filter_query = {"$and": [{"$or": filter_query["$or"]}, {"$or": search_clauses}]}
            else:
                filter_query["$or"] = search_clauses

        total = await self.collection.count_documents(filter_query)
        skip = (page - 1) * page_size
        cursor = self.collection.find(filter_query).sort(sort_by, sort_order).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    async def create_lead(self, data: Dict[str, Any], user_email: str) -> str:
        """
        Create lead with duplicate check and initial activity entry.
        """
        # Duplicate detection by phone or company
        company = data.get("company_name", "").strip()
        phone = data.get("phone", "").strip()
        existing = await self.collection.find_one({
            "$or": [
                {"company_name": re.compile(f"^{re.escape(company)}$", re.IGNORECASE), "status": {"$nin": ["LOST"]}},
                {"phone": phone, "status": {"$nin": ["LOST"]}},
            ]
        })
        if existing:
            raise ValueError(f"An active lead for company '{company}' or phone '{phone}' already exists ({existing.get('code')}).")

        code = data.get("code")
        if not code:
            code = await self.generate_lead_code()
        else:
            code = code.strip().upper()
            if await self.get_by_code(code):
                raise ValueError(f"Lead with code '{code}' already exists.")

        now = datetime.now(timezone.utc)
        record = {
            **data,
            "code": code,
            "created_at": now,
            "created_by": user_email,
            "updated_at": now,
            "updated_by": user_email,
        }

        result = await self.collection.insert_one(record)
        lead_id = str(result.inserted_id)

        # Log initial creation activity
        await self.add_activity(
            lead_id=lead_id,
            activity_type="NOTE",
            summary="Lead Created",
            details=f"Lead recorded by {user_email}. Initial stage: {data.get('status', 'NEW')}.",
            user_email=user_email,
        )

        return lead_id

    async def update_lead(self, lead_id: str, data: Dict[str, Any], user_email: str) -> bool:
        """
        Update lead fields and log status changes if stage changed.
        """
        if not ObjectId.is_valid(lead_id):
            return False

        existing = await self.collection.find_one({"_id": ObjectId(lead_id)})
        if not existing:
            return False

        old_status = existing.get("status")
        new_status = data.get("status")

        now = datetime.now(timezone.utc)
        update_doc = {
            **data,
            "updated_at": now,
            "updated_by": user_email,
        }

        res = await self.collection.update_one(
            {"_id": ObjectId(lead_id)},
            {"$set": update_doc}
        )

        if new_status and new_status != old_status:
            await self.add_activity(
                lead_id=lead_id,
                activity_type="STATUS_CHANGE",
                summary=f"Stage changed: {old_status} ➔ {new_status}",
                details=f"Updated by {user_email}.",
                user_email=user_email,
            )

        return res.matched_count > 0

    async def add_activity(
        self,
        lead_id: str,
        activity_type: str,
        summary: str,
        details: Optional[str],
        user_email: str,
        next_follow_up: Optional[datetime] = None,
    ) -> str:
        """
        Log an interaction activity against a lead and optionally update lead's next follow-up.
        """
        now = datetime.now(timezone.utc)
        act_doc = {
            "lead_id": lead_id,
            "activity_type": activity_type,
            "summary": summary,
            "details": details,
            "created_at": now,
            "created_by": user_email,
        }
        res = await self.activities_col.insert_one(act_doc)

        if next_follow_up is not None and ObjectId.is_valid(lead_id):
            await self.collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": {"next_follow_up": next_follow_up, "updated_at": now, "updated_by": user_email}}
            )

        return str(res.inserted_id)

    async def list_activities(self, lead_id: str) -> List[Dict[str, Any]]:
        """Fetch all activities for a lead sorted latest first."""
        cursor = self.activities_col.find({"lead_id": lead_id}).sort("created_at", -1)
        items = await cursor.to_list(length=100)
        return items

    async def convert_lead_to_customer(
        self,
        lead_id: str,
        customer_payload: Dict[str, Any],
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Convert a qualified lead into a permanent Customer Master record.
        Enforces duplicate prevention across code and tax registers.
        """
        if not ObjectId.is_valid(lead_id):
            raise ValueError("Invalid lead ID.")

        lead = await self.collection.find_one({"_id": ObjectId(lead_id)})
        if not lead:
            raise ValueError("Lead record not found.")

        if lead.get("status") == "CONVERTED":
            raise ValueError(f"Lead is already converted (Customer ID: {lead.get('converted_customer_id')}).")

        # Create customer record through MasterRepository to ensure uniqueness and audit
        raw_code = (customer_payload.get("customer_code") or "").strip()
        if not raw_code:
            lead_code = lead.get("code") or f"L-{lead_id[:6]}"
            raw_code = f"CUST-{lead_code.replace('LEAD-', '')}"
        customer_code = raw_code.upper()

        lead_email = (lead.get("email") or "").strip()
        if not lead_email or "@" not in lead_email:
            lead_email = None

        cust_doc = {
            "code": customer_code,
            "name": lead["company_name"],
            "gstin": customer_payload.get("gstin") or None,
            "pan": customer_payload.get("pan") or None,
            "contact_person": lead.get("contact_person") or None,
            "phone": lead.get("phone") or None,
            "email": lead_email,
            "billing_address": customer_payload.get("billing_address") or None,
            "shipping_address": customer_payload.get("shipping_address") or None,
            "credit_limit": float(customer_payload.get("credit_limit") or 0.0),
            "payment_terms_days": int(customer_payload.get("payment_terms_days") or 30),
            "unit_id": customer_payload.get("unit_id") or lead.get("unit_id", "BOTH"),
            "is_active": True,
        }

        # MasterRepository.create_record raises ValueError if code exists
        created_customer_id = await self.customers_repo.create_record(cust_doc, user_email=user_email)

        now = datetime.now(timezone.utc)
        # Update lead status to CONVERTED
        await self.collection.update_one(
            {"_id": ObjectId(lead_id)},
            {
                "$set": {
                    "status": "CONVERTED",
                    "converted_customer_id": created_customer_id,
                    "converted_at": now,
                    "updated_at": now,
                    "updated_by": user_email,
                }
            }
        )

        # Log conversion activity
        await self.add_activity(
            lead_id=lead_id,
            activity_type="STATUS_CHANGE",
            summary=f"Converted to Customer ({customer_code})",
            details=f"Lead converted by {user_email}. Customer master created with ID {created_customer_id}.",
            user_email=user_email,
        )

        created_customer = await self.customers_repo.get_by_id(created_customer_id)
        return {
            "customer_id": created_customer_id,
            "customer_code": customer_code,
            "customer": created_customer,
        }

    async def get_dashboard_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregate CRM metrics: total, active, hot, converted, pipeline breakdown, and follow-ups.
        """
        base_filter: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            base_filter["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]

        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)

        total_leads = await self.collection.count_documents(base_filter)
        active_leads = await self.collection.count_documents({
            **base_filter,
            "status": {"$nin": ["CONVERTED", "LOST"]},
        })
        hot_leads = await self.collection.count_documents({
            **base_filter,
            "priority": "HOT",
            "status": {"$nin": ["CONVERTED", "LOST"]},
        })
        converted_leads = await self.collection.count_documents({
            **base_filter,
            "status": "CONVERTED",
        })

        conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

        # Follow-ups counts
        follow_ups_due_today = await self.collection.count_documents({
            **base_filter,
            "status": {"$nin": ["CONVERTED", "LOST"]},
            "next_follow_up": {"$gte": start_of_day, "$lte": end_of_day},
        })
        follow_ups_overdue = await self.collection.count_documents({
            **base_filter,
            "status": {"$nin": ["CONVERTED", "LOST"]},
            "next_follow_up": {"$lt": now, "$ne": None},
        })

        # Pipeline by status
        pipeline_cursor = self.collection.aggregate([
            {"$match": base_filter},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ])
        pipeline_by_status = {
            item["_id"]: item["count"] for item in await pipeline_cursor.to_list(length=20)
        }

        return {
            "total_leads": total_leads,
            "active_leads": active_leads,
            "hot_leads": hot_leads,
            "converted_leads": converted_leads,
            "conversion_rate_percentage": conv_rate,
            "pipeline_by_status": pipeline_by_status,
            "follow_ups_due_today": follow_ups_due_today,
            "follow_ups_overdue": follow_ups_overdue,
        }

    # -------------------------------------------------------------
    # Lead-As-A-Project End-to-End Tracking Hub
    # -------------------------------------------------------------
    async def get_lead_project_summary(self, lead_id: str) -> Dict[str, Any]:
        """
        Aggregate complete end-to-end Project lifecycle records for a Lead:
        - Material Requirements & Estimates
        - Supplier Bills (AP) & Material Purchases
        - Quotations & Sales Invoices (AR)
        - Site / Operational Expenses
        - Receipts & Disbursements (Payments)
        - Financial Costing & Profitability Overview
        """
        lead = await self.get_by_id(lead_id)
        if not lead:
            raise ValueError("Lead / Project not found.")

        lead_code = lead.get("code", "")
        customer_id = lead.get("converted_customer_id")

        # 1. Material Requirements
        mat_cursor = self.db["crm_lead_materials"].find({
            "$or": [{"lead_id": lead_id}, {"lead_code": lead_code}]
        }).sort("created_at", -1)
        materials = await mat_cursor.to_list(length=100)
        for m in materials:
            m["id"] = str(m["_id"])

        # 2. Supplier Bills (AP) / Material Bills
        bill_filter: Dict[str, Any] = {
            "$or": [
                {"project_id": lead_id},
                {"project_code": lead_code},
                {"po_reference": lead_code},
            ]
        }
        bills_cursor = self.db["supplier_bills"].find(bill_filter).sort("bill_date", -1)
        supplier_bills = await bills_cursor.to_list(length=100)
        for b in supplier_bills:
            b["id"] = str(b["_id"])

        # 3. Customer Invoices (AR) & Sales Orders
        inv_filter: Dict[str, Any] = {
            "$or": [
                {"project_id": lead_id},
                {"project_code": lead_code},
                {"sales_order_number": lead_code},
            ]
        }
        if customer_id:
            inv_filter["$or"].append({"customer_id": customer_id})

        inv_cursor = self.db["invoices"].find(inv_filter).sort("invoice_date", -1)
        invoices = await inv_cursor.to_list(length=100)
        for inv in invoices:
            inv["id"] = str(inv["_id"])

        # Also get linked Sales Orders / Quotations if any
        so_filter: Dict[str, Any] = {
            "$or": [
                {"lead_id": lead_id},
                {"project_code": lead_code},
                {"customer_order_reference": lead_code},
            ]
        }
        if customer_id:
            so_filter["$or"].append({"customer_id": customer_id})

        so_cursor = self.db["sales_orders"].find(so_filter).sort("order_date", -1)
        sales_orders = await so_cursor.to_list(length=50)
        for so in sales_orders:
            so["id"] = str(so["_id"])

        # 4. Project Expenses
        exp_filter: Dict[str, Any] = {
            "$or": [
                {"project_id": lead_id},
                {"project_code": lead_code},
                {"reference_number": lead_code},
            ]
        }
        exp_cursor = self.db["expenses"].find(exp_filter).sort("expense_date", -1)
        expenses = await exp_cursor.to_list(length=100)
        for exp in expenses:
            exp["id"] = str(exp["_id"])

        # 5. Payments & Disbursements
        pay_filter: Dict[str, Any] = {
            "$or": [
                {"project_id": lead_id},
                {"project_code": lead_code},
            ]
        }
        # Include payments for any of the project's invoices or bills
        inv_ids = [str(inv["_id"]) for inv in invoices]
        bill_ids = [str(b["_id"]) for b in supplier_bills]
        if inv_ids or bill_ids:
            pay_filter["$or"].append({"reference_doc_id": {"$in": inv_ids + bill_ids}})

        pay_cursor = self.db["payments"].find(pay_filter).sort("payment_date", -1)
        payments = await pay_cursor.to_list(length=100)
        for p in payments:
            p["id"] = str(p["_id"])

        # Financial aggregation
        budget_value = float(lead.get("estimated_value", 0.0))
        total_invoiced_ar = round(sum(float(inv.get("total_amount", 0.0)) for inv in invoices), 2)
        total_collected = round(
            sum(float(p.get("amount", 0.0)) for p in payments if p.get("payment_type") == "CUSTOMER_RECEIPT"), 2
        )
        receivables_balance = max(0.0, round(total_invoiced_ar - total_collected, 2))

        total_material_bills = round(sum(float(b.get("total_amount", 0.0)) for b in supplier_bills), 2)
        total_disbursed_suppliers = round(
            sum(float(p.get("amount", 0.0)) for p in payments if p.get("payment_type") == "VENDOR_PAYMENT"), 2
        )
        payables_balance = max(0.0, round(total_material_bills - total_disbursed_suppliers, 2))

        total_expenses = round(sum(float(e.get("total_amount", e.get("amount", 0.0))) for e in expenses), 2)
        total_cost = round(total_material_bills + total_expenses, 2)

        # Base revenue for margin: invoices total if invoiced, otherwise estimated budget value
        effective_revenue = total_invoiced_ar if total_invoiced_ar > 0 else budget_value
        net_profit = round(effective_revenue - total_cost, 2)
        margin_pct = (
            round((net_profit / effective_revenue * 100), 1)
            if effective_revenue > 0
            else 0.0
        )

        return {
            "lead": {
                "id": str(lead["_id"]),
                "code": lead.get("code"),
                "company_name": lead.get("company_name"),
                "contact_person": lead.get("contact_person"),
                "phone": lead.get("phone"),
                "email": lead.get("email"),
                "status": lead.get("status"),
                "priority": lead.get("priority"),
                "estimated_value": budget_value,
                "machine_interest": lead.get("machine_interest"),
                "unit_id": lead.get("unit_id"),
                "assigned_to": lead.get("assigned_to"),
                "converted_customer_id": customer_id,
            },
            "financial_metrics": {
                "budget_value": budget_value,
                "total_invoiced_ar": total_invoiced_ar,
                "total_collected": total_collected,
                "receivables_balance": receivables_balance,
                "total_material_bills": total_material_bills,
                "total_disbursed_suppliers": total_disbursed_suppliers,
                "payables_balance": payables_balance,
                "total_expenses": total_expenses,
                "total_cost": total_cost,
                "net_profit": net_profit,
                "margin_pct": margin_pct,
            },
            "materials": materials,
            "supplier_bills": supplier_bills,
            "invoices": invoices,
            "sales_orders": sales_orders,
            "expenses": expenses,
            "payments": payments,
        }

    async def add_lead_material_requirement(
        self,
        lead_id: str,
        data: Dict[str, Any],
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Record a Bill of Material / Material Requirement directly against the Lead/Project.
        """
        lead = await self.get_by_id(lead_id)
        if not lead:
            raise ValueError("Lead / Project not found.")

        now = datetime.now(timezone.utc)
        qty = float(data.get("required_quantity", 1.0))
        rate = float(data.get("estimated_unit_cost", 0.0))
        total = round(qty * rate, 2)

        doc = {
            "lead_id": lead_id,
            "lead_code": lead.get("code", ""),
            "item_code": data.get("item_code", "").strip().upper(),
            "description": data.get("description", "").strip(),
            "required_quantity": qty,
            "uom": data.get("uom", "NOS").strip().upper(),
            "estimated_unit_cost": rate,
            "total_estimated_cost": total,
            "required_date": data.get("required_date"),
            "status": data.get("status", "PENDING"),
            "notes": data.get("notes"),
            "created_at": now,
            "created_by": user_email,
        }
        res = await self.db["crm_lead_materials"].insert_one(doc)
        doc["_id"] = res.inserted_id
        doc["id"] = str(res.inserted_id)

        # Also log activity on the project
        await self.add_activity(
            lead_id=lead_id,
            activity_type="NOTE",
            summary=f"Material Requirement added: {doc['item_code']} (Qty: {qty} {doc['uom']})",
            details=f"Est. cost ₹{total} for {doc['description']}",
            user_email=user_email,
        )

        return doc
