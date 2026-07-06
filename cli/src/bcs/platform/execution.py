"""The Platform Layer's execution seam - the only module permitted to
import ``subprocess``.

Design: ``docs/PLATFORM_LAYER.md#commandrunner-api`` /
``#architectural-rule-argument-lists-only-never-shelltrue``, accepted
per ``docs/decisions/0009-platform-layer-command-runner.md``.

Two things live here:

- :class:`CommandRunner` - a structural interface (``Protocol``), so
  callers depend on "anything with this shape" rather than on
  ``subprocess`` or on this module directly. Consumed via dependency
  injection, never a module-level singleton.
- :class:`SubprocessCommandRunner` - the one production
  implementation, wrapping :func:`subprocess.run`.

Every command is an argument list; ``shell=True`` is never passed to
``subprocess``, anywhere, under any circumstance - see
``docs/PLATFORM_LAYER.md``'s named architectural rule. There is no
code path here that accepts or interpolates a shell string.

This module intentionally does **not** integrate with
``bcs.context.RuntimeContext`` and defines no adapters - both remain
later, separate steps (see ``docs/PLATFORM_LAYER.md``'s "Approved
Design Decisions" and "How Future Adapters Use It" sections).
"""

from __future__ import annotations

import subprocess  # the one module permitted to import this, see module docstring
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from bcs.platform.errors import CommandExecutionError, CommandNotFoundError, CommandTimeoutError
from bcs.platform.models import CommandResult


@runtime_checkable
class CommandRunner(Protocol):
    """Structural interface for running one external command.

    Anything matching this shape - :class:`SubprocessCommandRunner` in
    production, a test double in tests - can stand in for a
    ``CommandRunner``. There is no shared base implementation to
    inherit; see ``docs/PLATFORM_LAYER.md``'s rationale for a
    ``Protocol`` over an ``abc.ABC`` here.
    """

    def run(  # noqa: PLR0913 - six kwonly knobs mirroring subprocess.run's own shape
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float | None = None,
        check: bool = False,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        """Run ``command`` and return its :class:`CommandResult`.

        Args:
            command: The command and its arguments, as a sequence of
                strings - never a single shell string. ``command[0]``
                is resolved via ``PATH`` the same way ``subprocess.run``
                already resolves it.
            timeout_seconds: Per-call timeout budget. ``None`` means no
                timeout - legal but discouraged; see
                ``docs/PLATFORM_LAYER.md#commandrunner-api``.
            check: If true, a non-zero exit raises
                :class:`~bcs.platform.errors.CommandExecutionError`.
                If false (the default), the caller inspects the
                returned :class:`CommandResult` itself.
            cwd: Working directory for the child process. ``None``
                inherits the runner's own process working directory.
            env: Matches :class:`subprocess.Popen`'s own ``env``
                semantics exactly: ``None`` inherits the current
                process's environment; a provided mapping *replaces*
                it entirely (it is not merged/overlaid).
            input_text: Text piped to the child's stdin, if any.

        Returns:
            A :class:`CommandResult` - on success, or on a non-zero
            exit when ``check`` is false.

        Raises:
            CommandNotFoundError: The executable can't be located or
                executed at all.
            CommandTimeoutError: ``timeout_seconds`` elapsed before the
                process finished.
            CommandExecutionError: ``check`` was true and the process
                exited non-zero.
        """
        ...  # pragma: no cover - a Protocol stub body, never meant to run


def _decode(value: str | bytes | None) -> str:
    """Decode captured output defensively - never raises on bad bytes."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


class SubprocessCommandRunner:
    """The one production :class:`CommandRunner`, wrapping :func:`subprocess.run`.

    Output is always captured (never inherited/passthrough) - see
    ``docs/PLATFORM_LAYER.md#relationship-to-existing-code`` for why
    plugin dispatch (which *does* want passthrough I/O) is a
    deliberately separate case, untouched by this class.
    """

    def run(  # noqa: PLR0913 - six kwonly knobs mirroring subprocess.run's own shape
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float | None = None,
        check: bool = False,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        command_tuple = tuple(command)
        if not command_tuple:
            msg = "command must not be empty"
            raise ValueError(msg)

        working_directory = str(cwd) if cwd is not None else None
        started_at = datetime.now(UTC)

        try:
            completed = subprocess.run(  # argument list only, shell=True never used
                command_tuple,
                timeout=timeout_seconds,
                cwd=cwd,
                env=dict(env) if env is not None else None,
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                check=False,
            )
        except (FileNotFoundError, PermissionError) as exc:
            executable = command_tuple[0]
            msg = f"{executable!r} could not be executed: {exc}"
            raise CommandNotFoundError(msg, executable=executable) from exc
        except subprocess.TimeoutExpired as exc:
            finished_at = datetime.now(UTC)
            partial_result = CommandResult(
                command=command_tuple,
                stdout=_decode(exc.stdout),
                stderr=_decode(exc.stderr),
                exit_code=None,
                duration=(finished_at - started_at).total_seconds(),
                started_at=started_at,
                finished_at=finished_at,
                working_directory=working_directory,
                timed_out=True,
            )
            msg = f"command {command_tuple!r} timed out after {timeout_seconds}s"
            raise CommandTimeoutError(msg, partial_result=partial_result) from exc

        finished_at = datetime.now(UTC)
        result = CommandResult(
            command=command_tuple,
            stdout=_decode(completed.stdout),
            stderr=_decode(completed.stderr),
            exit_code=completed.returncode,
            duration=(finished_at - started_at).total_seconds(),
            started_at=started_at,
            finished_at=finished_at,
            working_directory=working_directory,
            timed_out=False,
        )

        if check and not result.success:
            msg = f"command {command_tuple!r} exited with code {result.exit_code}"
            raise CommandExecutionError(msg, result=result)

        return result


__all__ = ["CommandRunner", "SubprocessCommandRunner"]
