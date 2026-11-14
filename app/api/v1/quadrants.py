# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de cuadrantes y ADN Cosmico: GET /quadrants y GET /dna."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_cosmic_dna_use_case, get_list_quadrants_use_case
from app.application.use_cases import GetCosmicDNA, ListQuadrants

router = APIRouter(tags=["quadrants", "dna"])


class QuadrantItemResponse(BaseModel):
    id: str
    nombre: str
    ra: float
    dec: float
    fov: int
    epoca_a: str
    epoca_b: str
    estado: str
    es_objeto_prueba: bool
    tipo_prueba: str | None = None
    url_dinamica: str | None = None


class QuadrantsListResponse(BaseModel):
    cuadrantes: list[QuadrantItemResponse]


class CosmicDnaResponse(BaseModel):
    objeto: str
    bandas: list[str]
    valores: list[float]
    tipo_prueba: str | None = None
    descripcion: str | None = None


@router.get("/quadrants", response_model=QuadrantsListResponse)
def list_quadrants(
    use_case: ListQuadrants = Depends(get_list_quadrants_use_case),
) -> QuadrantsListResponse:
    items = use_case.execute()
    return QuadrantsListResponse(
        cuadrantes=[
            QuadrantItemResponse(
                id=q.id,
                nombre=q.nombre,
                ra=q.ra,
                dec=q.dec,
                fov=q.fov,
                epoca_a=q.epoca_a,
                epoca_b=q.epoca_b,
                estado=q.estado,
                es_objeto_prueba=q.es_objeto_prueba,
                tipo_prueba=q.tipo_prueba,
                url_dinamica=q.url_dinamica,
            )
            for q in items
        ]
    )


@router.get("/dna/{objeto}", response_model=CosmicDnaResponse)
def get_dna_by_path(
    objeto: str,
    use_case: GetCosmicDNA = Depends(get_cosmic_dna_use_case),
) -> CosmicDnaResponse:
    sig = use_case.execute(objeto)
    return CosmicDnaResponse(
        objeto=sig.objeto,
        bandas=sig.bandas,
        valores=sig.valores,
        tipo_prueba=sig.tipo_prueba,
        descripcion=sig.descripcion,
    )


@router.get("/dna", response_model=CosmicDnaResponse)
def get_dna_by_query(
    objeto: str = Query(..., description="Nombre del objeto de prueba"),
    use_case: GetCosmicDNA = Depends(get_cosmic_dna_use_case),
) -> CosmicDnaResponse:
    sig = use_case.execute(objeto)
    return CosmicDnaResponse(
        objeto=sig.objeto,
        bandas=sig.bandas,
        valores=sig.valores,
        tipo_prueba=sig.tipo_prueba,
        descripcion=sig.descripcion,
    )
