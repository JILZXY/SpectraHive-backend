# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Cliente TAP acotado de IRSA para uso exclusivo del script offline scripts/fetch_cutouts.py."""

from __future__ import annotations

from pathlib import Path

import httpx

IRSA_TAP_SYNC_URL = "https://irsa.ipac.caltech.edu/TAP/sync"


class BoundedIrsaTapClient:
    """Consulta TAP acotada solo para localizar cutouts de los 5 objetos de prueba (RN-10)."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._timeout = timeout_seconds

    def query_spherex_cutout_url(
        self, ra_deg: float, dec_deg: float, epoch_tag: str
    ) -> str | None:
        """Consulta metadatos SIA/ObsCore acotados en IRSA para una coordenada puntual."""
        adql = (
            "SELECT TOP 1 access_url "
            "FROM ivoa.ObsCore "
            "WHERE obs_collection LIKE '%SPHEREx%' "
            f"AND CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra_deg:.6f}, {dec_deg:.6f}, 0.25)) = 1"
        )
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(
                    IRSA_TAP_SYNC_URL,
                    params={
                        "QUERY": adql,
                        "LANG": "ADQL",
                        "FORMAT": "csv",
                        "EPOCH": epoch_tag,
                    },
                )
                if resp.status_code != 200:
                    return None
                lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
                if len(lines) < 2:
                    return None
                candidate = lines[1].strip('"')
                return candidate if candidate.startswith("http") else None
        except httpx.HTTPError:
            return None

    def download_fits(self, url: str, dest_path: Path) -> bool:
        """Descarga un cutout FITS a disco si la URL responde correctamente."""
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code != 200 or not resp.content:
                    return False
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(resp.content)
                return True
        except httpx.HTTPError:
            return False
