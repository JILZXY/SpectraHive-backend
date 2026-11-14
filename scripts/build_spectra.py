# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Script offline de preparacion de datos: construye ADN Cosmico precalculado en data/spectra/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.domain.entities import TEST_OBJECTS_CATALOG

BANDAS_IR = [
    "0.75 um",
    "1.10 um",
    "1.65 um",
    "2.20 um",
    "3.40 um",
    "4.10 um",
    "4.80 um",
]

# Firmas visuales normalizadas (0..1) por perfil espectral infrarrojo de referencia (RF-14, RF-15)
_PRECOMPUTED_PROFILES: dict[str, tuple[list[float], str]] = {
    "barnards_star": (
        [0.54, 0.88, 1.00, 0.84, 0.46, 0.34, 0.28],
        "Firma visual infrarroja de referencia (enana roja M4V de alto movimiento propio). Uso comparativo visual, no identificacion quimica directa.",
    ),
    "wise_0855_0714": (
        [0.04, 0.08, 0.14, 0.19, 0.48, 0.86, 1.00],
        "Firma visual infrarroja de referencia (enana marron fria tipo Y, flujo dominante en infrarrojo medio). Uso comparativo visual, no identificacion quimica directa.",
    ),
    "epsilon_indi_b": (
        [0.12, 0.42, 0.65, 0.58, 0.62, 0.88, 1.00],
        "Firma visual infrarroja de referencia (sistema binario de enanas marrones T1/T6). Uso comparativo visual, no identificacion quimica directa.",
    ),
    "rw_aurigae": (
        [0.48, 0.68, 0.82, 0.94, 1.00, 0.91, 0.85],
        "Firma visual infrarroja de referencia (estrella joven T Tauri con exceso infrarrojo variable). Uso comparativo visual, no identificacion quimica directa.",
    ),
    "r_draconis": (
        [0.42, 0.85, 1.00, 0.92, 0.71, 0.58, 0.49],
        "Firma visual infrarroja de referencia (gigante roja variable tipo Mira, variacion de brillo). Uso comparativo visual, no identificacion quimica directa.",
    ),
}


def build_all_spectra(output_dir: Path | None = None) -> list[Path]:
    target_dir = output_dir or (ROOT_DIR / "data" / "spectra")
    target_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    index_entries: list[dict[str, object]] = []

    for spec in TEST_OBJECTS_CATALOG:
        valores, descripcion = _PRECOMPUTED_PROFILES[spec.slug]
        payload = {
            "objeto": spec.nombre,
            "slug": spec.slug,
            "tipo_prueba": spec.tipo_prueba,
            "bandas": BANDAS_IR,
            "valores": valores,
            "descripcion": descripcion,
        }
        out_path = target_dir / f"{spec.slug}.json"
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(out_path)
        index_entries.append(
            {
                "objeto": spec.nombre,
                "slug": spec.slug,
                "tipo_prueba": spec.tipo_prueba,
                "archivo": out_path.name,
            }
        )

    index_path = target_dir / "index.json"
    index_path.write_text(
        json.dumps({"objetos": index_entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(index_path)
    return written


if __name__ == "__main__":
    files = build_all_spectra()
    print(f"Generados {len(files)} archivos de ADN Cosmico en data/spectra/.")
