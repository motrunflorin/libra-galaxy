"""FastAPI application factory.

``create_app`` takes settings and an optional pre-built container so tests can
inject in-memory repositories without touching the environment.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from libra.api.v1.router import router as v1_router
from libra.core.api.exception_handlers import register_exception_handlers
from libra.core.api.middleware import RequestContextMiddleware
from libra.core.config import Settings, get_settings
from libra.core.container import Container, build_container
from libra.core.logging import setup_logging


def create_app(
    settings: Settings | None = None,
    *,
    container: Container | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    setup_logging(resolved_settings.observability)
    resolved_container = container or build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Index creation is idempotent and cheap; doing it at startup keeps
        # the deployed schema in step with the declarations in code.
        if resolved_container.mongo is not None:
            await resolved_container.mongo.ensure_indexes()
        yield
        if resolved_container.mongo is not None:
            await resolved_container.mongo.close()

    app = FastAPI(
        title=resolved_settings.app.name,
        version="0.1.0",
        lifespan=lifespan,
        # The envelope is documented in docs/API_CONVENTIONS.md; suppress
        # FastAPI's default error shapes from the schema.
        responses={},
    )
    app.state.container = resolved_container

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.app.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(v1_router, prefix=resolved_settings.app.api_prefix)
    return app
