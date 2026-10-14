import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.schemas.inventory import (
    ItemType,
    MovementType,
    AdjustmentReason,
    MaterialInwardCreate,
    MaterialOutwardCreate,
    StockTransferCreate,
    StockAdjustmentCreate,
    OpeningStockImportRequest,
)

logger = logging.getLogger("app.inventory.repository")


class InventoryRepository:
    """
    Production-grade repository for Inventory & Warehouse Management.
    Enforces:
    1. Atomic balance maintenance on `inventory_stock` without negative quantities.
    2. Immutable ledger tracking on `inventory_ledger`.
    3. Reconciled inventory valuation and multi-warehouse stock visibility.
    4. Controlled transfers, adjustments, and inward/outward flows.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.stock_col = db["inventory_stock"]
        self.ledger_col = db["inventory_ledger"]
        self.raw_materials_col = db["raw_materials"]
        self.finished_products_col = db["finished_products"]
        self.warehouses_col = db["warehouses"]

    # -------------------------------------------------------------
    # Number & Sequence Generators
    # -------------------------------------------------------------
    async def generate_transaction_number(self, prefix: str = "TXN") -> str:
        """
        Generates consecutive atomic transaction numbers: TXN-YYYY-XXXX.
        """
        now = datetime.now(timezone.utc)
        year_str = str(now.year)
        seq_doc = await self.db["counters"].find_one_and_update(
            {"_id": f"inv_{prefix}_{year_str}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq_num = seq_doc["seq"]
        return f"{prefix}-{year_str}-{seq_num:04d}"

    # -------------------------------------------------------------
    # Master Item & Warehouse Resolvers
    # -------------------------------------------------------------
    async def resolve_item_info(self, item_id: str, item_type: Optional[ItemType] = None) -> Dict[str, Any]:
        """
        Resolves item metadata from raw_materials or finished_products master collections.
        """
        item_doc = None
        detected_type = item_type

        # 1. Try finding in raw_materials
        if not detected_type or detected_type == ItemType.RAW_MATERIAL:
            if ObjectId.is_valid(item_id):
                item_doc = await self.raw_materials_col.find_one({"_id": ObjectId(item_id)})
            if not item_doc:
                item_doc = await self.raw_materials_col.find_one({"code": item_id})
            if item_doc:
                detected_type = ItemType.RAW_MATERIAL

        # 2. Try finding in finished_products
        if not item_doc and (not detected_type or detected_type == ItemType.FINISHED_GOOD):
            if ObjectId.is_valid(item_id):
                item_doc = await self.finished_products_col.find_one({"_id": ObjectId(item_id)})
            if not item_doc:
                item_doc = await self.finished_products_col.find_one({"code": item_id})
            if item_doc:
                detected_type = ItemType.FINISHED_GOOD

        if not item_doc:
            raise ValueError(f"Item with identifier '{item_id}' not found in master records.")

        return {
            "item_id": str(item_doc["_id"]),
            "item_code": item_doc.get("code", "UNKNOWN"),
            "item_name": item_doc.get("name", "Unknown Item"),
            "item_type": detected_type.value if detected_type else ItemType.RAW_MATERIAL.value,
            "uom": item_doc.get("uom", "NOS"),
            "reorder_level": float(item_doc.get("reorder_level", 0.0) or 0.0),
            "safety_stock": float(item_doc.get("safety_stock", 0.0) or 0.0),
            "standard_cost": float(item_doc.get("standard_cost", item_doc.get("selling_price", 0.0)) or 0.0),
            "unit_id": item_doc.get("unit_id", "Unit_1"),
        }

    async def resolve_warehouse_info(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Resolves warehouse metadata from warehouses master collection.
        """
        wh_doc = None
        if ObjectId.is_valid(warehouse_id):
            wh_doc = await self.warehouses_col.find_one({"_id": ObjectId(warehouse_id)})
        if not wh_doc:
            wh_doc = await self.warehouses_col.find_one({"code": warehouse_id})

        if not wh_doc:
            raise ValueError(f"Warehouse with identifier '{warehouse_id}' not found in master records.")

        return {
            "warehouse_id": str(wh_doc["_id"]),
            "warehouse_code": wh_doc.get("code", "UNKNOWN"),
            "warehouse_name": wh_doc.get("name", "Unknown Warehouse"),
            "unit_id": wh_doc.get("unit_id", "Unit_1"),
        }

    # -------------------------------------------------------------
    # Atomic Ledger & Stock Mutation Primitives
    # -------------------------------------------------------------
    async def record_stock_movement(
        self,
        item_info: Dict[str, Any],
        warehouse_info: Dict[str, Any],
        batch_no: str,
        quantity_change: float,
        movement_type: MovementType,
        unit_cost: float,
        created_by: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atomically mutates `inventory_stock` and appends an immutable entry to `inventory_ledger`.
        Rejects transaction if decrement causes `quantity_on_hand` to drop below 0.
        """
        batch_no = (batch_no or "DEFAULT").strip().upper()
        now = datetime.now(timezone.utc)
        filter_query: Dict[str, Any] = {
            "item_id": item_info["item_id"],
            "warehouse_id": warehouse_info["warehouse_id"],
            "batch_no": batch_no,
        }

        # If reducing stock, atomic condition: quantity_on_hand must be >= abs(quantity_change)
        if quantity_change < 0:
            abs_qty = abs(quantity_change)
            filter_query["quantity_on_hand"] = {"$gte": abs_qty}

        stock_doc = await self.stock_col.find_one({
            "item_id": item_info["item_id"],
            "warehouse_id": warehouse_info["warehouse_id"],
            "batch_no": batch_no,
        })

        current_val_rate = stock_doc.get("valuation_rate", unit_cost) if stock_doc else unit_cost
        if current_val_rate == 0.0 and unit_cost > 0.0:
            current_val_rate = unit_cost
        elif unit_cost > 0.0 and quantity_change > 0:
            # Weighted moving average valuation update
            curr_qty = stock_doc.get("quantity_on_hand", 0.0) if stock_doc else 0.0
            if curr_qty + quantity_change > 0:
                current_val_rate = round(
                    ((curr_qty * current_val_rate) + (quantity_change * unit_cost)) / (curr_qty + quantity_change),
                    4,
                )

        update_ops: Dict[str, Any] = {
            "$inc": {
                "quantity_on_hand": quantity_change,
            },
            "$set": {
                "item_code": item_info["item_code"],
                "item_name": item_info["item_name"],
                "item_type": item_info["item_type"],
                "warehouse_code": warehouse_info["warehouse_code"],
                "warehouse_name": warehouse_info["warehouse_name"],
                "unit_id": warehouse_info["unit_id"],
                "uom": item_info["uom"],
                "valuation_rate": current_val_rate,
                "reorder_level": item_info["reorder_level"],
                "safety_stock": item_info["safety_stock"],
                "updated_at": now,
            },
            "$setOnInsert": {
                "quantity_reserved": 0.0,
                "created_at": now,
            },
        }

        updated_stock = await self.stock_col.find_one_and_update(
            filter_query,
            update_ops,
            upsert=(quantity_change > 0),
            return_document=ReturnDocument.AFTER,
        )

        if not updated_stock:
            curr_stock = await self.stock_col.find_one({
                "item_id": item_info["item_id"],
                "warehouse_id": warehouse_info["warehouse_id"],
                "batch_no": batch_no,
            })
            available = curr_stock.get("quantity_on_hand", 0.0) if curr_stock else 0.0
            raise ValueError(
                f"Negative stock prohibited: Attempted to deduct {abs(quantity_change)} {item_info['uom']} "
                f"of {item_info['item_code']} from {warehouse_info['warehouse_code']} (Batch: {batch_no}), "
                f"but only {available} on hand."
            )

        new_balance = round(updated_stock["quantity_on_hand"], 4)
        new_reserved = round(updated_stock.get("quantity_reserved", 0.0), 4)
        new_available = round(new_balance - new_reserved, 4)

        # Update available quantity
        await self.stock_col.update_one(
            {"_id": updated_stock["_id"]},
            {"$set": {"quantity_available": new_available}}
        )

        # Generate transaction number and create immutable ledger record
        txn_number = await self.generate_transaction_number(prefix="TXN")
        ledger_entry = {
            "transaction_number": txn_number,
            "movement_type": movement_type.value,
            "item_id": item_info["item_id"],
            "item_code": item_info["item_code"],
            "item_name": item_info["item_name"],
            "item_type": item_info["item_type"],
            "warehouse_id": warehouse_info["warehouse_id"],
            "warehouse_code": warehouse_info["warehouse_code"],
            "warehouse_name": warehouse_info["warehouse_name"],
            "unit_id": warehouse_info["unit_id"],
            "batch_no": batch_no,
            "quantity_change": round(quantity_change, 4),
            "balance_after": new_balance,
            "unit_cost": round(unit_cost, 4),
            "uom": item_info["uom"],
            "reference_id": reference_id,
            "reference_type": reference_type,
            "reason": reason,
            "notes": notes,
            "created_at": now,
            "created_by": created_by,
        }

        res = await self.ledger_col.insert_one(ledger_entry)
        ledger_entry["_id"] = res.inserted_id
        return ledger_entry

    # -------------------------------------------------------------
    # 1. Material Inward (GRN / Production Receipt)
    # -------------------------------------------------------------
    async def process_material_inward(
        self,
        inward_data: MaterialInwardCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Records receipt of materials or finished products into a specified warehouse.
        """
        item_info = await self.resolve_item_info(inward_data.item_id, inward_data.item_type)
        warehouse_info = await self.resolve_warehouse_info(inward_data.warehouse_id)

        unit_cost = inward_data.unit_cost if inward_data.unit_cost > 0 else item_info["standard_cost"]
        ref_id = inward_data.invoice_no or inward_data.po_number or inward_data.supplier_id
        ref_type = "PURCHASE_INVOICE" if inward_data.invoice_no else ("PO" if inward_data.po_number else "SUPPLIER")

        notes = inward_data.notes or (
            f"Inward receipt from supplier {inward_data.supplier_id or 'N/A'}, Invoice: {inward_data.invoice_no or 'N/A'}"
        )

        ledger_entry = await self.record_stock_movement(
            item_info=item_info,
            warehouse_info=warehouse_info,
            batch_no=inward_data.batch_no or "DEFAULT",
            quantity_change=inward_data.quantity,
            movement_type=MovementType.MATERIAL_INWARD,
            unit_cost=unit_cost,
            created_by=created_by,
            reference_id=ref_id,
            reference_type=ref_type,
            reason="MATERIAL_INWARD",
            notes=notes,
        )
        return ledger_entry

    # -------------------------------------------------------------
    # 2. Material Outward (Issue to Production / Shop Floor)
    # -------------------------------------------------------------
    async def process_material_outward(
        self,
        outward_data: MaterialOutwardCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Records issuance of raw materials or components to shop floor / machine line.
        """
        item_info = await self.resolve_item_info(outward_data.item_id)
        warehouse_info = await self.resolve_warehouse_info(outward_data.warehouse_id)

        ref_id = outward_data.destination or outward_data.department
        ref_type = "SHOP_FLOOR_DESTINATION"
        notes = outward_data.notes or f"Issued to {outward_data.destination or outward_data.department or 'Shop Floor'}"

        ledger_entry = await self.record_stock_movement(
            item_info=item_info,
            warehouse_info=warehouse_info,
            batch_no=outward_data.batch_no or "DEFAULT",
            quantity_change=-abs(outward_data.quantity),
            movement_type=MovementType.MATERIAL_OUTWARD,
            unit_cost=item_info["standard_cost"],
            created_by=created_by,
            reference_id=ref_id,
            reference_type=ref_type,
            reason="SHOP_FLOOR_ISSUE",
            notes=notes,
        )
        return ledger_entry

    # -------------------------------------------------------------
    # 3. Inter-Warehouse & Inter-Unit Stock Transfers
    # -------------------------------------------------------------
    async def process_stock_transfer(
        self,
        transfer_data: StockTransferCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Atomically transfers stock from source warehouse to target warehouse.
        Generates paired TRANSFER_OUT and TRANSFER_IN ledger entries.
        """
        if transfer_data.source_warehouse_id == transfer_data.target_warehouse_id:
            raise ValueError("Source warehouse and target warehouse cannot be the same.")

        item_info = await self.resolve_item_info(transfer_data.item_id)
        src_wh = await self.resolve_warehouse_info(transfer_data.source_warehouse_id)
        tgt_wh = await self.resolve_warehouse_info(transfer_data.target_warehouse_id)

        batch_no = transfer_data.batch_no or "DEFAULT"
        transfer_ref = await self.generate_transaction_number(prefix="TRF")

        # 1. Deduct from source warehouse
        outward_notes = (
            f"Transfer {transfer_ref} dispatched to {tgt_wh['warehouse_code']} "
            f"({tgt_wh['unit_id']}). Vehicle: {transfer_data.vehicle_number or 'N/A'}"
        )
        out_ledger = await self.record_stock_movement(
            item_info=item_info,
            warehouse_info=src_wh,
            batch_no=batch_no,
            quantity_change=-abs(transfer_data.quantity),
            movement_type=MovementType.TRANSFER_OUT,
            unit_cost=item_info["standard_cost"],
            created_by=created_by,
            reference_id=transfer_ref,
            reference_type="STOCK_TRANSFER",
            reason=transfer_data.transfer_reason or "INTER_FACILITY_TRANSFER",
            notes=outward_notes,
        )

        # 2. Add to target warehouse
        inward_notes = (
            f"Transfer {transfer_ref} received from {src_wh['warehouse_code']} "
            f"({src_wh['unit_id']}). Vehicle: {transfer_data.vehicle_number or 'N/A'}"
        )
        in_ledger = await self.record_stock_movement(
            item_info=item_info,
            warehouse_info=tgt_wh,
            batch_no=batch_no,
            quantity_change=abs(transfer_data.quantity),
            movement_type=MovementType.TRANSFER_IN,
            unit_cost=item_info["standard_cost"],
            created_by=created_by,
            reference_id=transfer_ref,
            reference_type="STOCK_TRANSFER",
            reason=transfer_data.transfer_reason or "INTER_FACILITY_TRANSFER",
            notes=inward_notes,
        )

        return {
            "transfer_number": transfer_ref,
            "item_id": item_info["item_id"],
            "item_code": item_info["item_code"],
            "quantity": transfer_data.quantity,
            "source_warehouse": src_wh["warehouse_code"],
            "target_warehouse": tgt_wh["warehouse_code"],
            "outward_ledger_id": str(out_ledger["_id"]),
            "inward_ledger_id": str(in_ledger["_id"]),
            "status": "COMPLETED",
        }

    # -------------------------------------------------------------
    # 4. Inventory Adjustments & Controlled Reconciliation
    # -------------------------------------------------------------
    async def process_stock_adjustment(
        self,
        adjustment_data: StockAdjustmentCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Records authorized stock adjustments with mandatory reason and justification notes.
        """
        if adjustment_data.quantity_delta == 0:
            raise ValueError("Adjustment quantity delta cannot be zero.")

        item_info = await self.resolve_item_info(adjustment_data.item_id)
        warehouse_info = await self.resolve_warehouse_info(adjustment_data.warehouse_id)

        movement_type = (
            MovementType.ADJUSTMENT_IN
            if adjustment_data.quantity_delta > 0
            else MovementType.ADJUSTMENT_OUT
        )

        adj_ref = await self.generate_transaction_number(prefix="ADJ")
        notes = f"Adjustment justification: {adjustment_data.notes}"

        ledger_entry = await self.record_stock_movement(
            item_info=item_info,
            warehouse_info=warehouse_info,
            batch_no=adjustment_data.batch_no or "DEFAULT",
            quantity_change=adjustment_data.quantity_delta,
            movement_type=movement_type,
            unit_cost=item_info["standard_cost"],
            created_by=created_by,
            reference_id=adj_ref,
            reference_type="STOCK_ADJUSTMENT",
            reason=adjustment_data.reason.value,
            notes=notes,
        )
        return ledger_entry

    # -------------------------------------------------------------
    # 5. Opening Stock Bulk Import
    # -------------------------------------------------------------
    async def import_opening_stock(
        self,
        import_request: OpeningStockImportRequest,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Imports opening stock entries with validation and duplicate prevention.
        """
        import_ref = await self.generate_transaction_number(prefix="OPN")
        processed_count = 0
        skipped_count = 0
        errors: List[str] = []

        for item in import_request.items:
            try:
                item_info = await self.resolve_item_info(item.item_code, item.item_type)
                wh_info = await self.resolve_warehouse_info(item.warehouse_code)
                batch_no = (item.batch_no or "DEFAULT").strip().upper()

                # Check if opening stock already exists for this exact item+warehouse+batch
                existing_opn = await self.ledger_col.find_one({
                    "item_id": item_info["item_id"],
                    "warehouse_id": wh_info["warehouse_id"],
                    "batch_no": batch_no,
                    "movement_type": MovementType.OPENING_STOCK.value,
                })
                if existing_opn:
                    skipped_count += 1
                    continue

                unit_cost = item.unit_cost if item.unit_cost > 0 else item_info["standard_cost"]
                await self.record_stock_movement(
                    item_info=item_info,
                    warehouse_info=wh_info,
                    batch_no=batch_no,
                    quantity_change=item.quantity,
                    movement_type=MovementType.OPENING_STOCK,
                    unit_cost=unit_cost,
                    created_by=created_by,
                    reference_id=import_ref,
                    reference_type="OPENING_IMPORT",
                    reason="OPENING_STOCK_IMPORT",
                    notes=import_request.notes or "Opening balance import",
                )
                processed_count += 1
            except Exception as e:
                errors.append(f"{item.item_code} @ {item.warehouse_code}: {str(e)}")

        return {
            "import_batch": import_ref,
            "total_requested": len(import_request.items),
            "processed_count": processed_count,
            "skipped_count": skipped_count,
            "errors_count": len(errors),
            "errors": errors,
        }

    # -------------------------------------------------------------
    # 6. Sales Dispatch Deduction Hook
    # -------------------------------------------------------------
    async def deduct_dispatch_stock(
        self,
        order_id: str,
        order_number: str,
        unit_id: str,
        items: List[Dict[str, Any]],
        dispatched_by: str,
        remarks: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deducts finished goods stock when a sales dispatch is finalized.
        Assigns deduction to the default finished goods warehouse for the unit.
        """
        # Find finished goods warehouse for this unit
        wh_doc = await self.warehouses_col.find_one({
            "unit_id": unit_id,
            "warehouse_type": "FINISHED_GOODS",
        })
        if not wh_doc:
            wh_doc = await self.warehouses_col.find_one({
                "unit_id": unit_id,
                "code": {"$regex": "FG", "$options": "i"},
            })
        if not wh_doc:
            wh_doc = await self.warehouses_col.find_one({"unit_id": unit_id})
        if not wh_doc:
            wh_doc = await self.warehouses_col.find_one({})

        if not wh_doc:
            logger.warning("No warehouse configured to deduct dispatch stock. Skipping inventory deduction.")
            return []

        wh_info = {
            "warehouse_id": str(wh_doc["_id"]),
            "warehouse_code": wh_doc.get("code", "WH-FG-MAIN"),
            "warehouse_name": wh_doc.get("name", "Finished Goods Warehouse"),
            "unit_id": wh_doc.get("unit_id", unit_id),
        }

        ledger_entries: List[Dict[str, Any]] = []
        for it in items:
            p_code = it.get("product_code") or it.get("product_id")
            p_qty = float(it.get("quantity", 0.0))
            if p_qty <= 0:
                continue

            item_info = await self.resolve_item_info(p_code, ItemType.FINISHED_GOOD)

            # Resolve matching batch with available stock in this warehouse
            stock_doc = await self.stock_col.find_one({
                "item_code": item_info["item_code"],
                "warehouse_code": wh_info["warehouse_code"],
                "current_quantity": {"$gte": p_qty},
            }) or await self.stock_col.find_one({
                "item_code": item_info["item_code"],
                "warehouse_code": wh_info["warehouse_code"],
                "current_quantity": {"$gt": 0},
            }) or await self.stock_col.find_one({
                "item_code": item_info["item_code"],
                "warehouse_code": wh_info["warehouse_code"],
            })
            batch_no = stock_doc.get("batch_no", "DEFAULT") if stock_doc else "DEFAULT"

            ledger_entry = await self.record_stock_movement(
                item_info=item_info,
                warehouse_info=wh_info,
                batch_no=batch_no,
                quantity_change=-abs(p_qty),
                movement_type=MovementType.SALES_DISPATCH,
                unit_cost=item_info["standard_cost"],
                created_by=dispatched_by,
                reference_id=order_number,
                reference_type="SALES_ORDER",
                reason="SALES_DISPATCH",
                notes=f"Sales dispatch for order {order_number}. {remarks or ''}".strip(),
            )
            ledger_entries.append(ledger_entry)

        return ledger_entries

    # -------------------------------------------------------------
    # 7. Queries, Balances, Ledger & Dashboard Aggregations
    # -------------------------------------------------------------
    async def list_stock_balances(
        self,
        item_type: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        search: Optional[str] = None,
        below_reorder_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists real-time stock balances across warehouses with filtering and pagination.
        """
        query: Dict[str, Any] = {}
        if item_type:
            query["item_type"] = item_type
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        if search:
            query["$or"] = [
                {"item_code": {"$regex": search, "$options": "i"}},
                {"item_name": {"$regex": search, "$options": "i"}},
                {"warehouse_code": {"$regex": search, "$options": "i"}},
                {"batch_no": {"$regex": search, "$options": "i"}},
            ]

        if below_reorder_only:
            query["$expr"] = {"$lte": ["$quantity_on_hand", "$reorder_level"]}

        total = await self.stock_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.stock_col.find(query).sort([("item_code", 1), ("warehouse_code", 1)]).skip(skip).limit(page_size)

        balances = await cursor.to_list(length=page_size)
        formatted: List[Dict[str, Any]] = []

        for b in balances:
            on_hand = float(b.get("quantity_on_hand", 0.0))
            reserved = float(b.get("quantity_reserved", 0.0))
            avail = float(b.get("quantity_available", on_hand - reserved))
            val_rate = float(b.get("valuation_rate", 0.0))
            reorder = float(b.get("reorder_level", 0.0))
            safety = float(b.get("safety_stock", 0.0))

            formatted.append({
                "id": str(b["_id"]),
                "item_id": b["item_id"],
                "item_code": b.get("item_code", ""),
                "item_name": b.get("item_name", ""),
                "item_type": b.get("item_type", ItemType.RAW_MATERIAL.value),
                "warehouse_id": b["warehouse_id"],
                "warehouse_code": b.get("warehouse_code", ""),
                "warehouse_name": b.get("warehouse_name", ""),
                "unit_id": b.get("unit_id", "Unit_1"),
                "batch_no": b.get("batch_no", "DEFAULT"),
                "quantity_on_hand": round(on_hand, 4),
                "quantity_reserved": round(reserved, 4),
                "quantity_available": round(avail, 4),
                "uom": b.get("uom", "NOS"),
                "valuation_rate": round(val_rate, 2),
                "total_valuation": round(on_hand * val_rate, 2),
                "reorder_level": round(reorder, 2),
                "safety_stock": round(safety, 2),
                "is_below_reorder": on_hand <= reorder if reorder > 0 else False,
                "updated_at": b.get("updated_at") or datetime.now(timezone.utc),
            })

        return formatted, total

    async def list_ledger_entries(
        self,
        item_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        movement_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists immutable stock movement ledger entries.
        """
        query: Dict[str, Any] = {}
        if item_id:
            query["item_id"] = item_id
        if warehouse_id:
            query["warehouse_id"] = warehouse_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if movement_type:
            query["movement_type"] = movement_type

        total = await self.ledger_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.ledger_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)

        entries = await cursor.to_list(length=page_size)
        formatted: List[Dict[str, Any]] = []

        for e in entries:
            formatted.append({
                "id": str(e["_id"]),
                "transaction_number": e.get("transaction_number", ""),
                "movement_type": e.get("movement_type", ""),
                "item_id": e.get("item_id", ""),
                "item_code": e.get("item_code", ""),
                "item_name": e.get("item_name", ""),
                "item_type": e.get("item_type", ItemType.RAW_MATERIAL.value),
                "warehouse_id": e.get("warehouse_id", ""),
                "warehouse_code": e.get("warehouse_code", ""),
                "warehouse_name": e.get("warehouse_name", ""),
                "unit_id": e.get("unit_id", "Unit_1"),
                "batch_no": e.get("batch_no", "DEFAULT"),
                "quantity_change": round(float(e.get("quantity_change", 0.0)), 4),
                "balance_after": round(float(e.get("balance_after", 0.0)), 4),
                "uom": e.get("uom", "NOS"),
                "reference_id": e.get("reference_id"),
                "reference_type": e.get("reference_type"),
                "reason": e.get("reason"),
                "notes": e.get("notes"),
                "created_at": e.get("created_at") or datetime.now(timezone.utc),
                "created_by": e.get("created_by", "SYSTEM"),
            })

        return formatted, total

    async def get_low_stock_alerts(self, unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns items whose aggregated available quantity is at or below the reorder level.
        """
        match_stage: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            match_stage["unit_id"] = unit_id

        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {
                "$group": {
                    "_id": {"item_id": "$item_id", "unit_id": "$unit_id"},
                    "item_code": {"$first": "$item_code"},
                    "item_name": {"$first": "$item_name"},
                    "item_type": {"$first": "$item_type"},
                    "uom": {"$first": "$uom"},
                    "reorder_level": {"$first": "$reorder_level"},
                    "safety_stock": {"$first": "$safety_stock"},
                    "total_on_hand": {"$sum": "$quantity_on_hand"},
                    "total_reserved": {"$sum": "$quantity_reserved"},
                    "total_available": {"$sum": "$quantity_available"},
                }
            },
            {
                "$project": {
                    "item_id": "$_id.item_id",
                    "unit_id": "$_id.unit_id",
                    "item_code": 1,
                    "item_name": 1,
                    "item_type": 1,
                    "uom": 1,
                    "reorder_level": 1,
                    "safety_stock": 1,
                    "total_on_hand": 1,
                    "total_reserved": 1,
                    "total_available": 1,
                    "shortage_quantity": {"$subtract": ["$reorder_level", "$total_available"]},
                }
            },
            {
                "$match": {
                    "reorder_level": {"$gt": 0},
                    "$expr": {"$lte": ["$total_available", "$reorder_level"]},
                }
            },
            {"$sort": {"shortage_quantity": -1}},
        ]

        cursor = self.stock_col.aggregate(pipeline)
        docs = await cursor.to_list(length=100)

        alerts: List[Dict[str, Any]] = []
        for d in docs:
            alerts.append({
                "item_id": d["item_id"],
                "item_code": d.get("item_code", ""),
                "item_name": d.get("item_name", ""),
                "item_type": d.get("item_type", ItemType.RAW_MATERIAL.value),
                "unit_id": d["unit_id"],
                "total_on_hand": round(float(d.get("total_on_hand", 0.0)), 2),
                "total_reserved": round(float(d.get("total_reserved", 0.0)), 2),
                "total_available": round(float(d.get("total_available", 0.0)), 2),
                "uom": d.get("uom", "NOS"),
                "reorder_level": round(float(d.get("reorder_level", 0.0)), 2),
                "safety_stock": round(float(d.get("safety_stock", 0.0)), 2),
                "shortage_quantity": round(max(0.0, float(d.get("shortage_quantity", 0.0))), 2),
            })
        return alerts

    async def get_dashboard_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Computes high-level Inventory KPIs: total valuation, item counts, alert count, and warehouse counts.
        """
        match_filter: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            match_filter["unit_id"] = unit_id

        # 1. Valuation and item count aggregation
        pipeline = [
            {"$match": match_filter} if match_filter else {"$match": {}},
            {
                "$group": {
                    "_id": None,
                    "total_valuation": {
                        "$sum": {"$multiply": ["$quantity_on_hand", "$valuation_rate"]}
                    },
                    "total_items": {"$addToSet": "$item_id"},
                    "rm_items": {
                        "$addToSet": {
                            "$cond": [{"$eq": ["$item_type", ItemType.RAW_MATERIAL.value]}, "$item_id", "$$REMOVE"]
                        }
                    },
                    "fg_items": {
                        "$addToSet": {
                            "$cond": [{"$eq": ["$item_type", ItemType.FINISHED_GOOD.value]}, "$item_id", "$$REMOVE"]
                        }
                    },
                }
            }
        ]
        agg_cursor = self.stock_col.aggregate(pipeline)
        agg_res = await agg_cursor.to_list(length=1)

        total_val = round(agg_res[0]["total_valuation"], 2) if agg_res else 0.0
        total_items = len(agg_res[0].get("total_items", [])) if agg_res else 0
        rm_items = len(agg_res[0].get("rm_items", [])) if agg_res else 0
        fg_items = len(agg_res[0].get("fg_items", [])) if agg_res else 0

        # 2. Alerts count
        alerts = await self.get_low_stock_alerts(unit_id)
        alert_count = len(alerts)

        # 3. Warehouses count
        wh_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            wh_query["unit_id"] = unit_id
        warehouses_count = await self.warehouses_col.count_documents(wh_query)

        # 4. Movements today count
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_query: Dict[str, Any] = {"created_at": {"$gte": today_start}}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            today_query["unit_id"] = unit_id
        movements_today = await self.ledger_col.count_documents(today_query)

        return {
            "total_items_tracked": total_items,
            "raw_material_items": rm_items,
            "finished_goods_items": fg_items,
            "total_valuation_inr": total_val,
            "low_stock_alerts_count": alert_count,
            "warehouses_count": warehouses_count,
            "movements_today_count": movements_today,
        }
