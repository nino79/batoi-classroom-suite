"""Tests for the Host Discovery Orchestrator's coordination logic.

Follows the same testing philosophy as the EFI/Storage adapter tests:
lightweight fake collaborators (here, plain Python callables standing
in for adapter slots) rather than any mock of ``subprocess`` or
``CommandRunner`` - this module never touches either, so there is
nothing of that kind to fake in the first place.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
from bcs.inventory.models import CpuInfo, MemoryInfo, NetworkInterface
from bcs.platform.adapters.efi.errors import FirmwareBootUnavailableError
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.storage.errors import StorageUnavailableError
from bcs.platform.adapters.storage.models import StorageConfiguration
from bcs.platform.errors import PlatformError


class _CountingAdapter[T]:
    """A fake adapter callable that records how many times it was
    called, and either returns ``value`` or raises ``error`` (never
    both, on any single call) each time it is invoked.
    """

    def __init__(self, value: T, *, error: Exception | None = None) -> None:
        self._value = value
        self._error = error
        self.call_count = 0

    def __call__(self) -> T:
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return self._value


def _make_firmware_boot_configuration() -> FirmwareBootConfiguration:
    return FirmwareBootConfiguration(raw_text="BootCurrent: 0000\n")


def _make_storage_configuration() -> StorageConfiguration:
    return StorageConfiguration()


def _make_secure_boot_status() -> SecureBootStatus:
    return SecureBootStatus(state=SecureBootState.ENABLED, raw_text="SecureBoot enabled\n")


def _make_cpu_info() -> CpuInfo:
    return CpuInfo(architecture="x86_64")


def _make_memory_info() -> MemoryInfo:
    return MemoryInfo(total_bytes=1024)


def _make_network_interfaces() -> list[NetworkInterface]:
    return [NetworkInterface(name="eth0", is_up=True, is_loopback=False)]


# ---------------------------------------------------------------------------
# No adapters configured
# ---------------------------------------------------------------------------


def test_no_adapters_configured_yields_empty_snapshot() -> None:
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters())
    snapshot = orchestrator.discover()

    assert snapshot == HostDiscoverySnapshot()
    assert snapshot.firmware_boot_configuration is None
    assert snapshot.storage_topology is None
    assert snapshot.secure_boot is None
    assert snapshot.filesystem is None
    assert snapshot.network == ()
    assert snapshot.cpu is None
    assert snapshot.memory is None
    assert snapshot.tpm is None
    assert snapshot.caveats == ()


# ---------------------------------------------------------------------------
# One / multiple / all adapters configured
# ---------------------------------------------------------------------------


def test_single_adapter_configured() -> None:
    efi = _CountingAdapter(_make_firmware_boot_configuration())
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi))
    snapshot = orchestrator.discover()

    assert snapshot.firmware_boot_configuration == _make_firmware_boot_configuration()
    assert snapshot.storage_topology is None
    assert snapshot.cpu is None
    assert efi.call_count == 1


def test_multiple_adapters_configured() -> None:
    efi = _CountingAdapter(_make_firmware_boot_configuration())
    cpu = _CountingAdapter(_make_cpu_info())
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi, cpu=cpu))
    snapshot = orchestrator.discover()

    assert snapshot.firmware_boot_configuration == _make_firmware_boot_configuration()
    assert snapshot.cpu == _make_cpu_info()
    assert snapshot.storage_topology is None
    assert snapshot.memory is None


def test_all_adapters_configured_snapshot_contents() -> None:
    adapters = HostDiscoveryAdapters(
        efi=_CountingAdapter(_make_firmware_boot_configuration()),
        storage=_CountingAdapter(_make_storage_configuration()),
        secure_boot=_CountingAdapter(_make_secure_boot_status()),
        filesystem=_CountingAdapter({"placeholder": True}),
        network=_CountingAdapter(_make_network_interfaces()),
        cpu=_CountingAdapter(_make_cpu_info()),
        memory=_CountingAdapter(_make_memory_info()),
        tpm=_CountingAdapter(123),
    )
    snapshot = HostDiscoveryOrchestrator(adapters).discover()

    assert snapshot.firmware_boot_configuration == _make_firmware_boot_configuration()
    assert snapshot.storage_topology == _make_storage_configuration()
    assert snapshot.secure_boot == _make_secure_boot_status()
    assert snapshot.filesystem == {"placeholder": True}
    assert snapshot.network == tuple(_make_network_interfaces())
    assert snapshot.cpu == _make_cpu_info()
    assert snapshot.memory == _make_memory_info()
    assert snapshot.tpm == 123
    assert snapshot.caveats == ()


def test_network_adapter_result_is_converted_from_list_to_tuple() -> None:
    network = _CountingAdapter(_make_network_interfaces())
    snapshot = HostDiscoveryOrchestrator(HostDiscoveryAdapters(network=network)).discover()

    assert isinstance(snapshot.network, tuple)
    assert snapshot.network == tuple(_make_network_interfaces())


# ---------------------------------------------------------------------------
# Partial failures
# ---------------------------------------------------------------------------


def test_platform_error_from_one_adapter_does_not_stop_the_others() -> None:
    efi = _CountingAdapter(
        _make_firmware_boot_configuration(),
        error=FirmwareBootUnavailableError("no UEFI here"),
    )
    cpu = _CountingAdapter(_make_cpu_info())
    memory = _CountingAdapter(_make_memory_info())
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi, cpu=cpu, memory=memory))
    snapshot = orchestrator.discover()

    assert snapshot.firmware_boot_configuration is None
    assert snapshot.cpu == _make_cpu_info()
    assert snapshot.memory == _make_memory_info()
    assert efi.call_count == 1
    assert cpu.call_count == 1
    assert memory.call_count == 1
    assert len(snapshot.caveats) == 1
    assert snapshot.caveats[0].startswith("efi: FirmwareBootUnavailableError:")
    assert "no UEFI here" in snapshot.caveats[0]


def test_multiple_platform_errors_each_produce_their_own_caveat() -> None:
    efi = _CountingAdapter(
        _make_firmware_boot_configuration(), error=FirmwareBootUnavailableError("no UEFI")
    )
    storage = _CountingAdapter(
        _make_storage_configuration(), error=StorageUnavailableError("no lsblk")
    )
    cpu = _CountingAdapter(_make_cpu_info())
    orchestrator = HostDiscoveryOrchestrator(
        HostDiscoveryAdapters(efi=efi, storage=storage, cpu=cpu)
    )
    snapshot = orchestrator.discover()

    assert snapshot.firmware_boot_configuration is None
    assert snapshot.storage_topology is None
    assert snapshot.cpu == _make_cpu_info()
    assert len(snapshot.caveats) == 2
    assert snapshot.caveats[0].startswith("efi: FirmwareBootUnavailableError:")
    assert snapshot.caveats[1].startswith("storage: StorageUnavailableError:")


def test_base_platform_error_is_also_isolated_not_only_subclasses() -> None:
    tpm = _CountingAdapter(0, error=PlatformError("tpm probe failed"))
    snapshot = HostDiscoveryOrchestrator(HostDiscoveryAdapters(tpm=tpm)).discover()

    assert snapshot.tpm is None
    assert snapshot.caveats == ("tpm: PlatformError: tpm probe failed",)


def test_a_none_slot_never_produces_a_caveat() -> None:
    snapshot = HostDiscoveryOrchestrator(HostDiscoveryAdapters()).discover()
    assert snapshot.caveats == ()


def test_network_failure_leaves_network_as_empty_tuple_not_none() -> None:
    network = _CountingAdapter([], error=PlatformError("network probe failed"))
    snapshot = HostDiscoveryOrchestrator(HostDiscoveryAdapters(network=network)).discover()

    assert snapshot.network == ()
    assert snapshot.caveats == ("network: PlatformError: network probe failed",)


# ---------------------------------------------------------------------------
# Unexpected exceptions
# ---------------------------------------------------------------------------


def test_unexpected_exception_propagates_unchanged() -> None:
    efi = _CountingAdapter(
        _make_firmware_boot_configuration(), error=TypeError("miswired callable")
    )
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi))

    with pytest.raises(TypeError, match="miswired callable"):
        orchestrator.discover()


def test_unexpected_exception_stops_subsequent_adapters() -> None:
    """Propagation is immediate: adapters that would run after the one
    that raised are never called at all.
    """
    efi = _CountingAdapter(_make_firmware_boot_configuration(), error=TypeError("boom"))
    cpu = _CountingAdapter(_make_cpu_info())
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi, cpu=cpu))

    with pytest.raises(TypeError):
        orchestrator.discover()

    assert efi.call_count == 1
    assert cpu.call_count == 0


def test_unexpected_exception_is_not_wrapped() -> None:
    """The exact exception instance propagates - no translation, no
    chaining into a different exception type.
    """
    original = ValueError("unexpected")
    efi = _CountingAdapter(_make_firmware_boot_configuration(), error=original)
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi))

    with pytest.raises(ValueError) as exc_info:
        orchestrator.discover()
    assert exc_info.value is original


# ---------------------------------------------------------------------------
# Execution order / call counts
# ---------------------------------------------------------------------------


def test_execution_order_matches_declared_field_order() -> None:
    calls: list[str] = []

    def _efi() -> FirmwareBootConfiguration:
        calls.append("efi")
        return _make_firmware_boot_configuration()

    def _storage() -> StorageConfiguration:
        calls.append("storage")
        return _make_storage_configuration()

    def _secure_boot() -> SecureBootStatus:
        calls.append("secure_boot")
        return _make_secure_boot_status()

    def _filesystem() -> object:
        calls.append("filesystem")
        return None

    def _network() -> list[NetworkInterface]:
        calls.append("network")
        return []

    def _cpu() -> CpuInfo:
        calls.append("cpu")
        return _make_cpu_info()

    def _memory() -> MemoryInfo:
        calls.append("memory")
        return _make_memory_info()

    def _tpm() -> object:
        calls.append("tpm")
        return None

    adapters = HostDiscoveryAdapters(
        efi=_efi,
        storage=_storage,
        secure_boot=_secure_boot,
        filesystem=_filesystem,
        network=_network,
        cpu=_cpu,
        memory=_memory,
        tpm=_tpm,
    )
    HostDiscoveryOrchestrator(adapters).discover()

    assert calls == [
        "efi",
        "storage",
        "secure_boot",
        "filesystem",
        "network",
        "cpu",
        "memory",
        "tpm",
    ]


def test_every_configured_adapter_is_called_exactly_once() -> None:
    adapters_kwargs = {
        "efi": _CountingAdapter(_make_firmware_boot_configuration()),
        "storage": _CountingAdapter(_make_storage_configuration()),
        "secure_boot": _CountingAdapter(_make_secure_boot_status()),
        "filesystem": _CountingAdapter(None),
        "network": _CountingAdapter(_make_network_interfaces()),
        "cpu": _CountingAdapter(_make_cpu_info()),
        "memory": _CountingAdapter(_make_memory_info()),
        "tpm": _CountingAdapter(None),
    }
    adapters = HostDiscoveryAdapters(**adapters_kwargs)  # type: ignore[arg-type]

    HostDiscoveryOrchestrator(adapters).discover()

    for fake in adapters_kwargs.values():
        assert fake.call_count == 1


def test_calling_discover_twice_calls_each_adapter_twice_total() -> None:
    """Each *individual* discover() call invokes every wired adapter
    exactly once - calling discover() itself twice is a fresh sweep
    each time, not a violation of "at most once per call."
    """
    efi = _CountingAdapter(_make_firmware_boot_configuration())
    orchestrator = HostDiscoveryOrchestrator(HostDiscoveryAdapters(efi=efi))

    orchestrator.discover()
    orchestrator.discover()

    assert efi.call_count == 2


# ---------------------------------------------------------------------------
# Purity / independence
# ---------------------------------------------------------------------------


def test_orchestrator_module_imports_nothing_but_its_own_dependencies() -> None:
    """AST-based, not a substring search - this module's own docstring
    legitimately *discusses* subprocess/CommandRunner as things it does
    not depend on, so a naive text search would false-positive on its
    own documentation.
    """
    import bcs.inventory.discovery.orchestrator as orchestrator_module

    source = Path(orchestrator_module.__file__).read_text(encoding="utf-8")
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "subprocess",
        "typer",
        "rich",
        "bcs.platform.execution",
        "bcs.context",
        "bcs.app",
    }
    assert not imported_modules & forbidden
    assert imported_modules == {
        "__future__",
        "collections.abc",
        "bcs.inventory.discovery.models",
        "bcs.platform.errors",
    }
