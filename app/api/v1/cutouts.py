# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Router de cutouts: GET /cutout (def sincrono segun CoVe V3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from app.api.deps import get_cutout_use_case
from app.application.use_cases import GetCutout

router = APIRouter(tags=["cutouts"])


class CutoutResponse(BaseModel):
    ra: float
    dec: float
    fov: int
    epoca: str
    fuente: str
    objeto: str | None = None
    imagen: str


@router.get("/cutout", response_model=CutoutResponse)
def get_cutout(
    ra: str = Query(..., description="Ascension Recta J2000 (decimal o sexagesimal)"),
    dec: str = Query(..., description="Declinacion J2000 (decimal o sexagesimal)"),
    fov: int = Query(2, description="FOV permitido: 1 o 2 grados"),
    epoca: str = Query("A", description="Epoca solicitada: A/DR1 o B/QR3"),
    format: str = Query("json", description="Formato de respuesta: json o png"),
    use_case: GetCutout = Depends(get_cutout_use_case),
):
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
