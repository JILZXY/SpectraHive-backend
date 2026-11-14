# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Pruebas e2e de endpoints FastAPI con TestClient."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import (
    get_cutout_provider,
    get_optional_quadrant_repo,
    get_quadrant_repo,
    get_report_repo,
    get_spectral_provider,
)
from app.infrastructure.irsa.precomputed import PrecomputedSpectralProvider
from app.infrastructure.synthetic.fallback import SyntheticCutoutProvider
from app.main import app
from scripts.build_spectra import build_all_spectra
from tests.test_use_cases import InMemoryQuadrantRepo, InMemoryReportRepo


def test_api_endpoints_end_to_end(tmp_path: Path) -> None:
    spectra_dir = tmp_path / "spectra"
    build_all_spectra(spectra_dir)

    q_repo = InMemoryQuadrantRepo()
    r_repo = InMemoryReportRepo(q_repo)

    app.dependency_overrides[get_cutout_provider] = lambda: SyntheticCutoutProvider()
    app.dependency_overrides[get_spectral_provider] = lambda: PrecomputedSpectralProvider(
        spectra_dir
    )
    app.dependency_overrides[get_quadrant_repo] = lambda: q_repo
    app.dependency_overrides[get_optional_quadrant_repo] = lambda: q_repo
    app.dependency_overrides[get_report_repo] = lambda: r_repo

    try:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            # 1. GET /cutout
            cutout = client.get(
                "/cutout",
                params={"ra": "17h57m", "dec": "+4d41m", "fov": 2, "epoca": "A"},
            )
            assert cutout.status_code == 200
            cutout_json = cutout.json()
            assert cutout_json["fuente"] == "sintetico"
            assert cutout_json["fov"] == 2
            assert cutout_json["imagen"].startswith("data:image/png;base64,")

            cutout_png = client.get(
                "/cutout",
                params={"ra": "269.452075", "dec": "4.693365", "fov": 2, "format": "png"},
            )
            assert cutout_png.status_code == 200
            assert cutout_png.headers["content-type"] == "image/png"

            bad_coord = client.get(
                "/cutout",
                params={"ra": "400", "dec": "0", "fov": 2},
            )
            assert bad_coord.status_code == 400

            bad_fov = client.get(
                "/cutout",
                params={"ra": "10", "dec": "10", "fov": 5},
            )
            assert bad_fov.status_code == 400

            # 2. POST /diff
            diff = client.post(
                "/diff",
                json={"cuadrante_id": "Barnard's Star", "epoca_a": "A", "epoca_b": "B"},
            )
            assert diff.status_code == 200
            diff_json = diff.json()
            assert diff_json["umbral"] > 0
            assert len(diff_json["candidatos"]) >= 2
            assert diff_json["imagen"].startswith("data:image/png;base64,")

            # 3. GET /quadrants y GET /dna
            quads = client.get("/quadrants")
            assert quads.status_code == 200
            quad_list = quads.json()["cuadrantes"]
            assert len(quad_list) == 5
            barnard_id = quad_list[0]["id"]
            rw_id = next(q["id"] for q in quad_list if q["nombre"] == "RW Aurigae")

            dna = client.get("/dna/Barnard's Star")
            assert dna.status_code == 200
            assert dna.json()["objeto"] == "Barnard's Star"
            assert len(dna.json()["bandas"]) == 7

            # 4. POST /report y validacion cruzada con 3 votos simulados
            bad_report = client.post(
                "/report",
                json={
                    "cuadrante_id": rw_id,
                    "ra": 76.956067,
                    "dec": 30.401326,
                    "tipo": "movimiento",
                },
            )
            assert bad_report.status_code == 400

            rep = client.post(
                "/report",
                json={
                    "cuadrante_id": barnard_id,
                    "ra": 269.452075,
                    "dec": 4.693365,
                    "tipo": "movimiento",
                },
            )
            assert rep.status_code == 201
            reporte_id = rep.json()["reporte_id"]
            assert rep.json()["estado"] == "pendiente"

            for step in (1, 2, 3):
                val = client.post(
                    f"/report/{reporte_id}/validate",
                    json={"coincide": True, "es_simulado": True},
                )
                assert val.status_code == 201
                body = val.json()
                assert body["etiqueta"] == "simulado"
                assert body["votos_coinciden"] == step
                assert body["confirmado"] is (step == 3)
                assert body["estado_cuadrante"] == (
                    "confirmado" if step == 3 else "pendiente"
                )
    finally:
        app.dependency_overrides.clear()
