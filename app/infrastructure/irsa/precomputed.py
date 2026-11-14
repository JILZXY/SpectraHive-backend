# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Proveedores precalculados de cutouts FITS y ADN Cosmico JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from astropy.io import fits

from app.domain.entities import (
    SpectralSignature,
    find_test_object_by_name,
    match_test_object,
)
from app.domain.errors import ResourceNotFoundError
from app.domain.ports import CutoutProvider
from app.domain.value_objects import Cutout, Epoch, Fov, Image, RaDec
from app.infrastructure.fits.loader import load_fits_cutout
from app.infrastructure.fits.rendering import render_false_color_png
from app.infrastructure.synthetic.fallback import SyntheticCutoutProvider

logger = logging.getLogger(__name__)


def _read_fits_source_tag(path: Path) -> str:
    """Inspecciona cabecera FITS para distinguir origen real IRSA vs fallback sintetico."""
    try:
        with fits.open(path, memmap=False) as hdul:
            header = hdul[0].header
            if bool(header.get("SYNTHETC", False)):
                return "sintetico"
            src = str(header.get("SOURCE", "")).strip().lower()
            if src == "sintetico":
                return "sintetico"
    except Exception:
        return "sintetico"
    return "irsa"


class PrecomputedCutoutProvider:
    """Lee FITS precalculados de data/cutouts/ con Astropy o delega a fallback sintetico (RF-16)."""

    def __init__(
        self,
        cutouts_dir: Path,
        fallback: CutoutProvider | None = None,
    ) -> None:
        self._cutouts_dir = cutouts_dir
        self._fallback = fallback or SyntheticCutoutProvider()

    def _resolve_fits_path(self, slug: str, epoch: Epoch, fov: int) -> Path | None:
        explicit_candidates = [
            self._cutouts_dir / f"{slug}_{epoch.canonical}_fov{fov}.fits",
            self._cutouts_dir / f"{slug}_{epoch.canonical}.fits",
            self._cutouts_dir / f"{slug}_{epoch.alias}.fits",
            self._cutouts_dir / f"{slug}_{epoch.name}.fits",
        ]
        for path in explicit_candidates:
            if path.is_file():
                return path

        # Archivos reales descargados con fecha: {slug}_{YYYY-MM-DD}.fits
        dated = sorted(self._cutouts_dir.glob(f"{slug}_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.fits"))
        if not dated:
            return None
        if epoch.alias == "A" or epoch.canonical == "DR1":
            return dated[0]
        if epoch.alias == "B" or epoch.canonical == "QR3":
            return dated[1] if len(dated) >= 2 else dated[-1]
        return dated[0]

    def get_cutout(self, ra_dec: RaDec, fov: Fov, epoch: Epoch) -> Cutout:
        matched = match_test_object(ra_dec.ra, ra_dec.dec, tolerance_deg=0.5)
        if matched is not None:
            fits_path = self._resolve_fits_path(matched.slug, epoch, fov.value)
            if fits_path is not None:
                try:
                    raw_data = load_fits_cutout(
                        fits_path,
                        ra_deg=ra_dec.ra,
                        dec_deg=ra_dec.dec,
                        fov_deg=fov.value,
                    )
                    fuente = _read_fits_source_tag(fits_path)
                    png_bytes = render_false_color_png(raw_data, is_diff=False)
                    img = Image(
                        data=raw_data,
                        ra=ra_dec.ra,
                        dec=ra_dec.dec,
                        fov=fov.value,
                        epoch=epoch.canonical,
                        source=fuente,  # type: ignore[arg-type]
                        object_name=matched.nombre,
                    )
                    return Cutout(
                        image=img,
                        png_bytes=png_bytes,
                        ra=ra_dec.ra,
                        dec=ra_dec.dec,
                        fov=fov.value,
                        epoca=epoch.canonical,
                        fuente=fuente,  # type: ignore[arg-type]
                        objeto=matched.nombre,
                    )
                except Exception as exc:
                    logger.warning(
                        "Fallo lectura FITS '%s' (%s); usando fallback sintetico.",
                        fits_path,
                        exc,
                    )

        return self._fallback.get_cutout(ra_dec, fov, epoch)


class PrecomputedSpectralProvider:
    """Lee el ADN Cosmico precalculado desde data/spectra/ (RF-14, RF-15)."""

    def __init__(self, spectra_dir: Path) -> None:
        self._spectra_dir = spectra_dir

    def list_objects(self) -> list[str]:
        if not self._spectra_dir.is_dir():
            return []
        names: list[str] = []
        for path in sorted(self._spectra_dir.glob("*.json")):
            if path.name == "index.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if "objeto" in payload:
                    names.append(str(payload["objeto"]))
            except Exception:
                continue
        return names

    def signature(self, objeto: str) -> SpectralSignature:
        spec = find_test_object_by_name(objeto)
        if spec is not None:
            candidate_path = self._spectra_dir / f"{spec.slug}.json"
            if candidate_path.is_file():
                return self._load_file(candidate_path)

        # Busqueda secundaria sobre cualquier JSON existente en data/spectra/
        norm = (objeto or "").strip().lower()
        if self._spectra_dir.is_dir() and norm:
            for path in self._spectra_dir.glob("*.json"):
                if path.name == "index.json":
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    obj_val = str(payload.get("objeto", "")).lower()
                    if norm == obj_val or norm in obj_val or path.stem == norm:
                        return self._to_entity(payload)
                except Exception:
                    continue

        raise ResourceNotFoundError(
            f"No existe ADN Cosmico precalculado para '{objeto}'."
        )

    @staticmethod
    def _to_entity(payload: dict) -> SpectralSignature:
        return SpectralSignature(
            objeto=str(payload["objeto"]),
            bandas=[str(b) for b in payload["bandas"]],
            valores=[float(v) for v in payload["valores"]],
            tipo_prueba=payload.get("tipo_prueba"),
            descripcion=payload.get("descripcion"),
        )

    def _load_file(self, path: Path) -> SpectralSignature:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._to_entity(payload)
