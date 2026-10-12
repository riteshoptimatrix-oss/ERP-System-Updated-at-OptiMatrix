import logging
import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware.request_logging")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware that tracks request execution time, status codes,
    client IP, and method, paired with correlation ID.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Unhandled server exception intercepted in middleware",
                exc_info=exc,
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": process_time_ms,
                }
            )
            from fastapi.responses import JSONResponse
            from fastapi import status
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "message": "An unexpected internal server error occurred. Please contact system support.",
                        "correlation_id": correlation_id,
                    }
                },
                headers={"X-Correlation-ID": correlation_id}
            )
            return response

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        extra = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": process_time_ms,
        }

        # Filter out repetitive health check noise in production logs if needed
        if request.url.path.endswith("/health"):
            logger.debug(f"{request.method} {request.url.path} completed in {process_time_ms}ms", extra=extra)
        else:
            logger.info(f"{request.method} {request.url.path} {response.status_code} in {process_time_ms}ms", extra=extra)

        return response
