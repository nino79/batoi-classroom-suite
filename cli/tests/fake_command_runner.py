"""Shared test infrastructure for Platform Layer adapter tests.

Provides a consolidated :class:`FakeCommandRunner` and
:func:`build_command_result` helper that replace the seven duplicated
``FakeCommandRunner`` + ``FakeCommandResult`` + ``_make_result`` triple
that previously existed across every adapter test file.

Usage::

    from tests.fake_command_runner import FakeCommandRunner, build_command_result

    # Single-result mode (EFI, Secure Boot, Filesystem, Network)
    runner = FakeCommandRunner(result=build_command_result(stdout="..."))

    # Multi-tool mode (Storage, Pipeline)
    runner = FakeCommandRunner(results={
        "lsblk": build_command_result(stdout="..."),
        "blkid": build_command_result(stdout="..."),
    })

    # Error simulation
    runner = FakeCommandRunner(not_found_tools=frozenset({"efibootmgr"}))
    runner = FakeCommandRunner(timeout_tools=frozenset({"df"}))

    # Convenience constructors
    runner = FakeCommandRunner.that_succeeds(stdout="...")
    runner = FakeCommandRunner.that_fails(stderr="...", exit_code=1)

    # Assert on recorded calls
    assert runner.calls[0]["command"] == ["efibootmgr", "-v"]
    assert runner.calls[0]["env"]["LANG"] == "C"

See ``docs/TESTING_INFRASTRUCTURE.md`` for the full design rationale,
migration guide, and best practices.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from bcs.platform.errors import CommandNotFoundError, CommandTimeoutError
from bcs.platform.models import CommandResult


def build_command_result(
    *,
    command: tuple[str, ...] = ("tool",),
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    duration: float = 0.1,
) -> CommandResult:
    """Return a reproducible ``CommandResult`` for deterministic tests.

    All keyword-only::

        build_command_result(stdout="SecureBoot enabled\\n")
        build_command_result(stderr="Permission denied", exit_code=1)
        build_command_result(command=("efibootmgr", "-v"), stdout=...)
    """
    now = datetime.now(tz=UTC)
    return CommandResult(
        command=command,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration=duration,
        started_at=now,
        finished_at=now,
        working_directory=None,
        timed_out=False,
    )


@dataclass
class FakeCommandRunner:
    """A configurable ``CommandRunner`` stand-in for adapter tests.

    Two modes:

    1. **Single-result mode** — pass ``result`` (a ``CommandResult``):
       the same result is returned on every ``run()`` call.
       Used by EFI, Secure Boot, Filesystem, and Network adapter tests.

    2. **Multi-tool mode** — pass ``results`` (a ``dict[str, CommandResult]``):
       results are keyed by ``command[0]`` (the tool name).
       Used by Storage adapter and pipeline tests.

    Error simulation via ``not_found_tools`` and ``timeout_tools``:
    Named tools raise ``CommandNotFoundError`` or ``CommandTimeoutError``
    respectively, checked **before** result lookup, so a runner with
    empty ``results`` and a non-empty ``not_found_tools`` correctly
    raises instead of ``KeyError``-ing.

    Every call (including arguments) is recorded in ``calls`` regardless
    of outcome, so tests can assert exactly what was (and was not)
    invoked.

    Satisfies ``isinstance(runner, CommandRunner)`` against the
    ``@runtime_checkable`` protocol.
    """

    result: CommandResult | None = None
    results: dict[str, CommandResult] | None = None
    not_found_tools: frozenset[str] = frozenset()
    timeout_tools: frozenset[str] = frozenset()
    calls: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def that_succeeds(cls, stdout: str = "") -> FakeCommandRunner:
        """Build a single-result runner that returns ``stdout`` with
        ``exit_code=0``."""
        return cls(result=build_command_result(stdout=stdout))

    @classmethod
    def that_fails(cls, stderr: str = "", exit_code: int = 1) -> FakeCommandRunner:
        """Build a single-result runner that returns ``stderr`` with the
        given ``exit_code``."""
        return cls(result=build_command_result(stderr=stderr, exit_code=exit_code))

    def run(  # noqa: PLR0913 — mirrors CommandRunner.run()'s own protocol signature
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float | None = None,
        check: bool = False,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        tool = command[0] if command else ""
        self.calls.append(
            {
                "command": command,
                "timeout_seconds": timeout_seconds,
                "check": check,
                "cwd": cwd,
                "env": env,
                "input_text": input_text,
            }
        )
        if tool in self.not_found_tools:
            raise CommandNotFoundError(f"{tool} not found", executable=tool)
        if tool in self.timeout_tools:
            raise CommandTimeoutError(
                f"{tool} timed out",
                partial_result=MagicMock(),
            )
        if self.results is not None:
            return self.results[tool]
        if self.result is not None:
            return self.result
        msg = f"FakeCommandRunner: no result configured for {tool!r}"
        raise RuntimeError(msg)


__all__ = ["FakeCommandRunner", "build_command_result"]
