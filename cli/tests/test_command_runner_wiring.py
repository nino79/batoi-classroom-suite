"""Integration tests for Platform-001 Part 4: wiring a CommandRunner into
RuntimeContext via bcs.app's root callback.

These deliberately test at the ``bcs.app``/CliRunner level, not just the
``RuntimeContext`` dataclass in isolation, to prove the actual wiring
(construction happens once, in one place, and is not a module-level
singleton or service locator) - not just that the dataclass *can* hold
a CommandRunner.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from bcs import app as app_module
from bcs.app import app
from bcs.platform.execution import CommandRunner

runner = CliRunner()


def test_command_behaviour_is_unchanged() -> None:
    """This integration is dependency injection only - a real command's
    observable behaviour and exit code must be identical to before.
    """
    result = runner.invoke(app, ["--output", "json", "version"])
    assert result.exit_code == 0
    assert '"schemaVersion"' in result.output


def test_command_runner_is_constructed_exactly_once_per_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves 'create once, reuse the same instance, no global state, no
    service locator': if SubprocessCommandRunner were constructed more
    than once per invocation (e.g. lazily per-access, or independently
    by more than one collaborator), this count would be > 1.
    """
    created: list[object] = []

    class _CountingCommandRunner:
        def __init__(self) -> None:
            created.append(self)

        def run(self, command, **kwargs):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    monkeypatch.setattr(app_module, "SubprocessCommandRunner", _CountingCommandRunner)

    # `version` always succeeds regardless of host state (unlike `doctor`,
    # whose real checks depend on the machine running the test suite) -
    # the point here is proving construction count, not command outcome.
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert len(created) == 1
    assert isinstance(created[0], _CountingCommandRunner)


def test_command_runner_used_by_the_context_is_the_one_constructed_in_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact instance built in bcs.app.main() is what RuntimeContext
    carries - not a copy, not a re-wrapped equivalent.
    """
    captured: dict[str, object] = {}
    original_runtime_context = app_module.RuntimeContext

    def _capturing_runtime_context(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["command_runner"] = kwargs["command_runner"]
        return original_runtime_context(*args, **kwargs)

    monkeypatch.setattr(app_module, "RuntimeContext", _capturing_runtime_context)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert isinstance(captured["command_runner"], CommandRunner)
    assert isinstance(captured["command_runner"], app_module.SubprocessCommandRunner)
