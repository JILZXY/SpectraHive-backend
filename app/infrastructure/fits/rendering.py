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
    """Calcula |B - A|, aplica umbral robusto sobre la resta cruda y clasifica candidatos (RF-08, RF-09)."""
    diff = np.abs(img_b.data - img_a.data).astype(np.float32)
    signed_diff = (img_b.data - img_a.data).astype(np.float32)

    # Umbral robusto sobre la resta cruda (evita saturar p99 con ruido de fondo)
    med = float(np.median(diff))
    mad = float(np.median(np.abs(diff - med)))
    sigma_mad = 1.4826 * mad
    std_raw = float(np.std(diff))
    umbral = round(max(med + 10.0 * sigma_mad, med + 5.0 * std_raw, 5.0), 4)

    binary_mask = diff >= umbral
    labeled, num_features = ndimage.label(binary_mask)

    h, w = diff.shape
    min_area = 4
    dipole_radius = max(12.0, min(h, w) / 4.0)

    # Recolectar solo componentes con area >= 4 px (sin ruido puntual)
    components: list[dict[str, object]] = []
    valid_mask = np.zeros_like(binary_mask, dtype=bool)
    for label_idx in range(1, num_features + 1):
        comp_mask = labeled == label_idx
        area = int(np.sum(comp_mask))
        if area < min_area:
            continue
        valid_mask |= comp_mask

        ys, xs = np.nonzero(comp_mask)
        weights = diff[ys, xs]
        integrated_flux = float(np.sum(weights))
        total_w = integrated_flux or 1.0
        py = float(np.sum(ys * weights)) / total_w
        px = float(np.sum(xs * weights)) / total_w

        comp_signed = signed_diff[comp_mask]
        pos_in_comp = float(np.max(comp_signed))
        neg_in_comp = float(-np.min(comp_signed))
        signed_sum = float(np.sum(comp_signed))
        peak_raw = float(np.max(diff[comp_mask]))

        components.append(
            {
                "mask": comp_mask,
                "ys": ys,
                "xs": xs,
                "py": py,
                "px": px,
                "flux": integrated_flux,
                "peak": peak_raw,
                "pos_in_comp": pos_in_comp,
                "neg_in_comp": neg_in_comp,
                "sign": 1 if signed_sum >= 0.0 else -1,
            }
        )

    scored_candidates: list[tuple[float, Candidate]] = []
    for idx, comp in enumerate(components):
        comp_mask = comp["mask"]
        ys = comp["ys"]
        xs = comp["xs"]
        py = float(comp["py"])
        px = float(comp["px"])
        integrated_flux = float(comp["flux"])
        peak_raw = float(comp["peak"])
        pos_in_comp = float(comp["pos_in_comp"])
        neg_in_comp = float(comp["neg_in_comp"])
        comp_sign = int(comp["sign"])

        # Medir desplazamiento dipolar solo con pixeles dentro de valid_mask
        if max(pos_in_comp, neg_in_comp) > 1e-9 and (
            min(pos_in_comp, neg_in_comp) / max(pos_in_comp, neg_in_comp)
        ) >= 0.35:
            comp_vals = signed_diff[ys, xs]
            pos_rel = int(np.argmax(comp_vals))
            neg_rel = int(np.argmin(comp_vals))
            displacement_px = float(
                math.hypot(ys[pos_rel] - ys[neg_rel], xs[pos_rel] - xs[neg_rel])
            )
        else:
            displacement_px = 0.0
            best_partner_dist = dipole_radius + 1.0
            for other_idx, other in enumerate(components):
                if other_idx == idx or int(other["sign"]) == comp_sign:
                    continue
                other_peak = float(other["peak"])
                if max(peak_raw, other_peak) <= 1e-9:
                    continue
                if min(peak_raw, other_peak) / max(peak_raw, other_peak) < 0.35:
                    continue
                dist = float(math.hypot(py - float(other["py"]), px - float(other["px"])))
                if dist <= dipole_radius and dist < best_partner_dist:
                    best_partner_dist = dist
                    displacement_px = dist

        tipo, motivo = classify_candidate(displacement_px, peak_raw)
        cand_ra, cand_dec = _pixel_to_sky(
            px, py, w, h, img_a.ra, img_a.dec, img_a.fov
        )
        scored_candidates.append(
            (
                integrated_flux,
                Candidate(
                    ra=cand_ra,
                    dec=cand_dec,
                    valor=round(peak_raw, 4),
                    motivo=motivo,
                    tipo=tipo,
                    x=int(round(px)),
                    y=int(round(py)),
                ),
            )
        )

    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    return diff, umbral, [cand for _, cand in scored_candidates[:10]]


class FitsDiffProcessor:
    """Implementa DiffProcessor usando NumPy, SciPy y Pillow."""

    def compute_diff_and_render(
        self, a: Image, b: Image
    ) -> tuple[float, list[Candidate], bytes]:
        diff, umbral, candidates = compute_diff_and_candidates(a, b)
        png_bytes = render_false_color_png(diff, is_diff=True)
        return umbral, candidates, png_bytes
