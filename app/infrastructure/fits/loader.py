# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Carga y escritura de archivos FITS multi-extension con Astropy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


def _sanitize_2d(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    while arr.ndim > 2:
        arr = arr[0]
    finite_mask = np.isfinite(arr)
    if not np.all(finite_mask):
        fill = float(np.median(arr[finite_mask])) if np.any(finite_mask) else 0.0
        arr = np.where(finite_mask, arr, fill)
    return arr.astype(np.float32)


def _find_image_hdu(hdul: fits.HDUList):
    for ext_name in ("IMAGE", "SCI"):
        if ext_name in hdul and hdul[ext_name].data is not None:
            return hdul[ext_name]
    for hdu in hdul:
        if hdu.data is not None and np.asarray(hdu.data).ndim >= 2:
            return hdu
    return None


def load_fits_image(path: Path) -> np.ndarray:
    """Lee la extension IMAGE (o primera 2D valida) de un archivo FITS MEF."""
    with fits.open(path, memmap=False) as hdul:
        hdu = _find_image_hdu(hdul)
        if hdu is None or hdu.data is None:
            raise ValueError(f"El archivo FITS '{path}' no contiene una imagen 2D valida.")
        arr = _sanitize_2d(hdu.data)
        if arr.ndim == 2 and arr.size > 0:
            return arr
    raise ValueError(f"El archivo FITS '{path}' no contiene una imagen 2D valida.")


def load_fits_cutout(
    path: Path,
    ra_deg: float,
    dec_deg: float,
    fov_deg: int,
    max_output_size: int = 256,
) -> np.ndarray:
    """Lee un MEF (p. ej. 2040x2040) y recorta la ventana centrada en (RA, Dec) con WCS."""
    with fits.open(path, memmap=False) as hdul:
        hdu = _find_image_hdu(hdul)
        if hdu is None or hdu.data is None:
            raise ValueError(f"El archivo FITS '{path}' no contiene una imagen 2D valida.")
        arr = _sanitize_2d(hdu.data)
        h, w = arr.shape
        if h <= max_output_size and w <= max_output_size:
            if fov_deg == 1 and h >= 32 and w >= 32:
                return arr[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4].copy()
            return arr

        # Ventana centrada en las coordenadas del objeto via WCS (si existe)
        cx, cy = w / 2.0, h / 2.0
        try:
            wcs = WCS(hdu.header, naxis=2)
            if wcs.has_celestial:
                px, py = wcs.world_to_pixel_values(ra_deg, dec_deg)
                if np.isfinite(px) and np.isfinite(py) and 0 <= px < w and 0 <= py < h:
                    cx, cy = float(px), float(py)
        except Exception:
            pass

        half = max_output_size // 2 if fov_deg == 2 else max_output_size // 4
        half = max(32, min(half, h // 2, w // 2))
        y0 = max(0, min(h - 2 * half, int(round(cy)) - half))
        x0 = max(0, min(w - 2 * half, int(round(cx)) - half))
        return arr[y0 : y0 + 2 * half, x0 : x0 + 2 * half].copy()


def save_fits_image(
    path: Path,
    data: np.ndarray,
    header_meta: dict[str, Any] | None = None,
) -> Path:
    """Guarda un arreglo 2D como archivo FITS multi-extension con cabecera basica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    primary = fits.PrimaryHDU()
    image_hdu = fits.ImageHDU(data=np.asarray(data, dtype=np.float32), name="IMAGE")

    if header_meta:
        for key, value in header_meta.items():
            clean_key = str(key).upper()[:8]
            primary.header[clean_key] = value
            image_hdu.header[clean_key] = value

    hdul = fits.HDUList([primary, image_hdu])
    hdul.writeto(path, overwrite=True)
    return path
