# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Cache local en disco (data/cache/) para cutouts renderizados."""

from __future__ import annotations

import hashlib
from pathlib import Path


class DiskCutoutCache:
    """Implementa CutoutCache guardando bytes PNG en disco local."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return self._cache_dir / f"{digest}.bin"

    def get(self, key: str) -> bytes | None:
        path = self._path_for(key)
        if path.is_file():
            return path.read_bytes()
        return None

    def set(self, key: str, value: bytes) -> None:
        path = self._path_for(key)
        path.write_bytes(value)
