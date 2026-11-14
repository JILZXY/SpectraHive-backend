# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Casos de uso de SpectraHive (orquestacion pura de puertos y dominio)."""

from __future__ import annotations

import base64

from app.application.dto import (
    CutoutResult,
    DiffResult,
    ReportResult,
    ValidationResult,
)
from app.domain.entities import (
    Quadrant,
    Report,
    SpectralSignature,
    Validation,
    find_test_object_by_name,
)
from app.domain.errors import (
    InvalidValidationOperationError,
    ResourceNotFoundError,
)
from app.domain.ports import (
    AlignmentService,
    CutoutProvider,
    DiffProcessor,
    QuadrantRepository,
    ReportRepository,
    SpectralProvider,
)
from app.domain.rules import (
    confirm_report,
    determine_quadrant_state_after_validation,
    ensure_simulated_vote_labelled,
    validate_report_type,
)
from app.domain.value_objects import Epoch, Fov, RaDec


def _to_base64_data_uri(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class GetCutout:
    """Obtiene un cutout (precalculado IRSA o fallback sintetico) para RA/Dec/FOV/epoca."""

    def __init__(self, cutout_provider: CutoutProvider) -> None:
        self._cutout_provider = cutout_provider

    def execute(
        self,
        ra: float | int | str,
        dec: float | int | str,
        fov: int = 2,
        epoca: str = "A",
    ) -> CutoutResult:
        ra_dec = RaDec.parse(ra, dec)
        fov_vo = Fov(fov)
        epoch_vo = Epoch(epoca)

        cutout = self._cutout_provider.get_cutout(ra_dec, fov_vo, epoch_vo)
        return CutoutResult(
            ra=cutout.ra,
            dec=cutout.dec,
            fov=cutout.fov,
            epoca=cutout.epoca,
            fuente=cutout.fuente,
            imagen_base64=_to_base64_data_uri(cutout.png_bytes),
            png_bytes=cutout.png_bytes,
            objeto=cutout.objeto,
        )


class ComputeDiff:
    """Alinea dos epocas, resta |B - A|, aplica umbral y clasifica candidatos."""

    def __init__(
        self,
        cutout_provider: CutoutProvider,
        alignment_service: AlignmentService,
        diff_processor: DiffProcessor,
        quadrant_repo: QuadrantRepository | None = None,
    ) -> None:
        self._cutout_provider = cutout_provider
        self._alignment_service = alignment_service
        self._diff_processor = diff_processor
        self._quadrant_repo = quadrant_repo

    def execute(
        self,
        cuadrante_id: str,
        epoca_a: str = "A",
        epoca_b: str = "B",
        ra: float | int | str | None = None,
        dec: float | int | str | None = None,
        fov: int = 2,
    ) -> DiffResult:
        resolved_id = cuadrante_id
        if ra is not None and dec is not None:
            ra_dec = RaDec.parse(ra, dec)
            fov_vo = Fov(fov)
        else:
            quadrant: Quadrant | None = None
            if self._quadrant_repo is not None:
                quadrant = self._quadrant_repo.get(cuadrante_id)

            if quadrant is not None:
                ra_dec = RaDec(ra=quadrant.ra, dec=quadrant.dec)
                fov_vo = Fov(quadrant.fov)
                resolved_id = quadrant.id
                if not epoca_a and quadrant.epoca_a:
                    epoca_a = quadrant.epoca_a
                if not epoca_b and quadrant.epoca_b:
                    epoca_b = quadrant.epoca_b
            else:
                spec = find_test_object_by_name(cuadrante_id)
                if spec is None:
                    raise ResourceNotFoundError(
                        f"Cuadrante '{cuadrante_id}' no encontrado."
                    )
                ra_dec = RaDec(ra=spec.ra, dec=spec.dec)
                fov_vo = Fov(fov)

        epoch_a_vo = Epoch(epoca_a or "A")
        epoch_b_vo = Epoch(epoca_b or "B")

        cutout_a = self._cutout_provider.get_cutout(ra_dec, fov_vo, epoch_a_vo)
        cutout_b = self._cutout_provider.get_cutout(ra_dec, fov_vo, epoch_b_vo)

        aligned_a, aligned_b, shift = self._alignment_service.align(
            cutout_a.image, cutout_b.image
        )
        umbral, candidatos, diff_png = self._diff_processor.compute_diff_and_render(
            aligned_a, aligned_b
        )

        fuente = (
            "irsa"
            if cutout_a.fuente == "irsa" and cutout_b.fuente == "irsa"
            else "sintetico"
        )

        return DiffResult(
            cuadrante_id=resolved_id,
            epoca_a=cutout_a.epoca,
            epoca_b=cutout_b.epoca,
            umbral=umbral,
            candidatos=candidatos,
            imagen_base64=_to_base64_data_uri(diff_png),
            png_bytes=diff_png,
            fuente=fuente,
            shift_aplicado=shift,
        )


class CreateReport:
    """Valida reglas RN-02/RN-03/RF-11 y persiste un reporte en la base."""

    def __init__(
        self,
        quadrant_repo: QuadrantRepository,
        report_repo: ReportRepository,
    ) -> None:
        self._quadrant_repo = quadrant_repo
        self._report_repo = report_repo

    def execute(
        self,
        cuadrante_id: str,
        ra: float | int | str,
        dec: float | int | str,
        tipo: str,
    ) -> ReportResult:
        coords = RaDec.parse(ra, dec)
        quadrant = self._quadrant_repo.get(cuadrante_id)
        if quadrant is None:
            raise ResourceNotFoundError(f"Cuadrante '{cuadrante_id}' no encontrado.")

        validate_report_type(quadrant, tipo)
        normalized_tipo = tipo.strip().lower()

        saved = self._report_repo.save(
            Report(
                id=None,
                cuadrante_id=quadrant.id,
                ra=coords.ra,
                dec=coords.dec,
                tipo=normalized_tipo,  # type: ignore[arg-type]
            )
        )
        return ReportResult(
            reporte_id=saved.id or "",
            cuadrante_id=quadrant.id,
            estado=quadrant.estado,
            tipo=normalized_tipo,
        )


class ValidateReport:
    """Registra una validacion y actualiza estado del cuadrante si alcanza >= 3 votos."""

    def __init__(self, report_repo: ReportRepository) -> None:
        self._report_repo = report_repo

    def execute(
        self,
        reporte_id: str,
        coincide: bool,
        es_simulado: bool = False,
    ) -> ValidationResult:
        report = self._report_repo.get(reporte_id)
        if report is None:
            raise ResourceNotFoundError(f"Reporte '{reporte_id}' no encontrado.")

        if report.tipo == "limpio":
            raise InvalidValidationOperationError(
                "Un cuadrante marcado como 'limpio' no genera validaciones de confirmacion (RF-11)."
            )

        validation = Validation(
            id=None,
            reporte_id=reporte_id,
            coincide=bool(coincide),
            es_simulado=bool(es_simulado),
        )
        (
            saved_validation,
            votos_coinciden,
            confirmado_repo,
            estado_cuadrante,
        ) = self._report_repo.add_validation_and_check_confirmation(validation)

        confirmado = confirm_report(votos_coinciden) or confirmado_repo
        estado_final = determine_quadrant_state_after_validation(
            estado_cuadrante, confirmado
        )
        labelled = ensure_simulated_vote_labelled(saved_validation)

        return ValidationResult(
            validacion_id=str(labelled["validacion_id"] or ""),
            reporte_id=reporte_id,
            coincide=bool(saved_validation.coincide),
            es_simulado=bool(saved_validation.es_simulado),
            etiqueta=str(labelled["etiqueta"]),
            votos_coinciden=votos_coinciden,
            confirmado=confirmado,
            estado_cuadrante=estado_final,
        )


class GetCosmicDNA:
    """Devuelve la firma espectral precalculada del ADN Cosmico (RF-14, RF-15)."""

    def __init__(self, spectral_provider: SpectralProvider) -> None:
        self._spectral_provider = spectral_provider

    def execute(self, objeto: str) -> SpectralSignature:
        return self._spectral_provider.signature(objeto)


class ListQuadrants:
    """Devuelve la cola fija de cuadrantes ordenada (RF-05)."""

    def __init__(self, quadrant_repo: QuadrantRepository) -> None:
        self._quadrant_repo = quadrant_repo

    def execute(self) -> list[Quadrant]:
        return self._quadrant_repo.list_queue()
