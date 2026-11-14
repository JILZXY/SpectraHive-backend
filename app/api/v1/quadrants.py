# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de cuadrantes y ADN Cosmico: GET /quadrants y GET /dna/{objeto}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_cosmic_dna_use_case, get_list_quadrants_use_case
from app.application.use_cases import GetCosmicDNA, ListQuadrants
from app.core.errors import ErrorResponse

router = APIRouter(tags=["quadrants", "dna"])


class QuadrantItemResponse(BaseModel):
    """Cuadrante de la cola fija ordenado para revision."""

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
    """Lista ordenada de cuadrantes de la cola fija (RF-05)."""

    cuadrantes: list[QuadrantItemResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cuadrantes": [
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "nombre": "Barnard's Star",
                        "ra": 269.452075,
                        "dec": 4.693365,
                        "fov": 2,
                        "epoca_a": "DR1",
                        "epoca_b": "QR3",
                        "estado": "pendiente",
                        "es_objeto_prueba": True,
                        "tipo_prueba": "movimiento",
                        "url_dinamica": "/?ra=17h57m&dec=+4d41m&fov=2",
                    }
                ]
            }
        }
    )


class CosmicDnaResponse(BaseModel):
    """Firma espectral visual precalculada del ADN Cosmico (RF-14, RF-15)."""

    objeto: str
    bandas: list[str]
    valores: list[float]
    tipo_prueba: str | None = None
    descripcion: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objeto": "Barnard's Star",
                "bandas": [
                    "0.75 um",
                    "1.10 um",
                    "1.65 um",
                    "2.20 um",
                    "3.40 um",
                    "4.10 um",
                    "4.80 um",
                ],
                "valores": [0.54, 0.88, 1.0, 0.84, 0.46, 0.34, 0.28],
                "tipo_prueba": "movimiento",
                "descripcion": "Firma visual infrarroja de referencia (enana roja M4V de alto movimiento propio). Uso comparativo visual, no identificacion quimica directa.",
            }
        }
    )


@router.get(
    "/quadrants",
    response_model=QuadrantsListResponse,
    summary="Listar cola fija de cuadrantes",
    responses={
        503: {
            "model": ErrorResponse,
            "description": "Base de datos no configurada (falta DATABASE_URL)",
        }
    },
)
def list_quadrants(
    use_case: ListQuadrants = Depends(get_list_quadrants_use_case),
) -> QuadrantsListResponse:
    """Devuelve la cola fija de hasta 10 cuadrantes (5 de prueba + 5 de practica, RF-05)."""
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


@router.get(
    "/dna/{objeto}",
    response_model=CosmicDnaResponse,
    summary="Obtener ADN Cosmico precalculado de un objeto",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "No existe ADN Cosmico precalculado para el objeto solicitado",
        }
    },
)
def get_dna_by_path(
    objeto: str,
    use_case: GetCosmicDNA = Depends(get_cosmic_dna_use_case),
) -> CosmicDnaResponse:
    """Devuelve la firma espectral precalculada para comparar visualmente (RF-14, RF-15)."""
    sig = use_case.execute(objeto)
    return CosmicDnaResponse(
        objeto=sig.objeto,
        bandas=sig.bandas,
        valores=sig.valores,
        tipo_prueba=sig.tipo_prueba,
        descripcion=sig.descripcion,
    )


@router.get(
    "/dna",
    response_model=CosmicDnaResponse,
    include_in_schema=False,
)
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
