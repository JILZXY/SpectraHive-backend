# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Entidades del dominio y catalogo de objetos de prueba (J2000)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Quadrant:
    """Cuadrante de la cola fija (tabla cuadrantes)."""

    id: str
    nombre: str
    ra: float
    dec: float
    fov: int
    epoca_a: str
    epoca_b: str
    estado: Literal["pendiente", "confirmado", "descartado"]
    es_objeto_prueba: bool
    tipo_prueba: Literal["movimiento", "brillo"] | None
    url_dinamica: str | None = None


@dataclass(frozen=True)
class Report:
    """Reporte de anomalia o cuadrante limpio (tabla reportes, RN-07)."""

    id: str | None
    cuadrante_id: str
    ra: float
    dec: float
    tipo: Literal["movimiento", "brillo", "limpio"]
    creado_en: str | None = None


@dataclass(frozen=True)
class Validation:
    """Voto de validacion cruzada sobre un reporte (tabla validaciones, RF-12, RF-13)."""

    id: str | None
    reporte_id: str
    coincide: bool
    es_simulado: bool = False
    creado_en: str | None = None


@dataclass(frozen=True)
class Candidate:
    """Candidato detectado tras restar |B - A| y aplicar umbral (RF-09)."""

    ra: float
    dec: float
    valor: float
    motivo: str
    tipo: str = "movimiento"
    x: int | None = None
    y: int | None = None


@dataclass(frozen=True)
class SpectralSignature:
    """Firma espectral precalculada del ADN Cosmico (RF-14, RF-15)."""

    objeto: str
    bandas: list[str]
    valores: list[float]
    tipo_prueba: str | None = None
    descripcion: str | None = None


@dataclass(frozen=True)
class TestObjectSpec:
    """Especificacion inmutable de cada uno de los 5 objetos de prueba (00 §5)."""

    slug: str
    nombre: str
    tipo_prueba: Literal["movimiento", "brillo"]
    ra: float
    dec: float
    pm_ra_arcsec_yr: float
    pm_dec_arcsec_yr: float
    url_dinamica: str
    clasificacion: str


TEST_OBJECTS_CATALOG: tuple[TestObjectSpec, ...] = (
    TestObjectSpec(
        slug="barnards_star",
        nombre="Barnard's Star",
        tipo_prueba="movimiento",
        ra=269.452075,
        dec=4.693365,
        pm_ra_arcsec_yr=-0.802,
        pm_dec_arcsec_yr=10.362,
        url_dinamica="/?ra=17h57m&dec=+4d41m&fov=2",
        clasificacion="Estrella de alto movimiento propio (~10.39\"/ano)",
    ),
    TestObjectSpec(
        slug="wise_0855_0714",
        nombre="WISE 0855-0714",
        tipo_prueba="movimiento",
        ra=133.795133,
        dec=-7.245146,
        pm_ra_arcsec_yr=-8.118,
        pm_dec_arcsec_yr=0.680,
        url_dinamica="/?ra=08h55m&dec=-7d14m&fov=2",
        clasificacion="Enana marron fria de alto movimiento propio (~8.15\"/ano)",
    ),
    TestObjectSpec(
        slug="epsilon_indi_b",
        nombre="Epsilon Indi B",
        tipo_prueba="movimiento",
        ra=331.044147,
        dec=-56.782844,
        pm_ra_arcsec_yr=3.961,
        pm_dec_arcsec_yr=-2.502,
        url_dinamica="/?ra=22h04m&dec=-56d47m&fov=2",
        clasificacion="Sistema binario de enanas marrones (~4.68\"/ano)",
    ),
    TestObjectSpec(
        slug="rw_aurigae",
        nombre="RW Aurigae",
        tipo_prueba="brillo",
        ra=76.956067,
        dec=30.401326,
        pm_ra_arcsec_yr=0.0,
        pm_dec_arcsec_yr=0.0,
        url_dinamica="/?ra=05h07m&dec=+30d24m&fov=2",
        clasificacion="Estrella variable T Tauri (cambio de brillo, sin movimiento)",
    ),
    TestObjectSpec(
        slug="r_draconis",
        nombre="R Draconis",
        tipo_prueba="brillo",
        ra=248.167625,
        dec=66.754972,
        pm_ra_arcsec_yr=0.0,
        pm_dec_arcsec_yr=0.0,
        url_dinamica="/?ra=16h32m&dec=+66d45m&fov=2",
        clasificacion="Estrella variable Mira (periodo ~8 meses, cambio de brillo)",
    ),
)


def _angular_separation_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Separacion angular aproximada en grados sobre la esfera celeste."""
    r1, d1 = math.radians(ra1), math.radians(dec1)
    r2, d2 = math.radians(ra2), math.radians(dec2)
    cos_sep = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))


def match_test_object(
    ra: float, dec: float, tolerance_deg: float = 0.5
) -> TestObjectSpec | None:
    """Devuelve el objeto de prueba mas cercano dentro del radio de tolerancia."""
    best_obj: TestObjectSpec | None = None
    best_dist = tolerance_deg
    for obj in TEST_OBJECTS_CATALOG:
        dist = _angular_separation_deg(ra, dec, obj.ra, obj.dec)
        if dist <= best_dist:
            best_dist = dist
            best_obj = obj
    return best_obj


def find_test_object_by_name(name: str) -> TestObjectSpec | None:
    """Busca un objeto de prueba por nombre completo, slug o alias comun."""
    normalized = (name or "").strip().lower().replace("'", "").replace("_", " ").replace("-", " ")
    if not normalized:
        return None
    for obj in TEST_OBJECTS_CATALOG:
        candidates = {
            obj.nombre.lower().replace("'", ""),
            obj.slug.replace("_", " "),
            obj.nombre.lower().replace("'", "").replace("-", " "),
        }
        if normalized in candidates:
            return obj
        if normalized in obj.nombre.lower().replace("'", ""):
            return obj
    return None
