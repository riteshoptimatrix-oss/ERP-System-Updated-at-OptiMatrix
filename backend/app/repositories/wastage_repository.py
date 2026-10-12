from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, date
from bson import ObjectId
import logging
from app.schemas.wastage import (
    ScrapEntryCreate,
    ScrapEntryUpdate,
    ScrapApprovalRequest,
    ScrapRejectionRequest,
    ScrapEntryStatus,
    ScrapDisposition,
    ScrapCategory,
)
from app.models.user import ManufacturingUnit

logger = logging.getLogger(__name__)


class WastageRepository:
    def __init__(self, db: Any):
        self.db = db
        self.scrap_col = db["scrap_entries"]
        self.orders_col = db["production_orders"]
        self.raw_col = db["raw_materials"]
        self.fin_col = db["finished_products"]
        self.boms_col = db["boms"]

    async def generate_entry_number(self) -> str:
        """Generate sequence-safe unique identifier e.g. SCRAP-202610-0001."""
        now = datetime.now(timezone.utc)
        ym_prefix = now.strftime("%Y%m")
        count = await self.scrap_col.count_documents({
            "entry_number": {"$regex": f"^SCRAP-{ym_prefix}-"}
        })
        return f"SCRAP-{ym_prefix}-{(count + 1):04d}"

    async def resolve_item_cost(self, item_id: str, item_type: str = "RAW_MATERIAL") -> Tuple[str, str, float, str]:
        """Look up item code, name, standard unit cost, and uom from master records."""
        query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(item_id) else {"code": item_id}
        doc = None
        if item_type == "FINISHED_GOOD":
            doc = await self.fin_col.find_one(query)
            if doc:
                return doc.get("code", ""), doc.get("name", ""), float(doc.get("selling_price", 0.0) or 0.0), doc.get("uom", "PCS")
        else:
            doc = await self.raw_col.find_one(query)
            if doc:
                return doc.get("code", ""), doc.get("name", ""), float(doc.get("standard_cost", 0.0) or 0.0), doc.get("uom", "KG")

        return "", "", 0.0, "PCS"

    async def create_scrap_entry(
        self,
        entry_data: ScrapEntryCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Record a daily scrap/wastage entry with unit and production order association,
        preventing duplicate submissions.
        """
        now = datetime.now(timezone.utc)
        entry_date_str = entry_data.entry_date or now.strftime("%Y-%m-%d")

        # Validate production order reference if provided
        po_doc = None
        if entry_data.production_order_id:
            po_id_query = (
                {"_id": ObjectId(entry_data.production_order_id)}
                if ObjectId.is_valid(entry_data.production_order_id)
                else {"order_number": entry_data.production_order_id}
            )
            po_doc = await self.orders_col.find_one(po_id_query)
            if not po_doc:
                raise ValueError(f"Referenced production order '{entry_data.production_order_id}' does not exist.")

            # Validate unit association
            if entry_data.unit_id.value not in ["BOTH", "ALL"] and po_doc.get("unit_id") != entry_data.unit_id.value:
                raise ValueError(
                    f"Production order {po_doc.get('order_number')} belongs to unit {po_doc.get('unit_id')}, "
                    f"not {entry_data.unit_id.value}."
                )

            # Check for duplicate submission for the same order, item, category, and date
            duplicate_existing = await self.scrap_col.find_one({
                "production_order_id": str(po_doc["_id"]),
                "item_code": entry_data.item_code,
                "scrap_category": entry_data.scrap_category.value,
                "entry_date": entry_date_str,
                "status": {"$in": [ScrapEntryStatus.DRAFT.value, ScrapEntryStatus.SUBMITTED.value, ScrapEntryStatus.APPROVED.value]},
            })
            if duplicate_existing:
                raise ValueError(
                    f"Duplicate scrap entry prevented: An entry for order {po_doc.get('order_number')}, "
                    f"item {entry_data.item_code}, and category {entry_data.scrap_category.value} "
                    f"already exists on {entry_date_str} (Entry: {duplicate_existing.get('entry_number')})."
                )

        # Lookup or verify standard material unit cost
        _, _, master_unit_cost, _ = await self.resolve_item_cost(entry_data.item_id, entry_data.item_type)
        unit_cost = master_unit_cost if master_unit_cost > 0 else 0.0
        total_cost = round(entry_data.quantity * unit_cost, 2)

        entry_number = await self.generate_entry_number()
        doc = {
            "entry_number": entry_number,
            "entry_date": entry_date_str,
            "unit_id": entry_data.unit_id.value,
            "production_order_id": str(po_doc["_id"]) if po_doc else None,
            "production_order_number": po_doc.get("order_number") if po_doc else entry_data.production_order_number,
            "item_id": entry_data.item_id,
            "item_code": entry_data.item_code,
            "item_name": entry_data.item_name,
            "item_type": entry_data.item_type,
            "scrap_category": entry_data.scrap_category.value,
            "quantity": float(entry_data.quantity),
            "uom": entry_data.uom,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "reason": entry_data.reason,
            "disposition": entry_data.disposition.value,
            "status": ScrapEntryStatus.SUBMITTED.value,
            "operator_name": entry_data.operator_name,
            "machine_id": entry_data.machine_id,
            "notes": entry_data.notes,
            "created_at": now,
            "created_by": created_by,
            "updated_at": None,
            "updated_by": None,
            "approved_at": None,
            "approved_by": None,
            "rejection_reason": None,
        }

        res = await self.scrap_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get_scrap_entry_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single scrap entry by ObjectId or entry_number."""
        if ObjectId.is_valid(entry_id):
            return await self.scrap_col.find_one({"_id": ObjectId(entry_id)})
        return await self.scrap_col.find_one({"entry_number": entry_id})

    async def list_scrap_entries(
        self,
        unit_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        scrap_category: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Paginated search for scrap and wastage records."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if production_order_id:
            query["$or"] = [
                {"production_order_id": production_order_id},
                {"production_order_number": production_order_id},
            ]
        if scrap_category:
            query["scrap_category"] = scrap_category
        if status:
            query["status"] = status
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["entry_date"] = date_filter
        if search:
            query["$or"] = [
                {"entry_number": {"$regex": search, "$options": "i"}},
                {"item_code": {"$regex": search, "$options": "i"}},
                {"item_name": {"$regex": search, "$options": "i"}},
                {"reason": {"$regex": search, "$options": "i"}},
                {"production_order_number": {"$regex": search, "$options": "i"}},
            ]

        total = await self.scrap_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.scrap_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    async def update_scrap_entry(
        self,
        entry_id: str,
        update_data: ScrapEntryUpdate,
        updated_by: str,
    ) -> Dict[str, Any]:
        """Update/correct scrap entry (only when DRAFT or SUBMITTED)."""
        doc = await self.get_scrap_entry_by_id(entry_id)
        if not doc:
            raise ValueError("Scrap entry not found.")

        if doc.get("status") not in [ScrapEntryStatus.DRAFT.value, ScrapEntryStatus.SUBMITTED.value]:
            raise ValueError(f"Cannot edit scrap entry in '{doc.get('status')}' status.")

        update_fields: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc),
            "updated_by": updated_by,
        }

        if update_data.scrap_category is not None:
            update_fields["scrap_category"] = update_data.scrap_category.value
        if update_data.reason is not None:
            update_fields["reason"] = update_data.reason
        if update_data.disposition is not None:
            update_fields["disposition"] = update_data.disposition.value
        if update_data.operator_name is not None:
            update_fields["operator_name"] = update_data.operator_name
        if update_data.machine_id is not None:
            update_fields["machine_id"] = update_data.machine_id
        if update_data.notes is not None:
            update_fields["notes"] = update_data.notes

        if update_data.quantity is not None:
            new_qty = float(update_data.quantity)
            unit_cost = doc.get("unit_cost", 0.0)
            update_fields["quantity"] = new_qty
            update_fields["total_cost"] = round(new_qty * unit_cost, 2)

        await self.scrap_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_fields}
        )
        return await self.scrap_col.find_one({"_id": doc["_id"]})

    async def approve_scrap_entry(
        self,
        entry_id: str,
        approval_data: ScrapApprovalRequest,
        approved_by: str,
    ) -> Dict[str, Any]:
        """Authorize scrap entry and apply disposition."""
        doc = await self.get_scrap_entry_by_id(entry_id)
        if not doc:
            raise ValueError("Scrap entry not found.")

        if doc.get("status") == ScrapEntryStatus.APPROVED.value:
            return doc

        update_fields: Dict[str, Any] = {
            "status": ScrapEntryStatus.APPROVED.value,
            "approved_at": datetime.now(timezone.utc),
            "approved_by": approved_by,
        }
        if approval_data.disposition is not None:
            update_fields["disposition"] = approval_data.disposition.value
        if approval_data.notes:
            update_fields["approval_notes"] = approval_data.notes

        await self.scrap_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_fields}
        )
        return await self.scrap_col.find_one({"_id": doc["_id"]})

    async def reject_scrap_entry(
        self,
        entry_id: str,
        rejection_data: ScrapRejectionRequest,
        rejected_by: str,
    ) -> Dict[str, Any]:
        """Reject scrap entry with justification."""
        doc = await self.get_scrap_entry_by_id(entry_id)
        if not doc:
            raise ValueError("Scrap entry not found.")

        update_fields: Dict[str, Any] = {
            "status": ScrapEntryStatus.REJECTED.value,
            "rejection_reason": rejection_data.rejection_reason,
            "approved_at": datetime.now(timezone.utc),
            "approved_by": rejected_by,
        }

        await self.scrap_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_fields}
        )
        return await self.scrap_col.find_one({"_id": doc["_id"]})

    async def get_planned_vs_actual_wastage(self, production_order_id: str) -> Dict[str, Any]:
        """
        Reconcile planned wastage (derived from approved BOM scrap % and production order volume)
        against actual approved shop-floor scrap records.
        """
        po_query = (
            {"_id": ObjectId(production_order_id)}
            if ObjectId.is_valid(production_order_id)
            else {"order_number": production_order_id}
        )
        po_doc = await self.orders_col.find_one(po_query)
        if not po_doc:
            raise ValueError(f"Production order '{production_order_id}' not found.")

        order_id_str = str(po_doc["_id"])
        planned_prod_qty = float(po_doc.get("planned_quantity", 1.0))
        actual_produced_qty = float(po_doc.get("produced_quantity", 0.0))

        # Retrieve referenced BOM to get component-level scrap allowances
        bom_id = po_doc.get("bom_id")
        bom_doc = None
        if bom_id:
            bom_query = {"_id": ObjectId(bom_id)} if ObjectId.is_valid(bom_id) else {"bom_number": bom_id}
            bom_doc = await self.boms_col.find_one(bom_query)

        bom_components_map = {}
        if bom_doc and "components" in bom_doc:
            for comp in bom_doc["components"]:
                bom_components_map[comp.get("material_id")] = comp

        # Fetch all approved scrap entries for this order
        scrap_cursor = self.scrap_col.find({
            "production_order_id": order_id_str,
            "status": ScrapEntryStatus.APPROVED.value,
        })
        scrap_entries = await scrap_cursor.to_list(length=500)

        # Aggregate actual scrap by item_code / item_id
        actual_scrap_map: Dict[str, float] = {}
        for entry in scrap_entries:
            key = entry.get("item_code") or entry.get("item_id")
            actual_scrap_map[key] = actual_scrap_map.get(key, 0.0) + float(entry.get("quantity", 0.0))

        # Calculate planned vs actual per component in production order
        components_report = []
        total_planned_scrap_cost = 0.0
        total_actual_scrap_cost = 0.0

        materials_list = po_doc.get("materials", [])
        for mat in materials_list:
            mat_id = mat.get("material_id")
            mat_code = mat.get("material_code")
            total_req = float(mat.get("total_standard_required", 0.0))
            unit_cost = float(mat.get("unit_cost", 0.0))

            # Retrieve scrap percentage from BOM
            bom_comp = bom_components_map.get(mat_id)
            scrap_pct = float(bom_comp.get("scrap_percentage", 0.0)) if bom_comp else 0.0

            # Planned scrap quantity = total standard required * (scrap_pct / 100)
            planned_scrap_qty = round(total_req * (scrap_pct / 100.0), 2)
            actual_scrap_qty = round(actual_scrap_map.get(mat_code, actual_scrap_map.get(mat_id, 0.0)), 2)
            scrap_var = round(actual_scrap_qty - planned_scrap_qty, 2)

            planned_scrap_cost = round(planned_scrap_qty * unit_cost, 2)
            actual_scrap_cost = round(actual_scrap_qty * unit_cost, 2)
            cost_var = round(actual_scrap_cost - planned_scrap_cost, 2)

            total_planned_scrap_cost += planned_scrap_cost
            total_actual_scrap_cost += actual_scrap_cost

            components_report.append({
                "material_id": mat_id,
                "material_code": mat_code,
                "material_name": mat.get("material_name", ""),
                "uom": mat.get("uom", "KG"),
                "planned_quantity": total_req,
                "planned_scrap_percentage": scrap_pct,
                "planned_scrap_quantity": planned_scrap_qty,
                "actual_scrap_quantity": actual_scrap_qty,
                "scrap_variance": scrap_var,
                "unit_cost": unit_cost,
                "planned_scrap_cost": planned_scrap_cost,
                "actual_scrap_cost": actual_scrap_cost,
                "cost_variance": cost_var,
            })

        return {
            "production_order_id": order_id_str,
            "order_number": po_doc.get("order_number", ""),
            "product_code": po_doc.get("product_code", ""),
            "product_name": po_doc.get("product_name", ""),
            "unit_id": po_doc.get("unit_id", "Unit_1"),
            "planned_production_qty": planned_prod_qty,
            "actual_produced_qty": actual_produced_qty,
            "components": components_report,
            "total_planned_scrap_cost": round(total_planned_scrap_cost, 2),
            "total_actual_scrap_cost": round(total_actual_scrap_cost, 2),
            "total_cost_variance": round(total_actual_scrap_cost - total_planned_scrap_cost, 2),
        }

    async def get_wastage_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate high-level wastage dashboard metrics and category breakdown."""
        match_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            match_query["unit_id"] = unit_id

        total_entries = await self.scrap_col.count_documents(match_query)
        pending_count = await self.scrap_col.count_documents({
            **match_query,
            "status": ScrapEntryStatus.SUBMITTED.value,
        })
        approved_count = await self.scrap_col.count_documents({
            **match_query,
            "status": ScrapEntryStatus.APPROVED.value,
        })

        # Category pipeline
        pipeline = [
            {"$match": {**match_query, "status": ScrapEntryStatus.APPROVED.value}},
            {
                "$group": {
                    "_id": "$scrap_category",
                    "total_quantity": {"$sum": "$quantity"},
                    "total_cost": {"$sum": "$total_cost"},
                    "entry_count": {"$sum": 1},
                }
            },
            {"$sort": {"total_cost": -1}},
        ]
        cat_results = await self.scrap_col.aggregate(pipeline).to_list(length=50)
        breakdown = [
            {
                "category": r["_id"],
                "total_quantity": round(float(r["total_quantity"]), 2),
                "total_cost": round(float(r["total_cost"]), 2),
                "entry_count": int(r["entry_count"]),
            }
            for r in cat_results
        ]
        total_scrap_cost = round(sum(b["total_cost"] for b in breakdown), 2)

        return {
            "total_scrap_entries": total_entries,
            "pending_approvals": pending_count,
            "approved_entries": approved_count,
            "total_scrap_cost": total_scrap_cost,
            "category_breakdown": breakdown,
            "unit_id": unit_id,
        }
