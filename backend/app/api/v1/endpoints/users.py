import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from app.database.mongodb import mongodb_manager
from app.models.user import (
    RoleName,
    ManufacturingUnit,
    AccountType,
    DEPARTMENT_JOB_ROLES,
    JOB_ROLE_DEFAULT_PERMISSIONS,
)
from app.schemas.user import UserCreateRequest, UserUpdateRequest, UserResponse
from app.core.security import hash_password
from app.api.deps import require_permission, get_current_active_user, verify_csrf_token

logger = logging.getLogger("app.api.v1.users")
router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/meta/departments-roles",
    summary="Get Account Types, Departments and Job Roles Metadata",
    dependencies=[Depends(require_permission("users", "read"))]
)
async def get_departments_and_roles_metadata():
    """
    Returns the 4 ERP Account Types and the 8 manufacturing departments with their respective job roles.
    """
    return {
        "account_types": [
            {
                "type": AccountType.SUPER_ADMIN.value,
                "label": "Super Admin (Owner)",
                "access": "Full access to all features",
                "assignable": True,
            },
            {
                "type": AccountType.ADMIN.value,
                "label": "Admin",
                "access": "Assigned administrative permissions",
                "assignable": True,
            },
            {
                "type": AccountType.HR.value,
                "label": "HR",
                "access": "Assigned HR permissions",
                "assignable": True,
            },
            {
                "type": AccountType.EMPLOYEE.value,
                "label": "Employee",
                "access": "Assigned operational permissions",
                "assignable": True,
            },
        ],
        "departments": [d for d in DEPARTMENT_JOB_ROLES.keys() if d != "Production"],
        "department_roles": DEPARTMENT_JOB_ROLES,
        "job_role_permissions": JOB_ROLE_DEFAULT_PERMISSIONS,
    }


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List ERP Users",
    dependencies=[Depends(require_permission("users", "read"))]
)
async def list_users() -> List[UserResponse]:
    """
    Returns list of all ERP user accounts. Requires 'users:read' permission.
    """
    db = mongodb_manager.get_database()
    cursor = db["users"].find({}).sort("created_at", -1)
    users = await cursor.to_list(length=200)

    result = []
    for u in users:
        j_roles = u.get("job_roles")
        if not j_roles and u.get("job_role"):
            j_roles = [u["job_role"]]
        elif not j_roles:
            j_roles = []

        result.append(
            UserResponse(
                id=str(u["_id"]),
                email=u["email"],
                full_name=u["full_name"],
                role=RoleName(u["role"]),
                account_type=u.get("account_type", u["role"]),
                department=u.get("department"),
                job_role=u.get("job_role"),
                job_roles=j_roles,
                employee_code=u.get("employee_code"),
                allowed_units=[ManufacturingUnit(unit) for unit in u.get("allowed_units", [ManufacturingUnit.BOTH.value])],
                is_active=u.get("is_active", True),
                must_change_password=u.get("must_change_password", False),
                password_changed_at=u.get("password_changed_at"),
                password_reset_requested_at=u.get("password_reset_requested_at"),
                created_at=u["created_at"],
                last_login_at=u.get("last_login_at")
            )
        )
    return result


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New ERP User",
    dependencies=[Depends(require_permission("users", "create")), Depends(verify_csrf_token)]
)
async def create_user(
    payload: UserCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> UserResponse:
    """
    Creates an ERP user account. Self-registration is strictly forbidden;
    only authorized administrators and HR can provision accounts.
    Enforces strict anti-privilege-escalation and role delegation rules.
    """
    current_role = current_user.get("role")

    # 1. Super Admin accounts cannot be provisioned by non-Super-Admins
    if current_role != RoleName.SUPER_ADMIN.value and (payload.role == RoleName.SUPER_ADMIN or payload.account_type == AccountType.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin (Owner) accounts cannot be provisioned via user management."
        )

    # 2. HR can only provision Employee accounts
    if current_role == RoleName.HR.value:
        if payload.role in [RoleName.ADMIN, RoleName.SUPER_ADMIN] or payload.account_type in [AccountType.ADMIN, AccountType.SUPER_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR accounts cannot provision Administrator accounts. Only Employee accounts can be provisioned by HR."
            )

    db = mongodb_manager.get_database()
    clean_email = payload.email.lower().strip()

    existing = await db["users"].find_one({"email": clean_email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user account with this email address already exists."
        )

    if payload.confirm_password and payload.confirm_password != payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial password and confirmation do not match."
        )

    now = datetime.now(timezone.utc)
    account_type_val = payload.account_type.value if payload.account_type else payload.role.value

    # Normalize assigned multi-job roles
    assigned_job_roles: List[str] = []
    if payload.job_roles:
        assigned_job_roles = [r.strip() for r in payload.job_roles if r.strip()]
    if payload.job_role and payload.job_role.strip() not in assigned_job_roles:
        assigned_job_roles.append(payload.job_role.strip())
    primary_job_role = payload.job_role.strip() if payload.job_role else (assigned_job_roles[0] if assigned_job_roles else None)

    new_user = {
        "email": clean_email,
        "full_name": payload.full_name.strip(),
        "hashed_password": hash_password(payload.password),
        "role": payload.role.value,
        "account_type": account_type_val,
        "department": payload.department.strip() if payload.department else None,
        "job_role": primary_job_role,
        "job_roles": assigned_job_roles,
        "employee_code": payload.employee_code.strip() if payload.employee_code else None,
        "allowed_units": [u.value for u in payload.allowed_units],
        "is_active": True,
        "must_change_password": payload.must_change_password,
        "password_changed_at": None,
        "password_reset_requested_at": None,
        "created_at": now,
        "last_login_at": None,
    }

    result = await db["users"].insert_one(new_user)
    user_id = str(result.inserted_id)

    # If an employee code was provided, link the user account in the employees collection
    if payload.employee_code:
        await db["employees"].update_one(
            {"code": payload.employee_code.strip()},
            {"$set": {"user_id": user_id, "email": clean_email, "job_roles": assigned_job_roles}}
        )

    # Audit log
    await db["audit_logs"].insert_one({
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "action": "USER_CREATE",
        "resource": user_id,
        "timestamp": now,
        "status": "SUCCESS",
        "details": {
            "created_email": clean_email,
            "role": payload.role.value,
            "department": payload.department,
            "job_role": primary_job_role,
            "job_roles": assigned_job_roles,
        }
    })

    return UserResponse(
        id=user_id,
        email=clean_email,
        full_name=payload.full_name.strip(),
        role=payload.role,
        account_type=account_type_val,
        department=payload.department,
        job_role=primary_job_role,
        job_roles=assigned_job_roles,
        employee_code=payload.employee_code,
        allowed_units=payload.allowed_units,
        is_active=True,
        must_change_password=payload.must_change_password,
        password_changed_at=None,
        password_reset_requested_at=None,
        created_at=now,
        last_login_at=None
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update ERP User",
    dependencies=[Depends(require_permission("users", "update")), Depends(verify_csrf_token)]
)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> UserResponse:
    """
    Updates user role, department, job roles, unit assignments, password, or activation status.
    Strictly prevents privilege escalation and protects against final Owner lockout.
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

    db = mongodb_manager.get_database()
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    current_role = current_user.get("role")

    # 1. Protect existing Super Admin (Owner) account
    if user.get("role") == RoleName.SUPER_ADMIN.value:
        if payload.role and payload.role != RoleName.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter Super Admin (Owner) role.")
        if payload.account_type and payload.account_type != AccountType.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter Super Admin (Owner) account type.")
        if payload.is_active is False:
            active_owners = await db["users"].count_documents({
                "role": RoleName.SUPER_ADMIN.value,
                "is_active": True
            })
            if active_owners <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the final active Super Admin (Owner) account. System requires at least one active Owner."
                )
        if current_role not in [RoleName.ADMIN.value, RoleName.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized Administrators or Super Admin can update profile settings for Super Admin."
            )

    # 2. HR Privilege Escalation Prevention
    if current_role == RoleName.HR.value:
        if user.get("role") in [RoleName.ADMIN.value, RoleName.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR accounts cannot modify Administrator or Super Admin accounts."
            )
        if payload.role in [RoleName.ADMIN, RoleName.SUPER_ADMIN] or payload.account_type in [AccountType.ADMIN, AccountType.SUPER_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR accounts cannot escalate user privileges to Administrator or Super Admin."
            )

    # 3. Admin cannot escalate anyone to Super Admin (Owner)
    if current_role == RoleName.ADMIN.value:
        if payload.role == RoleName.SUPER_ADMIN or payload.account_type == AccountType.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot grant Super Admin (Owner) privileges."
            )

    updates: Dict[str, Any] = {}
    if payload.full_name is not None:
        updates["full_name"] = payload.full_name.strip()
    if payload.role is not None:
        updates["role"] = payload.role.value
    if payload.account_type is not None:
        updates["account_type"] = payload.account_type.value
    if payload.department is not None:
        updates["department"] = payload.department.strip() if payload.department else None
    if payload.job_roles is not None:
        assigned_job_roles = [r.strip() for r in payload.job_roles if r.strip()]
        updates["job_roles"] = assigned_job_roles
        if not updates.get("job_role") and assigned_job_roles:
            updates["job_role"] = assigned_job_roles[0]
    if payload.job_role is not None:
        updates["job_role"] = payload.job_role.strip() if payload.job_role else None
        if updates["job_role"]:
            cur_roles = updates.get("job_roles", user.get("job_roles", []))
            if updates["job_role"] not in cur_roles:
                updates["job_roles"] = cur_roles + [updates["job_role"]]
    if payload.employee_code is not None:
        updates["employee_code"] = payload.employee_code.strip() if payload.employee_code else None
    if payload.allowed_units is not None:
        updates["allowed_units"] = [u.value for u in payload.allowed_units]
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
        if not payload.is_active:
            # Revoke all sessions immediately on deactivation
            await db["sessions"].update_many(
                {"user_id": user_id},
                {"$set": {"is_revoked": True}}
            )
        # Also sync employee active status if linked
        if user.get("employee_code"):
            await db["employees"].update_one(
                {"code": user["employee_code"]},
                {"$set": {"is_active": payload.is_active, "status": "ACTIVE" if payload.is_active else "DEACTIVATED"}}
            )
    if payload.password:
        updates["hashed_password"] = hash_password(payload.password)
        updates["must_change_password"] = payload.must_change_password if payload.must_change_password is not None else True
        updates["password_reset_requested_at"] = datetime.now(timezone.utc)
        # Invalidate existing sessions on password change
        await db["sessions"].update_many(
            {"user_id": user_id},
            {"$set": {"is_revoked": True}}
        )
    elif payload.must_change_password is not None:
        updates["must_change_password"] = payload.must_change_password

    if updates:
        await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    updated_user = await db["users"].find_one({"_id": ObjectId(user_id)})

    # Audit log
    await db["audit_logs"].insert_one({
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "action": "USER_UPDATE",
        "resource": user_id,
        "timestamp": datetime.now(timezone.utc),
        "status": "SUCCESS",
        "details": {"updated_fields": list(updates.keys())}
    })

    ret_job_roles = updated_user.get("job_roles")
    if not ret_job_roles and updated_user.get("job_role"):
        ret_job_roles = [updated_user["job_role"]]
    elif not ret_job_roles:
        ret_job_roles = []

    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        full_name=updated_user["full_name"],
        role=RoleName(updated_user["role"]),
        account_type=updated_user.get("account_type", updated_user["role"]),
        department=updated_user.get("department"),
        job_role=updated_user.get("job_role"),
        job_roles=ret_job_roles,
        employee_code=updated_user.get("employee_code"),
        allowed_units=[ManufacturingUnit(u) for u in updated_user.get("allowed_units", [ManufacturingUnit.BOTH.value])],
        is_active=updated_user.get("is_active", True),
        must_change_password=updated_user.get("must_change_password", False),
        password_changed_at=updated_user.get("password_changed_at"),
        password_reset_requested_at=updated_user.get("password_reset_requested_at"),
        created_at=updated_user["created_at"],
        last_login_at=updated_user.get("last_login_at")
    )
