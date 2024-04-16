"""Application factory, middleware and error translation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.db.session import init_db
from app.services.errors import (
    CsvDecodeError,
    CsvEmptyError,
    CsvError,
    CsvTooLargeError,
    MappingPlanError,
    RunNotFoundError,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE = 422
HTTP_PAYLOAD_TOO_LARGE = 413

# Which status each domain error maps to. Checked most specific first.
ERROR_STATUS: tuple[tuple[type[Exception], int, str], ...] = (
    (CsvTooLargeError, HTTP_PAYLOAD_TOO_LARGE, "file_too_large"),
    (CsvEmptyError, HTTP_UNPROCESSABLE, "empty_file"),
    (CsvDecodeError, HTTP_UNPROCESSABLE, "undecodable_file"),
    (CsvError, HTTP_BAD_REQUEST, "invalid_file"),
    (MappingPlanError, HTTP_UNPROCESSABLE, "invalid_plan"),
    (RunNotFoundError, HTTP_NOT_FOUND, "not_found"),
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create missing tables before the first request is served."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="Suggests how the columns of an uploaded CSV map onto a target schema.",
        lifespan=lifespan,
    )

    # The browser app is the only client, so the allow-list is explicit
    # rather than "*" -- credentials plus a wildcard origin is a hole.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    for exception_type, status, code in ERROR_STATUS:
        app.add_exception_handler(exception_type, _handler(status, code))

    app.include_router(router)

    @app.get("/", tags=["service"])
    def index() -> dict[str, str]:
        """Point a curious browser at the docs."""
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


def _handler(status: int, code: str):
    """Build a handler that renders one domain error as JSON."""

    async def handle(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": code, "detail": str(exc)})

    return handle


app = create_app()
