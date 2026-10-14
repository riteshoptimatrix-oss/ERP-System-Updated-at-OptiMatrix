import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from bson import ObjectId
from app.core.config import settings
from app.core.security import hash_token
from app.database.mongodb import mongodb_manager
from app.models.user import (
    RoleName,
    ManufacturingUnit,
    DEFAULT_ROLE_PERMISSIONS,
    ActionType,
    resolve_user_permissions,
)

logger = logging.getLogger("app.api.deps")

async def get_current_user_and_session(request: Request) -> Dict[str, Any]:
    """
    Extracts session cookie from request, checks SHA-256 hash in MongoDB,
    verifies validity, idle timeout, expiration, and user active status.
    Raises 401 if missing, invalid, expired, or revoked.
    """
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. No active session cookie found."
        )

    token_hash = hash_token(session_token)
    db = mongodb_manager.get_database()

    # Find active session
    session_doc = await db["sessions"].find_one({
        "token_hash": token_hash,
        "is_revoked": False
    })

    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or has been revoked."
        )

    now = datetime.now(timezone.utc)
    expires_at = session_doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # 1. Absolute Expiration Check
    if now > expires_at:
        await db["sessions"].update_one(
            {"_id": session_doc["_id"]},
            {"$set": {"is_revoked": True}}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again."
        )

    # 2. Idle Timeout Check
    last_activity = session_doc.get("last_activity_at", session_doc["created_at"])
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    if (now - last_activity).total_seconds() > settings.SESSION_IDLE_TIMEOUT_SECONDS:
        await db["sessions"].update_one(
            {"_id": session_doc["_id"]},
            {"$set": {"is_revoked": True}}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session timed out due to inactivity."
        )

    # 3. Retrieve User
    user_id = session_doc["user_id"]
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session user ID.")

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found.")

    if not user.get("is_active", False):
        # Auto-revoke all active sessions if user was deactivated
        await db["sessions"].update_many(
            {"user_id": user_id},
            {"$set": {"is_revoked": True}}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact system administrator."
        )

    # Update session's last activity timestamp (rolling activity window)
    await db["sessions"].update_one(
        {"_id": session_doc["_id"]},
        {"$set": {"last_activity_at": now}}
    )

    # Resolve active permissions from role doc + multi job roles union
    role = user.get("role", RoleName.EMPLOYEE.value)
    role_doc = await db["roles"].find_one({"name": role})
    permissions = resolve_user_permissions(user, role_doc)

    user["permissions"] = permissions
    user["session"] = session_doc
    return user


async def get_current_active_user(user: Dict[str, Any] = Depends(get_current_user_and_session)) -> Dict[str, Any]:
    """
    Standard dependency returning authenticated active user.
    Centralized security enforcement: if must_change_password is true,
    blocks all protected ERP module requests with HTTP 403 Forbidden
    until the user successfully completes the first-login password change.
    """
    if user.get("must_change_password", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required on first login before accessing ERP resources.",
            headers={"X-Error-Code": "PASSWORD_CHANGE_REQUIRED"}
        )
    return user


def require_permission(module: Any, action: Any):
    """
    Dependency factory to check if the user has the required permission: 'module:action'.
    Super Admin has full access across all modules and actions.
    """
    async def permission_checker(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        module_val = module.value if hasattr(module, "value") else str(module)
        action_val = action.value if hasattr(action, "value") else str(action)
        required_perm = f"{module_val}:{action_val}"
        user_perms = user.get("permissions") or []
        user_role = user.get("role")

        # Super Admin has full unrestricted access across all features
        if user_role == RoleName.SUPER_ADMIN.value:
            return user

        if required_perm not in user_perms:
            logger.warning(
                f"Unauthorized permission attempt by {user.get('email')}: requires {required_perm}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: action '{action_val}' on module '{module_val}' is not permitted."
            )
        return user

    return permission_checker


def require_super_admin(user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
    """
    Dependency that restricts endpoint access strictly to Super Admin.
    Any other role (HR, Production Manager, Inventory Manager, Employee, etc.)
    receives an immediate HTTP 403 Forbidden.
    """
    user_role = user.get("role")
    if user_role != RoleName.SUPER_ADMIN.value:
        logger.warning(
            f"Forbidden access attempt to Super Admin restricted endpoint by user '{user.get('email')}' (Role: {user_role})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: this action is exclusively restricted to the Super Admin."
        )
    return user


def require_unit_access(unit_param_name: str = "unit_id"):
    """
    Dependency factory to enforce facility boundaries:
    Ensures user cannot access data from Unit 1 if only assigned to Unit 2, or vice versa.
    Users assigned to 'BOTH' can access both units.
    """
    async def unit_checker(request: Request, user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        allowed_units = user.get("allowed_units", [])
        allowed_units_upper = [str(u).strip().upper() for u in allowed_units]
        if ManufacturingUnit.BOTH.value in allowed_units or "BOTH" in allowed_units_upper:
            return user

        # Extract unit_id from query params or path params
        requested_unit = request.query_params.get(unit_param_name) or request.path_params.get(unit_param_name)
        if not requested_unit:
            return user

        requested_unit_upper = requested_unit.strip().upper()
        if requested_unit_upper not in allowed_units_upper:
            logger.warning(
                f"Cross-unit access violation by {user.get('email')}: tried to access {requested_unit} with access only to {allowed_units}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: you are not authorized to view or modify operations for unit '{requested_unit}'."
            )
        return user

    return unit_checker


async def verify_csrf_token(request: Request) -> None:
    """
    Validates CSRF token on state-changing HTTP requests (POST, PUT, PATCH, DELETE).
    Uses double-submit cookie validation: Header X-CSRF-Token must match cookie RG_csrf.
    """
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return

    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)

    if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
        logger.warning("CSRF validation failed for request")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed. Please refresh your browser."
        )
