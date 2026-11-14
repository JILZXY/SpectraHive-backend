# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Alineacion por desplazamiento entero de pixeles sin reproyeccion general (RN-09)."""

from __future__ import annotations

import numpy as np

from app.domain.value_objects import Image


class IntegerShiftAlignment:
    """Calcula y aplica desplazamiento entero (dy, dx) acotado entre A y B."""

    def __init__(self, max_shift: int = 5) -> None:
        self._max_shift = max_shift

    def align(self, a: Image, b: Image) -> tuple[Image, Image, tuple[int, int]]:
        if a.data.shape != b.data.shape:
            min_h = min(a.data.shape[0], b.data.shape[0])
            min_w = min(a.data.shape[1], b.data.shape[1])
            a_arr = a.data[:min_h, :min_w]
            b_arr = b.data[:min_h, :min_w]
        else:
            a_arr = a.data
            b_arr = b.data

        h, w = a_arr.shape
        margin = self._max_shift
        if h <= 2 * margin + 4 or w <= 2 * margin + 4:
            return (
                Image(
                    data=a_arr,
                    ra=a.ra,
                    dec=a.dec,
                    fov=a.fov,
                    epoch=a.epoch,
                    source=a.source,
                    object_name=a.object_name,
                ),
                Image(
                    data=b_arr,
                    ra=b.ra,
                    dec=b.dec,
                    fov=b.fov,
                    epoch=b.epoch,
                    source=b.source,
                    object_name=b.object_name,
                ),
                (0, 0),
            )

        a_bg = a_arr - float(np.median(a_arr))
        b_bg = b_arr - float(np.median(b_arr))

        ref = a_bg[margin : h - margin, margin : w - margin]
        ref_norm = float(np.linalg.norm(ref)) or 1.0

        best_score = -1.0
        best_shift = (0, 0)

        for dy in range(-margin, margin + 1):
            for dx in range(-margin, margin + 1):
                patch = b_bg[
                    margin + dy : h - margin + dy,
                    margin + dx : w - margin + dx,
                ]
                denom = ref_norm * (float(np.linalg.norm(patch)) or 1.0)
                score = float(np.sum(ref * patch)) / denom
                # Desempate ligero a favor de (0, 0) si el par ya viene alineado
                if dy == 0 and dx == 0:
                    score += 1e-6
                if score > best_score:
                    best_score = score
                    best_shift = (dy, dx)

        dy, dx = best_shift
        if dy == 0 and dx == 0:
            aligned_b_arr = b_arr.copy()
        else:
            bg_fill = float(np.median(b_arr))
            aligned_b_arr = np.full_like(b_arr, fill_value=bg_fill)
            src_y0 = max(0, dy)
            src_y1 = h + min(0, dy)
            src_x0 = max(0, dx)
            src_x1 = w + min(0, dx)
            dst_y0 = max(0, -dy)
            dst_y1 = h + min(0, -dy)
            dst_x0 = max(0, -dx)
            dst_x1 = w + min(0, -dx)
            aligned_b_arr[dst_y0:dst_y1, dst_x0:dst_x1] = b_arr[src_y0:src_y1, src_x0:src_x1]

        aligned_a = Image(
            data=a_arr.astype(np.float32),
            ra=a.ra,
            dec=a.dec,
            fov=a.fov,
            epoch=a.epoch,
            source=a.source,
            object_name=a.object_name,
        )
        aligned_b = Image(
            data=aligned_b_arr.astype(np.float32),
            ra=b.ra,
            dec=b.dec,
            fov=b.fov,
            epoch=b.epoch,
            source=b.source,
            object_name=b.object_name,
        )
        return aligned_a, aligned_b, best_shift
