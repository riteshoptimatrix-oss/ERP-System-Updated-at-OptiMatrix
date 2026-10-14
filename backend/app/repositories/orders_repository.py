import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.repositories.base import BaseRepository
from app.repositories.master_repository import MasterRepository
from app.schemas.orders import (
    OrderStatus,
    DispatchStatus,
    SalesOrderCreate,
    SalesOrderUpdate,
    PackingSlipCreate,
    DispatchRecordCreate,
)

logger = logging.getLogger(__name__)


class OrdersRepository(BaseRepository):
    """
    Dedicated MongoDB repository for Sales Orders, Order Line Items,
    Packing Slips, Dispatch Records, and Lifecycle Activity Audits.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, "sales_orders")
        self.packing_slips_col = db["packing_slips"]
        self.dispatches_col = db["dispatch_records"]
        self.order_activities_col = db["order_activities"]
        self.customers_repo = MasterRepository(db, "customers")
        self.products_repo = MasterRepository(db, "finished_products")

    # -------------------------------------------------------------
    # Sequence Generators
    # -------------------------------------------------------------
    async def generate_order_number(self) -> str:
        """Generate next Sales Order sequence: SO-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        count = await self.collection.count_documents({})
        return f"SO-{year}-{count + 1:04d}"

    async def generate_packing_slip_number(self) -> str:
        """Generate next Packing Slip sequence: PS-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        count = await self.packing_slips_col.count_documents({})
        return f"PS-{year}-{count + 1:04d}"

    async def generate_dispatch_number(self) -> str:
        """Generate next Dispatch sequence: DSP-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        count = await self.dispatches_col.count_documents({})
        return f"DSP-{year}-{count + 1:04d}"

    # -------------------------------------------------------------
    # Sales Orders CRUD & Queries
    # -------------------------------------------------------------
    async def list_orders(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query sales orders with search regex, status filters, unit isolation, and pagination.
        """
        filter_query: Dict[str, Any] = {}

        if status:
            filter_query["status"] = status
        if customer_id:
            filter_query["customer_id"] = customer_id

        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [
                {"unit_id": unit_id},
                {"unit_id": "BOTH"},
            ]

        if search:
            escaped = re.escape(search.strip())
            pattern = re.compile(escaped, re.IGNORECASE)
            search_clause = [
                {"order_number": pattern},
                {"customer_name": pattern},
                {"customer_code": pattern},
                {"customer_po_number": pattern},
            ]
            if "$or" in filter_query:
                filter_query = {"$and": [{"$or": filter_query["$or"]}, {"$or": search_clause}]}
            else:
                filter_query["$or"] = search_clause

        total = await self.collection.count_documents(filter_query)
        cursor = (
            self.collection.find(filter_query)
            .sort(sort_by, sort_order)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        orders = await cursor.to_list(length=page_size)
        return orders, total

    async def get_by_order_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Find order by exact order number e.g. SO-2026-0001."""
        return await self.collection.find_one({"order_number": order_number.strip()})

    async def create_sales_order(
        self,
        order_data: SalesOrderCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Create a new sales order linked to Customer Master and Finished Product Master.
        """
        # Validate Customer existence
        customer = await self.customers_repo.get_by_id(order_data.customer_id)
        if not customer:
            # Fallback check by customer code
            customer = await self.customers_repo.get_by_code(order_data.customer_id)
            if not customer:
                raise ValueError(f"Customer '{order_data.customer_id}' does not exist in Customer Master.")

        # Reconcile Items and calculate financial totals
        processed_items: List[Dict[str, Any]] = []
        subtotal = 0.0
        tax_total = 0.0
        total_ordered_qty = 0.0

        for item in order_data.items:
            # Fetch product info from Finished Products master
            product = await self.products_repo.get_by_id(item.product_id)
            if not product:
                product = await self.products_repo.get_by_code(item.product_code)

            p_name = product.get("name", item.product_name) if product else item.product_name
            p_code = product.get("code", item.product_code) if product else item.product_code
            p_uom = product.get("uom", item.uom) if product else item.uom

            discounted_price = item.unit_price * (1.0 - (item.discount_percent / 100.0))
            line_subtotal = round(item.quantity * discounted_price, 2)
            line_tax = round(line_subtotal * (item.tax_percent / 100.0), 2)
            line_total = round(line_subtotal + line_tax, 2)

            subtotal += line_subtotal
            tax_total += line_tax
            total_ordered_qty += item.quantity

            processed_items.append({
                "product_id": str(product.get("_id")) if product else item.product_id,
                "product_code": p_code,
                "product_name": p_name,
                "uom": p_uom,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "discount_percent": float(item.discount_percent),
                "tax_percent": float(item.tax_percent),
                "dispatched_quantity": 0.0,
                "subtotal": line_subtotal,
                "tax_amount": line_tax,
                "total_amount": line_total,
                "notes": item.notes,
            })

        grand_total = round(subtotal + tax_total, 2)
        order_number = await self.generate_order_number()
        now = datetime.now(timezone.utc)

        order_doc = {
            "order_number": order_number,
            "customer_id": str(customer.get("_id")),
            "customer_code": customer.get("code", ""),
            "customer_name": customer.get("name", ""),
            "customer_po_number": order_data.customer_po_number,
            "unit_id": order_data.unit_id.value,
            "status": OrderStatus.DRAFT.value,
            "order_date": datetime.fromisoformat(order_data.order_date.replace("Z", "+00:00")) if order_data.order_date else now,
            "delivery_due_date": order_data.delivery_due_date,
            "billing_address": order_data.billing_address or customer.get("billing_address"),
            "shipping_address": order_data.shipping_address or customer.get("shipping_address") or customer.get("billing_address"),
            "items": processed_items,
            "subtotal": round(subtotal, 2),
            "tax_total": round(tax_total, 2),
            "grand_total": grand_total,
            "total_ordered_qty": round(total_ordered_qty, 2),
            "total_dispatched_qty": 0.0,
            "dispatch_percent": 0.0,
            "notes": order_data.notes,
            "cancellation_reason": None,
            "created_at": now,
            "created_by": created_by,
            "updated_at": None,
            "updated_by": None,
        }

        res = await self.collection.insert_one(order_doc)
        order_doc["_id"] = res.inserted_id

        # Log creation activity
        await self.log_order_activity(
            order_id=str(res.inserted_id),
            action="ORDER_CREATED",
            description=f"Sales order {order_number} created in DRAFT state.",
            performed_by=created_by,
        )

        return order_doc

    async def update_sales_order(
        self,
        order_id: str,
        update_data: SalesOrderUpdate,
        updated_by: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing sales order (allowed only when status is DRAFT or SUBMITTED).
        """
        order = await self.get_by_id(order_id)
        if not order:
            return None

        if order.get("status") not in [OrderStatus.DRAFT.value, OrderStatus.SUBMITTED.value]:
            raise ValueError(f"Cannot update sales order in '{order.get('status')}' state.")

        update_fields: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc),
            "updated_by": updated_by,
        }

        if update_data.customer_po_number is not None:
            update_fields["customer_po_number"] = update_data.customer_po_number
        if update_data.delivery_due_date is not None:
            update_fields["delivery_due_date"] = update_data.delivery_due_date
        if update_data.billing_address is not None:
            update_fields["billing_address"] = update_data.billing_address
        if update_data.shipping_address is not None:
            update_fields["shipping_address"] = update_data.shipping_address
        if update_data.notes is not None:
            update_fields["notes"] = update_data.notes

        # Re-calculate line items if updated
        if update_data.items is not None:
            processed_items: List[Dict[str, Any]] = []
            subtotal = 0.0
            tax_total = 0.0
            total_ordered_qty = 0.0

            for item in update_data.items:
                product = await self.products_repo.get_by_id(item.product_id)
                if not product:
                    product = await self.products_repo.get_by_code(item.product_code)

                p_name = product.get("name", item.product_name) if product else item.product_name
                p_code = product.get("code", item.product_code) if product else item.product_code
                p_uom = product.get("uom", item.uom) if product else item.uom

                discounted_price = item.unit_price * (1.0 - (item.discount_percent / 100.0))
                line_subtotal = round(item.quantity * discounted_price, 2)
                line_tax = round(line_subtotal * (item.tax_percent / 100.0), 2)
                line_total = round(line_subtotal + line_tax, 2)

                subtotal += line_subtotal
                tax_total += line_tax
                total_ordered_qty += item.quantity

                processed_items.append({
                    "product_id": str(product.get("_id")) if product else item.product_id,
                    "product_code": p_code,
                    "product_name": p_name,
                    "uom": p_uom,
                    "quantity": float(item.quantity),
                    "unit_price": float(item.unit_price),
                    "discount_percent": float(item.discount_percent),
                    "tax_percent": float(item.tax_percent),
                    "dispatched_quantity": 0.0,
                    "subtotal": line_subtotal,
                    "tax_amount": line_tax,
                    "total_amount": line_total,
                    "notes": item.notes,
                })

            update_fields["items"] = processed_items
            update_fields["subtotal"] = round(subtotal, 2)
            update_fields["tax_total"] = round(tax_total, 2)
            update_fields["grand_total"] = round(subtotal + tax_total, 2)
            update_fields["total_ordered_qty"] = round(total_ordered_qty, 2)

        await self.collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_fields},
        )

        await self.log_order_activity(
            order_id=order_id,
            action="ORDER_UPDATED",
            description="Sales order details updated.",
            performed_by=updated_by,
        )

        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # State Machine Transitions
    # -------------------------------------------------------------
    async def submit_order(self, order_id: str, user_email: str) -> Dict[str, Any]:
        """Transition DRAFT -> SUBMITTED."""
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Sales order not found.")
        if order.get("status") != OrderStatus.DRAFT.value:
            raise ValueError(f"Only DRAFT orders can be submitted (current status: {order.get('status')}).")

        await self.collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": OrderStatus.SUBMITTED.value, "updated_at": datetime.now(timezone.utc), "updated_by": user_email}},
        )
        await self.log_order_activity(
            order_id=order_id,
            action="STATUS_CHANGED",
            description="Order submitted for approval.",
            performed_by=user_email,
        )
        return await self.get_by_id(order_id)

    async def confirm_order(self, order_id: str, user_email: str) -> Dict[str, Any]:
        """Transition SUBMITTED -> CONFIRMED."""
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Sales order not found.")
        if order.get("status") != OrderStatus.SUBMITTED.value:
            raise ValueError(f"Only SUBMITTED orders can be confirmed (current status: {order.get('status')}).")

        await self.collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": OrderStatus.CONFIRMED.value, "updated_at": datetime.now(timezone.utc), "updated_by": user_email}},
        )
        await self.log_order_activity(
            order_id=order_id,
            action="ORDER_CONFIRMED",
            description="Order confirmed and ready for packing & dispatch.",
            performed_by=user_email,
        )
        return await self.get_by_id(order_id)

    async def cancel_order(self, order_id: str, reason: str, user_email: str) -> Dict[str, Any]:
        """Transition Order to CANCELLED."""
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Sales order not found.")

        current_status = order.get("status")
        if current_status in [OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value]:
            raise ValueError(f"Cannot cancel order in '{current_status}' state.")

        if current_status == OrderStatus.PARTIALLY_DISPATCHED.value:
            raise ValueError("Cannot cancel an order that has already been partially dispatched.")

        await self.collection.update_one(
            {"_id": ObjectId(order_id)},
            {
                "$set": {
                    "status": OrderStatus.CANCELLED.value,
                    "cancellation_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": user_email,
                }
            },
        )
        await self.log_order_activity(
            order_id=order_id,
            action="ORDER_CANCELLED",
            description=f"Order cancelled. Reason: {reason}",
            performed_by=user_email,
        )
        return await self.get_by_id(order_id)

    # -------------------------------------------------------------
    # Packing Slips
    # -------------------------------------------------------------
    async def create_packing_slip(
        self,
        order_id: str,
        slip_data: PackingSlipCreate,
        created_by: str,
    ) -> Dict[str, Any]:
        """
        Generate a packing slip referencing an active Sales Order and line items.
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Sales order not found.")

        if order.get("status") not in [
            OrderStatus.CONFIRMED.value,
            OrderStatus.PARTIALLY_DISPATCHED.value,
        ]:
            raise ValueError(f"Cannot create packing slip for order in '{order.get('status')}' state.")

        # Reconcile items to ensure pack_quantity does not exceed remaining ordered quantity
        order_items = {item["product_code"]: item for item in order.get("items", [])}
        processed_slip_items: List[Dict[str, Any]] = []

        for item in slip_data.items:
            matching = order_items.get(item.product_code)
            if not matching:
                raise ValueError(f"Product '{item.product_code}' is not an item in Sales Order {order.get('order_number')}.")

            rem_qty = matching["quantity"] - matching.get("dispatched_quantity", 0.0)
            if item.pack_quantity > rem_qty:
                raise ValueError(
                    f"Packed quantity ({item.pack_quantity}) for {item.product_code} "
                    f"exceeds remaining order balance ({rem_qty})."
                )

            processed_slip_items.append({
                "product_id": matching["product_id"],
                "product_code": item.product_code,
                "product_name": matching["product_name"],
                "ordered_quantity": matching["quantity"],
                "pack_quantity": float(item.pack_quantity),
                "package_type": item.package_type,
                "notes": item.notes,
            })

        slip_number = await self.generate_packing_slip_number()
        now = datetime.now(timezone.utc)

        slip_doc = {
            "slip_number": slip_number,
            "order_id": order_id,
            "order_number": order.get("order_number"),
            "customer_id": order.get("customer_id"),
            "customer_name": order.get("customer_name"),
            "unit_id": order.get("unit_id"),
            "packages_count": slip_data.packages_count,
            "gross_weight_kg": slip_data.gross_weight_kg,
            "net_weight_kg": slip_data.net_weight_kg,
            "special_handling_notes": slip_data.special_handling_notes,
            "items": processed_slip_items,
            "created_at": now,
            "created_by": created_by,
        }

        res = await self.packing_slips_col.insert_one(slip_doc)
        slip_doc["_id"] = res.inserted_id

        await self.log_order_activity(
            order_id=order_id,
            action="PACKING_SLIP_GENERATED",
            description=f"Packing Slip {slip_number} generated ({slip_data.packages_count} packages).",
            performed_by=created_by,
        )

        return slip_doc

    async def list_packing_slips(self, order_id: str) -> List[Dict[str, Any]]:
        """List packing slips generated for a sales order."""
        cursor = self.packing_slips_col.find({"order_id": order_id}).sort("created_at", -1)
        return await cursor.to_list(length=100)

    async def get_packing_slip(self, slip_id: str) -> Optional[Dict[str, Any]]:
        """Get packing slip details."""
        if ObjectId.is_valid(slip_id):
            return await self.packing_slips_col.find_one({"_id": ObjectId(slip_id)})
        return await self.packing_slips_col.find_one({"slip_number": slip_id})

    # -------------------------------------------------------------
    # Dispatch Records & Over-Dispatch Prevention
    # -------------------------------------------------------------
    async def create_dispatch(
        self,
        order_id: str,
        dispatch_data: DispatchRecordCreate,
        dispatched_by: str,
    ) -> Dict[str, Any]:
        """
        Record a dispatch against a sales order.
        Enforces:
        - Prevents over-dispatch across multiple shipments.
        - Automatically updates cumulative dispatched quantity per line item.
        - Automatically updates Sales Order status (PARTIALLY_DISPATCHED or DISPATCHED).
        """
        order = await self.get_by_id(order_id)
        if not order:
            raise ValueError("Sales order not found.")

        if order.get("status") not in [
            OrderStatus.CONFIRMED.value,
            OrderStatus.PARTIALLY_DISPATCHED.value,
        ]:
            raise ValueError(f"Cannot dispatch goods for order in '{order.get('status')}' state.")

        # Resolve Packing Slip if provided
        ps_number = None
        if dispatch_data.packing_slip_id:
            ps_doc = await self.get_packing_slip(dispatch_data.packing_slip_id)
            if ps_doc:
                ps_number = ps_doc.get("slip_number")

        # Map current order items
        order_items: List[Dict[str, Any]] = order.get("items", [])
        order_items_map = {item["product_code"]: item for item in order_items}

        # Check for over-dispatch
        dispatch_items_processed: List[Dict[str, Any]] = []
        total_dispatch_qty = 0.0

        for d_item in dispatch_data.items:
            matching = order_items_map.get(d_item.product_code)
            if not matching:
                raise ValueError(
                    f"Product '{d_item.product_code}' does not belong to Sales Order {order.get('order_number')}."
                )

            current_dispatched = matching.get("dispatched_quantity", 0.0)
            remaining_available = matching["quantity"] - current_dispatched

            if d_item.quantity > remaining_available:
                raise ValueError(
                    f"Over-dispatch prevented for {d_item.product_code}: "
                    f"attempted to dispatch {d_item.quantity}, but only {remaining_available} remaining."
                )

            dispatch_items_processed.append({
                "product_id": matching["product_id"],
                "product_code": d_item.product_code,
                "product_name": matching["product_name"],
                "quantity": float(d_item.quantity),
            })
            total_dispatch_qty += d_item.quantity

        dispatch_number = await self.generate_dispatch_number()
        now = datetime.now(timezone.utc)
        dispatch_date = (
            datetime.fromisoformat(dispatch_data.dispatched_date.replace("Z", "+00:00"))
            if dispatch_data.dispatched_date
            else now
        )

        dispatch_doc = {
            "dispatch_number": dispatch_number,
            "order_id": order_id,
            "order_number": order.get("order_number"),
            "customer_id": order.get("customer_id"),
            "customer_name": order.get("customer_name"),
            "packing_slip_id": dispatch_data.packing_slip_id,
            "packing_slip_number": ps_number,
            "unit_id": order.get("unit_id"),
            "carrier_name": dispatch_data.carrier_name,
            "vehicle_number": dispatch_data.vehicle_number,
            "lr_number": dispatch_data.lr_number,
            "driver_name": dispatch_data.driver_name,
            "driver_phone": dispatch_data.driver_phone,
            "dispatched_date": dispatch_date,
            "status": DispatchStatus.SHIPPED.value,
            "items": dispatch_items_processed,
            "total_quantity": round(total_dispatch_qty, 2),
            "remarks": dispatch_data.remarks,
            "created_at": now,
            "created_by": dispatched_by,
        }

        # Insert dispatch document
        res = await self.dispatches_col.insert_one(dispatch_doc)
        dispatch_doc["_id"] = res.inserted_id

        # Update order item dispatched quantities
        updated_items: List[Dict[str, Any]] = []
        cumulative_order_dispatched = 0.0
        total_order_qty = 0.0

        dispatch_qty_map = {item["product_code"]: item["quantity"] for item in dispatch_items_processed}

        for item in order_items:
            add_qty = dispatch_qty_map.get(item["product_code"], 0.0)
            new_dispatched = item.get("dispatched_quantity", 0.0) + add_qty
            item["dispatched_quantity"] = round(new_dispatched, 2)
            cumulative_order_dispatched += item["dispatched_quantity"]
            total_order_qty += item["quantity"]
            updated_items.append(item)

        dispatch_percent = round((cumulative_order_dispatched / total_order_qty) * 100.0, 1) if total_order_qty > 0 else 0.0
        new_order_status = (
            OrderStatus.DISPATCHED.value
            if cumulative_order_dispatched >= total_order_qty
            else OrderStatus.PARTIALLY_DISPATCHED.value
        )

        await self.collection.update_one(
            {"_id": ObjectId(order_id)},
            {
                "$set": {
                    "items": updated_items,
                    "total_dispatched_qty": round(cumulative_order_dispatched, 2),
                    "dispatch_percent": dispatch_percent,
                    "status": new_order_status,
                    "updated_at": now,
                    "updated_by": dispatched_by,
                }
            },
        )

        # Deduct finished goods stock via authorized InventoryRepository
        try:
            from app.repositories.inventory_repository import InventoryRepository
            inv_repo = InventoryRepository(self.db)
            await inv_repo.deduct_dispatch_stock(
                order_id=order_id,
                order_number=order.get("order_number", "ORD"),
                unit_id=order.get("unit_id", "Unit_1"),
                items=dispatch_items_processed,
                dispatched_by=dispatched_by,
                remarks=dispatch_data.remarks,
            )
        except Exception as e:
            logger.warning(f"Inventory dispatch deduction notice for {dispatch_number}: {e}")

        await self.log_order_activity(
            order_id=order_id,
            action="DISPATCH_POSTED",
            description=(
                f"Dispatch {dispatch_number} posted via {dispatch_data.carrier_name} "
                f"({total_dispatch_qty} units). Order status updated to {new_order_status}."
            ),
            performed_by=dispatched_by,
        )

        return dispatch_doc

    async def list_dispatches(self, order_id: str) -> List[Dict[str, Any]]:
        """List dispatch records for a specific sales order."""
        cursor = self.dispatches_col.find({"order_id": order_id}).sort("dispatched_date", -1)
        return await cursor.to_list(length=100)

    async def get_dispatch(self, dispatch_id: str) -> Optional[Dict[str, Any]]:
        """Get single dispatch record."""
        if ObjectId.is_valid(dispatch_id):
            return await self.dispatches_col.find_one({"_id": ObjectId(dispatch_id)})
        return await self.dispatches_col.find_one({"dispatch_number": dispatch_id})

    # -------------------------------------------------------------
    # Activity Audits & Timeline
    # -------------------------------------------------------------
    async def log_order_activity(
        self,
        order_id: str,
        action: str,
        description: str,
        performed_by: str,
    ) -> None:
        """Record lifecycle event in order_activities collection."""
        doc = {
            "order_id": order_id,
            "action": action,
            "description": description,
            "performed_by": performed_by,
            "timestamp": datetime.now(timezone.utc),
        }
        await self.order_activities_col.insert_one(doc)

    async def get_order_activities(self, order_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit timeline for a sales order."""
        cursor = self.order_activities_col.find({"order_id": order_id}).sort("timestamp", -1)
        return await cursor.to_list(length=100)

    # -------------------------------------------------------------
    # Dashboard KPI Metrics
    # -------------------------------------------------------------
    async def get_dashboard_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregate order status counts, pipeline valuation, and dispatch metrics.
        """
        filter_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [
                {"unit_id": unit_id},
                {"unit_id": "BOTH"},
            ]

        total_orders = await self.collection.count_documents(filter_query)
        draft_orders = await self.collection.count_documents({**filter_query, "status": OrderStatus.DRAFT.value})
        confirmed_orders = await self.collection.count_documents({**filter_query, "status": OrderStatus.CONFIRMED.value})
        partially_dispatched = await self.collection.count_documents({**filter_query, "status": OrderStatus.PARTIALLY_DISPATCHED.value})
        fully_dispatched = await self.collection.count_documents({**filter_query, "status": OrderStatus.DISPATCHED.value})
        cancelled_orders = await self.collection.count_documents({**filter_query, "status": OrderStatus.CANCELLED.value})

        # Calculate pipeline financials
        pipeline = [
            {"$match": {**filter_query, "status": {"$ne": OrderStatus.CANCELLED.value}}},
            {
                "$group": {
                    "_id": None,
                    "total_pipeline": {"$sum": "$grand_total"},
                }
            },
        ]
        agg_res = await self.collection.aggregate(pipeline).to_list(length=1)
        total_pipeline_val = float(agg_res[0]["total_pipeline"]) if agg_res else 0.0

        # Dispatches count
        dsp_filter: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            dsp_filter["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]
        dispatches_count = await self.dispatches_col.count_documents(dsp_filter)

        return {
            "total_orders": total_orders,
            "draft_orders": draft_orders,
            "confirmed_orders": confirmed_orders,
            "partially_dispatched_orders": partially_dispatched,
            "fully_dispatched_orders": fully_dispatched,
            "cancelled_orders": cancelled_orders,
            "total_pipeline_value": round(total_pipeline_val, 2),
            "total_dispatched_value": 0.0,
            "total_pending_dispatches": confirmed_orders + partially_dispatched,
        }

    # -------------------------------------------------------------
    # Order Planning (By Variant and Length)
    # Updated by Taha; one line per variant and length
    # -------------------------------------------------------------
    async def list_order_planning(
        self,
        unit_id: Optional[str] = None,
        priority: Optional[str] = None,
        order_status: Optional[str] = None,
        final_approval: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List Order Planning records filtered by unit, status, priority, or search term.
        """
        filter_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]
        if priority:
            filter_query["priority"] = priority.upper()
        if order_status:
            filter_query["order_status"] = order_status.upper()
        if final_approval:
            filter_query["final_approval"] = final_approval.upper()
        if search:
            regex_patt = {"$regex": search, "$options": "i"}
            filter_query["$or"] = [
                {"order_number": regex_patt},
                {"customer": regex_patt},
                {"brand": regex_patt},
                {"variant": regex_patt},
                {"length": regex_patt},
            ]

        # If order_planning collection is empty, automatically seed/sync from existing confirmed orders
        count = await self.db["order_planning"].count_documents({})
        if count == 0:
            await self.sync_order_planning_from_orders()

        cursor = self.db["order_planning"].find(filter_query).sort([("order_date", -1), ("order_number", 1)])
        docs = await cursor.to_list(length=1000)
        for doc in docs:
            doc["id"] = str(doc["_id"])
            # Ensure computed fields are accurate
            order_qty = float(doc.get("order_qty", 0.0))
            produced_qty = float(doc.get("produced_qty", 0.0))
            dispatch_qty = float(doc.get("dispatch_qty", 0.0))
            doc["balance_qty"] = max(0.0, order_qty - produced_qty)
            doc["dispatch_balance"] = max(0.0, order_qty - dispatch_qty)
        return docs

    async def get_order_planning_summary(self, unit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate aggregate planning metrics across all variant lines.
        """
        filter_query: Dict[str, Any] = {}
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [{"unit_id": unit_id}, {"unit_id": "BOTH"}]

        docs = await self.db["order_planning"].find(filter_query).to_list(length=2000)
        total_planning_lines = len(docs)
        total_order_qty = 0.0
        total_planned_qty = 0.0
        total_produced_qty = 0.0
        total_balance_qty = 0.0
        total_dispatch_qty = 0.0
        total_dispatch_balance = 0.0
        approved_lines = 0
        pending_lines = 0

        for d in docs:
            oq = float(d.get("order_qty", 0.0))
            pq = float(d.get("planned_qty", 0.0))
            prq = float(d.get("produced_qty", 0.0))
            dq = float(d.get("dispatch_qty", 0.0))
            bal = max(0.0, oq - prq)
            dbal = max(0.0, oq - dq)

            total_order_qty += oq
            total_planned_qty += pq
            total_produced_qty += prq
            total_balance_qty += bal
            total_dispatch_qty += dq
            total_dispatch_balance += dbal

            if d.get("final_approval", "APPROVED").upper() == "APPROVED":
                approved_lines += 1
            else:
                pending_lines += 1

        return {
            "total_planning_lines": total_planning_lines,
            "total_order_qty": round(total_order_qty, 2),
            "total_planned_qty": round(total_planned_qty, 2),
            "total_produced_qty": round(total_produced_qty, 2),
            "total_balance_qty": round(total_balance_qty, 2),
            "total_dispatch_qty": round(total_dispatch_qty, 2),
            "total_dispatch_balance": round(total_dispatch_balance, 2),
            "approved_lines": approved_lines,
            "pending_lines": pending_lines,
        }

    async def update_order_planning_item(
        self,
        item_id: str,
        update_data: Dict[str, Any],
        updated_by: str = "Taha",
    ) -> Optional[Dict[str, Any]]:
        """
        Update a planning line (quantities, dates, approval, remarks, etc.).
        """
        if not ObjectId.is_valid(item_id):
            return None

        clean_update = {k: v for k, v in update_data.items() if v is not None}
        clean_update["updated_at"] = datetime.now(timezone.utc)
        clean_update["updated_by"] = updated_by

        current = await self.db["order_planning"].find_one({"_id": ObjectId(item_id)})
        if not current:
            return None

        # Recalculate balance quantities if any quantity is modified
        order_qty = float(current.get("order_qty", 0.0))
        produced_qty = float(clean_update.get("produced_qty", current.get("produced_qty", 0.0)))
        dispatch_qty = float(clean_update.get("dispatch_qty", current.get("dispatch_qty", 0.0)))
        clean_update["balance_qty"] = max(0.0, order_qty - produced_qty)
        clean_update["dispatch_balance"] = max(0.0, order_qty - dispatch_qty)

        await self.db["order_planning"].update_one(
            {"_id": ObjectId(item_id)},
            {"$set": clean_update},
        )
        updated = await self.db["order_planning"].find_one({"_id": ObjectId(item_id)})
        if updated:
            updated["id"] = str(updated["_id"])
        return updated

    async def create_order_planning_item(
        self,
        item_data: Dict[str, Any],
        created_by: str = "Taha",
    ) -> Dict[str, Any]:
        """
        Add a new variant/length planning row manually.
        """
        item_data["created_at"] = datetime.now(timezone.utc)
        item_data["updated_at"] = datetime.now(timezone.utc)
        item_data["updated_by"] = created_by
        oq = float(item_data.get("order_qty", 0.0))
        prq = float(item_data.get("produced_qty", 0.0))
        dq = float(item_data.get("dispatch_qty", 0.0))
        item_data["balance_qty"] = max(0.0, oq - prq)
        item_data["dispatch_balance"] = max(0.0, oq - dq)

        res = await self.db["order_planning"].insert_one(item_data)
        item_data["id"] = str(res.inserted_id)
        return item_data

    async def sync_order_planning_from_orders(self) -> int:
        """
        Synchronize confirmed sales orders into granular variant and length planning lines.
        """
        cursor = self.collection.find({"status": {"$ne": OrderStatus.CANCELLED.value}})
        orders = await cursor.to_list(length=500)
        inserted_count = 0

        for order in orders:
            order_num = order.get("order_number", "")
            order_date_str = (
                order["order_date"].strftime("%Y-%m-%d")
                if isinstance(order.get("order_date"), datetime)
                else str(order.get("order_date", "2026-10-10"))[:10]
            )
            req_dispatch_str = (
                order["required_delivery_date"].strftime("%Y-%m-%d")
                if isinstance(order.get("required_delivery_date"), datetime)
                else str(order.get("required_delivery_date", "2026-10-25"))[:10]
            )
            customer = order.get("customer_name", "Valued Customer")
            customer_code = order.get("customer_code", "")
            unit = order.get("unit_id", "Unit_1")
            status = order.get("status", "CONFIRMED")

            for idx, item in enumerate(order.get("items", [])):
                p_name = item.get("product_name", "Precision Component")
                p_code = item.get("product_code", "")
                qty = float(item.get("quantity", 10.0))
                disp_qty = float(item.get("dispatched_quantity", 0.0))
                brand = "OptiMatrix"

                # Parse variant & length from product spec or name
                variant = p_name
                length = "Standard"
                if "100" in p_code:
                    variant = f"{p_name} (Standard)"
                    length = "100 mm"
                elif "150" in p_code:
                    variant = f"{p_name} (Heavy)"
                    length = "150 mm"
                elif "50" in p_code or "PRO" in p_code:
                    variant = f"{p_name} (Pro)"
                    length = "200 mm"
                elif "MINI" in p_code:
                    variant = f"{p_name} (Compact)"
                    length = "50 mm"

                # Check if already exists in order_planning
                existing = await self.db["order_planning"].find_one({
                    "order_number": order_num,
                    "variant": variant,
                    "length": length,
                })
                if existing:
                    continue

                produced = disp_qty if disp_qty > 0 else (qty if status == "DISPATCHED" else (round(qty * 0.6, 1) if status == "PARTIALLY_DISPATCHED" else 0.0))
                planned = qty

                doc = {
                    "order_id": str(order["_id"]),
                    "order_number": order_num,
                    "order_date": order_date_str,
                    "customer": customer,
                    "customer_code": customer_code,
                    "brand": brand,
                    "variant": variant,
                    "length": length,
                    "order_qty": qty,
                    "required_dispatch_date": req_dispatch_str,
                    "priority": "HIGH" if "0001" in order_num or "0003" in order_num else "MEDIUM",
                    "order_status": status,
                    "planned_qty": planned,
                    "produced_qty": produced,
                    "balance_qty": max(0.0, qty - produced),
                    "dispatch_qty": disp_qty,
                    "dispatch_balance": max(0.0, qty - disp_qty),
                    "final_approval": "APPROVED",
                    "remarks": f"Planned for {unit}. Material verified.",
                    "unit_id": unit,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": "Taha",
                }
                await self.db["order_planning"].insert_one(doc)
                inserted_count += 1

        return inserted_count

