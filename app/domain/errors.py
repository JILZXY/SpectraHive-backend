# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Excepciones de dominio puras."""


class DomainError(Exception):
    """Base para errores de reglas de negocio y validaciones de dominio."""


class ValidationError(DomainError):
    """Entrada o invariante invalido segun RF/RN."""


class InvalidCoordinatesError(ValidationError):
    """Coordenadas RA/Dec fuera de rango o con formato invalido (RF-01)."""


class InvalidFovError(ValidationError):
    """FOV distinto de 1 o 2 (RF-02, RN-11)."""


class InvalidEpochError(ValidationError):
    """Identificador de epoca invalido."""


class InvalidReportTypeError(ValidationError):
    """Tipo de reporte desconocido (solo movimiento, brillo, limpio)."""


class ReportTypeMismatchError(ValidationError):
    """Tipo de reporte incompatible con el tipo_prueba del cuadrante (RN-02, RN-03)."""


class InvalidValidationOperationError(ValidationError):
    """Operacion de validacion no permitida (ej. validar un reporte 'limpio', RF-11)."""


class ResourceNotFoundError(DomainError):
    """Entidad o recurso solicitado no existe."""
