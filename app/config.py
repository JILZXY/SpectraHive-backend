# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Configuracion del backend cargada exclusivamente desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class DatabaseConfigError(RuntimeError):
    """Error explicito cuando falta DATABASE_URL en el entorno."""


def get_database_url() -> str:
    """Lee DATABASE_URL y falla rapido si no esta definida (02-backend-contexto-supabase §4.2)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise DatabaseConfigError(
            "Falta DATABASE_URL en las variables de entorno. "
            "Definela en .env (local) o en Render (produccion)."
        )
    return url


@dataclass(frozen=True)
class Settings:
    """Configuracion general de la API (sin credenciales hardcodeadas)."""

    cors_origins: list[str]
    data_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        raw_origins = os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        )
        origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
        data_dir = Path(os.environ.get("DATA_DIR", "data")).resolve()
        return cls(cors_origins=origins, data_dir=data_dir)
