import time
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.database.mongodb import mongodb_manager
from app.schemas.health import LivenessResponse, ReadinessResponse, DependencyStatus

router = APIRouter(tags=["Health & Probes"])


@router.get(
    "/health",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Liveness Probe",
    description="Indicates whether the FastAPI application process is alive and responsive."
)
async def get_liveness() -> LivenessResponse:
    """
    Returns 200 if the web process is running.
    Does not verify external dependencies to prevent cascading restart loops.
    """
    return LivenessResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Service and all required dependencies are ready to accept traffic."},
        503: {"description": "One or more critical dependencies (e.g., MongoDB) are unavailable."}
    },
    summary="Application Readiness Probe",
    description="Indicates whether the application and its critical dependencies (MongoDB) are ready to handle requests."
)
async def get_readiness(response: Response) -> ReadinessResponse:
    """
    Verifies connectivity to MongoDB and other critical dependencies.
    Returns HTTP 200 when ready, HTTP 503 when degraded or disconnected.
    """
    start_time = time.perf_counter()
    is_db_connected = await mongodb_manager.ping()
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    if is_db_connected:
        db_status = DependencyStatus(
            status="connected",
            latency_ms=elapsed_ms,
            details="MongoDB ping succeeded."
        )
        overall_ready = True
    else:
        db_status = DependencyStatus(
            status="disconnected",
            latency_ms=elapsed_ms,
            details="MongoDB ping failed or client disconnected."
        )
        overall_ready = False

    dependencies = {
        "mongodb": db_status
    }

    if not overall_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            dependencies=dependencies
        )

    return ReadinessResponse(
        status="ready",
        dependencies=dependencies
    )
