"""Wudao API — FastAPI application entry point."""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from python.core.database import init_db
from python.core.logging_config import RequestIdMiddleware, get_logger
from services.api.routers import exchange_account_router, health, order_router, position_router, settings_router, webhook_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup", message="Wudao API starting up")
    init_db()
    yield
    logger.info("shutdown", message="Wudao API shutting down")


app = FastAPI(
    title="Wudao API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID + structured logging
app.add_middleware(RequestIdMiddleware)

# Routers
app.include_router(health.router)
app.include_router(settings_router.router)
app.include_router(position_router.router)
app.include_router(exchange_account_router.router)
app.include_router(order_router.router)
app.include_router(webhook_router.router)
