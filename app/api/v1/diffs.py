# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de resta |B - A|: POST /diff (def sincrono segun CoVe V3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_compute_diff_use_case
from app.application.use_cases import ComputeDiff
from app.core.errors import ErrorResponse

router = APIRouter(tags=["diffs"])


class DiffRequest(BaseModel):
    """Peticion para calcular la resta absoluta |Epoca B - Epoca A|."""

    cuadrante_id: str
    epoca_a: str = "A"
    epoca_b: str = "B"
    ra: float | str | None = None
    dec: float | str | None = None
    fov: int = 2

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cuadrante_id": "Barnard's Star",
                "epoca_a": "DR1",
                "epoca_b": "QR3",
                "ra": 269.452075,
                "dec": 4.693365,
                "fov": 2,
            }
        }
    )


class CandidateResponse(BaseModel):
    """Candidato detectado por encima del umbral con explicacion de clasificacion."""

    ra: float
    dec: float
    valor: float
    motivo: str
    tipo: str


class DiffResponse(BaseModel):
    """Salida de POST /diff con umbral estadistico, candidatos e imagen |B - A|."""

    umbral: float
    candidatos: list[CandidateResponse]
    imagen: str
    fuente: str
    cuadrante_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "umbral": 14.1225,
                "candidatos": [
                    {
                        "ra": 269.4512,
                        "dec": 4.6941,
                        "valor": 242.5,
                        "motivo": "Desplazamiento dipolar de 8.6 px entre Epoca A y B con variacion delta=142.30 sobre el umbral (movimiento propio rapido)",
                        "tipo": "movimiento",
                    }
                ],
                "imagen": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "fuente": "irsa",
                "cuadrante_id": "Barnard's Star",
            }
        }
    )


@router.post(
    "/diff",
    response_model=DiffResponse,
    summary="Calcular resta absoluta |B - A| y candidatos sobre el umbral",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Parametros invalidos (coordenadas o FOV fuera de rango)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Cuadrante no encontrado",
        },
    },
)
def compute_diff(
    payload: DiffRequest,
    use_case: ComputeDiff = Depends(get_compute_diff_use_case),
) -> DiffResponse:
    """Alinea dos epocas por desplazamiento entero y calcula |Matriz_B - Matriz_A|.

    Aplica normalizacion por percentiles 1-99 (RF-07), resta absoluta (RF-08),
    umbral estadistico con explicacion del motivo de cada candidato (RF-09) y
    alineacion sin reproyeccion general (RN-09).
    """
    result = use_case.execute(
        cuadrante_id=payload.cuadrante_id,
        epoca_a=payload.epoca_a,
        epoca_b=payload.epoca_b,
        ra=payload.ra,
        dec=payload.dec,
        fov=payload.fov,
    )
    return DiffResponse(
        umbral=result.umbral,
        candidatos=[
            CandidateResponse(
                ra=c.ra,
                dec=c.dec,
                valor=c.valor,
                motivo=c.motivo,
                tipo=c.tipo,
            )
            for c in result.candidatos
        ],
        imagen=result.imagen_base64,
        fuente=result.fuente,
        cuadrante_id=result.cuadrante_id,
    )
