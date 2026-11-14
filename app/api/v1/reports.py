# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de reportes y validacion cruzada: POST /report y validaciones."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_create_report_use_case, get_validate_report_use_case
from app.application.use_cases import CreateReport, ValidateReport
from app.core.errors import ErrorResponse

router = APIRouter(tags=["reports"])


class CreateReportRequest(BaseModel):
    """Peticion para reportar una anomalia o marcar un cuadrante como limpio."""

    cuadrante_id: str
    ra: float | str
    dec: float | str
    tipo: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cuadrante_id": "Barnard's Star",
                "ra": 269.452075,
                "dec": 4.693365,
                "tipo": "movimiento",
            }
        }
    )


class CreateReportResponse(BaseModel):
    """Respuesta de POST /report con identificador y estado del cuadrante."""

    reporte_id: str
    estado: str
    cuadrante_id: str
    tipo: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reporte_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "estado": "pendiente",
                "cuadrante_id": "00000000-0000-0000-0000-000000000001",
                "tipo": "movimiento",
            }
        }
    )


class ValidateReportBody(BaseModel):
    """Voto de validacion cruzada sobre un reporte existente."""

    coincide: bool
    es_simulado: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "coincide": True,
                "es_simulado": True,
            }
        }
    )


class ValidateReportRequest(ValidateReportBody):
    reporte_id: str


class ValidateReportResponse(BaseModel):
    """Resultado de validacion cruzada y estado actualizado del cuadrante."""

    validacion_id: str
    reporte_id: str
    coincide: bool
    es_simulado: bool
    etiqueta: str
    votos_coinciden: int
    confirmado: bool
    estado_cuadrante: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "validacion_id": "f1e2d3c4-b5a6-7890-1234-567890abcdef",
                "reporte_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "coincide": True,
                "es_simulado": True,
                "etiqueta": "simulado",
                "votos_coinciden": 3,
                "confirmado": True,
                "estado_cuadrante": "confirmado",
            }
        }
    )


@router.post(
    "/report",
    response_model=CreateReportResponse,
    status_code=201,
    summary="Registrar un reporte de anomalia o cuadrante limpio",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Coordenadas invalidas o tipo incompatible con tipo_prueba del cuadrante (RN-02/RN-03)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Cuadrante no encontrado",
        },
        503: {
            "model": ErrorResponse,
            "description": "Base de datos no configurada (falta DATABASE_URL)",
        },
    },
)
def create_report(
    payload: CreateReportRequest,
    use_case: CreateReport = Depends(get_create_report_use_case),
) -> CreateReportResponse:
    """Crea un reporte en una posicion J2000 de un cuadrante (RF-10, RF-11).

    Valida RN-02 y RN-03 antes de insertar en `reportes`: `tipo` debe coincidir
    con el `tipo_prueba` del cuadrante (`movimiento` o `brillo`), salvo `limpio`.
    """
    result = use_case.execute(
        cuadrante_id=payload.cuadrante_id,
        ra=payload.ra,
        dec=payload.dec,
        tipo=payload.tipo,
    )
    return CreateReportResponse(
        reporte_id=result.reporte_id,
        estado=result.estado,
        cuadrante_id=result.cuadrante_id,
        tipo=result.tipo,
    )


@router.post(
    "/report/{reporte_id}/validate",
    response_model=ValidateReportResponse,
    status_code=201,
    summary="Registrar voto de validacion cruzada sobre un reporte",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Operacion invalida (ej. intentar validar un reporte limpio, RF-11)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Reporte no encontrado",
        },
        503: {
            "model": ErrorResponse,
            "description": "Base de datos no configurada (falta DATABASE_URL)",
        },
    },
)
def validate_report_by_id(
    reporte_id: str,
    payload: ValidateReportBody,
    use_case: ValidateReport = Depends(get_validate_report_use_case),
) -> ValidateReportResponse:
    """Registra una validacion sobre un reporte y verifica confirmacion (RF-12, RF-13).

    Cuando `vw_reportes_confirmados` registra >= 3 votos con `coincide=true` para el
    mismo `reporte_id`, el cuadrante pasa atomicamente a estado `confirmado` (RN-06).
    """
    result = use_case.execute(
        reporte_id=reporte_id,
        coincide=payload.coincide,
        es_simulado=payload.es_simulado,
    )
    return ValidateReportResponse(
        validacion_id=result.validacion_id,
        reporte_id=result.reporte_id,
        coincide=result.coincide,
        es_simulado=result.es_simulado,
        etiqueta=result.etiqueta,
        votos_coinciden=result.votos_coinciden,
        confirmado=result.confirmado,
        estado_cuadrante=result.estado_cuadrante,
    )


@router.post(
    "/validate",
    response_model=ValidateReportResponse,
    status_code=201,
    include_in_schema=False,
)
def validate_report(
    payload: ValidateReportRequest,
    use_case: ValidateReport = Depends(get_validate_report_use_case),
) -> ValidateReportResponse:
    result = use_case.execute(
        reporte_id=payload.reporte_id,
        coincide=payload.coincide,
        es_simulado=payload.es_simulado,
    )
    return ValidateReportResponse(
        validacion_id=result.validacion_id,
        reporte_id=result.reporte_id,
        coincide=result.coincide,
        es_simulado=result.es_simulado,
        etiqueta=result.etiqueta,
        votos_coinciden=result.votos_coinciden,
        confirmado=result.confirmado,
        estado_cuadrante=result.estado_cuadrante,
    )
