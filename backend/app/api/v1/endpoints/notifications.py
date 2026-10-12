from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from app.database.mongodb import mongodb_manager
from app.api.deps import get_current_active_user, verify_csrf_token, require_permission
from app.schemas.notification import NotificationResponse, AnnouncementResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/notifications", tags=["Notifications & Announcements"])


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    content: str = Field(..., min_length=5, max_length=2000)
    priority: str = Field(default="NORMAL", description="LOW, NORMAL, HIGH, URGENT")
    unit_id: str = Field(default="BOTH", description="Unit_1, Unit_2, BOTH")


def serialize_notification(doc: Dict[str, Any]) -> NotificationResponse:
    return NotificationResponse(
        id=str(doc["_id"]),
        user_id=doc.get("user_id"),
        employee_code=doc.get("employee_code"),
        title=doc.get("title", ""),
        message=doc.get("message", ""),
        notification_type=doc.get("notification_type", "INFO"),
        is_read=doc.get("is_read", False),
        link=doc.get("link"),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        read_at=doc.get("read_at"),
        metadata=doc.get("metadata"),
    )


def serialize_announcement(doc: Dict[str, Any]) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        content=doc.get("content", ""),
        priority=doc.get("priority", "NORMAL"),
        unit_id=doc.get("unit_id", "BOTH"),
        author_name=doc.get("author_name", "Management"),
        author_role=doc.get("author_role", "HR"),
        published_at=doc.get("published_at", datetime.now(timezone.utc)),
        expires_at=doc.get("expires_at"),
    )


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Retrieves all notifications for the authenticated user and their employee code.
    """
    db = mongodb_manager.get_database()
    emp_code = current_user.get("employee_code")

    query: Dict[str, Any] = {
        "$or": [
            {"user_id": str(current_user["_id"])},
            {"employee_code": emp_code},
            {"recipient_role": "ALL"},
        ]
    }
    if is_read is not None:
        query["is_read"] = is_read

    cursor = db["notifications"].find(query).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return [serialize_notification(it) for it in items]


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str = Path(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Marks a single notification as read.
    """
    db = mongodb_manager.get_database()
    query = {"_id": ObjectId(notification_id)} if ObjectId.is_valid(notification_id) else {"_id": notification_id}

    doc = await db["notifications"].find_one(query)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    now = datetime.now(timezone.utc)
    await db["notifications"].update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_read": True, "read_at": now}}
    )
    doc["is_read"] = True
    doc["read_at"] = now
    return serialize_notification(doc)


@router.post("/mark-all-read", response_model=Dict[str, Any])
async def mark_all_notifications_read(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Marks all notifications for the authenticated user as read.
    """
    db = mongodb_manager.get_database()
    emp_code = current_user.get("employee_code")
    now = datetime.now(timezone.utc)

    query = {
        "$or": [
            {"user_id": str(current_user["_id"])},
            {"employee_code": emp_code},
            {"recipient_role": "ALL"},
        ],
        "is_read": False,
    }

    res = await db["notifications"].update_many(query, {"$set": {"is_read": True, "read_at": now}})
    return {"message": "All notifications marked as read.", "modified_count": res.modified_count}


@router.get("/announcements", response_model=List[AnnouncementResponse])
async def list_announcements(
    unit_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Lists plant announcements scoped to the requested manufacturing unit and corporate broadcasts.
    """
    db = mongodb_manager.get_database()
    unit = unit_id or current_user.get("allowed_units", ["Unit_1"])[0]

    query: Dict[str, Any] = {
        "unit_id": {"$in": [unit, "BOTH"]},
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gte": datetime.now(timezone.utc)}},
        ]
    }

    cursor = db["announcements"].find(query).sort("published_at", -1).limit(20)
    items = await cursor.to_list(length=20)
    return [serialize_announcement(it) for it in items]


@router.post(
    "/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("hr", "create")), Depends(verify_csrf_token)],
)
async def create_announcement(
    payload: AnnouncementCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    """
    Creates a new plant or corporate announcement. Requires HR or Administrative permission.
    """
    db = mongodb_manager.get_database()
    now = datetime.now(timezone.utc)

    doc = {
        "title": payload.title,
        "content": payload.content,
        "priority": payload.priority,
        "unit_id": payload.unit_id,
        "author_name": current_user.get("full_name", "HR Management"),
        "author_role": current_user.get("role", "HR"),
        "published_at": now,
        "expires_at": None,
    }

    res = await db["announcements"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_announcement(doc)
