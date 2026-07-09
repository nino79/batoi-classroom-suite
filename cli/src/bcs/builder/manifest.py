"""BuildManifest serialization and deserialization.

A ``BuildManifest`` is the authoritative JSON record of what a build
produced. This module provides save/load helpers that wrap the
Pydantic model's own ``model_dump``/``model_validate`` with
consistent options (``by_alias=True`` for JSON, ``mode="json"`` for
portable output).
"""

from __future__ import annotations

import json
from pathlib import Path

from bcs.builder.execution import read_json, write_json
from bcs.builder.models import BuildManifest


def save_manifest(manifest: BuildManifest, path: Path) -> Path:
    """Serialize ``manifest`` to JSON and write it to ``path``.

    Uses camelCase aliases and a JSON-native mode so the output is
    portable across languages. Creates parent directories if needed.
    Returns ``path`` for chaining.
    """
    data = manifest.model_dump(mode="json", by_alias=True)
    return write_json(path, data)


def load_manifest(path: Path) -> BuildManifest:
    """Read ``path`` and deserialize it as a ``BuildManifest``.

    Accepts both camelCase and snake_case keys (``populate_by_name``
    is enabled on the model). Raises ``ManifestError`` if the file
    cannot be parsed or validated.
    """
    from bcs.builder.errors import ManifestError

    try:
        data = read_json(path)
    except FileNotFoundError as exc:
        msg = f"Manifest file not found: {path}"
        raise ManifestError(msg, details={"path": str(path)}) from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"Manifest file is not valid JSON: {exc}",
            details={"path": str(path), "error": str(exc)},
        ) from exc

    try:
        return BuildManifest.model_validate(data)
    except Exception as exc:
        raise ManifestError(
            f"Failed to validate manifest: {exc}",
            details={"path": str(path), "error": str(exc)},
        ) from exc


__all__ = ["load_manifest", "save_manifest"]
