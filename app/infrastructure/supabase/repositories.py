# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Repositorios PostgreSQL/Supabase para cuadrantes, reportes y validaciones."""

from __future__ import annotations

import uuid

from app.domain.entities import Quadrant, Report, Validation
from app.infrastructure.supabase.client import PostgresPoolManager


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _row_to_quadrant(row: tuple) -> Quadrant:
    return Quadrant(
        id=str(row[0]),
        nombre=str(row[1]),
        ra=float(row[2]),
        dec=float(row[3]),
        fov=int(row[4]),
        epoca_a=str(row[5] or "DR1"),
        epoca_b=str(row[6] or "QR3"),
        estado=row[7],
        es_objeto_prueba=bool(row[8]),
        tipo_prueba=row[9],
        url_dinamica=row[10],
    )


class SupabaseQuadrantRepository:
    """Implementa QuadrantRepository contra Postgres/Supabase."""

    def __init__(self, pool: PostgresPoolManager) -> None:
        self._pool = pool

    def get(self, id_or_name: str) -> Quadrant | None:
        query_base = (
            "SELECT id::text, nombre, ra, dec, fov::int, epoca_a, epoca_b, "
            "estado, es_objeto_prueba, tipo_prueba, url_dinamica "
            "FROM cuadrantes "
        )
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if _is_valid_uuid(id_or_name):
                    cur.execute(f"{query_base} WHERE id = %s", (id_or_name,))
                else:
                    cur.execute(
                        f"{query_base} WHERE lower(nombre) = lower(%s)",
                        (id_or_name.strip(),),
                    )
                row = cur.fetchone()
                return _row_to_quadrant(row) if row else None

    def list_queue(self) -> list[Quadrant]:
        sql = (
            "SELECT id::text, nombre, ra, dec, fov::int, epoca_a, epoca_b, "
            "estado, es_objeto_prueba, tipo_prueba, url_dinamica "
            "FROM cuadrantes "
            "ORDER BY es_objeto_prueba DESC, creado_en ASC, nombre ASC "
            "LIMIT 10"
        )
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return [_row_to_quadrant(row) for row in rows]

    def update_state(self, quadrant_id: str, new_state: str) -> None:
        if not _is_valid_uuid(quadrant_id):
            return
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE cuadrantes SET estado = %s WHERE id = %s",
                        (new_state, quadrant_id),
                    )


class SupabaseReportRepository:
    """Implementa ReportRepository con transacciones atomicas (RN-06, RF-12)."""

    def __init__(self, pool: PostgresPoolManager) -> None:
        self._pool = pool

    def save(self, report: Report) -> Report:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO reportes (cuadrante_id, ra, dec, tipo) "
                        "VALUES (%s, %s, %s, %s) "
                        "RETURNING id::text, creado_en::text",
                        (report.cuadrante_id, report.ra, report.dec, report.tipo),
                    )
                    row = cur.fetchone()
                    return Report(
                        id=str(row[0]),
                        cuadrante_id=report.cuadrante_id,
                        ra=report.ra,
                        dec=report.dec,
                        tipo=report.tipo,
                        creado_en=str(row[1]),
                    )

    def get(self, reporte_id: str) -> Report | None:
        if not _is_valid_uuid(reporte_id):
            return None
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, cuadrante_id::text, ra, dec, tipo, creado_en::text "
                    "FROM reportes WHERE id = %s",
                    (reporte_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return Report(
                    id=str(row[0]),
                    cuadrante_id=str(row[1]),
                    ra=float(row[2]),
                    dec=float(row[3]),
                    tipo=row[4],
                    creado_en=str(row[5]),
                )

    def validations_for(self, reporte_id: str) -> list[Validation]:
        if not _is_valid_uuid(reporte_id):
            return []
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id::text, reporte_id::text, coincide, es_simulado, creado_en::text "
                    "FROM validaciones WHERE reporte_id = %s ORDER BY creado_en ASC",
                    (reporte_id,),
                )
                rows = cur.fetchall()
                return [
                    Validation(
                        id=str(r[0]),
                        reporte_id=str(r[1]),
                        coincide=bool(r[2]),
                        es_simulado=bool(r[3]),
                        creado_en=str(r[4]),
                    )
                    for r in rows
                ]

    def add_validation_and_check_confirmation(
        self, validation: Validation
    ) -> tuple[Validation, int, bool, str]:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO validaciones (reporte_id, coincide, es_simulado) "
                        "VALUES (%s, %s, %s) "
                        "RETURNING id::text, creado_en::text",
                        (
                            validation.reporte_id,
                            validation.coincide,
                            validation.es_simulado,
                        ),
                    )
                    inserted_row = cur.fetchone()
                    saved_validation = Validation(
                        id=str(inserted_row[0]),
                        reporte_id=validation.reporte_id,
                        coincide=validation.coincide,
                        es_simulado=validation.es_simulado,
                        creado_en=str(inserted_row[1]),
                    )

                    # Fuente de verdad de confirmacion: vista vw_reportes_confirmados (RF-12)
                    cur.execute(
                        "SELECT votos_coinciden FROM vw_reportes_confirmados "
                        "WHERE reporte_id = %s",
                        (validation.reporte_id,),
                    )
                    view_row = cur.fetchone()
                    if view_row is not None:
                        confirmado = True
                        votos_coinciden = int(view_row[0])
                        cur.execute(
                            "UPDATE cuadrantes SET estado = 'confirmado' "
                            "WHERE id = (SELECT cuadrante_id FROM reportes WHERE id = %s) "
                            "RETURNING estado",
                            (validation.reporte_id,),
                        )
                        state_row = cur.fetchone()
                        estado_cuadrante = str(state_row[0]) if state_row else "confirmado"
                    else:
                        confirmado = False
                        cur.execute(
                            "SELECT count(*) FROM validaciones "
                            "WHERE reporte_id = %s AND coincide = true",
                            (validation.reporte_id,),
                        )
                        count_row = cur.fetchone()
                        votos_coinciden = int(count_row[0]) if count_row else 0
                        cur.execute(
                            "SELECT c.estado FROM cuadrantes c "
                            "JOIN reportes r ON r.cuadrante_id = c.id "
                            "WHERE r.id = %s",
                            (validation.reporte_id,),
                        )
                        state_row = cur.fetchone()
                        estado_cuadrante = str(state_row[0]) if state_row else "pendiente"

                    return saved_validation, votos_coinciden, confirmado, estado_cuadrante
