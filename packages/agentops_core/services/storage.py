"""Filesystem storage for SOP uploads and generated skill outputs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalStorage:
    """Local-filesystem storage rooted at a single directory.

    v0.1 implementation. Swap with an S3-backed Storage class later;
    callers depend only on save/load/dir_for/resolve.
    """

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, relative_path: str, data: bytes) -> Path:
        """Write bytes to <root>/<relative_path>; return absolute path."""
        target = self.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def load(self, absolute_or_relative_path: Path | str) -> bytes:
        path = Path(absolute_or_relative_path)
        if not path.is_absolute():
            path = self.resolve(str(path))
        return path.read_bytes()

    def dir_for(self, relative_path: str) -> Path:
        """Return the absolute path for a directory (does not create it)."""
        return self.resolve(relative_path)

    def resolve(self, relative_path: str) -> Path:
        return self.root / relative_path
