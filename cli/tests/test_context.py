from __future__ import annotations

import dataclasses

from bcs.context import RuntimeContext
from bcs.platform.execution import CommandRunner, SubprocessCommandRunner


def test_runtime_context_is_frozen(make_runtime_context) -> None:
    runtime = make_runtime_context()
    assert dataclasses.is_dataclass(runtime)
    try:
        runtime.no_input = True  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("RuntimeContext should be immutable")


def test_runtime_context_carries_all_collaborators(make_runtime_context) -> None:
    runtime = make_runtime_context()
    assert isinstance(runtime, RuntimeContext)
    assert runtime.config_loader is not None
    assert runtime.preferences is not None
    assert runtime.console is not None
    assert runtime.err_console is not None
    assert runtime.invocation_id
    assert runtime.command_runner is not None


# ---------------------------------------------------------------------------
# Platform-001 Part 4: CommandRunner dependency injection
# ---------------------------------------------------------------------------


def test_runtime_context_exposes_a_command_runner(make_runtime_context) -> None:
    """RuntimeContext exposes a CommandRunner."""
    runtime = make_runtime_context()
    assert hasattr(runtime, "command_runner")


def test_injected_command_runner_satisfies_the_protocol(make_runtime_context) -> None:
    """The injected object implements the CommandRunner protocol."""
    runtime = make_runtime_context()
    assert isinstance(runtime.command_runner, CommandRunner)


def test_default_command_runner_is_subprocess_command_runner(make_runtime_context) -> None:
    runtime = make_runtime_context()
    assert isinstance(runtime.command_runner, SubprocessCommandRunner)


def test_explicit_command_runner_is_preserved_by_identity(make_runtime_context) -> None:
    """A caller-supplied CommandRunner is stored as-is, not copied or wrapped."""

    class _Sentinel:
        def run(self, command, **kwargs):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    sentinel = _Sentinel()
    runtime = make_runtime_context(command_runner=sentinel)
    assert runtime.command_runner is sentinel


def test_command_runner_attribute_is_the_same_object_on_repeated_access(
    make_runtime_context,
) -> None:
    """The same instance is reused: repeated access never reconstructs it."""
    runtime = make_runtime_context()
    assert runtime.command_runner is runtime.command_runner
