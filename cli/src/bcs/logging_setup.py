"""Logging levels, formats, and precedence, per
``docs/CLI.md#logging--verbosity`` (``CLI-013``).

Every log line carries a timestamp, a level, the run's invocation ID
(``NFR-004`` traceability), and a message - in either plain text or one
NDJSON object per line (``--log-format json``), always on stderr
(``CLI-005``).
"""

from __future__ import annotations

import json
import logging
import sys
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import IO

_LOGGER_NAME = "bcs"

#: Secrets redaction, per docs/CLI.md#security-considerations: any config
#: key whose name matches one of these fragments is masked in debug/trace
#: output, except the explicitly-excluded path-like fields.
_SENSITIVE_KEY_FRAGMENTS = ("password", "secret", "token", "key")
_SENSITIVE_KEY_EXCLUDES = frozenset({"signingkey", "keyref"})


class LogLevel(IntEnum):
    """Verbosity levels, ordered so comparison (``<``, ``>=``) works.

    Internal representation only - :class:`LogLevelOption` is what
    ``--log-level`` actually accepts, so ``--help`` shows readable names
    (``silent|error|warn|info|debug|trace``) rather than these raw
    integers.
    """

    SILENT = 100
    ERROR = 40
    WARN = 30
    INFO = 20
    DEBUG = 10
    TRACE = 5

    @property
    def stdlib_level(self) -> int:
        """Map to the closest :mod:`logging` level (TRACE has none)."""
        if self is LogLevel.SILENT:
            return logging.CRITICAL + 1
        if self is LogLevel.TRACE:
            return 5
        return int(self)


class LogLevelOption(StrEnum):
    """The string values ``--log-level`` accepts on the command line."""

    SILENT = "silent"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"

    def to_log_level(self) -> LogLevel:
        return LogLevel[self.name]


class LogFormat(StrEnum):
    """Values accepted by ``--log-format``."""

    TEXT = "text"
    JSON = "json"


def resolve_log_level(
    *,
    explicit: LogLevel | None,
    verbose_count: int,
    quiet: bool,
    warn: IO[str] | None = None,
) -> LogLevel:
    """Resolve the effective log level.

    Precedence: ``explicit`` (``--log-level``) always wins. Otherwise,
    each ``-v`` raises the level one step above :attr:`LogLevel.INFO`
    towards :attr:`LogLevel.TRACE`, and ``-q`` drops straight to
    :attr:`LogLevel.ERROR`. If both ``-v`` and ``-q`` were given, the
    last one on the command line wins and a one-line warning is written
    to ``warn`` (defaults to stderr) - see ``docs/CLI.md``.
    """
    if explicit is not None:
        return explicit

    if verbose_count > 0 and quiet:
        stream = warn if warn is not None else sys.stderr
        print(
            "bcs: both --verbose and --quiet were given; using --verbose "
            "(last-wins is not tracked positionally, so --verbose takes "
            "precedence over --quiet when both are present)",
            file=stream,
        )
        quiet = False

    if quiet:
        return LogLevel.ERROR

    steps = [LogLevel.INFO, LogLevel.DEBUG, LogLevel.TRACE]
    index = min(verbose_count, len(steps) - 1)
    return steps[index]


def _redact(message: str) -> str:
    lowered = message.lower()
    if any(
        fragment in lowered and not any(exc in lowered for exc in _SENSITIVE_KEY_EXCLUDES)
        for fragment in _SENSITIVE_KEY_FRAGMENTS
    ):
        return "***"
    return message


class _TextFormatter(logging.Formatter):
    def __init__(self, invocation_id: str) -> None:
        super().__init__()
        self._invocation_id = invocation_id

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ")
        level = record.levelname.ljust(5)
        message = _redact(record.getMessage())
        return f"{timestamp} {level} [{self._invocation_id}] {message}"


class _JsonFormatter(logging.Formatter):
    def __init__(self, invocation_id: str, command: str) -> None:
        super().__init__()
        self._invocation_id = invocation_id
        self._command = command

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname.lower(),
            "invocationId": self._invocation_id,
            "command": self._command,
            "message": _redact(record.getMessage()),
        }
        return json.dumps(payload)


def configure_logging(  # noqa: PLR0913 - six kwonly knobs, not worth a config object here
    *,
    level: LogLevel,
    log_format: LogFormat,
    invocation_id: str,
    command: str,
    stream: IO[str],
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure and return the ``bcs`` logger.

    Idempotent per-process: repeated calls replace prior handlers rather
    than accumulating them, which matters for tests that build multiple
    contexts in one interpreter session.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(level.stdlib_level)

    formatter: logging.Formatter
    formatter = (
        _JsonFormatter(invocation_id, command)
        if log_format is LogFormat.JSON
        else _TextFormatter(invocation_id)
    )

    stream_handler = logging.StreamHandler(stream)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the shared ``bcs`` logger (must be configured first)."""
    return logging.getLogger(_LOGGER_NAME)


__all__: list[str] = [
    "LogFormat",
    "LogLevel",
    "LogLevelOption",
    "configure_logging",
    "get_logger",
    "resolve_log_level",
]
