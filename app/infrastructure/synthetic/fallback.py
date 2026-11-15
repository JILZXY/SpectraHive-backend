# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Generador sintetico determinista para los 5 objetos de prueba (RF-16)."""

from __future__ import annotations

import hashlib
import math

import numpy as np

from app.domain.entities import TestObjectSpec, match_test_object
from app.domain.value_objects import Cutout, Epoch, Fov, Image, RaDec
from app.infrastructure.fits.rendering import render_false_color_png


def _add_gaussian_star(
    canvas: np.ndarray, cx: float, cy: float, flux: float, sigma: float = 1.6
) -> None:
    """Anade una fuente puntual con perfil PSF gaussiano 2D."""
    h, w = canvas.shape
    y0 = max(0, int(math.floor(cy - 4 * sigma)))
    y1 = min(h, int(math.ceil(cy + 4 * sigma)) + 1)
    x0 = max(0, int(math.floor(cx - 4 * sigma)))
    x1 = min(w, int(math.ceil(cx + 4 * sigma)) + 1)
    if y1 <= y0 or x1 <= x0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    canvas[y0:y1, x0:x1] += flux * np.exp(-0.5 * r2 / (sigma**2))


def generate_synthetic_field(
    ra: float,
    dec: float,
    fov: int,
    epoch_canonical: str,
    size: int = 128,
) -> tuple[np.ndarray, TestObjectSpec | None]:
    """Genera matriz 2D determinista para (RA, Dec, FOV, Epoca)."""
    matched = match_test_object(ra, dec, tolerance_deg=0.5)
    seed_key = (
        matched.slug
        if matched is not None
        else f"{round(ra, 3):.3f}_{round(dec, 3):.3f}"
    )
    seed_int = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed_int)

    # Fondo base y ruido de lectura minimo compartido por campo
    canvas = np.full((size, size), 12.0, dtype=np.float32)

    # Estrellas fijas de fondo (no se mueven entre epocas, se cancelan en |B - A|)
    num_bg_stars = 24
    margin = 10
    for _ in range(num_bg_stars):
        sx = float(rng.uniform(margin, size - margin))
        sy = float(rng.uniform(margin, size - margin))
        s_flux = float(rng.uniform(18.0, 95.0))
        s_sigma = float(rng.uniform(1.3, 1.9))
        # Evitar tapar exactamente el centro de la fuente objetivo
        if math.hypot(sx - size / 2.0, sy - size / 2.0) < 14.0:
            continue
        _add_gaussian_star(canvas, sx, sy, s_flux, sigma=s_sigma)

    # Ruido sutil por epoca (determinista por epoca)
    epoch_seed = int(
        hashlib.sha256(f"{seed_key}_{epoch_canonical}".encode("utf-8")).hexdigest()[:8],
        16,
    )
    epoch_rng = np.random.default_rng(epoch_seed)
    canvas += epoch_rng.normal(0.0, 0.35, size=(size, size)).astype(np.float32)

    center = (size - 1) / 2.0
    is_epoch_b = epoch_canonical.upper() in ("QR3", "B")
    zoom_factor = 2.0 / float(fov)  # FOV=1 amplia desplazamientos en pixeles respecto a FOV=2

    if matched is not None:
        if matched.tipo_prueba == "movimiento":
            # Desplazamiento proporcional al movimiento propio del catalogo (RN-02)
            if matched.slug == "barnards_star":
                dx, dy = (5.0, -7.0)
            elif matched.slug == "wise_0855_0714":
                dx, dy = (-5.5, 2.5)
            else:  # epsilon_indi_b
                dx, dy = (3.2, 2.2)

            dx *= zoom_factor
            dy *= zoom_factor
            if is_epoch_b:
                tx, ty = center + dx * 0.5, center + dy * 0.5
            else:
                tx, ty = center - dx * 0.5, center - dy * 0.5
            _add_gaussian_star(canvas, tx, ty, flux=155.0, sigma=1.8)
        else:
            # RW Aurigae y R Draconis: posicion fija, cambio de brillo entre epocas (RN-03)
            flux = 175.0 if is_epoch_b else 42.0
            _add_gaussian_star(canvas, center, center, flux=flux, sigma=1.9)

    return canvas, matched


class SyntheticCutoutProvider:
    """Fallback sintetico determinista cuando IRSA precalculado no esta disponible (RF-16)."""

    def get_cutout(self, ra_dec: RaDec, fov: Fov, epoch: Epoch) -> Cutout:
        arr, matched = generate_synthetic_field(
            ra=ra_dec.ra,
            dec=ra_dec.dec,
            fov=fov.value,
            epoch_canonical=epoch.canonical,
            size=128,
        )
        png_bytes = render_false_color_png(arr, is_diff=False)
        obj_name = matched.nombre if matched is not None else None
        img = Image(
            data=arr,
            ra=ra_dec.ra,
            dec=ra_dec.dec,
            fov=fov.value,
            epoch=epoch.canonical,
            source="sintetico",
            object_name=obj_name,
        )
        return Cutout(
            image=img,
            png_bytes=png_bytes,
            ra=ra_dec.ra,
            dec=ra_dec.dec,
            fov=fov.value,
            epoca=epoch.canonical,
            fuente="sintetico",
            objeto=obj_name,
        )
