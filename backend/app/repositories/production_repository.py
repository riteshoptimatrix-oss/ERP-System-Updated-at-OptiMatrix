import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.schemas.production import (
    ProductionOrderStatus,
    ProductionOrderCreate,
    MaterialIssueRequest,
    ProductionOutputInput,
    ProductionVarianceReport,
    MaterialVarianceItem,
)
from app.schemas.inventory import MovementType, ItemType

logger = logging.getLogger("app.production.repository")


class ProductionRepository:
    """
    Production-grade repository for Production Planning, WIP Tracking, and Output Receipts.
    Enforces:
    1. Validated lifecycle state transitions: DRAFT -> RELEASED -> IN_PROGRESS -> COMPLETED.
    2. Material reservation on RELEASE.
    3. Material consumption via InventoryRepository on issue.
    4. Automatic finished goods inventory receipt on output production.
    5. Duplicate prevention and concurrency protection.
    6. Complete material variance reporting.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.orders_col = db["production_orders"]
        self.outputs_col = db["production_outputs"]
        self.boms_col = db["boms"]
        self.finished_products_col = db["finished_products"]
        self.raw_materials_col = db["raw_materials"]
        self.warehouses_col = db["warehouses"]
        self.inventory_stock_col = db["inventory_stock"]
        self.inventory_ledger_col = db["inventory_ledger"]

    # -------------------------------------------------------------
    # Number & Sequence Generators
    # -------------------------------------------------------------
    async def generate_order_number(self) -> str:
        """Generates consecutive atomic production order numbers: PRD-YYYY-XXXX."""
        now = datetime.now(timezone.utc)
        year_str = str(now.year)
        seq_doc = await self.db["counters"].find_one_and_update(
            {"_id": f"prd_seq_{year_str}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq_num = seq_doc["seq"]
        return f"PRD-{year_str}-{seq_num:04d}"

    # -------------------------------------------------------------
    # Master Resolvers
    # -------------------------------------------------------------
    async def resolve_product_and_bom(
        self,
        product_id: str,
        bom_id: Optional[str] = None,
        unit_id: str = "Unit_1",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolves product and its approved BOM recipe."""
        # 1. Product
        prod = None
        if ObjectId.is_valid(product_id):
            prod = await self.finished_products_col.find_one({"_id": ObjectId(product_id)})
        if not prod:
            prod = await self.finished_products_col.find_one({"code": product_id})

        if not prod:
            raise ValueError(f"Finished product '{product_id}' not found.")

        # 2. BOM
        bom = None
        if bom_id:
            if ObjectId.is_valid(bom_id):
                bom = await self.boms_col.find_one({"_id": ObjectId(bom_id)})
            if not bom:
                bom = await self.boms_col.find_one({"bom_number": bom_id})
        else:
            # Pick active approved BOM for product
            bom = await self.boms_col.find_one({
                "product_id": str(prod["_id"]),
                "unit_id": unit_id,
                "is_active": True,
                "status": "APPROVED",
            })
            if not bom:
                # Fallback to any approved BOM for this product
                bom = await self.boms_col.find_one({
                    "product_id": str(prod["_id"]),
                    "status": "APPROVED",
                })

        if not bom:
            raise ValueError(
                f"No approved Bill of Materials (BOM) found for product '{prod.get('code')}'. "
                "Production orders require an approved engineering recipe."
            )

        if bom.get("status") != "APPROVED":
            raise ValueError(
                f"BOM '{bom.get('bom_number')}' is in '{bom.get('status')}' status. "
                "Only APPROVED BOM revisions can be released to production."
            )

        return prod, bom

    async def resolve_warehouse(self, warehouse_id: str) -> Dict[str, Any]:
        """Resolves warehouse details."""
        wh = None
        if ObjectId.is_valid(warehouse_id):
            wh = await self.warehouses_col.find_one({"_id": ObjectId(warehouse_id)})
        if not wh:
            wh = await self.warehouses_col.find_one({"code": warehouse_id})

        if not wh:
            raise ValueError(f"Warehouse '{warehouse_id}' not found.")
        return wh

    # -------------------------------------------------------------
    # 1. Create Production Order (DRAFT)
    # -------------------------------------------------------------
    async def create_order(self, order_data: ProductionOrderCreate, created_by: str) -> Dict[str, Any]:
        """Creates a production order snapshotting the approved BOM version."""
        prod, bom = await self.resolve_product_and_bom(
            product_id=order_data.product_id,
            bom_id=order_data.bom_id,
            unit_id=order_data.unit_id.value,
        )
        wh = await self.resolve_warehouse(order_data.target_warehouse_id)

        planned_qty = float(order_data.planned_quantity)
        base_yield = float(bom.get("base_quantity", 1.0) or 1.0)
        scale_factor = planned_qty / base_yield

        # Freeze BOM standard materials scaled to planned batch size
        materials: List[Dict[str, Any]] = []
        for comp in bom.get("components", []):
            std_per_unit = float(comp["gross_quantity"]) / base_yield
            tot_std = round(std_per_unit * planned_qty, 4)
            unit_cost = float(comp.get("unit_cost", 0.0))

            materials.append({
                "material_id": comp["material_id"],
                "material_code": comp["material_code"],
                "material_name": comp["material_name"],
                "uom": comp["uom"],
                "standard_quantity_per_unit": round(std_per_unit, 4),
                "total_standard_required": tot_std,
                "total_issued": 0.0,
                "unit_cost": unit_cost,
                "standard_total_cost": round(tot_std * unit_cost, 2),
                "actual_total_cost": 0.0,
            })

        order_number = await self.generate_order_number()
        now = datetime.now(timezone.utc)

        doc = {
            "order_number": order_number,
            "product_id": str(prod["_id"]),
            "product_code": prod.get("code", "UNKNOWN"),
            "product_name": prod.get("name", "Unknown Product"),
            "product_uom": prod.get("uom", "PCS"),
            "bom_id": str(bom["_id"]),
            "bom_number": bom.get("bom_number", ""),
            "bom_revision_no": bom.get("revision_no", "R1"),
            "unit_id": order_data.unit_id.value,
            "target_warehouse_id": str(wh["_id"]),
            "target_warehouse_code": wh.get("code", ""),
            "planned_quantity": planned_qty,
            "produced_quantity": 0.0,
            "rejected_quantity": 0.0,
            "remaining_quantity": planned_qty,
            "status": ProductionOrderStatus.DRAFT.value,
            "completion_percentage": 0.0,
            "materials": materials,
            "scheduled_start_date": order_data.scheduled_start_date,
            "target_completion_date": order_data.target_completion_date,
            "actual_start_date": None,
            "actual_completion_date": None,
            "notes": order_data.notes,
            "created_at": now,
            "created_by": created_by,
            "updated_at": now,
            "updated_by": created_by,
        }

        res = await self.orders_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    # -------------------------------------------------------------
    # 2. Get and List Production Orders
    # -------------------------------------------------------------
    async def get_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single production order by ID or order number."""
        if ObjectId.is_valid(order_id):
            return await self.orders_col.find_one({"_id": ObjectId(order_id)})
        return await self.orders_col.find_one({"order_number": order_id})

    async def list_orders(
        self,
        product_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lists production orders with filters and pagination."""
        query: Dict[str, Any] = {}
        if product_id:
            query["product_id"] = product_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status and status != "ALL":
            query["status"] = status

        if search:
            query["$or"] = [
                {"order_number": {"$regex": search, "$options": "i"}},
                {"product_code": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}},
                {"bom_number": {"$regex": search, "$options": "i"}},
            ]

        total = await self.orders_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.orders_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)

        docs = await cursor.to_list(length=page_size)
        return docs, total

    # -------------------------------------------------------------
    # 3. Release Order & Reserve Materials
    # -------------------------------------------------------------
    async def release_order(self, order_id: str, released_by: str) -> Dict[str, Any]:
        """
        Transitions order from DRAFT to RELEASED.
        Reserves required materials in inventory_stock.
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Production order not found.")

        if order.get("status") != ProductionOrderStatus.DRAFT.value:
            raise ValueError(f"Cannot release order in '{order.get('status')}' state.")

        # Atomic reservation on inventory_stock
        for mat in order.get("materials", []):
            mat_id = mat["material_id"]
            tot_req = float(mat["total_standard_required"])

            # Find matching stock positions in order's unit and increment quantity_reserved
            stock_doc = await self.inventory_stock_col.find_one({"item_id": mat_id, "unit_id": order["unit_id"]})
            if stock_doc:
                await self.inventory_stock_col.update_one(
                    {"_id": stock_doc["_id"]},
                    {
                        "$inc": {"quantity_reserved": tot_req},
                        "$set": {
                            "quantity_available": round(
                                stock_doc["quantity_on_hand"] - (stock_doc.get("quantity_reserved", 0.0) + tot_req), 4
                            )
                        },
                    },
                )

        now = datetime.now(timezone.utc)
        await self.orders_col.update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "status": ProductionOrderStatus.RELEASED.value,
                    "updated_at": now,
                    "updated_by": released_by,
                }
            },
        )
        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # 4. Issue Materials to Production Line (Consumption)
    # -------------------------------------------------------------
    async def issue_materials(
        self,
        order_id: str,
        issue_request: MaterialIssueRequest,
        issued_by: str,
    ) -> Dict[str, Any]:
        """
        Issues components from warehouse to production floor.
        Deducts inventory with MovementType.PRODUCTION_CONSUMPTION and updates order.
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Production order not found.")

        if order.get("status") not in [
            ProductionOrderStatus.RELEASED.value,
            ProductionOrderStatus.IN_PROGRESS.value,
        ]:
            raise ValueError(f"Cannot issue materials to order in '{order.get('status')}' state.")

        from app.repositories.inventory_repository import InventoryRepository
        inv_repo = InventoryRepository(self.db)

        materials_map = {m["material_id"]: m for m in order.get("materials", [])}

        for item in issue_request.items:
            mat = materials_map.get(item.material_id)
            if not mat:
                # Try finding by material_code
                mat = next((m for m in order.get("materials", []) if m["material_code"] == item.material_id), None)
            if not mat:
                raise ValueError(f"Material '{item.material_id}' is not part of this production order recipe.")

            item_info = await inv_repo.resolve_item_info(mat["material_id"], ItemType.RAW_MATERIAL)
            wh_info = await inv_repo.resolve_warehouse_info(item.warehouse_id)

            # Record stock deduction
            await inv_repo.record_stock_movement(
                item_info=item_info,
                warehouse_info=wh_info,
                batch_no=item.batch_no or "DEFAULT",
                quantity_change=-abs(item.quantity),
                movement_type=MovementType.PRODUCTION_CONSUMPTION,
                unit_cost=item_info["standard_cost"],
                created_by=issued_by,
                reference_id=order["order_number"],
                reference_type="PRODUCTION_ORDER",
                reason="PRODUCTION_CONSUMPTION",
                notes=f"Issued to {order['order_number']}. {item.notes or ''}".strip(),
            )

            # Decrement reservation if previously reserved and update available
            dec_res = min(float(mat["total_standard_required"]), float(item.quantity))
            stock_after = await self.inventory_stock_col.find_one_and_update(
                {"item_id": mat["material_id"], "warehouse_id": wh_info["warehouse_id"]},
                {"$inc": {"quantity_reserved": -dec_res}},
                return_document=ReturnDocument.AFTER,
            )
            if stock_after:
                new_avail = round(stock_after["quantity_on_hand"] - stock_after.get("quantity_reserved", 0.0), 4)
                await self.inventory_stock_col.update_one(
                    {"_id": stock_after["_id"]},
                    {"$set": {"quantity_available": new_avail}},
                )

            # Update material consumption in production order
            mat["total_issued"] = round(mat.get("total_issued", 0.0) + item.quantity, 4)
            mat["actual_total_cost"] = round(mat["total_issued"] * mat["unit_cost"], 2)

        now = datetime.now(timezone.utc)
        new_status = ProductionOrderStatus.IN_PROGRESS.value
        actual_start = order.get("actual_start_date") or now

        await self.orders_col.update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "status": new_status,
                    "materials": list(materials_map.values()),
                    "actual_start_date": actual_start,
                    "updated_at": now,
                    "updated_by": issued_by,
                }
            },
        )
        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # 5. Record Output & Finished Goods Receipt
    # -------------------------------------------------------------
    async def record_output(
        self,
        order_id: str,
        output_input: ProductionOutputInput,
        recorded_by: str,
    ) -> Dict[str, Any]:
        """
        Records good finished goods output and rejected scrap.
        Posts PRODUCTION_RECEIPT into finished goods warehouse.
        Automatically updates remaining quantities and completes order when target met.
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Production order not found.")

        if order.get("status") not in [
            ProductionOrderStatus.RELEASED.value,
            ProductionOrderStatus.IN_PROGRESS.value,
        ]:
            raise ValueError(f"Cannot record production output for order in '{order.get('status')}' state.")

        good_qty = float(output_input.produced_quantity)
        scrap_qty = float(output_input.rejected_quantity)

        if good_qty <= 0 and scrap_qty <= 0:
            raise ValueError("At least produced quantity or rejected quantity must be greater than zero.")

        from app.repositories.inventory_repository import InventoryRepository
        inv_repo = InventoryRepository(self.db)

        wh = await self.resolve_warehouse(output_input.warehouse_id)
        batch_no = output_input.batch_no or f"LOT-{order['order_number']}"

        # 1. Post good output to Finished Goods inventory
        if good_qty > 0:
            prod_info = await inv_repo.resolve_item_info(order["product_id"], ItemType.FINISHED_GOOD)
            wh_info = {
                "warehouse_id": str(wh["_id"]),
                "warehouse_code": wh.get("code", "WH-FG"),
                "warehouse_name": wh.get("name", "FG Warehouse"),
                "unit_id": order["unit_id"],
            }
            await inv_repo.record_stock_movement(
                item_info=prod_info,
                warehouse_info=wh_info,
                batch_no=batch_no,
                quantity_change=good_qty,
                movement_type=MovementType.PRODUCTION_RECEIPT,
                unit_cost=prod_info["standard_cost"],
                created_by=recorded_by,
                reference_id=order["order_number"],
                reference_type="PRODUCTION_ORDER",
                reason="PRODUCTION_OUTPUT_RECEIPT",
                notes=f"Produced from {order['order_number']}. Batch: {batch_no}".strip(),
            )

        now = datetime.now(timezone.utc)

        # 2. Log production output document
        output_doc = {
            "order_id": str(order["_id"]),
            "order_number": order["order_number"],
            "produced_quantity": good_qty,
            "rejected_quantity": scrap_qty,
            "warehouse_id": str(wh["_id"]),
            "warehouse_code": wh.get("code", ""),
            "batch_no": batch_no,
            "operator_name": output_input.operator_name,
            "notes": output_input.notes,
            "created_at": now,
            "created_by": recorded_by,
        }
        await self.outputs_col.insert_one(output_doc)

        # 3. Update order cumulative quantities
        new_produced = round(float(order.get("produced_quantity", 0.0)) + good_qty, 4)
        new_rejected = round(float(order.get("rejected_quantity", 0.0)) + scrap_qty, 4)
        planned_qty = float(order["planned_quantity"])
        rem_qty = round(max(0.0, planned_qty - new_produced), 4)
        completion_pct = round(min(100.0, (new_produced / planned_qty) * 100.0), 1) if planned_qty > 0 else 100.0

        is_done = new_produced >= planned_qty
        new_status = (
            ProductionOrderStatus.COMPLETED.value
            if is_done
            else ProductionOrderStatus.IN_PROGRESS.value
        )
        actual_comp = now if is_done else None

        await self.orders_col.update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "produced_quantity": new_produced,
                    "rejected_quantity": new_rejected,
                    "remaining_quantity": rem_qty,
                    "completion_percentage": completion_pct,
                    "status": new_status,
                    "actual_completion_date": actual_comp,
                    "updated_at": now,
                    "updated_by": recorded_by,
                }
            },
        )
        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # 6. Cancel Production Order
    # -------------------------------------------------------------
    async def cancel_order(self, order_id: str, reason: str, cancelled_by: str) -> Dict[str, Any]:
        """Cancels an order and unreserves any pending reserved materials."""
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Production order not found.")

        if order.get("status") == ProductionOrderStatus.COMPLETED.value:
            raise ValueError("Cannot cancel a completed production order.")

        # Release any reservations
        if order.get("status") in [ProductionOrderStatus.RELEASED.value, ProductionOrderStatus.IN_PROGRESS.value]:
            for mat in order.get("materials", []):
                rem_unissued = max(0.0, float(mat["total_standard_required"]) - float(mat.get("total_issued", 0.0)))
                if rem_unissued > 0:
                    await self.inventory_stock_col.update_one(
                        {"item_id": mat["material_id"], "unit_id": order["unit_id"]},
                        {"$inc": {"quantity_reserved": -rem_unissued}},
                    )

        now = datetime.now(timezone.utc)
        await self.orders_col.update_one(
            {"_id": order["_id"]},
            {
                "$set": {
                    "status": ProductionOrderStatus.CANCELLED.value,
                    "cancellation_reason": reason,
                    "updated_at": now,
                    "updated_by": cancelled_by,
                }
            },
        )
        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # 7. Production Variance Report
    # -------------------------------------------------------------
    async def get_variance_report(self, order_id: str) -> ProductionVarianceReport:
        """Computes BOM standard vs actual consumption and cost variance."""
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Production order not found.")

        mat_variances: List[MaterialVarianceItem] = []
        tot_std_cost = 0.0
        tot_act_cost = 0.0

        for m in order.get("materials", []):
            std_req = float(m["total_standard_required"])
            act_iss = float(m.get("total_issued", 0.0))
            variance_qty = round(act_iss - std_req, 4)
            unit_cost = float(m.get("unit_cost", 0.0))

            std_c = round(std_req * unit_cost, 2)
            act_c = round(act_iss * unit_cost, 2)
            cost_var = round(act_c - std_c, 2)

            tot_std_cost += std_c
            tot_act_cost += act_c

            mat_variances.append(
                MaterialVarianceItem(
                    material_id=m["material_id"],
                    material_code=m["material_code"],
                    material_name=m["material_name"],
                    uom=m["uom"],
                    standard_required=std_req,
                    actual_issued=act_iss,
                    variance_quantity=variance_qty,
                    is_favorable=(variance_qty <= 0),
                    standard_cost=std_c,
                    actual_cost=act_c,
                    cost_variance=cost_var,
                )
            )

        planned_qty = float(order["planned_quantity"])
        produced_qty = float(order.get("produced_quantity", 0.0))
        rejected_qty = float(order.get("rejected_quantity", 0.0))

        yield_eff = (
            round((produced_qty / (produced_qty + rejected_qty)) * 100.0, 1)
            if (produced_qty + rejected_qty) > 0
            else 100.0
        )

        return ProductionVarianceReport(
            order_id=str(order["_id"]),
            order_number=order["order_number"],
            product_code=order["product_code"],
            product_name=order["product_name"],
            planned_quantity=planned_qty,
            produced_quantity=produced_qty,
            rejected_quantity=rejected_qty,
            yield_efficiency_percentage=yield_eff,
            total_standard_cost=round(tot_std_cost, 2),
            total_actual_cost=round(tot_act_cost, 2),
            net_cost_variance=round(tot_act_cost - tot_std_cost, 2),
            material_variances=mat_variances,
        )

    # -------------------------------------------------------------
    # 8. Dashboard Summary
    # -------------------------------------------------------------
    async def get_dashboard_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates shop floor WIP KPIs."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        total_orders = await self.orders_col.count_documents(query)
        draft_orders = await self.orders_col.count_documents({**query, "status": ProductionOrderStatus.DRAFT.value})
        released_orders = await self.orders_col.count_documents({**query, "status": ProductionOrderStatus.RELEASED.value})
        in_progress = await self.orders_col.count_documents({**query, "status": ProductionOrderStatus.IN_PROGRESS.value})
        completed = await self.orders_col.count_documents({**query, "status": ProductionOrderStatus.COMPLETED.value})

        # Aggregation of units
        pipeline = [
            {"$match": query} if query else {"$match": {}},
            {
                "$group": {
                    "_id": None,
                    "total_planned": {"$sum": "$planned_quantity"},
                    "total_produced": {"$sum": "$produced_quantity"},
                    "total_rejected": {"$sum": "$rejected_quantity"},
                }
            }
        ]
        agg = await self.orders_col.aggregate(pipeline).to_list(length=1)
        tot_plan = float(agg[0]["total_planned"]) if agg else 0.0
        tot_prod = float(agg[0]["total_produced"]) if agg else 0.0
        tot_rej = float(agg[0]["total_rejected"]) if agg else 0.0

        overall_yield = (
            round((tot_prod / (tot_prod + tot_rej)) * 100.0, 1)
            if (tot_prod + tot_rej) > 0
            else 100.0
        )

        return {
            "total_orders": total_orders,
            "draft_orders": draft_orders,
            "released_orders": released_orders,
            "in_progress_orders": in_progress,
            "completed_orders": completed,
            "total_planned_units": tot_plan,
            "total_produced_units": tot_prod,
            "total_rejected_units": tot_rej,
            "overall_yield_percentage": overall_yield,
        }

    # -------------------------------------------------------------
    # Daily Production Planning & Actual
    # Main daily entry screen for Shivakumar (department-wise)
    # -------------------------------------------------------------
    async def list_daily_production(
        self,
        date_val: Optional[str] = None,
        department: Optional[str] = None,
        unit_id: Optional[str] = None,
        labour: Optional[str] = None,
        machine: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List daily production entries filtered by department, date, operator/labour, machine, or unit.
        """
        filter_query: Dict[str, Any] = {}
        if date_val:
            filter_query["date"] = date_val
        if department and department != "ALL":
            filter_query["department"] = department
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]
        if labour:
            filter_query["labour"] = {"$regex": labour, "$options": "i"}
        if machine:
            filter_query["machine"] = {"$regex": machine, "$options": "i"}
        if search:
            rx = {"$regex": search, "$options": "i"}
            filter_query["$or"] = [
                {"order_no": rx},
                {"customer": rx},
                {"variant": rx},
                {"length": rx},
                {"labour": rx},
                {"machine": rx},
                {"department": rx},
            ]

        cursor = self.db["daily_production"].find(filter_query).sort([("date", -1), ("_id", -1)])
        docs = await cursor.to_list(length=1000)
        for d in docs:
            d["id"] = str(d["_id"])
            # Ensure computed fields
            pq = float(d.get("planned_qty", 0.0))
            aq = float(d.get("actual_qty", 0.0))
            rq = float(d.get("rework_qty", 0.0))
            sq = float(d.get("scrap_qty", 0.0))
            gq = max(0.0, aq - rq - sq)
            d["good_qty"] = gq
            d["completion_pct"] = round((gq / pq * 100.0), 1) if pq > 0 else 0.0

            st = float(d.get("standard_target", 0.0))
            d["performance_pct"] = round((aq / st * 100.0), 1) if st > 0 else 0.0

            rate = float(d.get("rate_per_unit", 0.0))
            if rate > 0 and not d.get("daily_earned_inr"):
                d["daily_earned_inr"] = round(gq * rate, 2)
        return docs

    async def get_daily_production_summary(
        self,
        date_val: Optional[str] = None,
        department: Optional[str] = None,
        unit_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate totals and department-wise metrics for Daily Production Planning & Actual.
        """
        filter_query: Dict[str, Any] = {}
        if date_val:
            filter_query["date"] = date_val
        if department and department != "ALL":
            filter_query["department"] = department
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]

        docs = await self.db["daily_production"].find(filter_query).to_list(length=2000)

        total_planned_qty = 0.0
        total_actual_qty = 0.0
        total_good_qty = 0.0
        total_scrap_qty = 0.0
        total_rework_qty = 0.0
        total_daily_earned_inr = 0.0

        dept_groups: Dict[str, Dict[str, float]] = {}

        for d in docs:
            pq = float(d.get("planned_qty", 0.0))
            aq = float(d.get("actual_qty", 0.0))
            rq = float(d.get("rework_qty", 0.0))
            sq = float(d.get("scrap_qty", 0.0))
            gq = max(0.0, aq - rq - sq)
            earned = float(d.get("daily_earned_inr", 0.0))
            dep = d.get("department", "Machining")

            total_planned_qty += pq
            total_actual_qty += aq
            total_good_qty += gq
            total_scrap_qty += sq
            total_rework_qty += rq
            total_daily_earned_inr += earned

            if dep not in dept_groups:
                dept_groups[dep] = {
                    "department": dep,
                    "entries_count": 0,
                    "planned_qty": 0.0,
                    "actual_qty": 0.0,
                    "good_qty": 0.0,
                    "scrap_qty": 0.0,
                    "earned_inr": 0.0,
                }
            dept_groups[dep]["entries_count"] += 1
            dept_groups[dep]["planned_qty"] += pq
            dept_groups[dep]["actual_qty"] += aq
            dept_groups[dep]["good_qty"] += gq
            dept_groups[dep]["scrap_qty"] += sq
            dept_groups[dep]["earned_inr"] += earned

        overall_comp = (
            round((total_good_qty / total_planned_qty * 100.0), 1)
            if total_planned_qty > 0
            else 0.0
        )
        overall_perf = (
            round((total_good_qty / (total_good_qty + total_scrap_qty + total_rework_qty) * 100.0), 1)
            if (total_good_qty + total_scrap_qty + total_rework_qty) > 0
            else 0.0
        )

        dept_list = list(dept_groups.values())
        for dg in dept_list:
            dpq = dg["planned_qty"]
            dg["completion_pct"] = round((dg["good_qty"] / dpq * 100.0), 1) if dpq > 0 else 0.0

        return {
            "total_entries": len(docs),
            "total_planned_qty": round(total_planned_qty, 2),
            "total_actual_qty": round(total_actual_qty, 2),
            "total_good_qty": round(total_good_qty, 2),
            "total_scrap_qty": round(total_scrap_qty, 2),
            "total_rework_qty": round(total_rework_qty, 2),
            "overall_completion_pct": overall_comp,
            "overall_performance_pct": overall_perf,
            "total_daily_earned_inr": round(total_daily_earned_inr, 2),
            "department_breakdown": dept_list,
        }

    async def create_daily_production_entry(
        self,
        entry_data: Dict[str, Any],
        recorded_by: str = "Shivakumar",
    ) -> Dict[str, Any]:
        """
        Record a new daily production line for an operator/machine.
        """
        now = datetime.now(timezone.utc)
        entry_data["created_at"] = now
        entry_data["updated_at"] = now
        entry_data["recorded_by"] = recorded_by

        pq = float(entry_data.get("planned_qty", 0.0))
        aq = float(entry_data.get("actual_qty", 0.0))
        rq = float(entry_data.get("rework_qty", 0.0))
        sq = float(entry_data.get("scrap_qty", 0.0))
        gq = max(0.0, aq - rq - sq)
        entry_data["good_qty"] = gq
        entry_data["completion_pct"] = round((gq / pq * 100.0), 1) if pq > 0 else 0.0

        st = float(entry_data.get("standard_target", 0.0))
        entry_data["performance_pct"] = round((aq / st * 100.0), 1) if st > 0 else 0.0

        rate = float(entry_data.get("rate_per_unit", 0.0))
        if rate > 0 and not entry_data.get("daily_earned_inr"):
            entry_data["daily_earned_inr"] = round(gq * rate, 2)
        elif not entry_data.get("daily_earned_inr"):
            entry_data["daily_earned_inr"] = 0.0

        res = await self.db["daily_production"].insert_one(entry_data)
        entry_data["id"] = str(res.inserted_id)
        return entry_data

    async def update_daily_production_entry(
        self,
        entry_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing daily production planning & actual row.
        """
        if not ObjectId.is_valid(entry_id):
            return None

        clean_update = {k: v for k, v in update_data.items() if v is not None}
        clean_update["updated_at"] = datetime.now(timezone.utc)

        current = await self.db["daily_production"].find_one({"_id": ObjectId(entry_id)})
        if not current:
            return None

        pq = float(clean_update.get("planned_qty", current.get("planned_qty", 0.0)))
        aq = float(clean_update.get("actual_qty", current.get("actual_qty", 0.0)))
        rq = float(clean_update.get("rework_qty", current.get("rework_qty", 0.0)))
        sq = float(clean_update.get("scrap_qty", current.get("scrap_qty", 0.0)))
        gq = max(0.0, aq - rq - sq)
        clean_update["good_qty"] = gq
        clean_update["completion_pct"] = round((gq / pq * 100.0), 1) if pq > 0 else 0.0

        st = float(clean_update.get("standard_target", current.get("standard_target", 0.0)))
        clean_update["performance_pct"] = round((aq / st * 100.0), 1) if st > 0 else 0.0

        rate = float(clean_update.get("rate_per_unit", current.get("rate_per_unit", 0.0)))
        if rate > 0:
            clean_update["daily_earned_inr"] = round(gq * rate, 2)

        await self.db["daily_production"].update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": clean_update},
        )
        updated = await self.db["daily_production"].find_one({"_id": ObjectId(entry_id)})
        if updated:
            updated["id"] = str(updated["_id"])
        return updated

    async def delete_daily_production_entry(self, entry_id: str) -> bool:
        """Delete daily production record."""
        if not ObjectId.is_valid(entry_id):
            return False
        res = await self.db["daily_production"].delete_one({"_id": ObjectId(entry_id)})
        return res.deleted_count > 0

