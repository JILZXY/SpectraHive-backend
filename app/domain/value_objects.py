# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Value objects del dominio: RaDec, Fov, Epoch, Image, Cutout."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

import numpy as np

from app.domain.errors import (
    InvalidCoordinatesError,
    InvalidEpochError,
    InvalidFovError,
)

_HMS_REGEX = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*(?:h|:|\s)\s*(\d+(?:\.\d+)?)?\s*(?:m|:|\s)?\s*(\d+(?:\.\d+)?)?\s*s?\s*$",
    re.IGNORECASE,
)
_DMS_REGEX = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*(?:d|°|:|\s)\s*(\d+(?:\.\d+)?)?\s*(?:m|'|′|:|\s)?\s*(\d+(?:\.\d+)?)?\s*(?:s|\"|″)?\s*$",
    re.IGNORECASE,
)


def _parse_ra_value(raw: float | int | str) -> float:
    """Convierte RA decimal o sexagesimal (h/m/s o hh:mm:ss) a grados [0, 360]."""
    if isinstance(raw, bool):
        raise InvalidCoordinatesError("RA no puede ser booleano.")
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if not text:
        raise InvalidCoordinatesError("RA no puede estar vacia.")

    # Numero decimal directo
    try:
        return float(text)
    except ValueError:
        pass

    # Si trae 'd' o '°' explicito, interpretar como grados sexagesimales
    if any(ch in text.lower() for ch in ("d", "°")):
        match = _DMS_REGEX.match(text)
        if not match:
            raise InvalidCoordinatesError(f"Formato de RA invalido: '{raw}'.")
        deg_part = float(match.group(1))
        min_part = float(match.group(2) or 0.0)
        sec_part = float(match.group(3) or 0.0)
        if min_part >= 60.0 or sec_part >= 60.0 or min_part < 0.0 or sec_part < 0.0:
            raise InvalidCoordinatesError(f"Minutos/segundos de RA fuera de rango: '{raw}'.")
        sign = -1.0 if text.lstrip().startswith("-") or deg_part < 0 else 1.0
        return sign * (abs(deg_part) + min_part / 60.0 + sec_part / 3600.0)

    # Formato horario (17h57m48.50s, 17h57m, 17:57:48.50)
    match = _HMS_REGEX.match(text)
    if not match:
        raise InvalidCoordinatesError(f"Formato de RA invalido: '{raw}'.")

    hours = float(match.group(1))
    minutes = float(match.group(2) or 0.0)
    seconds = float(match.group(3) or 0.0)
    if hours < 0.0 or hours > 24.0:
        raise InvalidCoordinatesError(f"Horas de RA fuera de rango [0, 24]: '{raw}'.")
    if minutes < 0.0 or minutes >= 60.0 or seconds < 0.0 or seconds >= 60.0:
        raise InvalidCoordinatesError(f"Minutos/segundos de RA fuera de rango: '{raw}'.")

    return (hours + minutes / 60.0 + seconds / 3600.0) * 15.0


def _parse_dec_value(raw: float | int | str) -> float:
    """Convierte Dec decimal o sexagesimal (d/m/s o dd:mm:ss) a grados [-90, +90]."""
    if isinstance(raw, bool):
        raise InvalidCoordinatesError("Dec no puede ser booleano.")
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip()
    if not text:
        raise InvalidCoordinatesError("Dec no puede estar vacia.")

    # Normalizar signo menos Unicode (−)
    text = text.replace("−", "-")

    try:
        return float(text)
    except ValueError:
        pass

    match = _DMS_REGEX.match(text)
    if not match:
        raise InvalidCoordinatesError(f"Formato de Dec invalido: '{raw}'.")

    deg_str = match.group(1)
    deg_part = float(deg_str)
    min_part = float(match.group(2) or 0.0)
    sec_part = float(match.group(3) or 0.0)
    if min_part < 0.0 or min_part >= 60.0 or sec_part < 0.0 or sec_part >= 60.0:
        raise InvalidCoordinatesError(f"Minutos/segundos de Dec fuera de rango: '{raw}'.")

    sign = -1.0 if deg_str.lstrip().startswith("-") or deg_part < 0 else 1.0
    return sign * (abs(deg_part) + min_part / 60.0 + sec_part / 3600.0)


@dataclass(frozen=True)
class RaDec:
    """Coordenadas ecuatoriales J2000 en grados decimales (RF-01, RN-05)."""

    ra: float
    dec: float

    def __post_init__(self) -> None:
        if isinstance(self.ra, bool) or isinstance(self.dec, bool):
            raise InvalidCoordinatesError("RA y Dec deben ser numericas.")
        ra_f = float(self.ra)
        dec_f = float(self.dec)
        if not math.isfinite(ra_f) or not math.isfinite(dec_f):
            raise InvalidCoordinatesError("RA y Dec deben ser finitas.")
        if ra_f < 0.0 or ra_f > 360.0:
            raise InvalidCoordinatesError(
                f"RA fuera de rango valido (0 a 360 grados): {ra_f}."
            )
        if dec_f < -90.0 or dec_f > 90.0:
            raise InvalidCoordinatesError(
                f"Dec fuera de rango valido (-90 a +90 grados): {dec_f}."
            )
        object.__setattr__(self, "ra", ra_f)
        object.__setattr__(self, "dec", dec_f)

    @classmethod
    def parse(cls, ra: float | int | str, dec: float | int | str) -> "RaDec":
        """Crea RaDec aceptando decimal o sexagesimal (RF-01, RF-03)."""
        return cls(ra=_parse_ra_value(ra), dec=_parse_dec_value(dec))

    def propagate(
        self,
        pm_ra_arcsec_yr: float,
        pm_dec_arcsec_yr: float,
        years: float = 26.9,
    ) -> "RaDec":
        """Propaga coordenadas J2000 por movimiento propio hasta la epoca destino (RN-05)."""
        delta_dec_deg = (pm_dec_arcsec_yr * years) / 3600.0
        new_dec = max(-90.0, min(90.0, self.dec + delta_dec_deg))
        cos_dec = math.cos(math.radians(self.dec))
        if abs(cos_dec) > 1e-6:
            delta_ra_deg = (pm_ra_arcsec_yr * years) / (3600.0 * cos_dec)
        else:
            delta_ra_deg = 0.0
        new_ra = (self.ra + delta_ra_deg) % 360.0
        return RaDec(ra=round(new_ra, 6), dec=round(new_dec, 6))


@dataclass(frozen=True)
class Fov:
    """Campo de vision permitido en el MVP: solo 1 o 2 grados (RF-02, RN-11)."""

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool):
            raise InvalidFovError("FOV invalido: solo se permiten los valores 1 o 2.")
        try:
            int_val = int(self.value)
        except (TypeError, ValueError) as exc:
            raise InvalidFovError(
                f"FOV invalido ({self.value}): solo se permiten 1 o 2."
            ) from exc
        if isinstance(self.value, float) and self.value != float(int_val):
            raise InvalidFovError(
                f"FOV invalido ({self.value}): solo se permiten valores enteros 1 o 2."
            )
        if int_val not in (1, 2):
            raise InvalidFovError(
                f"FOV fuera de alcance ({int_val}): en el MVP solo se permiten 1 o 2."
            )
        object.__setattr__(self, "value", int_val)


@dataclass(frozen=True)
class Epoch:
    """Identificador de epoca astronomica (hoy A/DR1 y B/QR3)."""

    name: str
    canonical: str
    alias: str

    def __init__(self, name: str) -> None:
        cleaned = (name or "").strip().upper()
        if not cleaned:
            raise InvalidEpochError("La epoca no puede estar vacia.")
        if cleaned in ("A", "EPOCA_A", "EPOCA A", "DR1"):
            canonical = "DR1"
            alias = "A"
        elif cleaned in ("B", "EPOCA_B", "EPOCA B", "QR3"):
            canonical = "QR3"
            alias = "B"
        else:
            canonical = cleaned
            alias = cleaned
        object.__setattr__(self, "name", name.strip())
        object.__setattr__(self, "canonical", canonical)
        object.__setattr__(self, "alias", alias)


@dataclass(frozen=True)
class Image:
    """Matriz 2D de imagen astronomica y metadatos minimos (CoVe V2)."""

    data: np.ndarray
    ra: float
    dec: float
    fov: int
    epoch: str
    source: Literal["irsa", "sintetico"]
    object_name: str | None = None


@dataclass(frozen=True)
class Cutout:
    """Cutout listo para servir al frontend junto con sus metadatos."""

    image: Image
    png_bytes: bytes
    ra: float
    dec: float
    fov: int
    epoca: str
    fuente: Literal["irsa", "sintetico"]
    objeto: str | None = None
