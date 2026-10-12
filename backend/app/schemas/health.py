from typing import Dict, Literal
from pydantic import BaseModel, Field

class LivenessResponse(BaseModel):
    status: Literal["healthy", "unhealthy"] = Field(..., description="Overall liveness status")
    environment: str = Field(..., description="Active runtime environment")
    version: str = Field(..., description="API software version")

class DependencyStatus(BaseModel):
    status: Literal["connected", "disconnected", "degraded"] = Field(..., description="Status of dependency")
    latency_ms: float = Field(..., description="Round-trip check latency in ms")
    details: str = Field(..., description="Descriptive status note")

class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"] = Field(..., description="Overall service readiness")
    dependencies: Dict[str, DependencyStatus] = Field(..., description="Status of underlying dependencies")
