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

import pytest
from tests.fake_command_runner import FakeCommandRunner, build_command_result
from typer.testing import CliRunner

from bcs import app as app_module
from bcs.app import app
from bcs.inventory import collectors
from bcs.inventory.discovery.models import HostDiscoveryAdapters, HostDiscoverySnapshot
from bcs.inventory.discovery.orchestrator import HostDiscoveryOrchestrator
from bcs.platform.adapters.efi.adapter import read_firmware_boot_configuration
from bcs.platform.adapters.efi.models import FirmwareBootConfiguration
from bcs.platform.adapters.filesystem.adapter import read_filesystem_usage
from bcs.platform.adapters.network.adapter import read_network_interfaces
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.secureboot.adapter import read_secure_boot_status
from bcs.platform.adapters.secureboot.models import SecureBootState, SecureBootStatus
from bcs.platform.adapters.storage.adapter import read_storage_topology
from bcs.platform.adapters.storage.models import StorageConfiguration

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
# Column order matches the adapter's real invocation exactly:
# source, fstype, itotal, iused, iavail, size, used, avail, target.
# '-' inode fields mirror real df behaviour for vfat (no fixed inode
# allocation) - see docs/FILESYSTEM_ADAPTER.md#parser-architecture.
_VALID_DF = "/dev/nvme0n1p1 vfat - - - 524288000 104857600 419430400 /boot/efi\n"
_VALID_IP = (
    '[{"ifname": "lo", "flags": ["LOOPBACK", "UP", "LOWER_UP"], '
    '"address": "00:00:00:00:00:00", '
    '"addr_info": [{"family": "inet", "local": "127.0.0.1"}]}, '
    '{"ifname": "eth0", "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"], '
    '"address": "52:54:00:12:34:56", '
    '"addr_info": [{"family": "inet", "local": "192.0.2.10"}]}]'
)


def _fully_successful_runner() -> FakeCommandRunner:
    return FakeCommandRunner(
        results={
            "efibootmgr": build_command_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "mokutil": build_command_result(stdout=_VALID_MOKUTIL),
            "df": build_command_result(stdout=_VALID_DF),
            "ip": build_command_result(stdout=_VALID_IP),
        }
    )


def _build_adapters(runner: FakeCommandRunner) -> HostDiscoveryAdapters:
    """Bind the real, implemented adapters to ``runner`` exactly the way
    ``bcs.app.main()``'s composition root does - same
    ``functools.partial`` shape, same shared runner instance, same
    direct references for the already-zero-argument collectors
    (``cpu``/``memory``, the only two domains with no adapter).
    """
    return HostDiscoveryAdapters(
        efi=functools.partial(read_firmware_boot_configuration, runner=runner),
        storage=functools.partial(read_storage_topology, runner=runner),
        secure_boot=functools.partial(read_secure_boot_status, runner=runner),
        filesystem=functools.partial(read_filesystem_usage, runner=runner),
        network=functools.partial(read_network_interfaces, runner=runner),
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
    # cpu/memory come from the real, unfaked collectors - stdlib-only,
    # degrade gracefully cross-platform, never raise.
    assert snapshot.cpu is not None
    assert snapshot.memory is not None
    assert isinstance(snapshot.network, NetworkInterfaceStatus)
    assert [iface.name for iface in snapshot.network.interfaces] == ["lo", "eth0"]
    assert snapshot.network.interfaces[1].ip_addresses == ("192.0.2.10",)
    # tpm: genuinely unset slot, not a failure.
    assert snapshot.tpm is None
    assert snapshot.caveats == ()

    # Every tool-based adapter invoked exactly once - one CommandRunner.run()
    # call per tool, no retries, no duplicate invocation.
    tools_called = [call["command"][0] for call in runner.calls]
    assert sorted(tools_called) == [
        "blkid",
        "df",
        "efibootmgr",
        "findmnt",
        "ip",
        "lsblk",
        "mokutil",
    ]
    assert len(tools_called) == len(set(tools_called)) == 7


def test_full_pipeline_calls_share_the_locale_forced_environment() -> None:
    """Every tool-based adapter forces LANG=C/LC_ALL=C independently -
    proving the shared runner sees a consistently-built environment from
    all adapters, not just one.
    """
    runner = _fully_successful_runner()
    HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert len(runner.calls) == 7
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
            "efibootmgr": build_command_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "df": build_command_result(stdout=_VALID_DF),
            "ip": build_command_result(stdout=_VALID_IP),
        },
        not_found_tools=frozenset({"mokutil"}),
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None
    assert snapshot.secure_boot is None
    assert snapshot.filesystem is not None
    assert snapshot.network is not None
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
            "efibootmgr": build_command_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "mokutil": build_command_result(stderr="Permission denied", exit_code=1),
            "df": build_command_result(stdout=_VALID_DF),
            "ip": build_command_result(stdout=_VALID_IP),
        },
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.secure_boot is None
    assert snapshot.filesystem is not None
    assert len(snapshot.caveats) == 1
    assert snapshot.caveats[0].startswith("secure_boot: SecureBootUnavailableError:")


def test_filesystem_failure_isolates_into_its_own_caveat() -> None:
    """A CommandNotFoundError from df is isolated into exactly one
    caveats entry under the 'filesystem' domain name - efi/storage/
    secure_boot still succeed, mirroring the mokutil-specific case
    above but for the fourth wired adapter.
    """
    runner = FakeCommandRunner(
        results={
            "efibootmgr": build_command_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "mokutil": build_command_result(stdout=_VALID_MOKUTIL),
            "ip": build_command_result(stdout=_VALID_IP),
        },
        not_found_tools=frozenset({"df"}),
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.firmware_boot_configuration is not None
    assert snapshot.storage_topology is not None
    assert snapshot.secure_boot is not None
    assert snapshot.filesystem is None

    assert len(snapshot.caveats) == 1
    assert snapshot.caveats[0] == "filesystem: CommandNotFoundError: df not found"


def test_filesystem_partial_failure_is_not_a_caveat_but_raw_stderr_carries_it() -> None:
    """The Filesystem Adapter's own unique judgment call, visible at the
    full-pipeline level: a non-zero df exit that still yields at least
    one parsed filesystem is *not* isolated into a caveats entry (the
    orchestrator only ever sees a raised PlatformError, and none was
    raised here) - the failure signal instead survives on
    FilesystemUsageReport.raw_stderr, one layer below where caveats
    operates. See docs/FILESYSTEM_ADAPTER.md#relationship-to-the-host-
    discovery-orchestrators-caveats-model.
    """
    runner = FakeCommandRunner(
        results={
            "efibootmgr": build_command_result(stdout=_VALID_EFIBOOTMGR),
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "mokutil": build_command_result(stdout=_VALID_MOKUTIL),
            "df": build_command_result(
                stdout=_VALID_DF,
                stderr="df: '/mnt/stale': Stale file handle",
                exit_code=1,
            ),
            "ip": build_command_result(stdout=_VALID_IP),
        },
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.filesystem is not None
    assert len(snapshot.filesystem.filesystems) == 1
    assert snapshot.filesystem.raw_stderr == "df: '/mnt/stale': Stale file handle"
    assert snapshot.caveats == ()


def test_multiple_independent_failures_each_get_their_own_caveat_in_order() -> None:
    """efi and secure_boot both fail (storage succeeds); both caveats
    are recorded, in the fixed field order (efi before secure_boot),
    and each attempt is still made independently - one failing does not
    stop the others.
    """
    runner = FakeCommandRunner(
        results={
            "lsblk": build_command_result(stdout=_VALID_LSBLK),
            "blkid": build_command_result(stdout=_VALID_BLKID),
            "findmnt": build_command_result(stdout=_VALID_FINDMNT),
            "df": build_command_result(stdout=_VALID_DF),
            "ip": build_command_result(stdout=_VALID_IP),
        },
        not_found_tools=frozenset({"efibootmgr", "mokutil"}),
    )
    snapshot = HostDiscoveryOrchestrator(_build_adapters(runner)).discover()

    assert snapshot.firmware_boot_configuration is None
    assert snapshot.storage_topology is not None
    assert snapshot.secure_boot is None
    assert snapshot.filesystem is not None
    assert len(snapshot.caveats) == 2
    assert snapshot.caveats[0].startswith("efi: CommandNotFoundError:")
    assert snapshot.caveats[1].startswith("secure_boot: CommandNotFoundError:")

    tools_called = [call["command"][0] for call in runner.calls]
    assert sorted(tools_called) == [
        "blkid",
        "df",
        "efibootmgr",
        "findmnt",
        "ip",
        "lsblk",
        "mokutil",
    ]


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
    assert snapshot.filesystem is not None
    assert isinstance(snapshot.network, NetworkInterfaceStatus)
    assert snapshot.caveats == ()

    tools_called = [call["command"][0] for call in fake_command_runner.calls]
    assert sorted(tools_called) == [
        "blkid",
        "df",
        "efibootmgr",
        "findmnt",
        "ip",
        "lsblk",
        "mokutil",
    ]
    assert len(tools_called) == len(set(tools_called)) == 7


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
    assert len(tools_called) == 14
    assert tools_called.count("mokutil") == 2
    assert tools_called.count("efibootmgr") == 2
    assert tools_called.count("df") == 2
    assert tools_called.count("ip") == 2
