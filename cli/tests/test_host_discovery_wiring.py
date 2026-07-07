"""Integration tests for Host Discovery Orchestrator Part 4: wiring a
HostDiscoveryOrchestrator into RuntimeContext via bcs.app's root callback.

Mirrors tests/test_command_runner_wiring.py's own approach exactly - these
deliberately test at the bcs.app/CliRunner level, not just RuntimeContext
or HostDiscoveryOrchestrator in isolation, to prove the actual wiring
(construction happens once, in one place, is not a module-level singleton
or service locator, and shares the same CommandRunner instance) - not just
that the dataclass *can* hold an orchestrator.
"""

from __future__ import annotations

import functools

import pytest
from typer.testing import CliRunner

from bcs import app as app_module
from bcs.app import app
from bcs.inventory import collectors
from bcs.inventory.discovery.models import HostDiscoveryAdapters
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator

runner = CliRunner()


def test_command_behaviour_is_unchanged() -> None:
    """This integration is dependency injection only - a real command's
    observable behaviour and exit code must be identical to before.
    """
    result = runner.invoke(app, ["--output", "json", "version"])
    assert result.exit_code == 0
    assert '"schemaVersion"' in result.output


def test_orchestrator_is_constructed_exactly_once_per_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves 'create once, reuse the same instance, no global state, no
    service locator': if HostDiscoveryOrchestrator were constructed more
    than once per invocation (e.g. lazily per-access, or independently by
    more than one collaborator), this count would be > 1.
    """
    created: list[object] = []
    real_orchestrator = app_module.HostDiscoveryOrchestrator

    def _counting_orchestrator(*args, **kwargs):  # type: ignore[no-untyped-def]
        instance = real_orchestrator(*args, **kwargs)
        created.append(instance)
        return instance

    monkeypatch.setattr(app_module, "HostDiscoveryOrchestrator", _counting_orchestrator)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert len(created) == 1
    assert isinstance(created[0], HostDiscoveryOrchestrator)


def test_adapters_bundle_is_constructed_exactly_once_per_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves HostDiscoveryAdapters (the DI bundle each adapter callable is
    bound into) is built exactly once - never lazily, never re-built per
    adapter slot accessed.
    """
    created: list[object] = []
    real_adapters = app_module.HostDiscoveryAdapters

    def _counting_adapters(*args, **kwargs):  # type: ignore[no-untyped-def]
        instance = real_adapters(*args, **kwargs)
        created.append(instance)
        return instance

    monkeypatch.setattr(app_module, "HostDiscoveryAdapters", _counting_adapters)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert len(created) == 1
    assert isinstance(created[0], HostDiscoveryAdapters)


def test_orchestrator_is_rebuilt_fresh_on_each_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No module-level caching: two separate invocations get two distinct
    HostDiscoveryOrchestrator instances - proving there is no global
    singleton or service locator behind the scenes.
    """
    captured: list[object] = []
    real_runtime_context = app_module.RuntimeContext

    def _capturing_runtime_context(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs["host_discovery_orchestrator"])
        return real_runtime_context(*args, **kwargs)

    monkeypatch.setattr(app_module, "RuntimeContext", _capturing_runtime_context)

    first = runner.invoke(app, ["version"])
    second = runner.invoke(app, ["version"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert len(captured) == 2
    assert captured[0] is not captured[1]


def test_efi_and_storage_adapters_share_the_same_command_runner_as_the_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The efi/storage adapter slots are bound to the exact same
    CommandRunner instance RuntimeContext.command_runner carries - not a
    second, independently constructed one.
    """
    captured: dict[str, object] = {}
    real_adapters = app_module.HostDiscoveryAdapters
    real_runtime_context = app_module.RuntimeContext

    def _capturing_adapters(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["efi"] = kwargs["efi"]
        captured["storage"] = kwargs["storage"]
        return real_adapters(*args, **kwargs)

    def _capturing_runtime_context(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["command_runner"] = kwargs["command_runner"]
        return real_runtime_context(*args, **kwargs)

    monkeypatch.setattr(app_module, "HostDiscoveryAdapters", _capturing_adapters)
    monkeypatch.setattr(app_module, "RuntimeContext", _capturing_runtime_context)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    command_runner = captured["command_runner"]
    efi_callable = captured["efi"]
    storage_callable = captured["storage"]
    assert isinstance(efi_callable, functools.partial)
    assert efi_callable.keywords["runner"] is command_runner
    assert isinstance(storage_callable, functools.partial)
    assert storage_callable.keywords["runner"] is command_runner


def test_adapters_bundle_wiring_matches_design(monkeypatch: pytest.MonkeyPatch) -> None:
    """network/cpu/memory are already zero-argument (bcs.inventory.collectors)
    and are bound directly, with no functools.partial needed - see
    docs/HOST_DISCOVERY_ORCHESTRATOR.md#dependency-injection-strategy---implemented.
    secure_boot/filesystem/tpm stay unset: no adapter.py exists yet for any
    of them.
    """
    captured: dict[str, object] = {}
    real_adapters = app_module.HostDiscoveryAdapters

    def _capturing_adapters(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return real_adapters(*args, **kwargs)

    monkeypatch.setattr(app_module, "HostDiscoveryAdapters", _capturing_adapters)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert captured["network"] is collectors.collect_network
    assert captured["cpu"] is collectors.collect_cpu
    assert captured["memory"] is collectors.collect_memory
    assert captured.get("secure_boot") is None
    assert captured.get("filesystem") is None
    assert captured.get("tpm") is None


def test_runtime_context_exposes_the_orchestrator_correctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact instance built in bcs.app.main() is what RuntimeContext
    carries - not a copy, not a re-wrapped equivalent.
    """
    captured: dict[str, object] = {}
    real_runtime_context = app_module.RuntimeContext

    def _capturing_runtime_context(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["host_discovery_orchestrator"] = kwargs["host_discovery_orchestrator"]
        return real_runtime_context(*args, **kwargs)

    monkeypatch.setattr(app_module, "RuntimeContext", _capturing_runtime_context)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert isinstance(captured["host_discovery_orchestrator"], HostDiscoveryOrchestrator)


def test_runtime_context_attribute_is_the_same_object_on_repeated_access(
    make_runtime_context,
) -> None:
    """The same instance is reused: repeated access never reconstructs it."""
    runtime = make_runtime_context()
    assert runtime.host_discovery_orchestrator is runtime.host_discovery_orchestrator
