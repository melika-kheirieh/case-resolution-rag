import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response

from app.services.logging_config import correlation_id_var, request_id_var


CallNext = Callable[[Request], Awaitable[Response]]

logger = logging.getLogger(__name__)


async def request_context_middleware(
    request: Request,
    call_next: CallNext,
) -> Response:
    request_id = (
        request.headers.get("x-request-id")
        or f"req_{uuid4().hex[:12]}"
    )
    correlation_id = (
        request.headers.get("x-correlation-id")
        or request_id
    )

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    request_token = request_id_var.set(request_id)
    correlation_token = correlation_id_var.set(correlation_id)

    try:
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response

    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise

    finally:
        request_id_var.reset(request_token)
        correlation_id_var.reset(correlation_token)