"""Structured logging configuration using structlog."""
import logging
import sys
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from services.api.config import settings


def _configure_structlog() -> None:
    """Configure structlog for JSON (production) or pretty-print (development)."""
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.app_env == "production":
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


_configure_structlog()


def get_logger(module_name: str) -> Any:
    """Return a bound structlog logger with the module name."""
    return structlog.get_logger(module_name)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request via structlog contextvars."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            mode=settings.app_mode,
        )
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
