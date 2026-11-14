# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Composition root: inyeccion de dependencias (Depends) para FastAPI."""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends

from app.application.use_cases import (
    ComputeDiff,
    CreateReport,
    GetCosmicDNA,
    GetCutout,
    ListQuadrants,
    ValidateReport,
)
from app.config import Settings
from app.domain.ports import (
    AlignmentService,
    CutoutProvider,
    DiffProcessor,
    QuadrantRepository,
    ReportRepository,
    SpectralProvider,
)
from app.infrastructure.fits.alignment import IntegerShiftAlignment
from app.infrastructure.fits.rendering import FitsDiffProcessor
from app.infrastructure.irsa.precomputed import (
    PrecomputedCutoutProvider,
    PrecomputedSpectralProvider,
)
from app.infrastructure.supabase.client import PostgresPoolManager, create_db_pool
from app.infrastructure.supabase.repositories import (
    SupabaseQuadrantRepository,
    SupabaseReportRepository,
)
from app.infrastructure.synthetic.fallback import SyntheticCutoutProvider


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def get_cutout_provider() -> CutoutProvider:
    settings = get_settings()
    return PrecomputedCutoutProvider(
        cutouts_dir=settings.data_dir / "cutouts",
        fallback=SyntheticCutoutProvider(),
    )


@lru_cache(maxsize=1)
def get_alignment_service() -> AlignmentService:
    return IntegerShiftAlignment()


@lru_cache(maxsize=1)
def get_diff_processor() -> DiffProcessor:
    return FitsDiffProcessor()


@lru_cache(maxsize=1)
def get_spectral_provider() -> SpectralProvider:
    settings = get_settings()
    return PrecomputedSpectralProvider(spectra_dir=settings.data_dir / "spectra")


_db_pool_instance: PostgresPoolManager | None = None


def get_db_pool_manager() -> PostgresPoolManager:
    global _db_pool_instance
    if _db_pool_instance is None:
        _db_pool_instance = create_db_pool()
    return _db_pool_instance


def get_quadrant_repo() -> QuadrantRepository:
    return SupabaseQuadrantRepository(get_db_pool_manager())


def get_optional_quadrant_repo() -> QuadrantRepository | None:
    if not os.environ.get("DATABASE_URL", "").strip():
        return None
    return get_quadrant_repo()


def get_report_repo() -> ReportRepository:
    return SupabaseReportRepository(get_db_pool_manager())


def get_cutout_use_case(
    provider: CutoutProvider = Depends(get_cutout_provider),
) -> GetCutout:
    return GetCutout(cutout_provider=provider)


def get_compute_diff_use_case(
    provider: CutoutProvider = Depends(get_cutout_provider),
    alignment: AlignmentService = Depends(get_alignment_service),
    diff_processor: DiffProcessor = Depends(get_diff_processor),
    quadrant_repo: QuadrantRepository | None = Depends(get_optional_quadrant_repo),
) -> ComputeDiff:
    return ComputeDiff(
        cutout_provider=provider,
        alignment_service=alignment,
        diff_processor=diff_processor,
        quadrant_repo=quadrant_repo,
    )


def get_create_report_use_case(
    quadrant_repo: QuadrantRepository = Depends(get_quadrant_repo),
    report_repo: ReportRepository = Depends(get_report_repo),
) -> CreateReport:
    return CreateReport(quadrant_repo=quadrant_repo, report_repo=report_repo)


def get_validate_report_use_case(
    report_repo: ReportRepository = Depends(get_report_repo),
) -> ValidateReport:
    return ValidateReport(report_repo=report_repo)


def get_cosmic_dna_use_case(
    spectral_provider: SpectralProvider = Depends(get_spectral_provider),
) -> GetCosmicDNA:
    return GetCosmicDNA(spectral_provider=spectral_provider)


def get_list_quadrants_use_case(
    quadrant_repo: QuadrantRepository = Depends(get_quadrant_repo),
) -> ListQuadrants:
    return ListQuadrants(quadrant_repo=quadrant_repo)
