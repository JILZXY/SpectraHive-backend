# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Pruebas de casos de uso con repositorios fake y adaptadores reales."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pytest

from app.application.use_cases import (
    ComputeDiff,
    CreateReport,
    GetCosmicDNA,
    GetCutout,
    ListQuadrants,
    ValidateReport,
)
from app.config import DatabaseConfigError, get_database_url
from app.domain.entities import TEST_OBJECTS_CATALOG, Quadrant, Report, Validation
from app.domain.errors import (
    InvalidValidationOperationError,
    ReportTypeMismatchError,
    ResourceNotFoundError,
)
from app.infrastructure.fits.alignment import IntegerShiftAlignment
from app.infrastructure.fits.loader import save_fits_image
from app.infrastructure.fits.rendering import FitsDiffProcessor
from app.infrastructure.irsa.precomputed import (
    PrecomputedCutoutProvider,
    PrecomputedSpectralProvider,
)
from app.infrastructure.supabase.client import create_db_pool
from app.infrastructure.synthetic.fallback import SyntheticCutoutProvider
from scripts.build_spectra import build_all_spectra


class InMemoryQuadrantRepo:
    def __init__(self) -> None:
        self._items: dict[str, Quadrant] = {}
        for idx, spec in enumerate(TEST_OBJECTS_CATALOG, start=1):
            qid = f"00000000-0000-0000-0000-00000000000{idx}"
            self._items[qid] = Quadrant(
                id=qid,
                nombre=spec.nombre,
                ra=spec.ra,
                dec=spec.dec,
                fov=2,
                epoca_a="DR1",
                epoca_b="QR3",
                estado="pendiente",
                es_objeto_prueba=True,
                tipo_prueba=spec.tipo_prueba,
                url_dinamica=spec.url_dinamica,
            )

    def get(self, id_or_name: str) -> Quadrant | None:
        if id_or_name in self._items:
            return self._items[id_or_name]
        lowered = id_or_name.strip().lower()
        for q in self._items.values():
            if q.nombre.lower() == lowered:
                return q
        return None

    def list_queue(self) -> list[Quadrant]:
        return list(self._items.values())

    def update_state(self, quadrant_id: str, new_state: str) -> None:
        q = self._items[quadrant_id]
        self._items[quadrant_id] = Quadrant(
            id=q.id,
            nombre=q.nombre,
            ra=q.ra,
            dec=q.dec,
            fov=q.fov,
            epoca_a=q.epoca_a,
            epoca_b=q.epoca_b,
            estado=new_state,  # type: ignore[arg-type]
            es_objeto_prueba=q.es_objeto_prueba,
            tipo_prueba=q.tipo_prueba,
            url_dinamica=q.url_dinamica,
        )


class InMemoryReportRepo:
    def __init__(self, quadrant_repo: InMemoryQuadrantRepo) -> None:
        self._quadrant_repo = quadrant_repo
        self._reports: dict[str, Report] = {}
        self._validations: dict[str, list[Validation]] = {}

    def save(self, report: Report) -> Report:
        rid = str(uuid.uuid4())
        saved = Report(
            id=rid,
            cuadrante_id=report.cuadrante_id,
            ra=report.ra,
            dec=report.dec,
            tipo=report.tipo,
            creado_en="2026-11-14T14:00:00Z",
        )
        self._reports[rid] = saved
        self._validations[rid] = []
        return saved

    def get(self, reporte_id: str) -> Report | None:
        return self._reports.get(reporte_id)

    def validations_for(self, reporte_id: str) -> list[Validation]:
        return list(self._validations.get(reporte_id, []))

    def add_validation_and_check_confirmation(
        self, validation: Validation
    ) -> tuple[Validation, int, bool, str]:
        vid = str(uuid.uuid4())
        saved = Validation(
            id=vid,
            reporte_id=validation.reporte_id,
            coincide=validation.coincide,
            es_simulado=validation.es_simulado,
            creado_en="2026-11-14T14:01:00Z",
        )
        self._validations[validation.reporte_id].append(saved)
        votos = sum(1 for v in self._validations[validation.reporte_id] if v.coincide)
        confirmado = votos >= 3
        report = self._reports[validation.reporte_id]
        if confirmado:
            self._quadrant_repo.update_state(report.cuadrante_id, "confirmado")
        quadrant = self._quadrant_repo.get(report.cuadrante_id)
        estado = quadrant.estado if quadrant else "pendiente"
        return saved, votos, confirmado, estado


def test_create_report_and_cross_validation_flow() -> None:
    q_repo = InMemoryQuadrantRepo()
    r_repo = InMemoryReportRepo(q_repo)
    create_uc = CreateReport(q_repo, r_repo)
    validate_uc = ValidateReport(r_repo)

    barnard = q_repo.get("Barnard's Star")
    assert barnard is not None

    report_res = create_uc.execute(
        cuadrante_id=barnard.id,
        ra=barnard.ra,
        dec=barnard.dec,
        tipo="movimiento",
    )
    assert report_res.estado == "pendiente"

    # Voto 1 y voto 2: sigue pendiente
    v1 = validate_uc.execute(report_res.reporte_id, coincide=True, es_simulado=True)
    assert v1.confirmado is False
    assert v1.votos_coinciden == 1
    assert v1.estado_cuadrante == "pendiente"
    assert v1.etiqueta == "simulado"

    v2 = validate_uc.execute(report_res.reporte_id, coincide=True, es_simulado=True)
    assert v2.confirmado is False
    assert v2.votos_coinciden == 2
    assert v2.estado_cuadrante == "pendiente"

    # Voto 3: confirma reporte y actualiza cuadrante (RN-06, RF-12)
    v3 = validate_uc.execute(report_res.reporte_id, coincide=True, es_simulado=True)
    assert v3.confirmado is True
    assert v3.votos_coinciden == 3
    assert v3.estado_cuadrante == "confirmado"
    assert q_repo.get(barnard.id).estado == "confirmado"  # type: ignore[union-attr]


def test_create_report_rejects_wrong_group_and_clean_validation() -> None:
    q_repo = InMemoryQuadrantRepo()
    r_repo = InMemoryReportRepo(q_repo)
    create_uc = CreateReport(q_repo, r_repo)
    validate_uc = ValidateReport(r_repo)

    rw = q_repo.get("RW Aurigae")
    assert rw is not None

    with pytest.raises(ReportTypeMismatchError):
        create_uc.execute(rw.id, rw.ra, rw.dec, "movimiento")

    clean = create_uc.execute(rw.id, rw.ra, rw.dec, "limpio")
    assert clean.tipo == "limpio"
    with pytest.raises(InvalidValidationOperationError):
        validate_uc.execute(clean.reporte_id, coincide=True, es_simulado=False)


def test_compute_diff_barnard_and_rw_aurigae() -> None:
    q_repo = InMemoryQuadrantRepo()
    diff_uc = ComputeDiff(
        cutout_provider=SyntheticCutoutProvider(),
        alignment_service=IntegerShiftAlignment(),
        diff_processor=FitsDiffProcessor(),
        quadrant_repo=q_repo,
    )

    barnard_diff = diff_uc.execute(cuadrante_id="Barnard's Star")
    assert barnard_diff.umbral > 0.0
    assert barnard_diff.imagen_base64.startswith("data:image/png;base64,")
    assert len(barnard_diff.candidatos) == 2
    assert all(c.tipo == "movimiento" for c in barnard_diff.candidatos)

    wise_diff = diff_uc.execute(cuadrante_id="WISE 0855-0714")
    assert len(wise_diff.candidatos) == 2
    assert all(c.tipo == "movimiento" for c in wise_diff.candidatos)

    rw_diff = diff_uc.execute(cuadrante_id="RW Aurigae")
    assert len(rw_diff.candidatos) == 1
    assert rw_diff.candidatos[0].tipo == "brillo"

    r_draconis_diff = diff_uc.execute(cuadrante_id="R Draconis")
    assert len(r_draconis_diff.candidatos) == 1
    assert r_draconis_diff.candidatos[0].tipo == "brillo"


def test_get_cutout_reads_irsa_fits_and_falls_back(tmp_path: Path) -> None:
    fits_path = tmp_path / "barnards_star_DR1.fits"
    arr = np.full((64, 64), 10.0, dtype=np.float32)
    arr[30:34, 30:34] = 200.0
    save_fits_image(fits_path, arr, header_meta={"SOURCE": "IRSA", "OBJECT": "Barnard's Star"})

    provider = PrecomputedCutoutProvider(cutouts_dir=tmp_path)
    uc = GetCutout(provider)

    res_a = uc.execute(ra=269.452075, dec=4.693365, fov=2, epoca="A")
    assert res_a.fuente == "irsa"
    assert res_a.epoca == "DR1"
    assert res_a.imagen_base64.startswith("data:image/png;base64,")

    # Epoca B no tiene FITS en tmp_path -> cae al fallback sintetico
    res_b = uc.execute(ra=269.452075, dec=4.693365, fov=2, epoca="B")
    assert res_b.fuente == "sintetico"
    assert res_b.epoca == "QR3"


def test_cosmic_dna_and_list_quadrants(tmp_path: Path) -> None:
    build_all_spectra(tmp_path)
    dna_uc = GetCosmicDNA(PrecomputedSpectralProvider(tmp_path))
    sig = dna_uc.execute("Barnard's Star")
    assert sig.objeto == "Barnard's Star"
    assert len(sig.bandas) == 7
    assert len(sig.valores) == 7

    with pytest.raises(ResourceNotFoundError):
        dna_uc.execute("Objeto Inexistente")

    q_repo = InMemoryQuadrantRepo()
    assert len(ListQuadrants(q_repo).execute()) == 5


def test_database_url_missing_fails_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigError, match="Falta DATABASE_URL"):
        get_database_url()

    with pytest.raises(RuntimeError, match="Falta DATABASE_URL"):
        create_db_pool()
