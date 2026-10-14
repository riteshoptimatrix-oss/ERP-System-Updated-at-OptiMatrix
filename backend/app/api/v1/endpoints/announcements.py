import logging
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from bson import ObjectId

from app.database.mongodb import mongodb_manager
from app.api.deps import (
    get_current_active_user,
    require_super_admin,
    verify_csrf_token,
)
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    UnreadCountResponse,
    RecipientOption,
    AudienceType,
)

logger = logging.getLogger("app.api.endpoints.announcements")

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def parse_object_id(id_str: str) -> Any:
    return ObjectId(id_str) if ObjectId.is_valid(id_str) else id_str


async def get_user_identifiers(current_user: Dict[str, Any], db: Any) -> Set[str]:
    """
    Collects all candidate identifiers for the authenticated user
    (User ObjectId string, email, employee_code, linked Employee ObjectId string, linked code).
    """
    identifiers: Set[str] = set()
    user_id_str = str(current_user["_id"])
    identifiers.add(user_id_str)

    email = current_user.get("email")
    if email:
        identifiers.add(email.strip().lower())

    emp_code = current_user.get("employee_code")
    if emp_code:
        identifiers.add(emp_code.strip())

    # Resolve linked employee record
    query: List[Dict[str, Any]] = []
    if emp_code:
        query.append({"code": emp_code})
    if email:
        query.append({"email": email})

    if query:
        emp_doc = await db["employees"].find_one({"$or": query})
        if emp_doc:
            identifiers.add(str(emp_doc["_id"]))
            if emp_doc.get("code"):
                identifiers.add(emp_doc["code"].strip())
            if emp_doc.get("email"):
                identifiers.add(emp_doc["email"].strip().lower())

    return identifiers


async def build_audience_query(current_user: Dict[str, Any], db: Any) -> Dict[str, Any]:
    """
    Builds MongoDB query criteria matching announcements meant for the current user.
    - Super Admin sees all non-deleted announcements.
    - Other roles see announcements targeted to @All (with sensible joining date threshold)
      or specifically targeted to them.
    """
    base_query: Dict[str, Any] = {"is_deleted": {"$ne": True}}

    if current_user.get("role") == "SUPER_ADMIN":
        return base_query

    identifiers = await get_user_identifiers(current_user, db)
    department = current_user.get("department")
    role = current_user.get("role")

    or_clauses: List[Dict[str, Any]] = []

    # 1. Targeted specifically to this user
    or_clauses.append({
        "audience_type": AudienceType.SPECIFIC.value,
        "recipients": {"$in": list(identifiers)},
    })

    # 2. Targeted to user's department or role
    if department:
        or_clauses.append({
            "audience_type": AudienceType.DEPARTMENT.value,
            "recipients": {"$in": [department, department.upper(), department.lower()]},
        })
    if role:
        or_clauses.append({
            "audience_type": AudienceType.ROLE.value,
            "recipients": {"$in": [role, role.upper(), role.lower()]},
        })

    # 3. Broadcast to @All
    # Edge case: for new employees joining later, show all active @All broadcasts posted
    # after their joining/account creation date (or all active if no date set).
    # We include a 3-day grace margin so newly onboarded employees see immediate recent notices.
    join_ref = current_user.get("created_at")
    if join_ref:
        if join_ref.tzinfo is None:
            join_ref = join_ref.replace(tzinfo=timezone.utc)
        earliest_broadcast = join_ref - timedelta(days=3)
        or_clauses.append({
            "audience_type": {"$in": [AudienceType.ALL.value, "ALL", "all"]},
            "published_at": {"$gte": earliest_broadcast},
        })
    else:
        or_clauses.append({
            "audience_type": {"$in": [AudienceType.ALL.value, "ALL", "all"]},
        })

    base_query["$or"] = or_clauses
    return base_query


# --------------------------------------------------------------------------
# GET /announcements (List for logged-in user)
# --------------------------------------------------------------------------
@router.get("", response_model=List[AnnouncementResponse])
async def list_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    audience_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    unit_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Lists announcements visible to the logged-in user.
    - Super Admin sees all active announcements with read counts.
    - Other roles see announcements intended for them (@All or specific).
    - Includes is_read and read_at status per user.
    """
    db = mongodb_manager.get_database()
    query = await build_audience_query(current_user, db)

    if audience_type:
        query["audience_type"] = audience_type.lower()
    if priority:
        query["priority"] = priority.upper()
    if unit_id and unit_id != "BOTH":
        query["unit_id"] = {"$in": [unit_id, "BOTH"]}

    if search and search.strip():
        term = search.strip()
        query["$and"] = query.get("$and", []) + [{
            "$or": [
                {"title": {"$regex": term, "$options": "i"}},
                {"message": {"$regex": term, "$options": "i"}},
                {"content": {"$regex": term, "$options": "i"}},
                {"author_name": {"$regex": term, "$options": "i"}},
            ]
        }]

    cursor = db["announcements"].find(query).sort("published_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)

    if not items:
        return []

    # Retrieve read status for current user
    user_id_str = str(current_user["_id"])
    item_ids = [str(it["_id"]) for it in items]

    reads = await db["announcement_reads"].find({
        "user_id": user_id_str,
        "announcement_id": {"$in": item_ids},
    }).to_list(length=len(item_ids))
    read_map = {r["announcement_id"]: r["read_at"] for r in reads}

    # If Super Admin, fetch total read count per announcement
    read_counts: Dict[str, int] = {}
    if current_user.get("role") == "SUPER_ADMIN":
        pipeline = [
            {"$match": {"announcement_id": {"$in": item_ids}}},
            {"$group": {"_id": "$announcement_id", "total": {"$sum": 1}}},
        ]
        agg_cursor = db["announcement_reads"].aggregate(pipeline)
        async for row in agg_cursor:
            read_counts[str(row["_id"])] = row["total"]

    results: List[AnnouncementResponse] = []
    for it in items:
        aid = str(it["_id"])
        msg = it.get("message") or it.get("content", "")
        results.append(
            AnnouncementResponse(
                id=aid,
                title=it.get("title", ""),
                message=msg,
                content=msg,
                priority=it.get("priority", "NORMAL"),
                unit_id=it.get("unit_id", "BOTH"),
                audience_type=it.get("audience_type", "all"),
                recipients=it.get("recipients", []),
                recipient_names=it.get("recipient_names", []),
                author_id=it.get("author_id"),
                author_name=it.get("author_name", "Management"),
                author_role=it.get("author_role", "SUPER_ADMIN"),
                is_read=(aid in read_map),
                read_at=read_map.get(aid),
                read_count=read_counts.get(aid, 0),
                created_at=it.get("created_at", datetime.now(timezone.utc)),
                published_at=it.get("published_at", datetime.now(timezone.utc)),
                updated_at=it.get("updated_at"),
                expires_at=it.get("expires_at"),
            )
        )
    return results


# --------------------------------------------------------------------------
# GET /announcements/unread-count (Unread notification badge count)
# --------------------------------------------------------------------------
@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_announcements_count(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Returns unread announcements count for the logged-in user.
    Counts only active, non-deleted announcements targeted to the user that
    have not yet been marked as read.
    """
    db = mongodb_manager.get_database()
    query = await build_audience_query(current_user, db)

    # Exclude expired announcements
    now = datetime.now(timezone.utc)
    query["$and"] = query.get("$and", []) + [{
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gte": now}},
        ]
    }]

    eligible_ids = await db["announcements"].distinct("_id", query)
    if not eligible_ids:
        return UnreadCountResponse(unread_count=0)

    eligible_id_strs = [str(x) for x in eligible_ids]
    user_id_str = str(current_user["_id"])

    read_count = await db["announcement_reads"].count_documents({
        "user_id": user_id_str,
        "announcement_id": {"$in": eligible_id_strs},
    })

    unread = len(eligible_id_strs) - read_count
    return UnreadCountResponse(unread_count=max(0, unread))


# --------------------------------------------------------------------------
# GET /announcements/recipients (Candidate employees for targeting)
# --------------------------------------------------------------------------
@router.get("/recipients", response_model=List[RecipientOption])
async def list_announcement_recipients(
    current_user: Dict[str, Any] = Depends(require_super_admin),
):
    """
    Returns active employees and users for Super Admin targeting dropdown.
    Strictly restricted to Super Admin.
    """
    db = mongodb_manager.get_database()
    options: List[RecipientOption] = []
    seen_ids: Set[str] = set()

    # 1. From Employees collection
    emp_cursor = db["employees"].find({"is_active": True}).sort("full_name", 1)
    async for emp in emp_cursor:
        eid = str(emp["_id"])
        code = emp.get("code", "")
        name = emp.get("full_name") or emp.get("name") or code or "Employee"
        email = emp.get("email", "")
        if eid not in seen_ids:
            seen_ids.add(eid)
            options.append(
                RecipientOption(
                    id=eid,
                    code=code,
                    name=name,
                    email=email,
                    department=emp.get("department", "General"),
                    role=emp.get("designation") or emp.get("job_role") or emp.get("role", "EMPLOYEE"),
                    unit_id=emp.get("unit_id", "BOTH"),
                )
            )

    # 2. From Users collection (in case users exist without employee docs)
    user_cursor = db["users"].find({"is_active": True}).sort("full_name", 1)
    async for u in user_cursor:
        uid = str(u["_id"])
        u_email = u.get("email", "")
        # Avoid duplicate entries matching existing employee emails
        if any(opt.email.lower() == u_email.lower() for opt in options if opt.email):
            continue
        if uid not in seen_ids:
            seen_ids.add(uid)
            options.append(
                RecipientOption(
                    id=uid,
                    code=u.get("employee_code") or u.get("username", "USER"),
                    name=u.get("full_name") or u_email or "User",
                    email=u_email,
                    department=u.get("department", "Operations"),
                    role=u.get("role", "EMPLOYEE"),
                    unit_id="BOTH",
                )
            )

    return options


# --------------------------------------------------------------------------
# POST /announcements (Create - Super Admin ONLY)
# --------------------------------------------------------------------------
@router.post(
    "",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_token)],
)
async def create_announcement(
    payload: AnnouncementCreate,
    current_user: Dict[str, Any] = Depends(require_super_admin),
):
    """
    Creates a new company announcement. Strictly restricted to Super Admin.
    Enforces audience validation: if 'specific', at least one recipient is required.
    """
    db = mongodb_manager.get_database()
    now = datetime.now(timezone.utc)

    title = payload.title.strip()
    message = (payload.message or payload.content or "").strip()

    if len(title) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title must be at least 3 characters long.",
        )
    if len(message) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content must be at least 5 characters long.",
        )

    # Validate audience
    audience_type = payload.audience_type.value
    recipients = [r.strip() for r in payload.recipients if r and r.strip()]

    if audience_type == AudienceType.SPECIFIC.value and not recipients:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one recipient must be selected when audience type is specific.",
        )

    # Resolve recipient human-readable names if not supplied
    recipient_names = payload.recipient_names or []
    if audience_type == AudienceType.SPECIFIC.value and not recipient_names:
        resolved_names: List[str] = []
        # Search employees and users matching recipient identifiers
        matched_emps = await db["employees"].find({
            "$or": [
                {"_id": {"$in": [parse_object_id(r) for r in recipients]}},
                {"code": {"$in": recipients}},
                {"email": {"$in": recipients}},
            ]
        }).to_list(length=100)
        for emp in matched_emps:
            resolved_names.append(f"{emp.get('name', 'Employee')} ({emp.get('code', '')})")

        matched_users = await db["users"].find({
            "$or": [
                {"_id": {"$in": [parse_object_id(r) for r in recipients]}},
                {"employee_code": {"$in": recipients}},
                {"email": {"$in": recipients}},
            ]
        }).to_list(length=100)
        for u in matched_users:
            uname = f"{u.get('full_name', 'User')} ({u.get('employee_code') or u.get('email', '')})"
            if uname not in resolved_names:
                resolved_names.append(uname)

        recipient_names = resolved_names if resolved_names else recipients

    doc: Dict[str, Any] = {
        "title": title,
        "message": message,
        "content": message,
        "priority": payload.priority.value,
        "unit_id": payload.unit_id,
        "audience_type": audience_type,
        "recipients": recipients,
        "recipient_names": recipient_names,
        "author_id": str(current_user["_id"]),
        "author_name": current_user.get("full_name", "Super Admin"),
        "author_role": current_user.get("role", "SUPER_ADMIN"),
        "is_deleted": False,
        "created_at": now,
        "published_at": now,
        "updated_at": None,
        "expires_at": payload.expires_at,
    }

    res = await db["announcements"].insert_one(doc)
    doc["_id"] = res.inserted_id

    # Audit Log
    try:
        await db["audit_logs"].insert_one({
            "action": "ANNOUNCEMENT_CREATED",
            "performed_by": current_user.get("email"),
            "performed_by_role": current_user.get("role"),
            "announcement_id": str(res.inserted_id),
            "title": title,
            "audience_type": audience_type,
            "recipient_count": len(recipients),
            "timestamp": now,
        })
    except Exception as e:
        logger.warning(f"Failed to write audit log for announcement creation: {e}")

    logger.info(f"Announcement created: '{title}' by {current_user.get('email')} (Audience: {audience_type})")

    return AnnouncementResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        message=doc["message"],
        content=doc["content"],
        priority=doc["priority"],
        unit_id=doc["unit_id"],
        audience_type=doc["audience_type"],
        recipients=doc["recipients"],
        recipient_names=doc["recipient_names"],
        author_id=doc["author_id"],
        author_name=doc["author_name"],
        author_role=doc["author_role"],
        is_read=True,  # Author has seen their own creation
        read_at=now,
        read_count=0,
        created_at=doc["created_at"],
        published_at=doc["published_at"],
        updated_at=doc["updated_at"],
        expires_at=doc["expires_at"],
    )


# --------------------------------------------------------------------------
# PATCH /announcements/{id}/read (Mark single as read)
# --------------------------------------------------------------------------
@router.patch("/{announcement_id}/read", response_model=Dict[str, Any])
async def mark_announcement_as_read(
    announcement_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Marks a single announcement as read for the logged-in user.
    Prevents duplicate entries via unique upsert in announcement_reads.
    """
    db = mongodb_manager.get_database()
    query = {"_id": parse_object_id(announcement_id), "is_deleted": {"$ne": True}}

    doc = await db["announcements"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found or has been deleted.",
        )

    now = datetime.now(timezone.utc)
    aid = str(doc["_id"])
    uid = str(current_user["_id"])

    # Atomic upsert preventing duplicates
    await db["announcement_reads"].update_one(
        {"announcement_id": aid, "user_id": uid},
        {"$setOnInsert": {"read_at": now}},
        upsert=True,
    )

    return {
        "message": "Announcement marked as read.",
        "id": aid,
        "is_read": True,
        "read_at": now.isoformat(),
    }


# --------------------------------------------------------------------------
# PATCH /announcements/read-all (Mark all eligible as read)
# --------------------------------------------------------------------------
@router.patch("/read-all", response_model=Dict[str, Any])
async def mark_all_announcements_as_read(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Marks all visible announcements as read for the authenticated user.
    Decreases unread badge count to 0 immediately.
    """
    db = mongodb_manager.get_database()
    query = await build_audience_query(current_user, db)

    eligible_ids = await db["announcements"].distinct("_id", query)
    if not eligible_ids:
        return {"message": "No announcements to mark as read.", "modified_count": 0}

    now = datetime.now(timezone.utc)
    uid = str(current_user["_id"])
    eligible_id_strs = [str(x) for x in eligible_ids]

    # Find already read IDs
    already_read = await db["announcement_reads"].distinct("announcement_id", {
        "user_id": uid,
        "announcement_id": {"$in": eligible_id_strs},
    })
    already_read_set = set(already_read)

    unread_ids = [aid for aid in eligible_id_strs if aid not in already_read_set]
    if unread_ids:
        docs_to_insert = [
            {"announcement_id": aid, "user_id": uid, "read_at": now}
            for aid in unread_ids
        ]
        # Insert without failing on any duplicates
        for item in docs_to_insert:
            await db["announcement_reads"].update_one(
                {"announcement_id": item["announcement_id"], "user_id": item["user_id"]},
                {"$setOnInsert": {"read_at": now}},
                upsert=True,
            )

    return {
        "message": "All announcements marked as read.",
        "modified_count": len(unread_ids),
    }


# --------------------------------------------------------------------------
# PUT /announcements/{id} (Edit - Super Admin ONLY)
# --------------------------------------------------------------------------
@router.put(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    dependencies=[Depends(verify_csrf_token)],
)
async def update_announcement(
    announcement_id: str = Path(...),
    payload: AnnouncementUpdate = ...,
    current_user: Dict[str, Any] = Depends(require_super_admin),
):
    """
    Edits an existing announcement. Strictly restricted to Super Admin.
    """
    db = mongodb_manager.get_database()
    query = {"_id": parse_object_id(announcement_id), "is_deleted": {"$ne": True}}

    doc = await db["announcements"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found or has been deleted.",
        )

    now = datetime.now(timezone.utc)
    update_data: Dict[str, Any] = {"updated_at": now}

    if payload.title is not None:
        title = payload.title.strip()
        if len(title) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Title must be at least 3 characters long.",
            )
        update_data["title"] = title

    msg = payload.message or payload.content
    if msg is not None:
        msg = msg.strip()
        if len(msg) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content must be at least 5 characters long.",
            )
        update_data["message"] = msg
        update_data["content"] = msg

    if payload.priority is not None:
        update_data["priority"] = payload.priority.value
    if payload.unit_id is not None:
        update_data["unit_id"] = payload.unit_id

    if payload.audience_type is not None:
        aud_type = payload.audience_type.value
        update_data["audience_type"] = aud_type
        if aud_type == AudienceType.SPECIFIC.value:
            recips = payload.recipients if payload.recipients is not None else doc.get("recipients", [])
            if not recips:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="At least one recipient must be selected when audience type is specific.",
                )
            update_data["recipients"] = [r.strip() for r in recips if r.strip()]

    if payload.recipients is not None:
        update_data["recipients"] = [r.strip() for r in payload.recipients if r.strip()]
        if update_data.get("audience_type", doc.get("audience_type")) == AudienceType.SPECIFIC.value and not update_data["recipients"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one recipient must be selected when audience type is specific.",
            )

    if payload.recipient_names is not None:
        update_data["recipient_names"] = payload.recipient_names
    if payload.expires_at is not None:
        update_data["expires_at"] = payload.expires_at

    await db["announcements"].update_one({"_id": doc["_id"]}, {"$set": update_data})
    updated_doc = await db["announcements"].find_one({"_id": doc["_id"]})

    # Audit log
    try:
        await db["audit_logs"].insert_one({
            "action": "ANNOUNCEMENT_UPDATED",
            "performed_by": current_user.get("email"),
            "performed_by_role": current_user.get("role"),
            "announcement_id": str(doc["_id"]),
            "timestamp": now,
        })
    except Exception as e:
        logger.warning(f"Failed to write audit log for announcement update: {e}")

    aid = str(updated_doc["_id"])
    read_count = await db["announcement_reads"].count_documents({"announcement_id": aid})

    return AnnouncementResponse(
        id=aid,
        title=updated_doc.get("title", ""),
        message=updated_doc.get("message") or updated_doc.get("content", ""),
        content=updated_doc.get("content") or updated_doc.get("message", ""),
        priority=updated_doc.get("priority", "NORMAL"),
        unit_id=updated_doc.get("unit_id", "BOTH"),
        audience_type=updated_doc.get("audience_type", "all"),
        recipients=updated_doc.get("recipients", []),
        recipient_names=updated_doc.get("recipient_names", []),
        author_id=updated_doc.get("author_id"),
        author_name=updated_doc.get("author_name", "Management"),
        author_role=updated_doc.get("author_role", "SUPER_ADMIN"),
        is_read=True,
        read_at=now,
        read_count=read_count,
        created_at=updated_doc.get("created_at", now),
        published_at=updated_doc.get("published_at", now),
        updated_at=updated_doc.get("updated_at"),
        expires_at=updated_doc.get("expires_at"),
    )


# --------------------------------------------------------------------------
# DELETE /announcements/{id} (Delete - Super Admin ONLY)
# --------------------------------------------------------------------------
@router.delete(
    "/{announcement_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(verify_csrf_token)],
)
async def delete_announcement(
    announcement_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(require_super_admin),
):
    """
    Deletes an announcement (soft delete). Strictly restricted to Super Admin.
    Removes announcement from unread counts and visible queries.
    """
    db = mongodb_manager.get_database()
    query = {"_id": parse_object_id(announcement_id), "is_deleted": {"$ne": True}}

    doc = await db["announcements"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found or has already been deleted.",
        )

    now = datetime.now(timezone.utc)
    aid = str(doc["_id"])

    # Soft delete to preserve audit trail
    await db["announcements"].update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "deleted_at": now}},
    )

    # Clean up reads associated with this deleted announcement
    await db["announcement_reads"].delete_many({"announcement_id": aid})

    # Audit log
    try:
        await db["audit_logs"].insert_one({
            "action": "ANNOUNCEMENT_DELETED",
            "performed_by": current_user.get("email"),
            "performed_by_role": current_user.get("role"),
            "announcement_id": aid,
            "title": doc.get("title"),
            "timestamp": now,
        })
    except Exception as e:
        logger.warning(f"Failed to write audit log for announcement deletion: {e}")

    logger.info(f"Announcement '{doc.get('title')}' ({aid}) deleted by {current_user.get('email')}")

    return {
        "message": "Announcement deleted successfully.",
        "id": aid,
        "deleted": True,
    }
