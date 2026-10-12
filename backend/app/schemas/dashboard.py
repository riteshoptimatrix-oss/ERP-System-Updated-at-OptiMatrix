from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.user import ManufacturingUnit


class KpiMetricItem(BaseModel):
    title: str = Field(..., description="KPI name (e.g., Active Orders, Pending QC)")
    value: int = Field(default=0, description="Primary count or total")
    pending_action_count: int = Field(default=0, description="Urgent items requiring action")
    unit_id: str = Field(..., description="Target facility (Unit_1, Unit_2, or BOTH)")
    module: str = Field(..., description="Underlying module key")
    permitted: bool = Field(default=True, description="Whether current user is authorized to view")
    subtitle: Optional[str] = None


class RecentActivityItem(BaseModel):
    id: str
    module: str
    action: str
    description: str
    timestamp: str
    user_email: Optional[str] = None
    unit_id: Optional[str] = None
    status: str = "SUCCESS"


class DashboardSummaryResponse(BaseModel):
    active_unit: ManufacturingUnit
    timestamp: datetime
    kpis: Dict[str, Optional[KpiMetricItem]]  # orders, dispatch, stock, production, qc, wastage, attendance, approvals
    total_permitted_kpis: int


class DashboardActivityResponse(BaseModel):
    active_unit: ManufacturingUnit
    activities: List[RecentActivityItem]
