import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from app.database.mongodb import mongodb_manager
from app.api.deps import require_permission

from datetime import datetime, timezone

logger = logging.getLogger("app.api.v1.audit")
router = APIRouter(prefix="/audit", tags=["Security Audit History"])

@router.get(
    "",
    summary="List Security Audit Events",
    dependencies=[Depends(require_permission("audit", "read"))]
)
async def list_audit_logs() -> List[Dict[str, Any]]:
    """
    Returns security events, logins, logouts, and administrative updates.
    """
    db = mongodb_manager.get_database()
    cursor = db["audit_logs"].find({}).sort("timestamp", -1).limit(100)
    logs = await cursor.to_list(length=100)

    for log in logs:
        log["id"] = str(log.pop("_id"))
        if "timestamp" in log:
            ts = log["timestamp"]
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                log["timestamp"] = ts.isoformat().replace("+00:00", "Z")
            elif isinstance(ts, str):
                if not ts.endswith("Z") and not ("+" in ts or "-" in ts[-6:]):
                    log["timestamp"] = ts + "Z"
                else:
                    log["timestamp"] = ts

    return logs
