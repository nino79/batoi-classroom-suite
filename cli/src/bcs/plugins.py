"""Git-style external plugin dispatch, per ``docs/CLI.md#plugin-system``
(``CLI-009``, ``ADR-0006``).

Any executable literally named ``bcs-<name>`` on ``$PATH`` becomes
invocable as ``bcs <name>``. There is no in-process plugin API, no
manifest, and - deliberately - no sandboxing: whoever controls ``PATH``
controls what plugins run (see ``docs/CLI.md#security-considerations``).
Built-in commands always take precedence and are never shadowed; the
caller (``bcs.app``) only consults this module once a name has already
failed to resolve to a built-in.
"""

from __future__ import annotations

import difflib
import shutil
import subprocess
from collections.abc import Mapping, Sequence

_PLUGIN_PREFIX = "bcs-"


def find_plugin(name: str) -> str | None:
    """Return the resolved path to ``bcs-<name>`` on ``PATH``, if any."""
    return shutil.which(f"{_PLUGIN_PREFIX}{name}")


def suggest_command(name: str, known_commands: Sequence[str]) -> str | None:
    """Suggest the closest built-in command name to a typo, if any."""
    matches = difflib.get_close_matches(name, known_commands, n=1, cutoff=0.6)
    return matches[0] if matches else None


def run_plugin(
    executable: str,
    args: Sequence[str],
    *,
    env: Mapping[str, str],
) -> int:
    """Run a discovered plugin, forwarding ``args``, and return its exit code.

    Uses :func:`subprocess.run` rather than ``exec`` so behaviour is
    identical on every platform ``bcs`` itself needs to run its own test
    suite on; see ``docs/CLI.md#implementation-notes`` for the tradeoff.
    """
    result = subprocess.run(
        [executable, *args],
        env=dict(env),
        check=False,
    )
    return result.returncode


__all__ = ["find_plugin", "run_plugin", "suggest_command"]
