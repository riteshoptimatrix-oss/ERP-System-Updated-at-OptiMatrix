import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates a unique correlation ID per request.
    The ID is attached to request.state and propagated in the response headers
    for end-to-end request traceability across services.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state for downstream handlers and logging
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
