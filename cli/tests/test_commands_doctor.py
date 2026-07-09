from __future__ import annotations

from pathlib import Path

import pytest

from bcs.commands import doctor as doctor_module
from bcs.commands.doctor import run_doctor
from bcs.errors import PreconditionFailedError, UsageError
from bcs.inventory.models import (
    EfiSystemPartition,
    FirmwareInfo,
    NetworkInterface,
    SecureBootState,
    StorageDevice,
    ToolStatus,
    UsbStorageDevice,
)
from bcs.output import OutputFormat
from bcs.platform.adapters.network.errors import NetworkUnavailableError
from bcs.platform.adapters.network.models import (
    NetworkInterface as PlatformNetworkInterface,
)
from bcs.platform.adapters.network.models import NetworkInterfaceStatus
from bcs.platform.adapters.secureboot.errors import (
    SecureBootParseError,
    SecureBootUnavailableError,
)
from bcs.platform.adapters.secureboot.models import SecureBootState as PlatformSecureBootState
from bcs.platform.adapters.secureboot.models import SecureBootStatus
from bcs.platform.adapters.storage.errors import StorageUnavailableError
from bcs.platform.adapters.storage.models import BlockDevice, StorageConfiguration
from bcs.platform.errors import CommandNotFoundError


def _make_block_device(**overrides: object) -> BlockDevice:
    """Build a minimal, valid ``BlockDevice`` for storage-adapter-path
    tests, mirroring ``test_inventory_service.py``'s own helper.
    """
    defaults: dict[str, object] = {
        "name": "sda",
        "path": "/dev/sda",
        "deviceType": "disk",
        "isRemovable": False,
        "isReadOnly": False,
        "isNvme": False,
    }
    defaults.update(overrides)
    return BlockDevice(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Individual check-evaluation logic, exercised directly against a
# monkeypatched Host Inventory collector - these are the tests that were
# missing before doctor.py was refactored to build on bcs.inventory:
# every other test in this file monkeypatches the whole _ALL_CHECKS
# registry and never runs the real evaluation logic below.
# ---------------------------------------------------------------------------


def test_check_firmware_ok_when_uefi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.ENABLED),
    )
    result = doctor_module._check_firmware()
    assert result.status == "ok"


def test_check_firmware_fail_when_not_uefi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=False, secureBoot=SecureBootState.UNSUPPORTED),
    )
    result = doctor_module._check_firmware()
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# _check_secure_boot (Beta M4) - a direct call to the Secure Boot Platform
# Adapter via runtime.command_runner, never HostDiscoveryOrchestrator.discover()
# (ADR-0011's own rejection of a full-sweep orchestrator for bcs doctor - see
# _check_secure_boot's own docstring). read_secure_boot_status is monkeypatched
# directly, mirroring how every other check here monkeypatches its own single
# collector - no real/fake CommandRunner needed at this level.
# ---------------------------------------------------------------------------


def test_check_secure_boot_skip_when_not_uefi(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=False, secureBoot=SecureBootState.UNSUPPORTED),
    )

    def _must_not_be_called(runner: object) -> SecureBootStatus:
        raise AssertionError("read_secure_boot_status must not be called when not UEFI")

    monkeypatch.setattr(doctor_module, "read_secure_boot_status", _must_not_be_called)

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == "skip"


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [
        (PlatformSecureBootState.ENABLED, "ok"),
        (PlatformSecureBootState.DISABLED, "warn"),
    ],
)
def test_check_secure_boot_maps_enabled_and_disabled(
    make_runtime_context,
    monkeypatch: pytest.MonkeyPatch,
    state: PlatformSecureBootState,
    expected_status: str,
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )
    monkeypatch.setattr(
        doctor_module,
        "read_secure_boot_status",
        lambda _runner: SecureBootStatus(state=state, rawText=f"SecureBoot {state.value}\n"),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == expected_status


def test_check_secure_boot_warn_when_adapter_reports_unknown(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successfully-returned but indeterminate ``SecureBootStatus``
    (``state=UNKNOWN`` - never actually produced by the real parser
    today, but handled defensively) degrades to ``warn``, not a crash.
    """
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )
    monkeypatch.setattr(
        doctor_module,
        "read_secure_boot_status",
        lambda _runner: SecureBootStatus(state=PlatformSecureBootState.UNKNOWN, rawText=""),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == "warn"
    assert "unknown" in result.message


def test_check_secure_boot_warn_when_mokutil_not_found(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The adapter's own ``PlatformError`` subclasses (raised e.g. when
    ``mokutil`` is missing, as on the project's own VirtualBox E01
    environment) degrade to a non-crashing ``warn`` result - ``bcs
    doctor`` never crashes because one tool is absent.
    """
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )

    def _raise_not_found(runner: object) -> SecureBootStatus:
        raise CommandNotFoundError("mokutil not found", executable="mokutil")

    monkeypatch.setattr(doctor_module, "read_secure_boot_status", _raise_not_found)

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == "warn"
    assert "CommandNotFoundError" in result.message
    assert "mokutil not found" in result.message


def test_check_secure_boot_warn_when_unavailable(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )

    def _raise_unavailable(runner: object) -> SecureBootStatus:
        raise SecureBootUnavailableError("Secure Boot state is not available in this environment.")

    monkeypatch.setattr(doctor_module, "read_secure_boot_status", _raise_unavailable)

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == "warn"
    assert "SecureBootUnavailableError" in result.message


def test_check_secure_boot_warn_when_parse_error(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )

    def _raise_parse_error(runner: object) -> SecureBootStatus:
        raise SecureBootParseError("Failed to parse mokutil output: no recognized line", text="")

    monkeypatch.setattr(doctor_module, "read_secure_boot_status", _raise_parse_error)

    runtime = make_runtime_context()
    result = doctor_module._check_secure_boot(runtime)
    assert result.status == "warn"
    assert "SecureBootParseError" in result.message


def test_check_secure_boot_uses_runtime_command_runner(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact ``runtime.command_runner`` instance is passed through -
    not a second, independently constructed one - matching every other
    Platform Layer consumer's own DI discipline.
    """
    monkeypatch.setattr(
        doctor_module,
        "collect_firmware",
        lambda: FirmwareInfo(uefi=True, secureBoot=SecureBootState.UNKNOWN),
    )
    captured: dict[str, object] = {}

    def _capturing(runner: object) -> SecureBootStatus:
        captured["runner"] = runner
        return SecureBootStatus(
            state=PlatformSecureBootState.ENABLED, rawText="SecureBoot enabled\n"
        )

    monkeypatch.setattr(doctor_module, "read_secure_boot_status", _capturing)

    runtime = make_runtime_context()
    doctor_module._check_secure_boot(runtime)
    assert captured["runner"] is runtime.command_runner


# ---------------------------------------------------------------------------
# _check_storage (Host Discovery Orchestrator completion) - a direct call to
# the Storage Platform Adapter via runtime.command_runner, never
# HostDiscoveryOrchestrator.discover() (ADR-0011), mirroring
# _check_secure_boot's own pattern. Falls back to collect_storage() (unlike
# Secure Boot) since the legacy collector produces real, useful data.
# ---------------------------------------------------------------------------


def test_check_storage_ok_when_adapter_reports_disk(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    # If this were called, the test would see the collector-sourced NVMe
    # device below instead of the adapter-sourced SATA device - proving
    # it was *not*.
    monkeypatch.setattr(
        doctor_module,
        "collect_storage",
        lambda: [StorageDevice(name="collector-should-not-run", path="/dev/nvme9n9", isNvme=True)],
    )
    monkeypatch.setattr(
        doctor_module,
        "read_storage_topology",
        lambda _runner: StorageConfiguration(devices=(_make_block_device(name="sda"),)),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_storage(runtime)
    assert result.status == "ok"
    assert "sda" in result.message


def test_check_storage_filters_out_non_disk_devices(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Matches ``bcs.inventory.service._translate_storage_devices()``'s
    own scope - a loop/rom device must not make this check pass, so
    ``bcs doctor`` never disagrees with ``bcs inventory`` about which
    devices count as storage.
    """
    monkeypatch.setattr(doctor_module, "collect_storage", list)
    monkeypatch.setattr(
        doctor_module,
        "read_storage_topology",
        lambda _runner: StorageConfiguration(
            devices=(_make_block_device(name="loop0", deviceType="loop"),)
        ),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_storage(runtime)
    assert result.status == "fail"


def test_check_storage_falls_back_to_collector_when_adapter_unavailable(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_storage",
        lambda: [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
    )

    def _raise_not_found(runner: object) -> StorageConfiguration:
        raise CommandNotFoundError("lsblk not found", executable="lsblk")

    monkeypatch.setattr(doctor_module, "read_storage_topology", _raise_not_found)

    runtime = make_runtime_context()
    result = doctor_module._check_storage(runtime)
    assert result.status == "ok"
    assert "nvme0n1" in result.message


def test_check_storage_falls_back_when_adapter_unavailable_error(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_storage",
        lambda: [StorageDevice(name="nvme0n1", path="/dev/nvme0n1", isNvme=True)],
    )

    def _raise_unavailable(runner: object) -> StorageConfiguration:
        raise StorageUnavailableError("lsblk could not provide storage data in this environment.")

    monkeypatch.setattr(doctor_module, "read_storage_topology", _raise_unavailable)

    runtime = make_runtime_context()
    result = doctor_module._check_storage(runtime)
    assert result.status == "ok"
    assert "nvme0n1" in result.message


def test_check_storage_fail_when_none_present(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor_module, "collect_storage", list)

    def _raise_not_found(runner: object) -> StorageConfiguration:
        raise CommandNotFoundError("lsblk not found", executable="lsblk")

    monkeypatch.setattr(doctor_module, "read_storage_topology", _raise_not_found)

    runtime = make_runtime_context()
    result = doctor_module._check_storage(runtime)
    assert result.status == "fail"


def test_check_storage_uses_runtime_command_runner(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _capturing(runner: object) -> StorageConfiguration:
        captured["runner"] = runner
        return StorageConfiguration()

    monkeypatch.setattr(doctor_module, "read_storage_topology", _capturing)

    runtime = make_runtime_context()
    doctor_module._check_storage(runtime)
    assert captured["runner"] is runtime.command_runner


def test_check_esp_fail_when_not_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=False, mounted=False),
    )
    result = doctor_module._check_esp()
    assert result.status == "fail"


def test_check_esp_warn_when_present_but_not_mounted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mounted=False),
    )
    result = doctor_module._check_esp()
    assert result.status == "warn"


def test_check_esp_ok_when_mounted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_efi_system_partition",
        lambda: EfiSystemPartition(present=True, mountPoint="/boot/efi", mounted=True),
    )
    result = doctor_module._check_esp()
    assert result.status == "ok"
    assert "/boot/efi" in result.message


def test_check_usb_storage_skip_when_none_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor_module, "collect_usb_storage", list)
    result = doctor_module._check_usb_storage()
    assert result.status == "skip"


def test_check_usb_storage_ok_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_usb_storage",
        lambda: [UsbStorageDevice(name="sdb", path="/dev/sdb", mounted=False)],
    )
    result = doctor_module._check_usb_storage()
    assert result.status == "ok"
    assert "sdb" in result.message


# ---------------------------------------------------------------------------
# _check_network (Host Discovery Orchestrator completion) - a direct call to
# the Network Platform Adapter via runtime.command_runner, never
# HostDiscoveryOrchestrator.discover() (ADR-0011), mirroring
# _check_secure_boot's/_check_storage's own pattern. Falls back to
# collect_network() on any PlatformError.
# ---------------------------------------------------------------------------


def _make_network_interface_status(
    *, interfaces: tuple[PlatformNetworkInterface, ...]
) -> NetworkInterfaceStatus:
    return NetworkInterfaceStatus(interfaces=interfaces, rawText="")


def test_check_network_skip_when_only_loopback(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor_module, "collect_network", list)
    monkeypatch.setattr(
        doctor_module,
        "read_network_interfaces",
        lambda _runner: _make_network_interface_status(
            interfaces=(PlatformNetworkInterface(name="lo", isUp=True, isLoopback=True),)
        ),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_network(runtime)
    assert result.status == "skip"


def test_check_network_ok_when_adapter_reports_interface_up(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    # If this were called, the test would see the collector-sourced
    # interface below instead of the adapter-sourced one - proving it
    # was *not*.
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="collector-should-not-run", isUp=True, isLoopback=False)],
    )
    monkeypatch.setattr(
        doctor_module,
        "read_network_interfaces",
        lambda _runner: _make_network_interface_status(
            interfaces=(PlatformNetworkInterface(name="eth0", isUp=True, isLoopback=False),)
        ),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_network(runtime)
    assert result.status == "ok"
    assert "eth0" in result.message


def test_check_network_warn_when_interface_present_but_down(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor_module, "collect_network", list)
    monkeypatch.setattr(
        doctor_module,
        "read_network_interfaces",
        lambda _runner: _make_network_interface_status(
            interfaces=(PlatformNetworkInterface(name="eth0", isUp=False, isLoopback=False),)
        ),
    )

    runtime = make_runtime_context()
    result = doctor_module._check_network(runtime)
    assert result.status == "warn"


def test_check_network_falls_back_to_collector_when_adapter_unavailable(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=True, isLoopback=False)],
    )

    def _raise_not_found(runner: object) -> NetworkInterfaceStatus:
        raise CommandNotFoundError("ip not found", executable="ip")

    monkeypatch.setattr(doctor_module, "read_network_interfaces", _raise_not_found)

    runtime = make_runtime_context()
    result = doctor_module._check_network(runtime)
    assert result.status == "ok"
    assert "eth0" in result.message


def test_check_network_falls_back_when_adapter_unavailable_error(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_network",
        lambda: [NetworkInterface(name="eth0", isUp=True, isLoopback=False)],
    )

    def _raise_unavailable(runner: object) -> NetworkInterfaceStatus:
        raise NetworkUnavailableError(
            "Network interface data is not available in this environment."
        )

    monkeypatch.setattr(doctor_module, "read_network_interfaces", _raise_unavailable)

    runtime = make_runtime_context()
    result = doctor_module._check_network(runtime)
    assert result.status == "ok"
    assert "eth0" in result.message


def test_check_network_uses_runtime_command_runner(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _capturing(runner: object) -> NetworkInterfaceStatus:
        captured["runner"] = runner
        return _make_network_interface_status(interfaces=())

    monkeypatch.setattr(doctor_module, "read_network_interfaces", _capturing)

    runtime = make_runtime_context()
    doctor_module._check_network(runtime)
    assert captured["runner"] is runtime.command_runner


def test_check_tooling_ok_when_all_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=True, path="/usr/bin/clonezilla")],
    )
    result = doctor_module._check_tooling()
    assert result.status == "ok"


def test_check_tooling_fail_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor_module,
        "collect_tooling",
        lambda: [ToolStatus(name="clonezilla", found=False, path=None)],
    )
    result = doctor_module._check_tooling()
    assert result.status == "fail"
    assert "clonezilla" in result.message


def test_unknown_check_name_raises_usage_error(make_runtime_context) -> None:
    runtime = make_runtime_context()
    with pytest.raises(UsageError):
        run_doctor(runtime, checks=["not-a-real-check"])


def test_all_checks_ok_returns_zero(make_runtime_context, monkeypatch: pytest.MonkeyPatch) -> None:
    def _always_ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "all good")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _always_ok)

    runtime = make_runtime_context()
    assert run_doctor(runtime) == 0


def test_any_failing_check_raises_precondition_failed(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    def _fail(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "fail", "broken")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)
    monkeypatch.setitem(doctor_module._ALL_CHECKS, "tooling", _fail)

    runtime = make_runtime_context()
    with pytest.raises(PreconditionFailedError):
        run_doctor(runtime)


def test_warnings_alone_do_not_fail_without_strict(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    def _warn(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "warn", "hmm")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)
    monkeypatch.setitem(doctor_module._ALL_CHECKS, "permissions", _warn)

    runtime = make_runtime_context()
    assert run_doctor(runtime) == 0
    with pytest.raises(PreconditionFailedError):
        run_doctor(runtime, strict=True)


def test_json_output_shape(make_runtime_context, monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(_runtime: object) -> doctor_module.CheckResult:
        return doctor_module.CheckResult("fake", "ok", "fine")

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _ok)

    runtime = make_runtime_context(output=OutputFormat.JSON)
    run_doctor(runtime)
    import json

    payload = json.loads(runtime.console.file.getvalue())
    assert payload["schemaVersion"] == "bcs-cli/v1alpha1"
    assert payload["summary"]["ok"] == len(doctor_module._ALL_CHECKS)


def test_config_check_warns_when_no_config_resolved(make_runtime_context) -> None:
    runtime = make_runtime_context()
    result = doctor_module._check_config(runtime)
    assert result.status == "warn"


def test_config_check_ok_for_valid_config(make_runtime_context, valid_config_path: Path) -> None:
    runtime = make_runtime_context(config_path=valid_config_path)
    result = doctor_module._check_config(runtime)
    assert result.status == "ok"


def test_selected_checks_limits_which_run(
    make_runtime_context, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def _tracker(name: str):
        def _inner(_runtime: object) -> doctor_module.CheckResult:
            calls.append(name)
            return doctor_module.CheckResult(name, "ok", "fine")

        return _inner

    for name in doctor_module._ALL_CHECKS:
        monkeypatch.setitem(doctor_module._ALL_CHECKS, name, _tracker(name))

    runtime = make_runtime_context()
    run_doctor(runtime, checks=["firmware", "storage"])
    assert calls == ["firmware", "storage"]
