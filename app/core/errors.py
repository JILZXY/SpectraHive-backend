# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Mapeo de excepciones de dominio e infraestructura a respuestas HTTP JSON."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.config import DatabaseConfigError
from app.domain.errors import ResourceNotFoundError, ValidationError


class ErrorResponse(BaseModel):
    """Modelo estandar de respuesta de error HTTP JSON."""

    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "RA fuera de rango valido (0 a 360 grados): 400.0."}
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra handlers globales para FastAPI."""

    @app.exception_handler(ValidationError)
    def handle_validation_error(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ResourceNotFoundError)
    def handle_not_found_error(
        _request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DatabaseConfigError)
    def handle_db_config_error(
        _request: Request, exc: DatabaseConfigError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})
