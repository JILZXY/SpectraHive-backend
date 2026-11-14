# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Normalizacion percentiles 1-99, falso color unico, resta |B-A| y candidatos."""

from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image as PilImage
from scipy import ndimage

from app.domain.entities import Candidate
from app.domain.rules import classify_candidate
from app.domain.value_objects import Image

# Paleta unica infrarroja (RF-07: sin multiples paletas en el MVP)
_LUT_POINTS = np.array([0.0, 0.25, 0.55, 0.80, 1.0], dtype=np.float32)
_LUT_R = np.array([8, 44, 158, 240, 255], dtype=np.float32)
_LUT_G = np.array([10, 18, 58, 152, 252], dtype=np.float32)
_LUT_B = np.array([28, 86, 118, 52, 224], dtype=np.float32)


def normalize_percentile_1_99(data: np.ndarray) -> np.ndarray:
    """Normaliza una matriz 2D usando percentiles 1 y 99 al rango [0, 1] (RF-07)."""
    arr = np.asarray(data, dtype=np.float32)
    finite_mask = np.isfinite(arr)
    if not np.all(finite_mask):
        fill = float(np.median(arr[finite_mask])) if np.any(finite_mask) else 0.0
        arr = np.where(finite_mask, arr, fill)

    p1, p99 = np.percentile(arr, [1.0, 99.0])
    if p99 <= p1 + 1e-9:
        vmax = float(np.max(arr))
        vmin = float(np.min(arr))
        if vmax <= vmin + 1e-9:
            return np.zeros_like(arr, dtype=np.float32)
        return np.clip((arr - vmin) / (vmax - vmin), 0.0, 1.0).astype(np.float32)

    return np.clip((arr - p1) / (p99 - p1), 0.0, 1.0).astype(np.float32)


def render_false_color_png(data: np.ndarray, is_diff: bool = False) -> bytes:
    """Aplica la normalizacion 1-99 y paleta unica infrarroja y codifica PNG."""
    del is_diff  # RF-07: una sola paleta falsa color en todo el MVP
    norm = normalize_percentile_1_99(data)

    r = np.interp(norm, _LUT_POINTS, _LUT_R)
    g = np.interp(norm, _LUT_POINTS, _LUT_G)
    b = np.interp(norm, _LUT_POINTS, _LUT_B)
    rgb = np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)

    pil_img = PilImage.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _pixel_to_sky(
    px: float,
    py: float,
    width: int,
    height: int,
    center_ra: float,
    center_dec: float,
    fov_deg: int,
) -> tuple[float, float]:
    """Convierte posicion en pixeles a RA/Dec aproximada dentro del cutout."""
    scale = float(fov_deg) / float(max(width, height))
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    dec_val = max(-90.0, min(90.0, center_dec + (cy - py) * scale))
    cos_dec = max(0.05, math.cos(math.radians(center_dec)))
    ra_val = (center_ra - (px - cx) * scale / cos_dec) % 360.0
    return round(ra_val, 6), round(dec_val, 6)


def compute_diff_and_candidates(
    img_a: Image,
    img_b: Image,
) -> tuple[np.ndarray, float, list[Candidate]]:
    """Calcula |B - A|, aplica umbral estadistico y clasifica candidatos (RF-08, RF-09)."""
    diff = np.abs(img_b.data - img_a.data).astype(np.float32)
    signed_diff = (img_b.data - img_a.data).astype(np.float32)
    diff_norm = normalize_percentile_1_99(diff)

    mean_val = float(np.mean(diff_norm))
    std_val = float(np.std(diff_norm))
    umbral = round(float(np.clip(mean_val + 3.5 * std_val, 0.35, 0.85)), 4)

    binary_mask = diff_norm >= umbral
    labeled, num_features = ndimage.label(binary_mask)

    h, w = diff.shape
    candidates: list[Candidate] = []
    window_radius = max(10, min(20, min(h, w) // 6))

    for label_idx in range(1, num_features + 1):
        comp_mask = labeled == label_idx
        area = int(np.sum(comp_mask))
        peak_val = float(np.max(diff_norm[comp_mask]))
        if area < 2 and peak_val < 0.75:
            continue

        # Centroide ponderado por intensidad normalizada
        weights = diff_norm * comp_mask
        ys, xs = np.nonzero(comp_mask)
        total_w = float(np.sum(weights[ys, xs])) or 1.0
        py = float(np.sum(ys * weights[ys, xs])) / total_w
        px = float(np.sum(xs * weights[ys, xs])) / total_w

        iy = int(round(py))
        ix = int(round(px))
        y0 = max(0, iy - window_radius)
        y1 = min(h, iy + window_radius + 1)
        x0 = max(0, ix - window_radius)
        x1 = min(w, ix + window_radius + 1)

        win = signed_diff[y0:y1, x0:x1]
        pos_peak = float(np.max(win))
        neg_peak = float(-np.min(win))

        # Si coexisten lobulo positivo y negativo cercanos, hay desplazamiento dipolar
        if max(pos_peak, neg_peak) > 1e-9 and (
            min(pos_peak, neg_peak) / max(pos_peak, neg_peak)
        ) >= 0.35:
            pos_idx = np.unravel_index(int(np.argmax(win)), win.shape)
            neg_idx = np.unravel_index(int(np.argmin(win)), win.shape)
            displacement_px = float(
                math.hypot(pos_idx[0] - neg_idx[0], pos_idx[1] - neg_idx[1])
            )
        else:
            displacement_px = 0.0

        brightness_delta = float(np.max(diff[comp_mask]))
        tipo, motivo = classify_candidate(displacement_px, brightness_delta)
        cand_ra, cand_dec = _pixel_to_sky(
            px, py, w, h, img_a.ra, img_a.dec, img_a.fov
        )
        candidates.append(
            Candidate(
                ra=cand_ra,
                dec=cand_dec,
                valor=round(peak_val, 4),
                motivo=motivo,
                tipo=tipo,
                x=ix,
                y=iy,
            )
        )

    candidates.sort(key=lambda c: c.valor, reverse=True)
    return diff, umbral, candidates[:10]


class FitsDiffProcessor:
    """Implementa DiffProcessor usando NumPy, SciPy y Pillow."""

    def compute_diff_and_render(
        self, a: Image, b: Image
    ) -> tuple[float, list[Candidate], bytes]:
        diff, umbral, candidates = compute_diff_and_candidates(a, b)
        png_bytes = render_false_color_png(diff, is_diff=True)
        return umbral, candidates, png_bytes
