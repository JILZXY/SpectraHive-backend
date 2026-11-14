# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Pruebas unitarias puras del dominio (RN-01..RN-14) y regla de dependencia."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from app.domain.entities import TEST_OBJECTS_CATALOG, Quadrant, Validation
from app.domain.errors import (
    InvalidCoordinatesError,
    InvalidFovError,
    InvalidReportTypeError,
    ReportTypeMismatchError,
)
from app.domain.rules import (
    classify_candidate,
    confirm_report,
    determine_quadrant_state_after_validation,
    ensure_simulated_vote_labelled,
    validate_report_type,
)
from app.domain.value_objects import Epoch, Fov, RaDec


def _make_quadrant(nombre: str, tipo_prueba: str) -> Quadrant:
    return Quadrant(
        id="11111111-1111-1111-1111-111111111111",
        nombre=nombre,
        ra=269.452075,
        dec=4.693365,
        fov=2,
        epoca_a="DR1",
        epoca_b="QR3",
        estado="pendiente",
        es_objeto_prueba=True,
        tipo_prueba=tipo_prueba,  # type: ignore[arg-type]
    )


def test_radec_valid_decimal_and_sexagesimal() -> None:
    coords = RaDec.parse(269.452075, 4.693365)
    assert math.isclose(coords.ra, 269.452075, abs_tol=1e-6)
    assert math.isclose(coords.dec, 4.693365, abs_tol=1e-6)

    # Atajos RF-03 / §5
    barnard_short = RaDec.parse("17h57m", "+4d41m")
    assert 269.0 < barnard_short.ra < 270.0
    assert 4.6 < barnard_short.dec < 4.8

    wise_short = RaDec.parse("08h55m", "-7d14m")
    assert 133.0 < wise_short.ra < 134.5
    assert -7.5 < wise_short.dec < -7.0


@pytest.mark.parametrize(
    "ra,dec",
    [
        (-0.1, 0.0),
        (360.1, 0.0),
        (100.0, -90.1),
        (100.0, 90.1),
        ("25h00m", "+10d00m"),
        ("invalid", "0.0"),
        ("", "0.0"),
    ],
)
def test_radec_rejects_out_of_range_and_invalid(ra, dec) -> None:
    with pytest.raises(InvalidCoordinatesError):
        RaDec.parse(ra, dec)


def test_radec_proper_motion_propagation_rn05() -> None:
    barnard = TEST_OBJECTS_CATALOG[0]
    j2000 = RaDec(ra=barnard.ra, dec=barnard.dec)
    epoch_2026 = j2000.propagate(
        pm_ra_arcsec_yr=barnard.pm_ra_arcsec_yr,
        pm_dec_arcsec_yr=barnard.pm_dec_arcsec_yr,
        years=26.9,
    )
    # Barnard ~10.39"/yr * 26.9 yr = ~279.5" = ~4.66 arcmin (~0.077 deg)
    delta_arcmin = math.hypot(
        (epoch_2026.ra - j2000.ra) * math.cos(math.radians(j2000.dec)),
        epoch_2026.dec - j2000.dec,
    ) * 60.0
    assert 4.4 < delta_arcmin < 5.0


def test_fov_only_allows_1_and_2() -> None:
    assert Fov(1).value == 1
    assert Fov(2).value == 2
    for invalid in (0, 3, -1, 1.5, True, "abc"):
        with pytest.raises(InvalidFovError):
            Fov(invalid)  # type: ignore[arg-type]


def test_epoch_aliases() -> None:
    assert Epoch("A").canonical == "DR1"
    assert Epoch("B").canonical == "QR3"
    assert Epoch("DR1").alias == "A"
    assert Epoch("QR3").alias == "B"


def test_validate_report_type_rn02_rn03_rf11() -> None:
    barnard = _make_quadrant("Barnard's Star", "movimiento")
    rw_aurigae = _make_quadrant("RW Aurigae", "brillo")
    r_draconis = _make_quadrant("R Draconis", "brillo")

    # Validos
    validate_report_type(barnard, "movimiento")
    validate_report_type(barnard, "limpio")
    validate_report_type(rw_aurigae, "brillo")
    validate_report_type(rw_aurigae, "limpio")
    validate_report_type(r_draconis, "brillo")

    # Cruzados invalidos (RN-02 / RN-03)
    with pytest.raises(ReportTypeMismatchError):
        validate_report_type(rw_aurigae, "movimiento")
    with pytest.raises(ReportTypeMismatchError):
        validate_report_type(r_draconis, "movimiento")
    with pytest.raises(ReportTypeMismatchError):
        validate_report_type(barnard, "brillo")

    with pytest.raises(InvalidReportTypeError):
        validate_report_type(barnard, "desconocido")


def test_confirm_report_requires_3_votes_rf12_rn06() -> None:
    assert confirm_report(0) is False
    assert confirm_report(1) is False
    assert confirm_report(2) is False
    assert confirm_report(3) is True
    assert confirm_report(5) is True

    assert determine_quadrant_state_after_validation("pendiente", False) == "pendiente"
    assert determine_quadrant_state_after_validation("pendiente", True) == "confirmado"


def test_classify_candidate_and_simulated_label() -> None:
    tipo_fast, motivo_fast = classify_candidate(displacement_px=6.5, brightness_delta=90.0)
    assert tipo_fast == "movimiento"
    assert "6.5 px" in motivo_fast

    tipo_slow, motivo_slow = classify_candidate(displacement_px=1.6, brightness_delta=70.0)
    assert tipo_slow == "lento"
    assert "Planet X" in motivo_slow

    tipo_bright, motivo_bright = classify_candidate(displacement_px=0.2, brightness_delta=120.0)
    assert tipo_bright == "brillo"
    assert "brillo" in motivo_bright.lower()

    labelled = ensure_simulated_vote_labelled(
        Validation(id="v1", reporte_id="r1", coincide=True, es_simulado=True)
    )
    assert labelled["es_simulado"] is True
    assert labelled["etiqueta"] == "simulado"


def test_clean_architecture_dependency_rule() -> None:
    """Verifica que domain/ y application/ no importen frameworks ni infraestructura."""
    forbidden = {
        "fastapi",
        "astropy",
        "supabase",
        "psycopg",
        "psycopg_pool",
        "sqlalchemy",
        "scipy",
        "PIL",
    }
    root = Path(__file__).resolve().parents[1] / "app"

    for layer_name in ("domain", "application"):
        layer_dir = root / layer_name
        for py_file in layer_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        assert top not in forbidden, f"{py_file} importa {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    assert top not in forbidden, f"{py_file} importa {node.module}"
                    if layer_name == "domain":
                        assert not node.module.startswith("app.application")
                        assert not node.module.startswith("app.infrastructure")
                        assert not node.module.startswith("app.api")
                    elif layer_name == "application":
                        assert not node.module.startswith("app.infrastructure")
                        assert not node.module.startswith("app.api")
