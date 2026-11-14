# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Composition root FastAPI de SpectraHive."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from app.api.v1 import cutouts, diffs, quadrants, reports
from app.config import Settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


class HealthResponse(BaseModel):
    """Estado de salud del servicio backend."""

    status: str
    service: str
    database_configured: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "spectrahive-backend",
                "database_configured": True,
            }
        }
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = Settings.from_env()

    application = FastAPI(
        title="SpectraHive API",
        description=(
            "Backend FastAPI para SpectraHive (SPHEREx Tracker): servicio de cutouts "
            "infrarrojos J2000, resta absoluta |B - A| con deteccion de candidatos, "
            "reportes y validacion cruzada en Supabase, y ADN Cosmico precalculado."
        ),
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

    # Contratos raiz unicos (§6 de 00-contexto-general.md)
    application.include_router(cutouts.router)
    application.include_router(diffs.router)
    application.include_router(reports.router)
    application.include_router(quadrants.router)

    @application.get(
        "/health",
        response_model=HealthResponse,
        summary="Verificar estado del servicio",
        tags=["health"],
    )
    def health() -> HealthResponse:
        """Verifica disponibilidad de la API y si DATABASE_URL esta configurada (warm-up Render)."""
        return HealthResponse(
            status="ok",
            service="spectrahive-backend",
            database_configured=bool(os.environ.get("DATABASE_URL", "").strip()),
        )

    return application


app = create_app()
