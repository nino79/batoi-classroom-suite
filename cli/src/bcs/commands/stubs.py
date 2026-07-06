"""Placeholder registrations for commands not implemented in this phase.

``docs/CLI.md#command-tree`` documents ten top-level commands
(``CLI-001``); this implementation phase covers only ``version``,
``doctor``, and ``validate`` (plus the built-in ``--help``). The
remaining commands - ``build``, ``install``, ``deploy``, ``backup``,
``restore``, ``update``, ``config`` - are registered here purely so
``bcs --help`` reflects the full, documented command surface, each
doing nothing but reporting that it is not yet implemented and pointing
at the owning component's roadmap phase. **No Boot Manager, Builder, or
Deploy logic lives here or anywhere in this package.**
"""

from __future__ import annotations

from dataclasses import dataclass

from bcs.context import RuntimeContext
from bcs.errors import BcsError
from bcs.exit_codes import ExitCode


class NotImplementedInPhaseError(BcsError):
    """Raised by every stub command; always ``ExitCode.GENERAL_ERROR``."""

    exit_code = ExitCode.GENERAL_ERROR


@dataclass(frozen=True)
class StubCommand:
    name: str
    owner: str
    roadmap_anchor: str


STUB_COMMANDS: tuple[StubCommand, ...] = (
    StubCommand("build", "Builder", "phase-2--builder-golden-image-pipeline"),
    StubCommand("install", "Deploy", "phase-3--deploy-single-classroom-rollout"),
    StubCommand("deploy", "Deploy", "phase-3--deploy-single-classroom-rollout"),
    StubCommand("backup", "Deploy", "phase-3--deploy-single-classroom-rollout"),
    StubCommand("restore", "Deploy", "phase-3--deploy-single-classroom-rollout"),
    StubCommand("update", "the bcs CLI itself", "phase-0--foundation-architecture--governance"),
    StubCommand("config", "the bcs CLI itself", "phase-0--foundation-architecture--governance"),
)


def run_stub(_runtime: RuntimeContext, stub: StubCommand) -> int:
    """Report that ``stub`` is not implemented in this phase, and stop.

    Takes (and ignores) ``_runtime`` to match every other command
    function's ``run_<command>(runtime, ...)`` signature convention.
    """
    msg = (
        f"bcs {stub.name}: not implemented in this phase. "
        f"Owned by {stub.owner}; see ROADMAP.md#{stub.roadmap_anchor} "
        f"and docs/CLI.md#bcs-{stub.name}."
    )
    raise NotImplementedInPhaseError(msg)


__all__ = ["STUB_COMMANDS", "NotImplementedInPhaseError", "StubCommand", "run_stub"]
