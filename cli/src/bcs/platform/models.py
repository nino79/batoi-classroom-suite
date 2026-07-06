"""Immutable data models for the Platform Layer.

``CommandResult`` is the outcome of one process execution, produced by
:class:`~bcs.platform.execution.CommandRunner` (not yet implemented -
see the module docstring of :mod:`bcs.platform`). This module contains
**only the model** - no execution logic, no ``subprocess`` usage, no
adapters. Per ``docs/PLATFORM_LAYER.md``'s "structured in, structured
out" design principle, a ``CommandResult`` is the *only* thing a
caller of the Platform Layer ever sees on success (or on a non-zero
exit when ``check`` is false); every other exit path is a typed
exception in ``bcs.platform.errors`` (not yet implemented), never a
raw ``subprocess.CompletedProcess`` or ``OSError``.

``CommandResult`` is **frozen**: it is a point-in-time record of one
already-finished (or already-killed) process invocation, never a live
handle to a still-running one - the same "immutable snapshot"
philosophy already established for ``bcs.inventory.models``, applied
to command execution rather than host facts.

Field naming mirrors the rest of BCS's models: Python attributes are
``snake_case``, JSON output is ``camelCase`` (``by_alias=True``), and
``populate_by_name=True`` lets callers construct instances with either
spelling. See ``docs/PLATFORM_LAYER.md#models`` for the authoritative
field-by-field reference this module implements exactly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommandResult(BaseModel):
    """The outcome of one external command invocation.

    Every field here is populated by whichever
    :class:`~bcs.platform.execution.CommandRunner` implementation
    produced this result (not yet implemented); this model has no
    knowledge of *how* a result came to be, only what happened.

    ``exit_code`` and ``timed_out`` are linked by construction: a
    killed-on-timeout process has no real exit code to report, and a
    process that actually exited always has one. See
    :meth:`_check_timed_out_matches_exit_code`.

    Deliberately does **not** carry its own ``schemaVersion`` - unlike
    ``HostInventory``, a ``CommandResult`` is never the top-level
    payload of a ``bcs`` command's own output; it is always embedded
    inside something else's result (a future adapter's parsed model, a
    session report), so versioning is that container's responsibility.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    command: tuple[str, ...] = Field(
        min_length=1,
        description="The exact command executed, argv-style. command[0] is the executable.",
    )
    stdout: str = Field(description="Captured stdout, decoded as UTF-8 with errors='replace'.")
    stderr: str = Field(description="Captured stderr, decoded as UTF-8 with errors='replace'.")
    exit_code: int | None = Field(
        alias="exitCode",
        description=(
            "The process's real exit code. None only when timed_out is True - a "
            "killed process has no real exit code to report."
        ),
    )
    duration: float = Field(
        ge=0,
        description=(
            "Wall-clock seconds from started_at to finished_at. Kept as its own "
            "field, even though it is arithmetically derivable from those two "
            "timestamps, so a consumer doesn't have to compute it."
        ),
    )
    started_at: datetime = Field(
        alias="startedAt", description="UTC, timezone-aware. When the child process was spawned."
    )
    finished_at: datetime = Field(
        alias="finishedAt",
        description="UTC, timezone-aware. When the child process exited or was killed on timeout.",
    )
    working_directory: str | None = Field(
        alias="workingDirectory",
        default=None,
        description=(
            "The effective working directory used for this invocation. None means "
            "the runner's own process working directory was inherited."
        ),
    )
    timed_out: bool = Field(
        alias="timedOut",
        description="Whether this result represents a process killed for exceeding its timeout.",
    )

    @model_validator(mode="after")
    def _check_timed_out_matches_exit_code(self) -> CommandResult:
        """Enforce the ``exit_code``/``timed_out`` relationship documented above."""
        if self.timed_out and self.exit_code is not None:
            msg = "exit_code must be None when timed_out is True"
            raise ValueError(msg)
        if not self.timed_out and self.exit_code is None:
            msg = "exit_code is required (must not be None) when timed_out is False"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_finished_at_not_before_started_at(self) -> CommandResult:
        if self.finished_at < self.started_at:
            msg = "finished_at must not be before started_at"
            raise ValueError(msg)
        return self

    @property
    def success(self) -> bool:
        """Whether the command completed normally with a zero exit code.

        A plain Python property, not a Pydantic computed field - it is
        derived state, not part of the model's own JSON shape (see
        ``docs/PLATFORM_LAYER.md#models``, which lists ``success`` as
        "computed, not a field").
        """
        return self.exit_code == 0 and not self.timed_out


__all__ = ["CommandResult"]
