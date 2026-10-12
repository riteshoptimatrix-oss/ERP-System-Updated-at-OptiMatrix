import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.repositories.base import BaseRepository

class MasterRepository(BaseRepository):
    """
    Dedicated MongoDB repository for Master Data entities.
    Provides:
    - Unique code enforcement / duplicate prevention
    - Dynamic text search (regex case-insensitive across code and name)
    - Pagination, sorting, and unit scoping
    - Full audit history stamping (created_by, created_at, updated_by, updated_at)
    """

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        super().__init__(db, collection_name)

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find a record by exact unique code (case-insensitive)."""
        pattern = re.compile(f"^{re.escape(code.strip())}$", re.IGNORECASE)
        return await self.collection.find_one({"code": pattern})

    async def list_paginated(
        self,
        search: Optional[str] = None,
        unit_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        department: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query records with search filtering, facility scoping, pagination and sorting.
        """
        filter_query: Dict[str, Any] = {}

        # Unit isolation: include records matching unit_id OR common/BOTH
        if unit_id and unit_id not in ["ALL", "BOTH"]:
            filter_query["$or"] = [
                {"unit_id": unit_id},
                {"unit_id": "BOTH"},
                {"unit_id": {"$exists": False}},  # For global masters like UoM or Categories
            ]

        # Active status filter
        if is_active is not None:
            filter_query["is_active"] = is_active

        # Category or department specific filters
        if category:
            filter_query["category_id"] = category
        if department:
            filter_query["department"] = department

        # Text search across code, name, and description/designation
        if search and search.strip():
            clean_search = re.escape(search.strip())
            search_regex = {"$regex": clean_search, "$options": "i"}
            search_clause = [
                {"code": search_regex},
                {"name": search_regex},
                {"full_name": search_regex},
            ]
            if "$or" in filter_query:
                filter_query = {"$and": [{"$or": filter_query["$or"]}, {"$or": search_clause}]}
            else:
                filter_query["$or"] = search_clause

        total = await self.collection.count_documents(filter_query)
        skip = (page - 1) * page_size
        cursor = self.collection.find(filter_query).sort(sort_by, sort_order).skip(skip).limit(page_size)
        items = await cursor.to_list(length=page_size)
        return items, total

    async def generate_next_employee_code(self) -> str:
        """
        Automatically generates the next sequential Employee ID e.g. EMP-001, EMP-002, etc.
        """
        cursor = self.collection.find({"code": {"$regex": r"^EMP-\d+$", "$options": "i"}}, {"code": 1})
        highest_num = 0
        async for doc in cursor:
            c = doc.get("code", "")
            match = re.search(r"EMP-(\d+)", c, re.IGNORECASE)
            if match:
                try:
                    num = int(match.group(1))
                    if num > highest_num:
                        highest_num = num
                except ValueError:
                    pass
        next_num = highest_num + 1
        return f"EMP-{next_num:03d}"

    async def create_record(self, data: Dict[str, Any], user_email: str) -> str:
        """
        Insert record with duplicate check, automatic code generation if applicable, and audit metadata.
        """
        raw_code = (data.get("code") or "").strip()
        if (not raw_code or raw_code.upper() == "AUTO") and self.collection_name == "employees":
            code = await self.generate_next_employee_code()
        elif not raw_code:
            raise ValueError("Record code is required.")
        else:
            code = raw_code.upper()

        existing = await self.get_by_code(code)
        if existing:
            raise ValueError(f"Record with code '{code}' already exists.")

        now = datetime.now(timezone.utc)
        record = {
            **data,
            "code": code,
            "created_at": now,
            "created_by": user_email,
            "updated_at": now,
            "updated_by": user_email,
        }

        # Check if user account provisioning was requested for employee or email is provided
        user_id = None
        if self.collection_name == "employees" and data.get("email"):
            emp_email = data["email"].strip().lower()
            password = data.get("user_password") or "admin123"
            confirm_pwd = data.get("confirm_user_password") or password
            must_change = data.get("must_change_password", True)

            if len(password) < 6:
                raise ValueError("Initial password must be at least 6 characters.")
            if confirm_pwd and confirm_pwd != password:
                raise ValueError("Initial password and confirmation do not match.")

            account_type = data.get("account_type") or "EMPLOYEE"

            # Check if user account already exists
            existing_user = await self.db["users"].find_one({"email": emp_email})
            if existing_user:
                user_id = str(existing_user["_id"])
            else:
                from app.core.security import hash_password
                unit = data.get("unit_id") or "Unit_1"
                user_doc = {
                    "email": emp_email,
                    "full_name": data.get("full_name", "").strip(),
                    "hashed_password": hash_password(password),
                    "role": account_type,
                    "account_type": account_type,
                    "department": data.get("department"),
                    "job_role": data.get("designation") or data.get("job_role"),
                    "employee_code": code,
                    "allowed_units": [unit],
                    "is_active": data.get("is_active", True),
                    "must_change_password": bool(must_change),
                    "password_changed_at": None,
                    "password_reset_requested_at": None,
                    "created_at": now,
                    "last_login_at": None,
                }
                user_res = await self.db["users"].insert_one(user_doc)
                user_id = str(user_res.inserted_id)

                # Record audit log for account provisioning
                await self.db["audit_logs"].insert_one({
                    "user_id": str(user_res.inserted_id),
                    "email": user_email,
                    "action": "USER_PROVISION_EMPLOYEE_ACCOUNT",
                    "resource": "users",
                    "timestamp": now,
                    "status": "SUCCESS",
                    "details": {
                        "employee_email": emp_email,
                        "employee_code": code,
                        "initial_password_set": "admin123" if password == "admin123" else "CUSTOM",
                        "must_change_password": bool(must_change)
                    }
                })

        if user_id:
            record["user_id"] = user_id

        # Strip helper fields before inserting
        record.pop("create_user_account", None)
        record.pop("user_password", None)
        record.pop("confirm_user_password", None)
        record.pop("must_change_password", None)

        result = await self.collection.insert_one(record)
        return str(result.inserted_id)

    async def update_record(self, record_id: str, data: Dict[str, Any], user_email: str) -> bool:
        """
        Update record by ID, preventing duplicate code conflicts and adding audit stamp.
        """
        if not ObjectId.is_valid(record_id):
            return False

        existing = await self.collection.find_one({"_id": ObjectId(record_id)})
        if not existing:
            return False

        # If code is being updated, verify uniqueness
        if "code" in data and data["code"]:
            new_code = data["code"].strip().upper()
            if new_code != existing.get("code"):
                conflict = await self.get_by_code(new_code)
                if conflict and str(conflict["_id"]) != record_id:
                    raise ValueError(f"Record with code '{new_code}' already exists.")
                data["code"] = new_code

        now = datetime.now(timezone.utc)
        update_payload = {
            **data,
            "updated_at": now,
            "updated_by": user_email,
        }

        result = await self.collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_payload}
        )
        return result.modified_count > 0 or result.matched_count > 0

    async def delete_record(self, record_id: str, soft_delete: bool = True, user_email: str = "system") -> bool:
        """
        Soft delete (toggle is_active to False) or permanent hard delete.
        """
        if not ObjectId.is_valid(record_id):
            return False

        if soft_delete:
            now = datetime.now(timezone.utc)
            res = await self.collection.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": {"is_active": False, "updated_at": now, "updated_by": user_email}}
            )
            return res.matched_count > 0
        else:
            res = await self.collection.delete_one({"_id": ObjectId(record_id)})
            return res.deleted_count > 0
