"""ClassroomConfig resolution and loading.

Implements ``docs/CLI.md#configuration-loading`` (``CLI-008``): the
precedence chain for *finding* a config file, and the pipeline for
turning it into a validated :class:`~bcs.config.models.ClassroomConfig`.
Deliberately has **no upward directory search** - see the doc for why:
guessing which classroom you mean is a safety risk in a tool that
reimages real machines.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from bcs.config.models import ClassroomConfig
from bcs.config.overrides import apply_env_overrides, apply_set_overrides
from bcs.errors import ConfigInvalidError, UsageError

ENV_CONFIG_PATH = "BCS_CONFIG"
_DEFAULT_CANDIDATES = ("bcs.yaml", "classroom.yaml")
SUPPORTED_API_VERSIONS = {"bcs/v1alpha1"}
_SUPPORTED_KINDS = {"ClassroomConfig"}


class ConfigLoader:
    """Resolves, loads, overrides, and validates one ClassroomConfig.

    An instance is constructed once per invocation (in the root Typer
    callback) with the run's ``--config``/``--set`` values and the
    process environment already captured, then handed to commands via
    :class:`~bcs.context.RuntimeContext` - this is the "dependency
    injection" seam: commands never read ``sys.argv``/``os.environ``
    themselves, only this already-configured collaborator.
    """

    def __init__(
        self,
        *,
        explicit_path: Path | None,
        set_overrides: list[str] | None = None,
        env: Mapping[str, str],
        cwd: Path | None = None,
    ) -> None:
        self._explicit_path = explicit_path
        self._set_overrides = list(set_overrides or [])
        self._env = env
        self._cwd = cwd or Path.cwd()

    def resolve_path(self) -> Path:
        """Resolve the ClassroomConfig path per the documented precedence."""
        if self._explicit_path is not None:
            if not self._explicit_path.is_file():
                msg = f"--config path does not exist: {self._explicit_path}"
                raise UsageError(msg)
            return self._explicit_path

        env_path = self._env.get(ENV_CONFIG_PATH)
        if env_path:
            candidate = Path(env_path)
            if not candidate.is_file():
                msg = f"${ENV_CONFIG_PATH} does not exist: {candidate}"
                raise UsageError(msg)
            return candidate

        found = [self._cwd / name for name in _DEFAULT_CANDIDATES if (self._cwd / name).is_file()]
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            names = ", ".join(p.name for p in found)
            msg = f"ambiguous: both {names} present in {self._cwd}; pass --config"
            raise UsageError(msg)

        msg = "no ClassroomConfig found; pass --config or set $BCS_CONFIG"
        raise UsageError(msg)

    def load_raw(self, path: Path | None = None) -> dict[str, Any]:
        """Load, override, but do not yet schema-validate, a config file."""
        target = path if path is not None else self.resolve_path()
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"could not read {target}: {exc}"
            raise ConfigInvalidError(msg) from exc

        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            msg = f"{target}: invalid YAML syntax: {exc}"
            raise ConfigInvalidError(msg) from exc

        if not isinstance(loaded, dict):
            msg = f"{target}: document root must be a mapping"
            raise ConfigInvalidError(msg)

        document = copy.deepcopy(loaded)
        apply_env_overrides(document, self._env)
        apply_set_overrides(document, self._set_overrides)
        return document

    def load(self, path: Path | None = None) -> ClassroomConfig:
        """Load a fully validated :class:`ClassroomConfig`.

        Raises :class:`~bcs.errors.ConfigInvalidError` (exit code ``3``)
        for anything wrong with the document's *content* - YAML syntax,
        an unrecognized envelope, or a schema violation - never
        :class:`~bcs.errors.UsageError`, per the ``2`` vs. ``3`` rule in
        ``docs/CLI.md#exit-codes``.
        """
        target = path if path is not None else self.resolve_path()
        document = self.load_raw(target)
        return parse_classroom_config(document, source=target)


def parse_classroom_config(document: Mapping[str, Any], *, source: Path) -> ClassroomConfig:
    """Validate the envelope, then the full schema, for one loaded document."""
    api_version = document.get("apiVersion")
    if api_version not in SUPPORTED_API_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_API_VERSIONS))
        msg = (
            f"{source}: unrecognized apiVersion {api_version!r}; "
            f"this bcs build supports: {supported}"
        )
        raise ConfigInvalidError(msg, errors=[msg])

    kind = document.get("kind")
    if kind not in _SUPPORTED_KINDS:
        supported = ", ".join(sorted(_SUPPORTED_KINDS))
        msg = f"{source}: unrecognized kind {kind!r}; this bcs build supports: {supported}"
        raise ConfigInvalidError(msg, errors=[msg])

    try:
        return ClassroomConfig.model_validate(document)
    except ValidationError as exc:
        errors = [_format_pydantic_error(e) for e in exc.errors()]
        msg = f"{source}: schema validation failed ({len(errors)} error(s))"
        raise ConfigInvalidError(msg, errors=errors) from exc


def _format_pydantic_error(error: Mapping[str, Any]) -> str:
    path = ".".join(str(part) for part in error["loc"])
    return f"{path}: {error['msg']}"


__all__ = ["SUPPORTED_API_VERSIONS", "ConfigLoader", "parse_classroom_config"]
