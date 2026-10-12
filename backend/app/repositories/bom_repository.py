import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.schemas.bom import (
    BOMStatus,
    BOMCreate,
    BOMUpdate,
    BOMRevisionCreate,
    BOMApprovalAction,
    MaterialRequirementCalculationRequest,
    MaterialRequirementCalculationResponse,
    MaterialRequirementItem,
    BOMImportRequest,
)

logger = logging.getLogger("app.bom.repository")


class BOMRepository:
    """
    Production-oriented repository for Bill of Materials (BOM) management.
    Enforces:
    1. Circular dependency prevention.
    2. Strict revision locking: approved versions are immutable.
    3. Unit of measure matching with raw materials master.
    4. Explicit scrap cost rollup without stock mutation.
    5. Real-time material requirement explosion against live inventory balances.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.bom_col = db["boms"]
        self.finished_products_col = db["finished_products"]
        self.raw_materials_col = db["raw_materials"]
        self.inventory_stock_col = db["inventory_stock"]

    # -------------------------------------------------------------
    # Number & Sequence Generators
    # -------------------------------------------------------------
    async def generate_bom_number(self) -> str:
        """Generates consecutive atomic BOM numbers: BOM-YYYY-XXXX."""
        now = datetime.now(timezone.utc)
        year_str = str(now.year)
        seq_doc = await self.db["counters"].find_one_and_update(
            {"_id": f"bom_seq_{year_str}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq_num = seq_doc["seq"]
        return f"BOM-{year_str}-{seq_num:04d}"

    # -------------------------------------------------------------
    # Validation & Resolvers
    # -------------------------------------------------------------
    async def resolve_finished_product(self, product_id: str) -> Dict[str, Any]:
        """Resolves finished product and validates its existence."""
        doc = None
        if ObjectId.is_valid(product_id):
            doc = await self.finished_products_col.find_one({"_id": ObjectId(product_id)})
        if not doc:
            doc = await self.finished_products_col.find_one({"code": product_id})

        if not doc:
            raise ValueError(f"Finished product with identifier '{product_id}' not found in master records.")

        return {
            "product_id": str(doc["_id"]),
            "product_code": doc.get("code", "UNKNOWN"),
            "product_name": doc.get("name", "Unknown Product"),
            "product_uom": doc.get("uom", "PCS"),
            "unit_id": doc.get("unit_id", "Unit_1"),
        }

    async def validate_and_enrich_components(
        self,
        product_code: str,
        components_input: List[Any],
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Validates components for:
        1. Non-circularity: components cannot be the parent finished product.
        2. Master existence in raw_materials.
        3. UoM compatibility.
        4. Calculates gross quantity and estimated line cost based on standard cost.
        """
        enriched_components: List[Dict[str, Any]] = []
        total_estimated_cost = 0.0
        seen_materials = set()

        for c in components_input:
            mat_id = c.material_id
            # 1. Circular check
            if mat_id == product_code:
                raise ValueError(f"Circular dependency error: Finished product '{product_code}' cannot be a component of itself.")

            # Resolve in raw_materials
            mat_doc = None
            if ObjectId.is_valid(mat_id):
                mat_doc = await self.raw_materials_col.find_one({"_id": ObjectId(mat_id)})
            if not mat_doc:
                mat_doc = await self.raw_materials_col.find_one({"code": mat_id})

            if not mat_doc:
                raise ValueError(f"Raw material component '{mat_id}' does not exist in master data.")

            resolved_mat_id = str(mat_doc["_id"])
            resolved_mat_code = mat_doc.get("code", "UNKNOWN")

            if resolved_mat_code == product_code:
                raise ValueError(f"Circular dependency error: Finished product '{product_code}' cannot use itself as component.")

            if resolved_mat_id in seen_materials:
                raise ValueError(f"Duplicate component error: Material '{resolved_mat_code}' specified multiple times in BOM.")
            seen_materials.add(resolved_mat_id)

            # 2. UoM compatibility check
            expected_uom = mat_doc.get("uom", "NOS").upper()
            provided_uom = c.uom.upper()
            if expected_uom != provided_uom:
                raise ValueError(
                    f"Incompatible Unit of Measure for '{resolved_mat_code}': "
                    f"Master specifies '{expected_uom}', but BOM component provided '{provided_uom}'."
                )

            # 3. Gross quantity calculation
            net_qty = float(c.net_quantity)
            if net_qty <= 0:
                raise ValueError(f"Net quantity for '{resolved_mat_code}' must be greater than zero.")

            scrap_pct = float(c.scrap_percentage or 0.0)
            if scrap_pct < 0 or scrap_pct > 100:
                raise ValueError(f"Scrap percentage for '{resolved_mat_code}' must be between 0 and 100.")

            gross_qty = round(net_qty * (1.0 + (scrap_pct / 100.0)), 4)

            # 4. Estimated costing policy: evaluate standard_cost from raw material master
            unit_cost = float(mat_doc.get("standard_cost", 0.0) or 0.0)
            line_cost = round(gross_qty * unit_cost, 2)
            total_estimated_cost += line_cost

            enriched_components.append({
                "material_id": resolved_mat_id,
                "material_code": resolved_mat_code,
                "material_name": mat_doc.get("name", "Unknown Material"),
                "uom": expected_uom,
                "net_quantity": net_qty,
                "scrap_percentage": scrap_pct,
                "gross_quantity": gross_qty,
                "unit_cost": round(unit_cost, 2),
                "estimated_cost": line_cost,
                "notes": c.notes,
            })

        return enriched_components, round(total_estimated_cost, 2)

    # -------------------------------------------------------------
    # 1. Create Draft BOM
    # -------------------------------------------------------------
    async def create_bom(self, bom_data: BOMCreate, created_by: str) -> Dict[str, Any]:
        """Creates a new Bill of Materials in DRAFT status."""
        prod = await self.resolve_finished_product(bom_data.product_id)

        # Check if revision already exists for this product and unit
        existing = await self.bom_col.find_one({
            "product_id": prod["product_id"],
            "unit_id": bom_data.unit_id.value,
            "revision_no": bom_data.revision_no.strip().upper(),
        })
        if existing:
            raise ValueError(
                f"BOM with revision '{bom_data.revision_no}' already exists for product '{prod['product_code']}' "
                f"in facility '{bom_data.unit_id.value}'."
            )

        components, total_cost = await self.validate_and_enrich_components(
            product_code=prod["product_code"],
            components_input=bom_data.components,
        )

        bom_number = await self.generate_bom_number()
        now = datetime.now(timezone.utc)

        doc = {
            "bom_number": bom_number,
            "product_id": prod["product_id"],
            "product_code": prod["product_code"],
            "product_name": prod["product_name"],
            "product_uom": prod["product_uom"],
            "unit_id": bom_data.unit_id.value,
            "base_quantity": float(bom_data.base_quantity),
            "revision_no": bom_data.revision_no.strip().upper(),
            "status": BOMStatus.DRAFT.value,
            "is_active": False,
            "effective_from": bom_data.effective_from,
            "effective_to": bom_data.effective_to,
            "description": bom_data.description,
            "total_estimated_cost": total_cost,
            "components": components,
            "created_at": now,
            "created_by": created_by,
            "updated_at": now,
            "updated_by": created_by,
        }

        res = await self.bom_col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    # -------------------------------------------------------------
    # 2. Get and List BOMs
    # -------------------------------------------------------------
    async def get_by_id(self, bom_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single BOM by ObjectId or BOM number."""
        if ObjectId.is_valid(bom_id):
            return await self.bom_col.find_one({"_id": ObjectId(bom_id)})
        return await self.bom_col.find_one({"bom_number": bom_id})

    async def list_boms(
        self,
        product_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Lists BOMs with search and filter capabilities."""
        query: Dict[str, Any] = {}
        if product_id:
            query["product_id"] = product_id
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id
        if status and status != "ALL":
            query["status"] = status
        if is_active is not None:
            query["is_active"] = is_active

        if search:
            query["$or"] = [
                {"bom_number": {"$regex": search, "$options": "i"}},
                {"product_code": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        total = await self.bom_col.count_documents(query)
        skip = (page - 1) * page_size
        cursor = self.bom_col.find(query).sort([("product_code", 1), ("created_at", -1)]).skip(skip).limit(page_size)

        docs = await cursor.to_list(length=page_size)
        return docs, total

    # -------------------------------------------------------------
    # 3. Update Draft BOM
    # -------------------------------------------------------------
    async def update_bom(self, bom_id: str, update_data: BOMUpdate, updated_by: str) -> Dict[str, Any]:
        """
        Updates a BOM in DRAFT status. Approved BOMs cannot be modified directly.
        """
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise ValueError("BOM record not found.")

        if bom.get("status") == BOMStatus.APPROVED.value:
            raise ValueError(
                f"Revision Lock: BOM {bom.get('bom_number')} ({bom.get('revision_no')}) is APPROVED and immutable. "
                "Create a new revision to introduce engineering changes."
            )

        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {
            "updated_at": now,
            "updated_by": updated_by,
        }

        if update_data.base_quantity is not None:
            updates["base_quantity"] = float(update_data.base_quantity)
        if update_data.effective_from is not None:
            updates["effective_from"] = update_data.effective_from
        if update_data.effective_to is not None:
            updates["effective_to"] = update_data.effective_to
        if update_data.description is not None:
            updates["description"] = update_data.description

        if update_data.components is not None:
            components, total_cost = await self.validate_and_enrich_components(
                product_code=bom["product_code"],
                components_input=update_data.components,
            )
            updates["components"] = components
            updates["total_estimated_cost"] = total_cost

        await self.bom_col.update_one({"_id": bom["_id"]}, {"$set": updates})
        return await self.get_by_id(bom_id)

    # -------------------------------------------------------------
    # 4. Create New Revision
    # -------------------------------------------------------------
    async def create_revision(
        self,
        base_bom_id: str,
        rev_data: BOMRevisionCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Clones an existing BOM to generate a new revision in DRAFT status.
        """
        base_bom = await self.get_by_id(base_bom_id)
        if not base_bom:
            raise ValueError("Base BOM not found.")

        new_rev_no = rev_data.new_revision_no.strip().upper()
        if new_rev_no == base_bom.get("revision_no"):
            raise ValueError(f"New revision must be different from base revision '{base_bom.get('revision_no')}'.")

        # Check uniqueness of revision
        existing = await self.bom_col.find_one({
            "product_id": base_bom["product_id"],
            "unit_id": base_bom["unit_id"],
            "revision_no": new_rev_no,
        })
        if existing:
            raise ValueError(f"Revision '{new_rev_no}' already exists for product '{base_bom['product_code']}'.")

        # Use new components if provided; otherwise clone base components
        raw_components = rev_data.components or [
            type("TempComp", (), {
                "material_id": c["material_id"],
                "net_quantity": c["net_quantity"],
                "uom": c["uom"],
                "scrap_percentage": c["scrap_percentage"],
                "notes": c.get("notes"),
            })()
            for c in base_bom["components"]
        ]

        components, total_cost = await self.validate_and_enrich_components(
            product_code=base_bom["product_code"],
            components_input=raw_components,
        )

        bom_number = await self.generate_bom_number()
        now = datetime.now(timezone.utc)

        new_doc = {
            "bom_number": bom_number,
            "product_id": base_bom["product_id"],
            "product_code": base_bom["product_code"],
            "product_name": base_bom["product_name"],
            "product_uom": base_bom["product_uom"],
            "unit_id": base_bom["unit_id"],
            "base_quantity": base_bom["base_quantity"],
            "revision_no": new_rev_no,
            "status": BOMStatus.DRAFT.value,
            "is_active": False,
            "effective_from": base_bom.get("effective_from"),
            "effective_to": base_bom.get("effective_to"),
            "description": rev_data.description or f"Revision cloned from {base_bom['bom_number']} ({base_bom['revision_no']})",
            "total_estimated_cost": total_cost,
            "components": components,
            "created_at": now,
            "created_by": created_by,
            "updated_at": now,
            "updated_by": created_by,
        }

        res = await self.bom_col.insert_one(new_doc)
        new_doc["_id"] = res.inserted_id
        return new_doc

    # -------------------------------------------------------------
    # 5. Workflow: Submit & Approve BOM
    # -------------------------------------------------------------
    async def submit_for_approval(self, bom_id: str, submitted_by: str) -> Dict[str, Any]:
        """Transitions BOM from DRAFT to PENDING_APPROVAL."""
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise ValueError("BOM record not found.")

        if bom.get("status") != BOMStatus.DRAFT.value:
            raise ValueError(f"Cannot submit BOM in '{bom.get('status')}' state for approval.")

        now = datetime.now(timezone.utc)
        await self.bom_col.update_one(
            {"_id": bom["_id"]},
            {
                "$set": {
                    "status": BOMStatus.PENDING_APPROVAL.value,
                    "updated_at": now,
                    "updated_by": submitted_by,
                }
            },
        )
        return await self.get_by_id(bom_id)

    async def approve_bom(
        self,
        bom_id: str,
        action: BOMApprovalAction,
        reviewed_by: str,
    ) -> Dict[str, Any]:
        """
        Approves or rejects a BOM revision.
        If approved and set_as_active is True:
        - Sets this revision as APPROVED and active.
        - Deactivates previous active versions for the product and unit.
        """
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise ValueError("BOM record not found.")

        now = datetime.now(timezone.utc)

        if not action.approved:
            # Reject back to DRAFT with remarks
            await self.bom_col.update_one(
                {"_id": bom["_id"]},
                {
                    "$set": {
                        "status": BOMStatus.DRAFT.value,
                        "description": f"Rejected by {reviewed_by}: {action.remarks or 'N/A'}",
                        "updated_at": now,
                        "updated_by": reviewed_by,
                    }
                },
            )
            return await self.get_by_id(bom_id)

        # Approved
        if action.set_as_active:
            # Deactivate other revisions of this product in this unit
            await self.bom_col.update_many(
                {
                    "product_id": bom["product_id"],
                    "unit_id": bom["unit_id"],
                    "_id": {"$ne": bom["_id"]},
                },
                {"$set": {"is_active": False}},
            )

        await self.bom_col.update_one(
            {"_id": bom["_id"]},
            {
                "$set": {
                    "status": BOMStatus.APPROVED.value,
                    "is_active": action.set_as_active,
                    "approved_by": reviewed_by,
                    "approved_at": now,
                    "updated_at": now,
                    "updated_by": reviewed_by,
                }
            },
        )
        return await self.get_by_id(bom_id)

    # -------------------------------------------------------------
    # 6. Material Requirements Calculation & Inventory Shortage
    # -------------------------------------------------------------
    async def calculate_material_requirements(
        self,
        bom_id: str,
        calc_request: MaterialRequirementCalculationRequest,
    ) -> MaterialRequirementCalculationResponse:
        """
        Calculates material explosion for target production quantity.
        Cross-references live `inventory_stock` without modifying stock balances.
        """
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise ValueError("BOM not found.")

        if bom.get("status") != BOMStatus.APPROVED.value:
            raise ValueError(
                f"Cannot run production requirement calculation on unapproved BOM '{bom.get('bom_number')}' "
                f"(Status: {bom.get('status')})."
            )

        base_qty = float(bom.get("base_quantity", 1.0) or 1.0)
        target_qty = float(calc_request.production_quantity)
        scale_factor = target_qty / base_qty

        requirements: List[MaterialRequirementItem] = []
        total_estimated_cost = 0.0
        shortage_count = 0

        for comp in bom.get("components", []):
            mat_id = comp["material_id"]
            mat_code = comp["material_code"]
            net_scaled = round(float(comp["net_quantity"]) * scale_factor, 4)
            scrap_pct = float(comp.get("scrap_percentage", 0.0))
            gross_scaled = round(net_scaled * (1.0 + (scrap_pct / 100.0)), 4)
            unit_cost = float(comp.get("unit_cost", 0.0))
            line_cost = round(gross_scaled * unit_cost, 2)
            total_estimated_cost += line_cost

            # Check live inventory stock across warehouses or specific warehouse
            stock_query: Dict[str, Any] = {"item_id": mat_id}
            if calc_request.warehouse_id:
                stock_query["warehouse_id"] = calc_request.warehouse_id
            elif bom.get("unit_id") not in ["ALL", "BOTH"]:
                stock_query["unit_id"] = bom.get("unit_id")

            # Aggregate available stock
            pipeline = [
                {"$match": stock_query},
                {
                    "$group": {
                        "_id": None,
                        "on_hand": {"$sum": "$quantity_on_hand"},
                        "reserved": {"$sum": "$quantity_reserved"},
                        "available": {"$sum": "$quantity_available"},
                    }
                }
            ]
            agg = await self.inventory_stock_col.aggregate(pipeline).to_list(length=1)
            on_hand = float(agg[0]["on_hand"]) if agg else 0.0
            reserved = float(agg[0]["reserved"]) if agg else 0.0
            available = float(agg[0]["available"]) if agg else (on_hand - reserved)

            is_shortage = available < gross_scaled
            shortage_qty = round(max(0.0, gross_scaled - available), 4) if is_shortage else 0.0
            if is_shortage:
                shortage_count += 1

            requirements.append(
                MaterialRequirementItem(
                    material_id=mat_id,
                    material_code=mat_code,
                    material_name=comp["material_name"],
                    uom=comp["uom"],
                    net_required_quantity=net_scaled,
                    scrap_percentage=scrap_pct,
                    gross_required_quantity=gross_scaled,
                    unit_cost=unit_cost,
                    total_estimated_cost=line_cost,
                    quantity_on_hand=round(on_hand, 4),
                    quantity_reserved=round(reserved, 4),
                    quantity_available=round(available, 4),
                    shortage_quantity=shortage_qty,
                    is_shortage=is_shortage,
                )
            )

        return MaterialRequirementCalculationResponse(
            bom_id=str(bom["_id"]),
            bom_number=bom.get("bom_number", "BOM"),
            product_code=bom.get("product_code", ""),
            product_name=bom.get("product_name", ""),
            revision_no=bom.get("revision_no", "R1"),
            unit_id=bom.get("unit_id", "Unit_1"),
            production_quantity=target_qty,
            total_estimated_material_cost=round(total_estimated_cost, 2),
            total_shortages_count=shortage_count,
            has_sufficient_stock=(shortage_count == 0),
            requirements=requirements,
        )

    # -------------------------------------------------------------
    # 7. Dashboard Metrics
    # -------------------------------------------------------------
    async def get_dashboard_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns KPI statistics for BOMs."""
        query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        total_boms = await self.bom_col.count_documents(query)
        approved_boms = await self.bom_col.count_documents({**query, "status": BOMStatus.APPROVED.value})
        pending_boms = await self.bom_col.count_documents({**query, "status": BOMStatus.PENDING_APPROVAL.value})
        draft_boms = await self.bom_col.count_documents({**query, "status": BOMStatus.DRAFT.value})
        active_boms = await self.bom_col.count_documents({**query, "is_active": True})

        # Distinct products with BOM
        distinct_prods = await self.bom_col.distinct("product_id", query)

        return {
            "total_boms": total_boms,
            "approved_boms": approved_boms,
            "pending_approval_boms": pending_boms,
            "draft_boms": draft_boms,
            "active_boms": active_boms,
            "products_with_bom_count": len(distinct_prods),
        }

    # -------------------------------------------------------------
    # 8. Bulk Import
    # -------------------------------------------------------------
    async def import_boms(self, import_request: BOMImportRequest, created_by: str) -> Dict[str, Any]:
        """
        Groups import items by product_code + revision_no + unit_id and creates BOMs.
        """
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in import_request.items:
            key = (item.product_code.strip(), item.revision_no.strip().upper(), item.unit_id.value)
            grouped[key].append(item)

        processed = 0
        skipped = 0
        errors: List[str] = []

        for (p_code, rev_no, u_id), comp_list in grouped.items():
            try:
                prod = await self.resolve_finished_product(p_code)
                existing = await self.bom_col.find_one({
                    "product_id": prod["product_id"],
                    "unit_id": u_id,
                    "revision_no": rev_no,
                })
                if existing:
                    skipped += 1
                    continue

                components_input = [
                    type("ImportComp", (), {
                        "material_id": c.material_code,
                        "net_quantity": c.net_quantity,
                        "uom": c.uom,
                        "scrap_percentage": c.scrap_percentage,
                        "notes": c.description,
                    })()
                    for c in comp_list
                ]

                components, total_cost = await self.validate_and_enrich_components(
                    product_code=prod["product_code"],
                    components_input=components_input,
                )

                bom_number = await self.generate_bom_number()
                now = datetime.now(timezone.utc)
                status_val = BOMStatus.APPROVED.value if import_request.auto_approve else BOMStatus.DRAFT.value

                doc = {
                    "bom_number": bom_number,
                    "product_id": prod["product_id"],
                    "product_code": prod["product_code"],
                    "product_name": prod["product_name"],
                    "product_uom": prod["product_uom"],
                    "unit_id": u_id,
                    "base_quantity": comp_list[0].base_quantity,
                    "revision_no": rev_no,
                    "status": status_val,
                    "is_active": import_request.auto_approve,
                    "description": comp_list[0].description or "Imported from template",
                    "total_estimated_cost": total_cost,
                    "components": components,
                    "approved_by": created_by if import_request.auto_approve else None,
                    "approved_at": now if import_request.auto_approve else None,
                    "created_at": now,
                    "created_by": created_by,
                    "updated_at": now,
                    "updated_by": created_by,
                }

                await self.bom_col.insert_one(doc)
                processed += 1
            except Exception as e:
                errors.append(f"{p_code} (Rev: {rev_no}): {str(e)}")

        return {
            "total_groups": len(grouped),
            "processed_count": processed,
            "skipped_count": skipped,
            "errors_count": len(errors),
            "errors": errors,
        }
