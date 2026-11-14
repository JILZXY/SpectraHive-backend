# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de reportes y validacion cruzada: POST /report y validaciones."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_create_report_use_case, get_validate_report_use_case
from app.application.use_cases import CreateReport, ValidateReport

router = APIRouter(tags=["reports"])


class CreateReportRequest(BaseModel):
    cuadrante_id: str
    ra: float | str
    dec: float | str
    tipo: str


class CreateReportResponse(BaseModel):
    reporte_id: str
    estado: str
    cuadrante_id: str
    tipo: str


class ValidateReportBody(BaseModel):
    coincide: bool
    es_simulado: bool = False


class ValidateReportRequest(ValidateReportBody):
    reporte_id: str


class ValidateReportResponse(BaseModel):
    validacion_id: str
    reporte_id: str
    coincide: bool
    es_simulado: bool
    etiqueta: str
    votos_coinciden: int
    confirmado: bool
    estado_cuadrante: str


@router.post("/report", response_model=CreateReportResponse, status_code=201)
def create_report(
    payload: CreateReportRequest,
    use_case: CreateReport = Depends(get_create_report_use_case),
) -> CreateReportResponse:
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
)
def validate_report_by_id(
    reporte_id: str,
    payload: ValidateReportBody,
    use_case: ValidateReport = Depends(get_validate_report_use_case),
) -> ValidateReportResponse:
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


@router.post("/validate", response_model=ValidateReportResponse, status_code=201)
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
