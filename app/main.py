# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Composition root FastAPI de SpectraHive."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import cutouts, diffs, quadrants, reports
from app.config import Settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = Settings.from_env()

    application = FastAPI(
        title="SpectraHive API",
        description="Backend FastAPI para SpectraHive (SPHEREx Tracker)",
        version="0.1.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    # Contratos raiz (§6 de 00-contexto-general.md) y prefijo /api/v1
    for prefix in ("", "/api/v1"):
        application.include_router(cutouts.router, prefix=prefix)
        application.include_router(diffs.router, prefix=prefix)
        application.include_router(reports.router, prefix=prefix)
        application.include_router(quadrants.router, prefix=prefix)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "spectrahive-backend",
            "database_configured": bool(os.environ.get("DATABASE_URL", "").strip()),
        }

    return application


app = create_app()
