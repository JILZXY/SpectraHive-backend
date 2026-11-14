# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Script offline para descargar cutouts IRSA (DR1/QR3) o generar FITS fallback local."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.domain.entities import TEST_OBJECTS_CATALOG
from app.infrastructure.fits.loader import save_fits_image
from app.infrastructure.irsa.client import BoundedIrsaTapClient
from app.infrastructure.synthetic.fallback import generate_synthetic_field


def fetch_or_build_cutouts(
    output_dir: Path | None = None,
    offline: bool = False,
    offline_fallback: bool = True,
) -> list[Path]:
    target_dir = output_dir or (ROOT_DIR / "data" / "cutouts")
    target_dir.mkdir(parents=True, exist_ok=True)
    client = BoundedIrsaTapClient(timeout_seconds=10.0)
    generated: list[Path] = []

    for spec in TEST_OBJECTS_CATALOG:
        for epoch_tag in ("DR1", "QR3"):
            dest_path = target_dir / f"{spec.slug}_{epoch_tag}.fits"
            downloaded = False

            if not offline:
                url = client.query_spherex_cutout_url(spec.ra, spec.dec, epoch_tag)
                if url:
                    downloaded = client.download_fits(url, dest_path)

            if downloaded:
                generated.append(dest_path)
                continue

            if offline or offline_fallback:
                arr, _ = generate_synthetic_field(
                    ra=spec.ra,
                    dec=spec.dec,
                    fov=2,
                    epoch_canonical=epoch_tag,
                    size=128,
                )
                save_fits_image(
                    dest_path,
                    arr,
                    header_meta={
                        "OBJECT": spec.nombre,
                        "EPOCH": epoch_tag,
                        "CRVAL1": spec.ra,
                        "CRVAL2": spec.dec,
                        "FOVDEG": 2,
                        "SOURCE": "SINTETICO",
                        "SYNTHETC": True,
                    },
                )
                generated.append(dest_path)

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepara cutouts FITS DR1/QR3 de los 5 objetos de prueba."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="No consultar IRSA y generar directamente FITS fallback locales.",
    )
    parser.add_argument(
        "--offline-fallback",
        action="store_true",
        help="Intentar IRSA primero y generar FITS fallback si no hay respuesta.",
    )
    args = parser.parse_args()
    files = fetch_or_build_cutouts(
        offline=args.offline,
        offline_fallback=args.offline_fallback or not args.offline,
    )
    print(f"Preparados {len(files)} archivos FITS en data/cutouts/.")


if __name__ == "__main__":
    main()
