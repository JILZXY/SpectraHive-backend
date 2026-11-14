# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Script offline para consultar IRSA SIA (astroquery) y descargar dos MEFs 2040x2040 por objeto."""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from astropy.io import fits

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.domain.entities import TEST_OBJECTS_CATALOG
from app.infrastructure.fits.loader import save_fits_image
from app.infrastructure.irsa.client import IrsaSiaClient
from app.infrastructure.synthetic.fallback import generate_synthetic_field


def _remove_stale_synthetic_files(target_dir: Path, slug: str) -> None:
    for old_tag in ("DR1", "QR3"):
        old_path = target_dir / f"{slug}_{old_tag}.fits"
        if old_path.is_file():
            old_path.unlink()


def _find_valid_irsa_mefs(target_dir: Path, slug: str) -> list[Path]:
    candidates = sorted(
        target_dir.glob(f"{slug}_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*.fits")
    )
    valid: list[Path] = []
    for path in candidates:
        try:
            with fits.open(path, memmap=False) as hdul:
                if "IMAGE" not in hdul or hdul["IMAGE"].data is None:
                    continue
                img = hdul["IMAGE"]
                if tuple(img.data.shape) != (2040, 2040):
                    continue
                if bool(img.header.get("SYNTHETC", False)):
                    continue
                if str(img.header.get("SOURCE", "")).strip().upper() != "IRSA":
                    continue
                valid.append(path)
        except Exception:
            continue
    return valid


def fetch_or_build_cutouts(
    output_dir: Path | None = None,
    offline: bool = False,
    offline_fallback: bool = False,
) -> list[Path]:
    target_dir = output_dir or (ROOT_DIR / "data" / "cutouts")
    target_dir.mkdir(parents=True, exist_ok=True)
    client = IrsaSiaClient(timeout_seconds=120.0)
    generated: list[Path] = []

    for spec in TEST_OBJECTS_CATALOG:
        if not offline:
            existing = _find_valid_irsa_mefs(target_dir, spec.slug)
            if len(existing) >= 2:
                _remove_stale_synthetic_files(target_dir, spec.slug)
                print(
                    f"\n[{spec.nombre}] MEFs IRSA reales ya presentes en {target_dir.name}: "
                    f"{', '.join(p.name for p in existing[:2])}"
                )
                for path in existing[:2]:
                    buf = io.StringIO()
                    fits.info(path, output=buf)
                    print(buf.getvalue().rstrip())
                generated.extend(existing[:2])
                continue
            try:
                obs_a, obs_b = client.select_two_epochs(spec.ra, spec.dec)
                dt_days = obs_b.t_min - obs_a.t_min
                print(
                    f"\n[{spec.nombre}] Par seleccionado: "
                    f"{obs_a.fecha} ({obs_a.collection}, {obs_a.detector}) <-> "
                    f"{obs_b.fecha} ({obs_b.collection}, {obs_b.detector}) | "
                    f"dt={dt_days:.1f} dias"
                )
                downloaded_pair: list[Path] = []
                for obs in (obs_a, obs_b):
                    dest_path = target_dir / f"{spec.slug}_{obs.fecha}.fits"
                    saved_path, fits_info_text = client.download_and_tag_mef(
                        obs=obs,
                        dest_path=dest_path,
                        object_name=spec.nombre,
                    )
                    print(fits_info_text.rstrip())
                    downloaded_pair.append(saved_path)

                _remove_stale_synthetic_files(target_dir, spec.slug)
                generated.extend(downloaded_pair)
                continue
            except Exception as exc:
                if not offline_fallback:
                    raise RuntimeError(
                        f"Fallo descarga SIA IRSA para {spec.nombre}: {exc}"
                    ) from exc
                print(
                    f"[WARN] SIA IRSA fallo para {spec.nombre} ({exc}); "
                    "generando fallback sintetico local."
                )

        if offline or offline_fallback:
            for epoch_tag in ("DR1", "QR3"):
                dest_path = target_dir / f"{spec.slug}_{epoch_tag}.fits"
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
        description="Consulta IRSA SIA con astroquery y descarga dos MEFs por objeto."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="No consultar IRSA y generar FITS fallback locales.",
    )
    parser.add_argument(
        "--offline-fallback",
        action="store_true",
        help="Si IRSA SIA no responde (ej. build Docker sin red), generar FITS fallback locales.",
    )
    args = parser.parse_args()
    files = fetch_or_build_cutouts(
        offline=args.offline,
        offline_fallback=args.offline_fallback,
    )
    print(f"\nPreparados {len(files)} archivos FITS en data/cutouts/.")


if __name__ == "__main__":
    main()
