# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Cliente SIA de IRSA con astroquery para localizar y descargar MEFs SPHEREx (2040x2040)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

import astropy.units as u
import httpx
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table, vstack
from astropy.time import Time
from astroquery.ipac.irsa import Irsa

SPHEREX_COLLECTIONS = ["spherex_dr1", "spherex_qr3"]
_DETECTOR_REGEX = re.compile(r"(?:SPHEREx-D|det(?:ector)?[_-]?|/+)([1-6])(?:/|$|\b)", re.IGNORECASE)


@dataclass(frozen=True)
class SiaObservation:
    """Registro SIA normalizado para seleccion de epoca y detector."""

    t_min: float
    fecha: str
    detector: str
    collection: str
    access_url: str
    s_xel1: int | None
    s_xel2: int | None


def _extract_detector(row: object) -> str:
    """Extrae el identificador de detector (D1..D6) desde las columnas SIA o URL."""
    for field in ("energy_bandpassname", "instrument_name", "obs_id", "access_url"):
        try:
            raw = str(row[field] or "").strip()  # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            continue
        if not raw or raw == "--":
            continue
        match = _DETECTOR_REGEX.search(raw)
        if match:
            return f"D{match.group(1)}"
    return "UNKNOWN"


def _row_to_observation(row: object) -> SiaObservation | None:
    """Convierte una fila de la tabla SIA a SiaObservation si es un MEF de ciencia valido."""
    try:
        access_url = str(row["access_url"] or "").strip()  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return None
    if not access_url.startswith("http"):
        return None

    try:
        access_fmt = str(row["access_format"] or "").lower()  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        access_fmt = ""
    if access_fmt and "fits" not in access_fmt and ".fits" not in access_url.lower():
        return None

    try:
        subtype = str(row["dataproduct_subtype"] or "").strip().lower()  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        subtype = ""
    if subtype and subtype != "science":
        return None

    try:
        t_min_val = float(row["t_min"])  # type: ignore[index]
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    try:
        fecha = Time(t_min_val, format="mjd").strftime("%Y-%m-%d")
    except Exception:
        return None

    try:
        col_name = str(row["obs_collection"] or "").strip()  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        col_name = ""

    def _opt_int(col: str) -> int | None:
        try:
            val = row[col]  # type: ignore[index]
            return int(val) if val is not None and str(val) != "--" else None
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    return SiaObservation(
        t_min=t_min_val,
        fecha=fecha,
        detector=_extract_detector(row),
        collection=col_name,
        access_url=access_url,
        s_xel1=_opt_int("s_xel1"),
        s_xel2=_opt_int("s_xel2"),
    )


def select_epoch_pair(
    observations: list[SiaObservation],
    target_days: float = 182.5,
) -> tuple[SiaObservation, SiaObservation]:
    """Elige un par (A, B) separado ~6 meses en fecha (t_min) y mismo detector si es posible."""
    if len(observations) < 2:
        raise ValueError("Se requieren al menos 2 observaciones SIA para formar un par de epocas.")

    # Deduplicar por (fecha, detector) conservando la exposicion mas representativa
    by_date_det: dict[tuple[str, str], SiaObservation] = {}
    for obs in sorted(observations, key=lambda o: o.t_min):
        key = (obs.fecha, obs.detector)
        if key not in by_date_det:
            by_date_det[key] = obs

    candidates = sorted(by_date_det.values(), key=lambda o: o.t_min)
    best_score: tuple[int, float, float] | None = None
    best_pair: tuple[SiaObservation, SiaObservation] | None = None

    for idx_a in range(len(candidates)):
        obs_a = candidates[idx_a]
        for idx_b in range(idx_a + 1, len(candidates)):
            obs_b = candidates[idx_b]
            if obs_a.fecha == obs_b.fecha:
                continue
            dt_days = obs_b.t_min - obs_a.t_min
            if dt_days <= 0:
                continue

            same_det = obs_a.detector != "UNKNOWN" and obs_a.detector == obs_b.detector
            in_six_month_band = 120.0 <= dt_days <= 245.0
            wide_sep = dt_days >= 60.0

            if same_det and in_six_month_band:
                tier = 0
            elif same_det and wide_sep:
                tier = 1
            elif in_six_month_band:
                tier = 2
            elif wide_sep:
                tier = 3
            else:
                tier = 4

            score = (tier, abs(dt_days - target_days), -dt_days)
            if best_score is None or score < best_score:
                best_score = score
                best_pair = (obs_a, obs_b)

    if best_pair is None:
        raise ValueError("No se encontraron dos fechas distintas (t_min) en la consulta SIA.")
    return best_pair


class IrsaSiaClient:
    """Consulta IRSA SIAv2 con astroquery y descarga MEFs 2040x2040 verificados."""

    def __init__(self, timeout_seconds: float = 90.0) -> None:
        self._timeout = timeout_seconds

    def query_observations(
        self,
        ra_deg: float,
        dec_deg: float,
        collections: list[str] | None = None,
    ) -> list[SiaObservation]:
        coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
        target_collections = collections or SPHEREX_COLLECTIONS

        try:
            table = Irsa.query_sia(
                pos=(coord, 1 * u.arcsec),
                collection=target_collections,
            )
        except Exception:
            tables: list[Table] = []
            for col in target_collections:
                sub = Irsa.query_sia(pos=(coord, 1 * u.arcsec), collection=col)
                if len(sub) > 0:
                    tables.append(sub)
            table = vstack(tables) if tables else Table()

        observations: list[SiaObservation] = []
        for row in table:
            obs = _row_to_observation(row)
            if obs is not None:
                observations.append(obs)
        return observations

    def select_two_epochs(
        self, ra_deg: float, dec_deg: float
    ) -> tuple[SiaObservation, SiaObservation]:
        observations = self.query_observations(ra_deg=ra_deg, dec_deg=dec_deg)
        return select_epoch_pair(observations)

    def download_and_tag_mef(
        self,
        obs: SiaObservation,
        dest_path: Path,
        object_name: str,
    ) -> tuple[Path, str]:
        """Descarga un MEF, marca SOURCE=IRSA en cabecera y verifica IMAGE 2040x2040."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(obs.access_url)
            resp.raise_for_status()
            if not resp.content:
                raise ValueError(f"Descarga vacia desde {obs.access_url}")
            dest_path.write_bytes(resp.content)

        with fits.open(dest_path, mode="update") as hdul:
            if "IMAGE" not in hdul:
                raise ValueError(
                    f"El FITS '{dest_path}' no contiene extension 'IMAGE'."
                )
            image_hdu = hdul["IMAGE"]
            if image_hdu.data is None or tuple(image_hdu.data.shape) != (2040, 2040):
                shape = None if image_hdu.data is None else tuple(image_hdu.data.shape)
                raise ValueError(
                    f"La extension IMAGE de '{dest_path}' tiene forma {shape}, se esperaba (2040, 2040)."
                )

            for hdr in (hdul[0].header, image_hdu.header):
                hdr["SOURCE"] = ("IRSA", "Data origin verified via astroquery SIA")
                hdr["SYNTHETC"] = (False, "Real IRSA SPHEREx MEF observation")
                hdr["OBJECT"] = object_name
                hdr["EPOCH"] = obs.fecha
                hdr["DETECTOR"] = obs.detector
                hdr["COLLECTN"] = obs.collection
            hdul.flush()

        info_buf = io.StringIO()
        fits.info(dest_path, output=info_buf)
        return dest_path, info_buf.getvalue()
