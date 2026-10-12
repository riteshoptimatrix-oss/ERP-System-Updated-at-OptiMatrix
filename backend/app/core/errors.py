import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.core.errors")

def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register centralized exception handlers to ensure consistent, secure JSON error responses.
    Prevents leaking internal stack traces or database connection strings to API clients.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "correlation_id": correlation_id,
                }
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        # Format validation error details cleanly
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(l) for l in err.get("loc", [])])
            errors.append({
                "field": loc,
                "message": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            })

        logger.warning(
            "Request validation failed",
            extra={"correlation_id": correlation_id, "path": request.url.path, "errors": errors}
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Request validation failed",
                    "details": errors,
                    "correlation_id": correlation_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        # Log full traceback internally with correlation ID
        logger.error(
            "Unhandled server exception",
            exc_info=exc,
            extra={"correlation_id": correlation_id, "path": request.url.path}
        )

        # Return sanitized error message without exposing internals or secrets
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "An unexpected internal server error occurred. Please contact system support.",
                    "correlation_id": correlation_id,
                }
            },
        )
