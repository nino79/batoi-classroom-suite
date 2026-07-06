"""Color-mode resolution, per ``docs/CLI.md#color-output`` (``CLI-014``).

Precedence: ``--color`` flag > ``BCS_COLOR`` env var > ``NO_COLOR`` env var
(https://no-color.org/: any non-empty value disables color) > TTY
auto-detection. Colorizing ``json``/``yaml`` output is never allowed,
regardless of TTY state, since it would corrupt machine parsing.
"""

from __future__ import annotations

import os
import sys
from enum import StrEnum
from typing import IO

from rich.console import Console

from bcs.output import OutputFormat


class ColorMode(StrEnum):
    """Values accepted by ``--color``."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


def resolve_color_enabled(
    *,
    mode: ColorMode,
    output_format: OutputFormat,
    stream: IO[str],
    env: dict[str, str] | None = None,
) -> bool:
    """Decide whether ANSI color should be used for ``stream``.

    ``env`` is injectable for tests; defaults to the real process
    environment. A single ``if/elif`` chain, rather than early returns
    per case, so the full precedence order (flag > ``BCS_COLOR`` >
    ``NO_COLOR`` > ``TERM`` > TTY auto-detection) reads top to bottom in
    one place.
    """
    if output_format is not OutputFormat.TEXT:
        enabled = False
    else:
        environ = env if env is not None else os.environ
        bcs_color = environ.get("BCS_COLOR", "").strip().lower()

        if mode is ColorMode.ALWAYS:
            enabled = True
        elif mode is ColorMode.NEVER:
            enabled = False
        elif bcs_color:
            enabled = bcs_color == "always"
        elif environ.get("NO_COLOR") or environ.get("TERM") == "dumb":
            enabled = False
        else:
            enabled = stream.isatty()

    return enabled


def build_console(*, stream: IO[str], color_enabled: bool) -> Console:
    """Construct a Rich :class:`Console` bound to ``stream``.

    ``force_terminal``/``no_color`` are set explicitly so Rich's own
    auto-detection never disagrees with :func:`resolve_color_enabled`.
    ``soft_wrap=True`` disables Rich's word-wrapping: JSON/YAML result
    output must never be wrapped mid-line, or it stops parsing as valid
    JSON/YAML (``CLI-005``/``CLI-012``).
    """
    return Console(
        file=stream,
        force_terminal=color_enabled or None,
        no_color=not color_enabled,
        highlight=False,
        soft_wrap=True,
    )


def default_streams() -> tuple[IO[str], IO[str]]:
    """Return ``(stdout, stderr)`` - kept as a seam so tests can patch them."""
    return sys.stdout, sys.stderr


__all__ = ["ColorMode", "build_console", "default_streams", "resolve_color_enabled"]
