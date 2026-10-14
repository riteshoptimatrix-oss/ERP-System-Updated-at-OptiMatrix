from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, users, roles, audit, dashboard, master, crm, orders,
    inventory, bom, production, wastage, power, hr, payroll, finance,
    reports, imports, employee, notifications, tasks, announcements,
)

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
api_router.include_router(master.router)
api_router.include_router(crm.router)
api_router.include_router(orders.router)
api_router.include_router(inventory.router)
api_router.include_router(bom.router)
api_router.include_router(production.router)
api_router.include_router(wastage.router)
api_router.include_router(power.router)
api_router.include_router(hr.router)
api_router.include_router(payroll.router)
api_router.include_router(finance.router)
api_router.include_router(reports.router)
api_router.include_router(imports.router)
api_router.include_router(employee.router)
api_router.include_router(notifications.router)
api_router.include_router(tasks.router)
api_router.include_router(announcements.router)

