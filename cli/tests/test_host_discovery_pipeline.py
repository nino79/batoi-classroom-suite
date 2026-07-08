"""End-to-end integration tests for the complete Host Discovery pipeline:
composition root (``bcs.app.main()``) -> ``RuntimeContext`` ->
``HostDiscoveryAdapters`` -> ``HostDiscoveryOrchestrator.discover()`` ->
``HostDiscoverySnapshot``.

Unlike ``test_host_discovery_wiring.py`` (which proves the composition
root *builds* the right objects, but never calls ``discover()``, since
no command consumes the orchestrator yet) and
``test_inventory_discovery_orchestrator.py`` (which proves the
orchestrator's own coordination logic using lightweight fake adapter
callables, not the real ``efi``/``storage``/``secure_boot`` adapters),
this module exercises the *real*, currently-implemented adapters
(``read_firmware_boot_configuration``/``read_storage_topology``/
``read_secure_boot_status``) wired together exactly as
``bcs.app.main()`` wires them - sharing one ``CommandRunner`` - and
verifies the resulting snapshot, call counts, and ``caveats`` end to
end. The only fake anywhere in this module is at the ``CommandRunner``
seam (``docs/PLATFORM_LAYER.md#design-principles`` item 5); nothing
about any adapter's own internals is touched or mocked.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from bcs import app as app_module
from bcs.app import app
from bcs.inventory import collectors
from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
from bcs.platform.adapters.efi.adapter import read_firmware_boot_configuration
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.storage.adapter import read_storage_topology
from bcs.platform.adapters.storage.models import StorageConfiguration
from bcs.platform.errors import CommandNotFoundError

# ---------------------------------------------------------------------------
# A single, shared, multi-tool FakeCommandRunner - keyed by tool name
# (command[0]), mirroring test_platform_adapters_storage_adapter.py's own
# FakeCommandRunner exactly, generalised to serve efibootmgr/lsblk/blkid/
# findmnt/mokutil simultaneously, the same way bcs.app.main() shares one
# real SubprocessCommandRunner across efi/storage/secure_boot.
# ---------------------------------------------------------------------------


@dataclass
class FakeCommandResult:
    """A minimal stand-in for ``CommandResult`` used in these tests."""

    command: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    started_at: datetime
    finished_at: datetime
    working_directory: str | None = None
    timed_out: bool = False

    def to_result(self) -> MagicMock:
        m = MagicMock()
        m.command = self.command
        m.stdout = self.stdout
        m.stderr = self.stderr
        m.exit_code = self.exit_code
        m.duration = self.duration
        m.started_at = self.started_at
        m.finished_at = self.finished_at
        m.working_directory = self.working_directory
        m.timed_out = self.timed_out
        return m


@dataclass
class FakeCommandRunner:
    """A configurable ``CommandRunner`` stand-in, keyed by tool name
    (``command[0]``) - shared across every tool-based adapter in one
    pipeline run, exactly as the real ``SubprocessCommandRunner``
    instance is in ``bcs.app.main()``.
    """

    results: dict[str, FakeCommandResult] = field(default_factory=dict)
    not_found_tools: frozenset[str] = frozenset()
    calls: list[dict[str, Any]] = field(default_factory=list)

    def run(  # noqa: PLR0913 - mirrors the CommandRunner Protocol's own signature exactly
        self,
        command: Any,
        *,
        timeout_seconds: Any = None,
        check: bool = False,
        cwd: Any = None,
        env: Any = None,
        input_text: Any = None,
    ) -> MagicMock:
        tool = command[0]
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
        return self.results[tool].to_result()


# ---------------------------------------------------------------------------
# Realistic, minimal-but-valid tool output for each of the three real,
# implemented adapters. Each parser's own correctness is covered by its
# own test module; only enough shape is used here to prove the pipeline
# actually threads real output through real parsing into a real snapshot.
# ---------------------------------------------------------------------------

_VALID_EFIBOOTMGR = (
    "BootCurrent: 0000\n"
    "Timeout: 5 seconds\n"
    "BootOrder: 0000\n"
    "Boot0000* ubuntu\tHD(1,GPT,aaaaaaaa-0000-0000-0000-000000000000,0x800,0x100000)"
    "/File(\\EFI\\ubuntu\\shimx64.efi)\n"
)
_VALID_LSBLK = (
    '{"blockdevices": [{"name": "nvme0n1", "size": 512110190592, "type": "disk", '
    '"ro": false, "rm": false, "mountpoint": null, "children": ['
    '{"name": "nvme0n1p1", "size": 524288000, "mountpoint": "/boot/efi", "partn": 1}'
    "]}]}"
)
_VALID_BLKID = (
    '{"blockdevices": [{"name": "/dev/nvme0n1p1", "type": "vfat", "uuid": "AAAA-BBBB", '
    '"partuuid": "11111111-1111-1111-1111-111111111111", '
    '"parttype": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"}]}'
)
_VALID_FINDMNT = (
    '{"filesystems": [{"target": "/boot/efi", "source": "/dev/nvme0n1p1", '
    '"fstype": "vfat", "options": "rw,relatime"}]}'
)
_VALID_MOKUTIL = "SecureBoot enabled\nSetupMode disabled\n"


def _make_result(*, stdout: str = "", stderr: str = "", exit_code: int = 0) -> FakeCommandResult:
    now = datetime.now(tz=UTC)
    return FakeCommandResult(
        command=("tool",),
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration=0.1,
        started_at=now,
        finished_at=now,
    )


def _fully_successful_runner() -> FakeCommandRunner:
    return FakeCommandRunner(
        results={
            "efibootmgr": _make_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": _make_result(stdout=_VALID_LSBLK),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
            "mokutil": _make_result(stdout=_VALID_MOKUTIL),
        }
    )


def _build_adapters(runner: FakeCommandRunner) -> HostDiscoveryAdapters:
    """Bind the three real, implemented adapters to ``runner`` exactly
    the way ``bcs.app.main()``'s composition root does - same
    ``functools.partial`` shape, same shared runner instance, same
    direct references for the already-zero-argument collectors.
    """
    return HostDiscoveryAdapters(
        efi=functools.partial(read_firmware_boot_configuration, runner=runner),
        storage=functools.partial(read_storage_topology, runner=runner),
        secure_boot=functools.partial(read_secure_boot_status, runner=runner),
        network=collectors.collect_network,
        cpu=collectors.collect_cpu,
        memory=collectors.collect_memory,
    )


# ---------------------------------------------------------------------------
# Full pipeline, success path
# ---------------------------------------------------------------------------


def test_full_pipeline_success_populates_every_wired_domain_exactly_once() -> None:
    runner = _fully_successful_runner()
    orchestrator = HostDiscoveryOrchestrator(_build_adapters(runner))

    snapshot = orchestrator.discover()

    assert isinstance(snapshot, HostDiscoverySnapshot)
    assert isinstance(snapshot.firmware_boot_configuration, FirmwareBootConfiguration)
    assert snapshot.firmware_boot_configuration.current_boot_number == "0000"
    assert isinstance(snapshot.storage_topology, StorageConfiguration)
    assert isinstance(snapshot.secure_boot, SecureBootStatus)
    assert snapshot.secure_boot.state == SecureBootState.ENABLED
    assert snapshot.secure_boot.setup_mode is False
    # network/cpu/memory come from the real, unfaked collectors - stdlib-only,
    # degrade gracefully cross-platform, never raise.
    assert snapshot.cpu is not None
    assert snapshot.memory is not None
    assert isinstance(snapshot.network, tuple)
    # filesystem/tpm: genuinely unset slots, not a failure.
    assert snapshot.filesystem is None
    assert snapshot.tpm is None
    assert snapshot.caveats == ()

    # Every tool-based adapter invoked exactly once - one CommandRunner.run()
    # call per tool, no retries, no duplicate invocation.
    tools_called = [call["command"][0] for call in runner.calls]
    assert sorted(tools_called) == ["blkid", "efibootmgr", "findmnt", "lsblk", "mokutil"]
    assert len(tools_called) == len(set(tools_called)) == 5


def test_full_pipeline_calls_share_the_locale_forced_environment() -> None:
    """Every tool-based adapter forces LANG=C/LC_ALL=C independently -
    proving the shared runner sees a consistently-built environment from
    all three adapters, not just one.
    """
    runner = _fully_successful_runner()
    HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert len(runner.calls) == 5
    for call in runner.calls:
        assert call["env"]["LANG"] == "C"
        assert call["env"]["LC_ALL"] == "C"
        assert call["check"] is False


# ---------------------------------------------------------------------------
# Full pipeline, partial failure: caveats generated exactly per ADR-0011
# ---------------------------------------------------------------------------


def test_one_adapter_failing_isolates_into_one_caveat_others_unaffected() -> None:
    """A CommandNotFoundError from mokutil (a PlatformError subclass,
    raised by CommandRunner itself, never wrapped by the adapter) is
    isolated into exactly one caveats entry - efi/storage still succeed,
    network/cpu/memory still run afterward.
    """
    runner = FakeCommandRunner(
        results={
            "efibootmgr": _make_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": _make_result(stdout=_VALID_LSBLK),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
        },
        not_found_tools=frozenset({"mokutil"}),
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None
    assert snapshot.secure_boot is None
    assert snapshot.cpu is not None
    assert snapshot.memory is not None

    assert len(snapshot.caveats) == 1
    # Exact ADR-0011 format: "{domain}: {ExceptionType}: {message}".
    assert snapshot.caveats[0] == "secure_boot: CommandNotFoundError: mokutil not found"


def test_unavailable_stderr_produces_the_domain_specific_exception_in_the_caveat() -> None:
    """A recognisable "environment cannot provide this data" stderr
    (rather than a missing executable) maps to each adapter's own
    Unavailable subclass - proving the caveat records the *actual*
    exception type raised, not a generic one.
    """
    runner = FakeCommandRunner(
        results={
            "efibootmgr": _make_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": _make_result(stdout=_VALID_LSBLK),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
            "mokutil": _make_result(stderr="Permission denied", exit_code=1),
        },
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.secure_boot is None
    assert len(snapshot.caveats) == 1
    assert snapshot.caveats[0].startswith("secure_boot: SecureBootUnavailableError:")


def test_multiple_independent_failures_each_get_their_own_caveat_in_order() -> None:
    """efi and secure_boot both fail (storage succeeds); both caveats
    are recorded, in the fixed field order (efi before secure_boot),
    and each attempt is still made independently - one failing does not
    stop the others.
    """
    runner = FakeCommandRunner(
        results={
            "lsblk": _make_result(stdout=_VALID_LSBLK),
            "blkid": _make_result(stdout=_VALID_BLKID),
            "findmnt": _make_result(stdout=_VALID_FINDMNT),
        },
        not_found_tools=frozenset({"efibootmgr", "mokutil"}),
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.firmware_boot_configuration is None
    assert snapshot.storage_topology is not None
    assert snapshot.secure_boot is None
    assert len(snapshot.caveats) == 2
    assert snapshot.caveats[0].startswith("efi: CommandNotFoundError:")
    assert snapshot.caveats[1].startswith("secure_boot: CommandNotFoundError:")

    tools_called = [call["command"][0] for call in runner.calls]
    assert sorted(tools_called) == ["blkid", "efibootmgr", "findmnt", "lsblk", "mokutil"]


# ---------------------------------------------------------------------------
# Full pipeline, starting from the real composition root (bcs.app.main())
# ---------------------------------------------------------------------------


def test_pipeline_built_by_the_real_composition_root_works_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The most complete end-to-end proof: patch only the one sanctioned
    seam (SubprocessCommandRunner, per docs/PLATFORM_LAYER.md#design-
    principles item 5), invoke a real CLI command through bcs.app.main()
    unmodified, capture the exact HostDiscoveryOrchestrator instance the
    composition root built, and call discover() on it directly - proving
    the assembled pipeline (composition root -> RuntimeContext ->
    HostDiscoveryAdapters -> HostDiscoveryOrchestrator) is wired
    correctly end to end, not just piece by piece.
    """
    runner = CliRunner()
    fake_command_runner = _fully_successful_runner()
    captured: dict[str, object] = {}
    real_runtime_context = app_module.RuntimeContext

    def _capturing_runtime_context(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["host_discovery_orchestrator"] = kwargs["host_discovery_orchestrator"]
        return real_runtime_context(*args, **kwargs)

    monkeypatch.setattr(app_module, "SubprocessCommandRunner", lambda: fake_command_runner)
    monkeypatch.setattr(app_module, "RuntimeContext", _capturing_runtime_context)

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0

    orchestrator = captured["host_discovery_orchestrator"]
    assert isinstance(orchestrator, HostDiscoveryOrchestrator)

    snapshot = orchestrator.discover()

    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None
    assert isinstance(snapshot.secure_boot, SecureBootStatus)
    assert snapshot.secure_boot.state == SecureBootState.ENABLED
    assert snapshot.caveats == ()

    tools_called = [call["command"][0] for call in fake_command_runner.calls]
    assert sorted(tools_called) == ["blkid", "efibootmgr", "findmnt", "lsblk", "mokutil"]
    assert len(tools_called) == len(set(tools_called)) == 5


def test_discover_called_twice_re_invokes_every_real_adapter_a_second_time() -> None:
    """Not a violation of "at most once per bcs invocation" - each
    individual discover() call is a fresh, independent sweep, matching
    HostDiscoveryOrchestrator's own documented contract.
    """
    runner = _fully_successful_runner()
    orchestrator = HostDiscoveryOrchestrator(_build_adapters(runner))

    orchestrator.discover()
    orchestrator.discover()

    tools_called = [call["command"][0] for call in runner.calls]
    assert len(tools_called) == 10
    assert tools_called.count("mokutil") == 2
    assert tools_called.count("efibootmgr") == 2
