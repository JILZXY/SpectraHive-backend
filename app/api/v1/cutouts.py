# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de cutouts: GET /cutout (def sincrono segun CoVe V3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_cutout_use_case
from app.application.use_cases import GetCutout
from app.core.errors import ErrorResponse

router = APIRouter(tags=["cutouts"])


class CutoutResponse(BaseModel):
    """Respuesta JSON de GET /cutout con metadatos y PNG codificado en base64."""

    ra: float
    dec: float
    fov: int
    epoca: str
    fuente: str
    objeto: str | None = None
    imagen: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ra": 269.452075,
                "dec": 4.693365,
                "fov": 2,
                "epoca": "DR1",
                "fuente": "irsa",
                "objeto": "Barnard's Star",
                "imagen": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
            }
        }
    )


@router.get(
    "/cutout",
    response_model=CutoutResponse,
    summary="Obtener cutout astronomico por coordenadas J2000",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Coordenadas fuera de rango (RA 0-360°, Dec -90°..+90°) o FOV distinto de 1 o 2",
        }
    },
)
def get_cutout(
    ra: str = Query(
        ...,
        description="Ascension Recta J2000 (decimal 0-360 o sexagesimal, ej. 269.452075 o 17h57m)",
        examples=["269.452075"],
    ),
    dec: str = Query(
        ...,
        description="Declinacion J2000 (decimal -90..+90 o sexagesimal, ej. 4.693365 o +4d41m)",
        examples=["4.693365"],
    ),
    fov: int = Query(
        2,
        description="Campo de vision permitido en el MVP: solo 1 o 2 grados (RF-02)",
        examples=[2],
    ),
    epoca: str = Query(
        "A",
        description="Epoca astronomica solicitada: A/DR1 o B/QR3 (RF-06)",
        examples=["A"],
    ),
    format: str = Query(
        "json",
        description="Formato de salida: json (metadatos + imagen base64) o png (binario image/png)",
        examples=["json"],
    ),
    use_case: GetCutout = Depends(get_cutout_use_case),
):
    """Sirve un cutout infrarrojo precalculado de IRSA (o fallback sintetico) en J2000.

    Cumple RF-01 (validacion de RA/Dec), RF-02 (FOV 1 o 2), RF-06 (2 epocas),
    RF-07 (normalizacion unica percentiles 1-99) y RF-16 (fallback sintetico declarado
    en el campo `fuente`: `irsa` | `sintetico`).
    """
    result = use_case.execute(ra=ra, dec=dec, fov=fov, epoca=epoca)
    if format.strip().lower() == "png":
        return Response(
            content=result.png_bytes,
            media_type="image/png",
            headers={
                "X-Fuente": result.fuente,
                "X-Epoca": result.epoca,
            },
        )
    return CutoutResponse(
        ra=result.ra,
        dec=result.dec,
        fov=result.fov,
        epoca=result.epoca,
        fuente=result.fuente,
        objeto=result.objeto,
        imagen=result.imagen_base64,
    )
