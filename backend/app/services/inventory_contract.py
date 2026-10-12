from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.schemas.orders import StockAvailabilityResult


class InventoryIntegrationContract:
    """
    Explicit integration contract for inventory availability verification.
    Guarantees:
    1. NEVER invents stock balances out of thin air.
    2. NEVER mutates stock balances directly from sales-order or dispatch endpoints.
    3. Safely queries inventory stock collections if configured and populated;
       otherwise gracefully reports UNTRACKED / unverified without generating false data.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.inventory_col = db["inventory_stock"]
        self.finished_products_col = db["finished_products"]

    async def check_availability(
        self,
        product_id: str,
        unit_id: str,
        required_quantity: float,
    ) -> StockAvailabilityResult:
        """
        Check if the finished product has sufficient stock in the specified unit.
        """
        # Resolve product information from finished products master
        product = None
        try:
            if ObjectId.is_valid(product_id):
                product = await self.finished_products_col.find_one({"_id": ObjectId(product_id)})
            if not product:
                product = await self.finished_products_col.find_one({"code": product_id})
        except Exception:
            product = None

        product_code = product.get("code", "UNKNOWN") if product else product_id

        # Check if actual inventory stock ledger exists and has entries
        stock_count = await self.inventory_col.count_documents({})
        if stock_count == 0:
            # Inventory tracking service is not yet initialized with balances
            return StockAvailabilityResult(
                product_id=product_id,
                product_code=product_code,
                unit_id=unit_id,
                required_quantity=required_quantity,
                available_quantity=None,
                is_sufficient=True,
                status="UNTRACKED",
                message=(
                    f"Product {product_code} inventory ledger not yet populated for {unit_id}. "
                    "Passing check under explicit non-invented contract without stock deduction."
                ),
            )

        # Query real inventory balance if tracking is live
        # Product can be matched by item_id or item_code
        query: Dict[str, Any] = {
            "$or": [
                {"item_id": product_id},
                {"item_code": product_code},
            ]
        }
        if unit_id not in ["ALL", "BOTH"]:
            query["unit_id"] = unit_id

        # Aggregate total available quantity across warehouses for this product
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_available": {"$sum": "$quantity_available"},
                    "total_on_hand": {"$sum": "$quantity_on_hand"},
                }
            }
        ]
        agg_res = await self.inventory_col.aggregate(pipeline).to_list(length=1)
        if not agg_res:
            return StockAvailabilityResult(
                product_id=product_id,
                product_code=product_code,
                unit_id=unit_id,
                required_quantity=required_quantity,
                available_quantity=0.0,
                is_sufficient=False,
                status="INSUFFICIENT",
                message=f"Zero stock recorded for product {product_code} at {unit_id}.",
            )

        available_qty = float(agg_res[0].get("total_available", agg_res[0].get("total_on_hand", 0.0)))
        is_sufficient = available_qty >= required_quantity

        return StockAvailabilityResult(
            product_id=product_id,
            product_code=product_code,
            unit_id=unit_id,
            required_quantity=required_quantity,
            available_quantity=round(available_qty, 2),
            is_sufficient=is_sufficient,
            status="VERIFIED" if is_sufficient else "INSUFFICIENT",
            message=(
                f"Stock verified: {available_qty} available vs {required_quantity} required."
                if is_sufficient
                else f"Insufficient stock: only {available_qty} available vs {required_quantity} required."
            ),
        )
