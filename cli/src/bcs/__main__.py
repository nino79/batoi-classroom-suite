"""The ``bcs`` process entry point.

Wraps :data:`bcs.app.app` in the single try/except that translates every
:class:`~bcs.errors.BcsError` into its documented exit code and a clean,
single-line message on stderr (``CLI-004``/``CLI-005``). ``typer.Exit``
(raised for ``--help``, ``--version``, and every command's normal
completion) is converted to a real ``SystemExit`` *inside* ``app()``
itself and is intentionally left to propagate here untouched - see
``docs/CLI.md#implementation-notes``.
"""

from __future__ import annotations

import sys

from bcs.app import app
from bcs.argv_normalize import normalize_argv
from bcs.errors import BcsError
from bcs.exit_codes import ExitCode


def main() -> None:
    try:
        app(args=normalize_argv(sys.argv[1:]))
    except BcsError as exc:
        print(f"bcs: error: {exc.message}", file=sys.stderr)
        raise SystemExit(int(exc.exit_code)) from None
    except KeyboardInterrupt:
        print("bcs: aborted (interrupted)", file=sys.stderr)
        raise SystemExit(int(ExitCode.INTERRUPTED)) from None
    except Exception as exc:  # noqa: BLE001 - top-level safety net, see module docstring
        print(f"bcs: unexpected error: {exc}", file=sys.stderr)
        raise SystemExit(int(ExitCode.GENERAL_ERROR)) from None


if __name__ == "__main__":
    main()
