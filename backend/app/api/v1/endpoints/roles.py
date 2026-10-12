import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from app.database.mongodb import mongodb_manager
from app.api.deps import require_permission

logger = logging.getLogger("app.api.v1.roles")
router = APIRouter(prefix="/roles", tags=["Role Management"])

@router.get(
    "",
    summary="List Roles and Permissions Matrix",
    dependencies=[Depends(require_permission("roles", "read"))]
)
async def list_roles() -> List[Dict[str, Any]]:
    """
    Returns configured roles and associated module permission lists.
    """
    db = mongodb_manager.get_database()
    roles = await db["roles"].find({}, {"_id": 0}).to_list(length=100)
    return roles
