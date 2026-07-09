"""Utility functions for file and JSON operations within the Builder.

These are pure file-IO helpers that the workspace manager and manifest
module rely on. They deliberately do **not** use the Platform Layer's
``CommandRunner`` -- they operate on local files only and never spawn
a subprocess.

Every function accepts and returns ``pathlib.Path`` objects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast


def ensure_directory(path: Path) -> Path:
    """Create ``path`` and all parent directories if they don't exist.

    Returns the path for chaining. Raises
    :class:`OSError` (or a subclass) if creation fails.

    Example::

        log_dir = ensure_directory(workspace_root / "logs")
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def compute_file_checksum(path: Path) -> str:
    """Compute the SHA-256 hex digest of ``path``.

    Reads the entire file into memory; suitable for build artifacts up
    to a few hundred MB. Raises ``FileNotFoundError`` if ``path`` does
    not exist.
    """
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def copy_file(source: Path, target: Path) -> Path:
    """Copy ``source`` to ``target``, creating parent directories.

    Uses binary copy via ``shutil.copy2`` (preserves metadata). Returns
    ``target`` for chaining. Raises ``FileNotFoundError`` if ``source``
    does not exist.
    """
    import shutil

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(target))
    return target


def read_json(path: Path) -> dict[str, Any]:
    """Load and return the JSON content of ``path``.

    Raises ``FileNotFoundError`` if ``path`` does not exist.
    Raises ``json.JSONDecodeError`` if the content is not valid JSON.
    """
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    return cast("dict[str, Any]", data)


def write_json(path: Path, data: Any) -> Path:
    """Serialise ``data`` as pretty-printed JSON to ``path``.

    Creates parent directories if they don't exist. Returns ``path``
    for chaining.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return path


__all__ = [
    "compute_file_checksum",
    "copy_file",
    "ensure_directory",
    "read_json",
    "write_json",
]
