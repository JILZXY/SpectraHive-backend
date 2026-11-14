# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de resta |B - A|: POST /diff (def sincrono segun CoVe V3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_compute_diff_use_case
from app.application.use_cases import ComputeDiff

router = APIRouter(tags=["diffs"])


class DiffRequest(BaseModel):
    cuadrante_id: str
    epoca_a: str = "A"
    epoca_b: str = "B"
    ra: float | str | None = None
    dec: float | str | None = None
    fov: int = 2


class CandidateResponse(BaseModel):
    ra: float
    dec: float
    valor: float
    motivo: str
    tipo: str


class DiffResponse(BaseModel):
    umbral: float
    candidatos: list[CandidateResponse]
    imagen: str
    fuente: str
    cuadrante_id: str


@router.post("/diff", response_model=DiffResponse)
def compute_diff(
    payload: DiffRequest,
    use_case: ComputeDiff = Depends(get_compute_diff_use_case),
) -> DiffResponse:
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
