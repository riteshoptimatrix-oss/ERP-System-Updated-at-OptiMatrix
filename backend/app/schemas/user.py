from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import RoleName, ManufacturingUnit, AccountType


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=1, description="Corporate email address or username")
    password: str = Field(..., min_length=4, description="Password")


class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Corporate email address")
    full_name: str = Field(..., min_length=2, description="Employee full name")
    password: str = Field(..., min_length=12, description="Initial password (minimum 12 characters)")
    confirm_password: Optional[str] = Field(None, min_length=12, description="Confirm initial password")
    role: RoleName = Field(..., description="Assigned role / account category")
    account_type: Optional[AccountType] = Field(None, description="Super Admin (Owner), Admin, HR, Employee")
    department: Optional[str] = Field(None, description="Manufacturing department")
    job_role: Optional[str] = Field(None, description="Employee primary job role")
    job_roles: Optional[List[str]] = Field(default_factory=list, description="List of assigned job roles")
    employee_code: Optional[str] = Field(None, description="Employee ID code (e.g. EMP-001)")
    allowed_units: List[ManufacturingUnit] = Field(
        default=[ManufacturingUnit.BOTH],
        description="Assigned manufacturing plants (Unit_1, Unit_2, or BOTH)"
    )
    must_change_password: bool = Field(
        default=True,
        description="Require password change on first login"
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=12, description="New password (minimum 12 characters)")
    confirm_password: str = Field(..., min_length=12, description="Confirmation of new password")


class ResetPasswordRequest(BaseModel):
    user_id: str = Field(..., description="Target employee user ID to reset")
    new_password: str = Field(..., min_length=12, description="New initial password (minimum 12 characters)")
    confirm_password: Optional[str] = Field(None, min_length=12, description="Confirm new password")
    must_change_password: bool = Field(
        default=True,
        description="Require password change on next login"
    )


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[RoleName] = None
    account_type: Optional[AccountType] = None
    department: Optional[str] = None
    job_role: Optional[str] = None
    job_roles: Optional[List[str]] = None
    employee_code: Optional[str] = None
    allowed_units: Optional[List[ManufacturingUnit]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=12)
    must_change_password: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: RoleName
    account_type: Optional[str] = None
    department: Optional[str] = None
    job_role: Optional[str] = None
    job_roles: Optional[List[str]] = Field(default_factory=list)
    employee_code: Optional[str] = None
    allowed_units: List[ManufacturingUnit]
    is_active: bool
    must_change_password: bool = False
    password_changed_at: Optional[datetime] = None
    password_reset_requested_at: Optional[datetime] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserWithPermissionsResponse(UserResponse):
    permissions: List[str]


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserWithPermissionsResponse] = None
    csrf_token: Optional[str] = None
