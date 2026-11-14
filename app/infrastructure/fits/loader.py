# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Carga y escritura de archivos FITS multi-extension con Astropy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits


def load_fits_image(path: Path) -> np.ndarray:
    """Lee la primera extension con datos 2D validos de un archivo FITS."""
    with fits.open(path, memmap=False) as hdul:
        for hdu in hdul:
            if hdu.data is None:
                continue
            arr = np.asarray(hdu.data, dtype=np.float32)
            if arr.ndim > 2:
                # Si es cubo (ej. bandas espectrales), colapsar o tomar plano central
                while arr.ndim > 2:
                    arr = arr[0]
            if arr.ndim == 2 and arr.size > 0:
                finite_mask = np.isfinite(arr)
                if not np.all(finite_mask):
                    fill = float(np.median(arr[finite_mask])) if np.any(finite_mask) else 0.0
                    arr = np.where(finite_mask, arr, fill)
                return arr.astype(np.float32)
    raise ValueError(f"El archivo FITS '{path}' no contiene una imagen 2D valida.")


def save_fits_image(
    path: Path,
    data: np.ndarray,
    header_meta: dict[str, Any] | None = None,
) -> Path:
    """Guarda un arreglo 2D como archivo FITS multi-extension con cabecera WCS basica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    primary = fits.PrimaryHDU()
    image_hdu = fits.ImageHDU(data=np.asarray(data, dtype=np.float32), name="SCI")

    if header_meta:
        for key, value in header_meta.items():
            clean_key = str(key).upper()[:8]
            primary.header[clean_key] = value
            image_hdu.header[clean_key] = value

    hdul = fits.HDUList([primary, image_hdu])
    hdul.writeto(path, overwrite=True)
    return path
