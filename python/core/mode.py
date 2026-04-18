"""Live/Sandbox mode utilities.

Provides get_current_mode() to read the current mode from the database,
and mode_context() as a context manager that binds the mode to structlog
contextvars for consistent log enrichment.
"""
from contextlib import contextmanager
from typing import Generator

import structlog
from sqlmodel import Session, select

from python.core.database import engine
from python.core.models import AppSettings


def get_current_mode() -> str:
    """Read the current trading mode ('live' or 'sandbox') from the DB.

    Returns 'sandbox' as the safe default if no AppSettings row exists.
    """
    with Session(engine) as session:
        app_settings = session.exec(select(AppSettings)).first()
        if app_settings is None:
            return "sandbox"
        return app_settings.current_mode


@contextmanager
def mode_context() -> Generator[str, None, None]:
    """Context manager that binds the current mode to structlog contextvars.

    Usage::

        with mode_context() as mode:
            logger.info("doing work", some_field="value")
            # all logs inside include mode=<current_mode>
    """
    mode = get_current_mode()
    structlog.contextvars.bind_contextvars(mode=mode)
    try:
        yield mode
    finally:
        structlog.contextvars.unbind_contextvars("mode")
