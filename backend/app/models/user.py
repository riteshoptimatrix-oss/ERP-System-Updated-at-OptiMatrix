from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RoleName(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    HR = "HR"
    PRODUCTION_MANAGER = "PRODUCTION_MANAGER"
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    QC_INSPECTOR = "QC_INSPECTOR"
    SALES_DISPATCH = "SALES_DISPATCH"
    EMPLOYEE = "EMPLOYEE"


class ActionType(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    APPROVE = "approve"
    POST = "post"
    EXPORT = "export"
    ADMINISTER = "administer"


class ModuleName(str, Enum):
    ORDERS = "orders"
    INVENTORY = "inventory"
    BOM = "bom"
    PRODUCTION = "production"
    QC = "qc"
    WASTAGE = "wastage"
    POWER = "power"
    CRM = "crm"
    HR = "hr"
    PAYROLL = "payroll"
    ATTENDANCE = "attendance"
    SALES = "sales"
    FINANCE = "finance"
    REPORTS = "reports"
    USERS = "users"
    ROLES = "roles"
    AUDIT = "audit"
    MASTER = "master"


class ManufacturingUnit(str, Enum):
    Unit_1 = "Unit_1"
    Unit_2 = "Unit_2"
    BOTH = "BOTH"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_upper = value.strip().upper().replace(" ", "_").replace("-", "_")
            if "1" in val_upper:
                return cls.Unit_1
            if "2" in val_upper:
                return cls.Unit_2
            if "BOTH" in val_upper or "ALL" in val_upper:
                return cls.BOTH
        return cls.BOTH


# Permission string format: "module:action" (e.g. "orders:read", "inventory:update")
class Permission(BaseModel):
    module: ModuleName
    action: ActionType

    def to_string(self) -> str:
        return f"{self.module.value}:{self.action.value}"


# Role definition model
class RoleDefinition(BaseModel):
    name: RoleName
    description: str
    permissions: List[str]  # List of "module:action"


# Default RBAC Matrix definition for Opti Matrix
ALL_MODULES = [m.value for m in ModuleName]
ALL_ACTIONS = [a.value for a in ActionType]

class AccountType(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    HR = "HR"
    EMPLOYEE = "EMPLOYEE"


# 8 Standard Manufacturing Departments and Job Roles
DEPARTMENT_JOB_ROLES = {
    "Production": [
        "Production Manager",
        "Production Supervisor",
        "Machine Operator",
        "Assembly Operator",
        "Production Planner",
        "Shift In-charge",
    ],
    "Production Department": [
        "Production Manager",
        "Production Supervisor",
        "Machine Operator",
        "Assembly Operator",
        "Production Planner",
        "Shift In-charge",
    ],
    "Quality Control": [
        "QC Manager",
        "QC Inspector",
        "QA Engineer",
        "Testing Technician",
        "Wastage Inspector",
    ],
    "Inventory & Purchase": [
        "Inventory Manager",
        "Storekeeper",
        "Warehouse Executive",
        "Purchase Manager",
        "Purchase Executive",
    ],
    "Sales & CRM": [
        "Sales Manager",
        "Sales Executive",
        "CRM Executive",
        "Lead Manager",
        "Customer Relationship Executive",
    ],
    "Dispatch & Logistics": [
        "Dispatch Manager",
        "Dispatch Executive",
        "Packing Operator",
        "Logistics Coordinator",
    ],
    "Billing & Finance": [
        "Billing Manager",
        "Billing Executive",
        "Accountant",
        "Finance Manager",
        "Accounts Executive",
    ],
    "HR & Administration": [
        "HR Manager",
        "HR Executive",
        "Recruiter",
        "Attendance Manager",
        "Payroll Manager",
        "Office Administrator",
    ],
    "Maintenance & Technical": [
        "Maintenance Manager",
        "Maintenance Technician",
        "Electrician",
        "Mechanical Technician",
        "CNC Programmer",
    ],
}

JOB_ROLE_DEFAULT_PERMISSIONS = {
    # Production Department
    "Production Manager": [
        "production:read", "production:create", "production:update", "production:approve", "production:post", "production:export",
        "bom:read", "bom:create", "bom:update",
        "inventory:read", "orders:read",
        "wastage:read", "wastage:create", "wastage:update", "wastage:approve",
        "power:read", "power:create", "power:update",
        "reports:read", "reports:export", "master:read",
    ],
    "Production Supervisor": [
        "production:read", "production:create", "production:update", "production:post",
        "bom:read", "inventory:read", "orders:read",
        "wastage:read", "wastage:create", "wastage:update",
        "power:read", "power:create", "master:read",
    ],
    "Machine Operator": ["production:read", "production:update", "wastage:create", "master:read"],
    "Assembly Operator": ["production:read", "production:update", "wastage:create", "master:read"],
    "Production Planner": [
        "production:read", "production:create", "production:update",
        "bom:read", "orders:read", "inventory:read", "reports:read", "master:read",
    ],
    "Shift In-charge": [
        "production:read", "production:create", "production:update", "production:post",
        "wastage:read", "wastage:create", "power:read", "power:create", "master:read",
    ],

    # Quality Control
    "QC Manager": [
        "qc:read", "qc:create", "qc:update", "qc:approve", "qc:export",
        "production:read", "wastage:read", "wastage:create", "wastage:update", "wastage:approve",
        "reports:read", "reports:export", "master:read",
    ],
    "QC Inspector": [
        "qc:read", "qc:create", "qc:update", "qc:approve",
        "production:read", "wastage:read", "wastage:create", "reports:read", "master:read",
    ],
    "QA Engineer": [
        "qc:read", "qc:create", "qc:update", "production:read", "reports:read", "master:read",
    ],
    "Testing Technician": ["qc:read", "qc:create", "production:read", "master:read"],
    "Wastage Inspector": ["wastage:read", "wastage:create", "wastage:update", "qc:read", "production:read", "master:read"],

    # Inventory & Purchase
    "Inventory Manager": [
        "inventory:read", "inventory:create", "inventory:update", "inventory:post", "inventory:export",
        "bom:read", "orders:read", "wastage:read", "reports:read", "reports:export", "master:read", "master:create", "master:update",
    ],
    "Storekeeper": ["inventory:read", "inventory:update", "inventory:post", "master:read"],
    "Warehouse Executive": ["inventory:read", "inventory:update", "master:read"],
    "Purchase Manager": [
        "inventory:read", "inventory:create", "orders:read", "master:read", "master:create", "master:update", "reports:read",
    ],
    "Purchase Executive": ["inventory:read", "orders:read", "master:read"],

    # Sales & CRM
    "Sales Manager": [
        "orders:read", "orders:create", "orders:update", "orders:export",
        "sales:read", "sales:create", "sales:update", "sales:post", "sales:export",
        "crm:read", "crm:create", "crm:update", "crm:export",
        "inventory:read", "reports:read", "reports:export", "master:read", "master:create", "master:update",
    ],
    "Sales Executive": [
        "orders:read", "orders:create", "orders:update",
        "sales:read", "sales:create", "sales:update",
        "crm:read", "crm:create", "crm:update", "master:read",
    ],
    "CRM Executive": ["crm:read", "crm:create", "crm:update", "orders:read", "master:read", "master:create"],
    "Lead Manager": ["crm:read", "crm:create", "crm:update", "reports:read", "master:read", "master:create"],
    "Customer Relationship Executive": ["crm:read", "crm:create", "crm:update", "orders:read", "master:read", "master:create"],

    # Dispatch & Logistics
    "Dispatch Manager": [
        "orders:read", "orders:update", "sales:read", "sales:create", "sales:update", "sales:post", "sales:export",
        "inventory:read", "reports:read", "reports:export",
    ],
    "Dispatch Executive": ["orders:read", "sales:read", "sales:update", "inventory:read"],
    "Packing Operator": ["orders:read", "sales:read", "sales:update"],
    "Logistics Coordinator": ["orders:read", "sales:read", "sales:update", "reports:read"],

    # Billing & Finance
    "Billing Manager": [
        "finance:read", "finance:create", "finance:update", "finance:approve", "finance:post", "finance:export",
        "orders:read", "sales:read", "crm:read", "master:read", "reports:read", "reports:export",
    ],
    "Billing Executive": [
        "finance:read", "finance:create", "finance:update", "finance:post",
        "orders:read", "sales:read", "crm:read", "master:read", "reports:read",
    ],
    "Accountant": [
        "finance:read", "finance:create", "finance:update", "finance:post",
        "payroll:read", "crm:read", "master:read", "reports:read",
    ],
    "Finance Manager": [
        "finance:read", "finance:create", "finance:update", "finance:approve", "finance:post", "finance:export",
        "payroll:read", "payroll:approve", "crm:read", "master:read", "reports:read", "reports:export",
    ],
    "Accounts Executive": [
        "finance:read", "finance:create", "finance:update", "finance:post",
        "orders:read", "crm:read", "master:read", "reports:read",
    ],

    # HR & Administration
    "HR Manager": [
        "hr:read", "hr:create", "hr:update", "hr:approve", "hr:export",
        "payroll:read", "payroll:create", "payroll:update", "payroll:approve", "payroll:post", "payroll:export",
        "attendance:read", "attendance:create", "attendance:update", "attendance:approve", "attendance:export",
        "users:read", "users:create", "users:update", "master:read", "master:create", "master:update",
        "reports:read", "reports:export",
    ],
    "HR Executive": [
        "hr:read", "hr:create", "hr:update",
        "attendance:read", "attendance:create", "attendance:update",
        "payroll:read", "users:read", "users:create", "master:read", "reports:read",
    ],
    "Recruiter": ["hr:read", "hr:create", "master:read"],
    "Attendance Manager": [
        "attendance:read", "attendance:create", "attendance:update", "attendance:approve", "attendance:export",
        "hr:read", "reports:read",
    ],
    "Payroll Manager": [
        "payroll:read", "payroll:create", "payroll:update", "payroll:approve", "payroll:post", "payroll:export",
        "attendance:read", "hr:read", "reports:read", "reports:export",
    ],
    "Office Administrator": ["hr:read", "attendance:read", "master:read"],

    # Maintenance & Technical
    "Maintenance Manager": [
        "power:read", "power:create", "power:update", "power:approve", "power:export",
        "production:read", "inventory:read", "reports:read",
    ],
    "Maintenance Technician": ["power:read", "power:create", "power:update", "production:read"],
    "Electrician": ["power:read", "power:create", "power:update"],
    "Mechanical Technician": ["power:read", "power:create", "production:read"],
    "CNC Programmer": ["production:read", "bom:read", "power:read"],
}

DEFAULT_ROLE_PERMISSIONS = {
    RoleName.SUPER_ADMIN: [
        f"{m}:{a}" for m in ALL_MODULES for a in ALL_ACTIONS
    ],
    RoleName.ADMIN: [
        f"{m}:{a}" for m in ALL_MODULES for a in ALL_ACTIONS
        if not (m in ["audit", "roles"] and a == "administer")
    ] + ["audit:read", "roles:read"],
    RoleName.HR: [
        "hr:read", "hr:create", "hr:update", "hr:approve", "hr:export",
        "payroll:read", "payroll:create", "payroll:update", "payroll:approve", "payroll:post", "payroll:export",
        "attendance:read", "attendance:create", "attendance:update", "attendance:approve", "attendance:export",
        "users:read", "users:create", "users:update",
        "reports:read", "reports:export",
        "master:read", "master:create", "master:update",
    ],
    RoleName.PRODUCTION_MANAGER: [
        "production:read", "production:create", "production:update", "production:approve", "production:post", "production:export",
        "bom:read", "bom:create", "bom:update",
        "inventory:read",
        "orders:read",
        "wastage:read", "wastage:create", "wastage:update", "wastage:approve",
        "power:read", "power:create", "power:update", "power:approve",
        "reports:read", "reports:export",
        "master:read",
    ],
    RoleName.INVENTORY_MANAGER: [
        "inventory:read", "inventory:create", "inventory:update", "inventory:post", "inventory:export",
        "bom:read",
        "orders:read",
        "wastage:read", "wastage:create", "wastage:update", "wastage:approve",
        "reports:read", "reports:export",
        "master:read", "master:create", "master:update",
    ],
    RoleName.QC_INSPECTOR: [
        "qc:read", "qc:create", "qc:update", "qc:approve", "qc:export",
        "production:read",
        "wastage:read", "wastage:create", "wastage:update",
        "reports:read",
        "master:read",
    ],
    RoleName.SALES_DISPATCH: [
        "orders:read", "orders:create", "orders:update", "orders:export",
        "sales:read", "sales:create", "sales:update", "sales:post", "sales:export",
        "crm:read", "crm:create", "crm:update", "crm:export",
        "inventory:read",
        "reports:read",
        "master:read", "master:create", "master:update",
    ],
    RoleName.EMPLOYEE: [
        "orders:read",
        "master:read",
        "inventory:read",
    ],
}


def resolve_user_permissions(user_doc: Dict[str, Any], role_doc: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Computes the deduplicated union of active permissions for a user:
    - Base role permissions (from database role doc or DEFAULT_ROLE_PERMISSIONS)
    - All assigned job roles from JOB_ROLE_DEFAULT_PERMISSIONS (supports multi-job roles)
    - Any direct custom permissions granted to the user account
    - Super Admin has full unrestricted access across all modules and actions
    """
    role_str = user_doc.get("role", RoleName.EMPLOYEE.value)

    # Super Admin has full unrestricted access to all permissions
    if role_str == RoleName.SUPER_ADMIN.value:
        return sorted(list(set(DEFAULT_ROLE_PERMISSIONS[RoleName.SUPER_ADMIN])))

    perms = set()

    # 1. Base Role Permissions
    if role_doc and "permissions" in role_doc:
        perms.update(role_doc["permissions"])
    else:
        try:
            role_enum = RoleName(role_str)
            perms.update(DEFAULT_ROLE_PERMISSIONS.get(role_enum, []))
        except ValueError:
            pass

    # 2. Multi Job Roles Permissions Union
    assigned_job_roles: List[str] = []
    if isinstance(user_doc.get("job_roles"), list):
        assigned_job_roles.extend([str(jr).strip() for jr in user_doc["job_roles"] if str(jr).strip()])
    if user_doc.get("job_role") and str(user_doc["job_role"]).strip() not in assigned_job_roles:
        assigned_job_roles.append(str(user_doc["job_role"]).strip())

    for jr in assigned_job_roles:
        if jr in JOB_ROLE_DEFAULT_PERMISSIONS:
            perms.update(JOB_ROLE_DEFAULT_PERMISSIONS[jr])

    # 3. Custom Permissions
    custom_perms = user_doc.get("custom_permissions") or []
    if isinstance(custom_perms, list):
        perms.update(custom_perms)

    return sorted(list(perms))

